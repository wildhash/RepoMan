"""Shared Pydantic v2 data models for the RepoMan pipeline."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class Phase(StrEnum):
    """Pipeline phase names."""

    ingestion = "ingestion"
    audit = "audit"
    consensus = "consensus"
    execution = "execution"
    review = "review"
    validation = "validation"
    learning = "learning"


class JobStatus(StrEnum):
    """Job lifecycle states."""

    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class Issue(BaseModel):
    """A single repository issue detected by an agent."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    severity: str  # critical | major | minor
    category: str  # bug | security | performance | architecture | style | docs
    file_path: str | None = None
    line_number: int | None = None
    description: str
    suggested_fix: str


class FileChange(BaseModel):
    """Represents a single file operation."""

    path: str
    action: str  # create | modify | delete
    content: str | None = None
    summary: str


class ChangeSet(BaseModel):
    """A group of file changes for one execution step."""

    step_name: str
    files_created: list[FileChange] = Field(default_factory=list)
    files_modified: list[FileChange] = Field(default_factory=list)
    files_deleted: list[str] = Field(default_factory=list)
    summary: str


class RepoSnapshot(BaseModel):
    """Complete snapshot of a repository at analysis time."""

    url: str
    name: str
    clone_path: str
    primary_language: str = ""
    languages: dict[str, float] = Field(default_factory=dict)
    frameworks: list[str] = Field(default_factory=list)
    dependencies: list[dict[str, Any]] = Field(default_factory=list)
    file_tree: list[str] = Field(default_factory=list)
    entry_points: list[str] = Field(default_factory=list)
    has_readme: bool = False
    has_tests: bool = False
    has_ci: bool = False
    has_dockerfile: bool = False
    has_license: bool = False
    has_env_example: bool = False
    total_files: int = 0
    total_lines: int = 0
    file_summaries: dict[str, str] = Field(default_factory=dict)
    health_score: float = 0.0
    issues_detected: list[Issue] = Field(default_factory=list)


class AgentAuditReport(BaseModel):
    """Full audit report from a single agent."""

    agent_name: str
    agent_role: str
    model_used: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    critical_issues: list[Issue] = Field(default_factory=list)
    major_issues: list[Issue] = Field(default_factory=list)
    minor_issues: list[Issue] = Field(default_factory=list)
    architecture_changes: list[dict[str, Any]] = Field(default_factory=list)
    new_files_needed: list[dict[str, Any]] = Field(default_factory=list)
    files_to_refactor: list[dict[str, Any]] = Field(default_factory=list)
    files_to_delete: list[str] = Field(default_factory=list)
    scores: dict[str, float] = Field(default_factory=dict)
    overall_score: float = 0.0
    executive_summary: str = ""
    estimated_effort: str = ""


class DebateMessage(BaseModel):
    """A single message in the consensus debate."""

    agent: str
    role: str  # PROPOSAL | CRITIQUE | REVISION | VOTE | SYNTHESIS | FINAL_DECISION
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    content: str
    references: list[str] = Field(default_factory=list)
    agreement_level: float | None = None
    blocking_concerns: list[str] = Field(default_factory=list)


class AgentVote(BaseModel):
    """Vote cast by an agent on the unified plan."""

    agent_name: str
    score: float  # 0-10
    approve: bool
    blocking_concerns: list[str] = Field(default_factory=list)
    minor_concerns: list[str] = Field(default_factory=list)
    rationale: str


class ConsensusResult(BaseModel):
    """Result of the consensus debate process."""

    achieved: bool
    rounds: int
    unified_plan: dict[str, Any] = Field(default_factory=dict)
    votes: dict[str, AgentVote] = Field(default_factory=dict)
    transcript: list[DebateMessage] = Field(default_factory=list)


class ValidationResult(BaseModel):
    """Result of a single validation check."""

    check_name: str
    passed: bool
    output: str
    details: dict[str, Any] = Field(default_factory=dict)


class ValidationReport(BaseModel):
    """Aggregated validation results."""

    all_passed: bool
    results: list[ValidationResult] = Field(default_factory=list)
    health_score: float = 0.0


class PipelineResult(BaseModel):
    """Full result of a pipeline run."""

    job_id: str
    status: JobStatus
    repo_url: str
    before_snapshot: RepoSnapshot | None = None
    after_snapshot: RepoSnapshot | None = None
    audit_reports: list[AgentAuditReport] = Field(default_factory=list)
    consensus: ConsensusResult | None = None
    change_sets: list[ChangeSet] = Field(default_factory=list)
    validation: ValidationReport | None = None
    before_score: float = 0.0
    after_score: float = 0.0
    issues_fixed: int = 0
    total_tokens_used: int = 0
    total_duration_seconds: float = 0.0
    error: str | None = None


class PipelineState(BaseModel):
    """Mutable state threaded through all pipeline phases."""

    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: JobStatus = JobStatus.queued
    current_phase: Phase = Phase.ingestion
    repo_url: str = ""
    snapshot: RepoSnapshot | None = None
    audit_reports: list[AgentAuditReport] = Field(default_factory=list)
    consensus: ConsensusResult | None = None
    change_sets: list[ChangeSet] = Field(default_factory=list)
    review_approved: bool = False
    validation: ValidationReport | None = None
    tokens_used: int = 0
    errors: list[str] = Field(default_factory=list)
