"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from repoman.config import Settings
from repoman.core.state import (
    AgentAuditReport,
    Issue,
    RepoSnapshot,
)


@pytest.fixture
def settings() -> Settings:
    """Return default test settings."""
    return Settings(
        anthropic_api_key="test-key",
        openai_api_key="test-key",
        learning_enabled=False,
        sandbox_enabled=False,
    )


@pytest.fixture
def sample_snapshot() -> RepoSnapshot:
    """Return a minimal RepoSnapshot for testing."""
    return RepoSnapshot(
        url="https://github.com/test/repo",
        name="repo",
        clone_path="/tmp/test-repo",
        primary_language="Python",
        languages={"Python": 0.9, "YAML": 0.1},
        frameworks=["FastAPI"],
        has_readme=True,
        has_tests=False,
        has_ci=False,
        has_dockerfile=False,
        has_license=True,
        total_files=10,
        total_lines=500,
    )


@pytest.fixture
def sample_issue() -> Issue:
    """Return a sample Issue."""
    return Issue(
        severity="critical",
        category="security",
        file_path="app.py",
        line_number=42,
        description="SQL injection vulnerability",
        suggested_fix="Use parameterised queries",
    )


@pytest.fixture
def sample_audit_report(sample_issue: Issue) -> AgentAuditReport:
    """Return a sample AgentAuditReport."""
    return AgentAuditReport(
        agent_name="Architect",
        agent_role="architect",
        model_used="claude-sonnet-4-20250514",
        critical_issues=[sample_issue],
        scores={
            "architecture": 6.0,
            "code_quality": 5.0,
            "test_coverage": 3.0,
            "security": 4.0,
            "documentation": 7.0,
            "performance": 6.0,
            "maintainability": 5.0,
            "deployment_readiness": 3.0,
        },
        overall_score=4.9,
        executive_summary="The repository has significant issues.",
    )
