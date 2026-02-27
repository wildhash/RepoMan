"""RepoMan CLI entry point."""

from __future__ import annotations

import asyncio

import typer
import uvicorn
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from repoman.config import Settings
from repoman.utils.exceptions import reraise_if_fatal
from repoman.utils.logging import configure_logging

app = typer.Typer(name="repoman", help="Multi-model agentic repository transformation system")
es_app = typer.Typer(name="es", help="Elasticsearch indexing and search utilities")
app.add_typer(es_app)
console = Console()


@app.command()
def transform(
    repo_url: str = typer.Argument(..., help="Git repository URL to transform"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
) -> None:
    """Run the full 7-phase transformation pipeline on a repository."""
    configure_logging("DEBUG" if verbose else "INFO")
    settings = Settings()

    async def _run() -> None:
        from repoman.core.pipeline import Pipeline

        pipeline = Pipeline(settings)
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            task = progress.add_task("Transforming repository...", total=None)
            result = await pipeline.run(repo_url)
            progress.update(task, description="Done!")

        # Results table
        table = Table(title="Transformation Results", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        table.add_row("Status", result.status.value)
        table.add_row("Before Score", f"{result.before_score:.1f}")
        table.add_row("After Score", f"{result.after_score:.1f}")
        table.add_row("Issues Fixed", str(result.issues_fixed))
        table.add_row("Duration", f"{result.total_duration_seconds:.1f}s")
        table.add_row("Consensus", "Achieved" if (result.consensus and result.consensus.achieved) else "Forced")
        console.print(table)

        if result.error:
            console.print(Panel(f"[red]Error: {result.error}[/red]", title="Pipeline Error"))

    asyncio.run(_run())


@app.command()
def audit(
    repo_url: str = typer.Argument(..., help="Git repository URL to audit"),
) -> None:
    """Run phases 1-2 only: ingest and audit the repository."""
    configure_logging()
    settings = Settings()

    async def _run() -> None:
        from repoman.agents.architect import ArchitectAgent
        from repoman.agents.auditor import AuditorAgent
        from repoman.agents.builder import BuilderAgent
        from repoman.analysis.ingestion import RepoIngester
        from repoman.models.router import ModelRouter

        router = ModelRouter(settings)
        ingester = RepoIngester(settings)

        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            task = progress.add_task("Cloning and analysing...", total=None)
            snapshot = await ingester.ingest(repo_url)
            progress.update(task, description="Running audits...")

            reports = await asyncio.gather(
                ArchitectAgent(router).audit(snapshot),
                AuditorAgent(router).audit(snapshot),
                BuilderAgent(router).audit(snapshot),
                return_exceptions=True,
            )
            progress.update(task, description="Done!")

        for report in reports:
            if isinstance(report, BaseException):
                reraise_if_fatal(report)
                console.print(f"[red]Audit failed: {report}[/red]")
                continue
            console.print(Panel(
                f"Critical: {len(report.critical_issues)} | Major: {len(report.major_issues)} | Score: {report.overall_score:.1f}\n\n{report.executive_summary}",
                title=f"[bold]{report.agent_name}[/bold] ({report.agent_role})",
            ))

    asyncio.run(_run())


@app.command()
def serve(
    host: str = typer.Option(None, "--host", help="Override API host"),
    port: int = typer.Option(None, "--port", help="Override API port"),
) -> None:
    """Start the FastAPI server with uvicorn."""
    configure_logging()
    settings = Settings()
    from repoman.api.app import create_app

    api_host = host or settings.api_host
    api_port = port or settings.api_port
    uvicorn.run(create_app(settings), host=api_host, port=api_port)


@es_app.command("setup")
def es_setup() -> None:
    """Create Elasticsearch indices and templates (idempotent)."""
    configure_logging()
    settings = Settings()

    async def _run() -> None:
        from repoman.elasticsearch.client import create_es_client
        from repoman.elasticsearch.index_management import ensure_indices

        es = create_es_client(settings)
        try:
            await ensure_indices(es, vector_dims=settings.embedding_dims)
            console.print("[green]Elasticsearch indices ensured.[/green]")
        finally:
            await es.close()

    asyncio.run(_run())


@es_app.command("ingest")
def es_ingest(
    input_value: str = typer.Argument(..., help="Repo URL, owner/repo, user/org, or GitHub search query"),
    limit: int = typer.Option(20, "--limit", help="Max repos for user/org/search inputs"),
    issues_limit: int | None = typer.Option(
        None,
        "--issues-limit",
        min=1,
        help="Max issues/PRs to ingest per repo",
    ),
    analyze: bool = typer.Option(False, "--analyze", help="Run analysis after ingestion"),
) -> None:
    """Ingest GitHub data into Elasticsearch."""
    configure_logging()
    settings = Settings()

    async def _run() -> None:
        from repoman.elasticsearch.client import create_es_client
        from repoman.elasticsearch.index_management import ensure_indices
        from repoman.elasticsearch.ingestion import ElasticsearchIngestionService

        es = create_es_client(settings)
        service = ElasticsearchIngestionService(settings, es=es)
        try:
            await ensure_indices(es, vector_dims=settings.embedding_dims)
            repos = await service.ingest_input(input_value, limit=limit)
            if not repos:
                console.print("[yellow]No repositories found.[/yellow]")
                return

            for repo_full_name in repos:
                result = await service.ingest_repo(repo_full_name, issues_limit=issues_limit)
                console.print(
                    f"[cyan]{repo_full_name}[/cyan] indexed: issues={result['issues_indexed']} health={result['health_score']}"
                )
                if analyze:
                    analysis_doc = await service.analyze_repo(repo_full_name)
                    console.print(
                        f"  analysis indexed: stale_issues={analysis_doc.get('stale_issues_count')} duplicates={len(analysis_doc.get('duplicate_issue_groups') or [])}"
                    )
        finally:
            await service.aclose()
            await es.close()

    asyncio.run(_run())


@es_app.command("analyze")
def es_analyze(
    repo_full_name: str = typer.Argument(..., help="owner/repo"),
) -> None:
    """Run analysis for a repo already ingested into Elasticsearch."""
    configure_logging()
    settings = Settings()

    async def _run() -> None:
        from repoman.elasticsearch.client import create_es_client
        from repoman.elasticsearch.ingestion import ElasticsearchIngestionService

        es = create_es_client(settings)
        service = ElasticsearchIngestionService(settings, es=es)
        try:
            analysis_doc = await service.analyze_repo(repo_full_name)
            console.print(
                f"[green]{repo_full_name}[/green] analysis indexed: missing={analysis_doc.get('missing_elements')} stale_issues={analysis_doc.get('stale_issues_count')}"
            )
        finally:
            await service.aclose()
            await es.close()

    asyncio.run(_run())


if __name__ == "__main__":
    app()
