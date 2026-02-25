"""RepoMan configuration via Pydantic Settings."""

from pydantic import Field
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
