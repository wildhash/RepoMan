"""RepoMan configuration via Pydantic Settings."""

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="REPOMAN_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    anthropic_api_key: str = Field(default="", description="Anthropic API key")
    openai_api_key: str = Field(default="", description="OpenAI API key")

    orchestrator_model: str = Field(default="claude-sonnet-4-20250514", description="Orchestrator LLM model")
    architect_model: str = Field(default="claude-sonnet-4-20250514", description="Architect LLM model")
    auditor_model: str = Field(default="gpt-4o", description="Auditor LLM model")
    builder_model: str = Field(default="claude-sonnet-4-20250514", description="Builder LLM model")

    max_consensus_rounds: int = Field(default=5, description="Maximum debate rounds")
    consensus_threshold: float = Field(default=7.0, description="Minimum vote score for consensus")
    max_files_to_process: int = Field(default=200, description="Maximum files to analyse")
    max_file_size_kb: int = Field(default=500, description="Maximum file size in KB")
    timeout_per_phase_seconds: int = Field(default=300, description="Timeout per pipeline phase")

    sandbox_enabled: bool = Field(default=True, description="Run execution in Docker sandbox")
    knowledge_base_path: str = Field(default="./repoman_knowledge", description="ChromaDB path")
    learning_enabled: bool = Field(default=True, description="Enable self-learning")

    api_host: str = Field(default="0.0.0.0", description="API server host")
    api_port: int = Field(default=8000, description="API server port")
    cors_origins: list[str] = Field(default=["http://localhost:5173"], description="CORS allowed origins")

    elasticsearch_url: str = Field(
        default="",
        description="Elasticsearch base URL (e.g. http://localhost:9200)",
        validation_alias=AliasChoices("REPOMAN_ELASTICSEARCH_URL", "ELASTICSEARCH_URL"),
    )
    elasticsearch_api_key: str = Field(
        default="",
        description="Elasticsearch API key",
        validation_alias=AliasChoices("REPOMAN_ELASTICSEARCH_API_KEY", "ELASTICSEARCH_API_KEY"),
    )
    elasticsearch_cloud_id: str = Field(
        default="",
        description="Elasticsearch Cloud ID",
        validation_alias=AliasChoices("REPOMAN_ELASTICSEARCH_CLOUD_ID", "ELASTICSEARCH_CLOUD_ID"),
    )

    github_token: str = Field(
        default="",
        description="GitHub personal access token",
        validation_alias=AliasChoices("REPOMAN_GITHUB_TOKEN", "GITHUB_TOKEN"),
    )

    github_issue_ingest_limit: int = Field(
        default=300,
        ge=1,
        le=5000,
        description="Maximum issues/PRs to ingest per repository (safety cap)",
        validation_alias=AliasChoices(
            "REPOMAN_GITHUB_ISSUE_INGEST_LIMIT",
            "GITHUB_ISSUE_INGEST_LIMIT",
        ),
    )

    embedding_model: str = Field(
        default="all-MiniLM-L6-v2",
        description="Embedding model identifier (used by the selected embedding provider)",
        validation_alias=AliasChoices("REPOMAN_EMBEDDING_MODEL", "EMBEDDING_MODEL"),
    )
    embedding_provider: str = Field(
        default="hash",
        description="Embedding provider: 'hash' (default) or 'sentence_transformers'",
        validation_alias=AliasChoices("REPOMAN_EMBEDDING_PROVIDER", "EMBEDDING_PROVIDER"),
    )

    embedding_dims: int = Field(
        default=384,
        ge=1,
        description="Embedding vector dimensions (must match Elasticsearch mappings)",
        validation_alias=AliasChoices("REPOMAN_EMBEDDING_DIMS", "EMBEDDING_DIMS"),
    )
