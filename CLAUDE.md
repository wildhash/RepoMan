# REPOMAN — CLAUDE.md

## Self-Assembling Build Specification — March 2026

## Multi-Model Agent Council for Repository Rehabilitation

## PRIME DIRECTIVE

You are building **RepoMan** — an enterprise-grade multi-model agentic system that transforms any GitHub repository from half-baked to production-ready. RepoMan deploys a council of specialized AI agents, each powered by a different frontier model, that independently audit a repository, engage in structured debate until consensus, then execute a unified transformation plan with cross-review, automated validation, and pull request generation.

**This is not a code assistant. This is an autonomous AI engineering firm.**

The repo already exists at `github.com/wildhash/RepoMan` with 36 commits. It has working Elasticsearch ingestion, repo health scoring, and a basic agent pipeline. Your job is to **complete the system** — fill every gap, upgrade every stub, and deliver a fully operational product with a web dashboard that visualizes the debate process and generates real GitHub PRs.

**Rules:**

1. Every file production-quality. No placeholders. No TODOs. No “implement later.”
2. Follow Boris Cherny CLAUDE.md practices: Plan Mode first, verify with feedback loops, concise code, update on mistakes, use subagents.
3. Type everything (Pydantic v2 for data, TypeScript strict for frontend).
4. Test everything (pytest for Python, vitest for frontend).
5. If a file already exists and works, extend it — don’t rewrite from scratch.

**Contributor workflow (CLAUDE.md practices):**

1. **Plan Mode first.** Read the relevant files, sketch a plan, and name the exact commands you’ll use to verify.
2. **Small diffs.** Prefer the smallest change that moves the system forward.
3. **Feedback loop.** Run linters/tests early; revise based on actual failures.
4. **No placeholders.** If something can’t be implemented safely, document the limitation in the PR/issue instead of landing stubs.

## SECTION 1: SYSTEM IDENTITY

```
Project:          RepoMan
Package Name:     repoman-ai
Tagline:          "Point it at any repo. Get back enterprise-grade."
Author:           Willy (wildhash) | BotSpot.trade
License:          MIT
Python:           3.12+
Node:             20+
Primary DB:       Elasticsearch 8.x
State:            Redis 7+
Queue:            Redis Streams (or Celery w/ Redis)
Frontend:         React 19 + TypeScript + Vite + TailwindCSS 4
API:              FastAPI 0.115+ with WebSocket support
```

## SECTION 2: THE AGENT COUNCIL — MODEL ASSIGNMENTS (March 2026)

Each agent runs on a different frontier model. The model router must support fallback chains with exponential backoff.

### Agent → Model Mapping

```
┌─────────────────────────────────────────────────────────────────────┐
│                        THE AGENT COUNCIL                            │
├──────────────┬──────────────┬───────────────┬───────────────────────┤
│  ARCHITECT   │   AUDITOR    │   BUILDER     │   ORCHESTRATOR        │
│  Claude      │   GPT-5.4    │   Gemini 3.1  │   DeepSeek            │
│  Opus 4.6    │   Thinking   │   Pro         │   R1-0528             │
│              │              │               │                       │
│  Structure   │   Bugs, Sec  │   Implement   │   Mediate, Plan       │
│  Design      │   Quality    │   Code Gen    │   Resolve Disputes    │
│  Patterns    │   Standards  │   Tests       │   Final Decisions     │
└──────┬───────┴──────┬───────┴───────┬───────┴───────────┬───────────┘
       │              │               │                   │
       └──────────────┼───────────────┘                   │
                      │                                   │
             ┌────────▼────────┐                          │
             │  CONSENSUS LOOP │◄─────────────────────────┘
             │  (All agents    │
             │   debate until  │
             │   agreement)    │
             └────────┬────────┘
                      │
             ┌────────▼────────┐
             │   EXECUTOR      │
             │   Apply changes │
             │   Generate PR   │
             │   Run CI        │
             └─────────────────┘
```

### Model Configuration (config.py / .env)

```python
REPOMAN_MODELS = {
    "architect": {
        "provider": "anthropic",
        "model": "claude-opus-4-6",
        "fallback": ["claude-sonnet-4-6"],
        "max_tokens": 16384,
        "temperature": 0.3,
        "role": "Chief Architect — structure, design patterns, dependency analysis",
    },
    "auditor": {
        "provider": "openai",
        "model": "gpt-5.4",
        "fallback": ["gpt-5.4-pro"],
        "max_tokens": 16384,
        "temperature": 0.2,
        "reasoning_effort": "high",
        "role": "Security & Quality Auditor — CVEs, code smells, test coverage gaps",
    },
    "builder": {
        "provider": "google",
        "model": "gemini-3.1-pro-preview",
        "fallback": ["gemini-3-flash-preview"],
        "max_tokens": 16384,
        "temperature": 0.4,
        "role": "Implementation Engineer — writes code, tests, docs, CI/CD",
    },
    "orchestrator": {
        "provider": "deepseek",
        "model": "deepseek-reasoner",
        "fallback": ["deepseek-chat"],
        "max_tokens": 8192,
        "temperature": 0.1,
        "role": "Project Manager — mediates debate, synthesizes plans, breaks ties",
    },
}
```

### Provider Client Requirements

```python
# repoman/llm/providers/anthropic_client.py  → anthropic SDK, Messages API
# repoman/llm/providers/openai_client.py      → openai SDK, Responses API (GPT-5.4 uses Responses API)
# repoman/llm/providers/google_client.py      → google-genai SDK, Gemini 3.1 Pro
# repoman/llm/providers/deepseek_client.py    → openai-compatible SDK, DeepSeek API

# Each provider client MUST implement:
class BaseLLMClient(ABC):
    async def complete(self, messages: list[Message], system: str, **kwargs) -> LLMResponse: ...
    async def complete_json(
        self, messages: list[Message], system: str, schema: type[BaseModel]
    ) -> dict: ...
    async def stream(
        self, messages: list[Message], system: str, **kwargs
    ) -> AsyncIterator[str]: ...

# The ModelRouter selects provider + model based on agent role, handles fallback, rate limiting, cost tracking.
```

## SECTION 3: THE 7-PHASE PIPELINE

```
Phase 1 ─► INGEST        Clone repo, parse tree, detect stack, map deps
Phase 2 ─► AUDIT         Each agent independently analyzes the repo
Phase 3 ─► CONSENSUS     Agents debate, critique, vote → unified plan
Phase 4 ─► IMPLEMENT     Builder executes the plan, writes code
Phase 5 ─► CROSS-REVIEW  Architect + Auditor review every change
Phase 6 ─► VALIDATE      Run tests, linters, type checks, security scan
Phase 7 ─► SHIP          Generate GitHub PR with full diff, changelog, summary
```

### Phase 1: Ingest & Analysis

Already partially implemented via Elasticsearch. Extend to produce a `RepoSnapshot`:

```python
class RepoSnapshot(BaseModel):
    repo_url: str
    full_name: str  # "owner/repo"
    default_branch: str
    languages: dict[str, int]  # language -> bytes
    framework: str | None  # detected framework (Next.js, FastAPI, Rails, etc.)
    package_manager: str | None  # npm, pip, cargo, go mod, etc.
    file_tree: list[FileNode]  # full directory tree with metadata
    readme_content: str | None
    has_tests: bool
    has_ci: bool
    has_dockerfile: bool
    has_license: bool
    dependency_graph: dict[str, list[str]]
    open_issues_count: int
    open_pr_count: int
    last_commit_date: datetime
    contributors_count: int
    health_score: HealthScore  # from existing scoring system
```

### Phase 2: Multi-Agent Audit

Each agent independently produces an `AgentAuditReport`:

```python
class Finding(BaseModel):
    category: Literal[
        "bug",
        "security",
        "performance",
        "architecture",
        "testing",
        "documentation",
        "ci_cd",
        "dependency",
        "code_quality",
        "accessibility",
    ]
    severity: Literal["critical", "high", "medium", "low", "info"]
    file_path: str | None
    line_range: tuple[int, int] | None
    title: str
    description: str
    suggested_fix: str
    confidence: float  # 0.0 - 1.0
    effort_hours: float  # estimated fix time


class AgentAuditReport(BaseModel):
    agent_name: str
    model_used: str
    provider: str
    timestamp: datetime
    findings: list[Finding]
    summary: str
    overall_health_assessment: str
    priority_ranking: list[str]  # ordered finding titles
    tokens_used: TokenUsage
    duration_seconds: float
```

### Phase 3: Consensus (THE HERO FEATURE)

This is the differentiator. The debate loop is a structured protocol:

```python
class DebateMessage(BaseModel):
    round: int
    speaker: str  # agent name
    message_type: Literal[
        "proposal",
        "critique",
        "defense",
        "concession",
        "counter_proposal",
        "question",
        "answer",
        "vote",
    ]
    content: str
    references: list[str]  # finding IDs being discussed
    confidence: float
    timestamp: datetime


class ConsensusVote(BaseModel):
    agent_name: str
    approve: bool
    conditions: list[str]  # "I approve IF these are also addressed"
    dissent_reason: str | None


class ConsensusResult(BaseModel):
    rounds_taken: int
    max_rounds: int  # default 5
    achieved_consensus: bool
    final_plan: TransformationPlan
    debate_transcript: list[DebateMessage]
    votes: list[ConsensusVote]
    dissenting_opinions: list[str]
```

**Consensus Protocol Rules:**

1. Round 1: Each agent proposes their transformation plan based on their audit.
2. Round 2: Each agent critiques ALL other agents’ plans (not their own).
3. Round 3+: Agents revise their plans based on critiques received. The Orchestrator mediates disputes and proposes compromises.
4. Final Round: All agents vote on the Orchestrator’s unified plan. Consensus = 3/4 approve. If no consensus after max_rounds, Orchestrator decides with documented dissent.
5. Every message is logged to the debate transcript and streamed to the frontend via WebSocket.

### Phase 4: Implementation

The Builder agent executes the agreed `TransformationPlan`:

```python
class FileChange(BaseModel):
    action: Literal["create", "modify", "delete", "rename"]
    file_path: str
    new_path: str | None  # for renames
    original_content: str | None
    new_content: str | None
    diff: str | None  # unified diff format
    change_description: str
    finding_refs: list[str]  # which findings this addresses


class TransformationPlan(BaseModel):
    plan_id: str  # UUID
    repo_snapshot_id: str
    title: str
    description: str
    changes: list[FileChange]
    estimated_total_hours: float
    risk_level: Literal["low", "medium", "high"]
    rollback_strategy: str
    test_plan: str
```

### Phase 5: Cross-Review

Architect and Auditor independently review every `FileChange`:

```python
class ReviewComment(BaseModel):
    reviewer: str  # agent name
    file_path: str
    line_number: int | None
    severity: Literal["blocker", "major", "minor", "suggestion", "praise"]
    comment: str
    requires_change: bool


class ReviewResult(BaseModel):
    reviewer: str
    approve: bool
    comments: list[ReviewComment]
    blockers_count: int
```

If any blocker exists, loop back to Phase 4 with the review comments.

### Phase 6: Validate

Run in a sandboxed environment (Docker or isolated temp dir):

```python
class ValidationResult(BaseModel):
    tests_passed: bool
    test_output: str
    lint_passed: bool
    lint_output: str
    type_check_passed: bool
    type_check_output: str
    security_scan_passed: bool
    security_scan_output: str
    build_passed: bool
    build_output: str
    overall_passed: bool
```

### Phase 7: Ship (PR Generation)

```python
class PRPayload(BaseModel):
    title: str  # "RepoMan: Enterprise-grade rehabilitation"
    body: str  # Full markdown: summary, changes, debate highlights, metrics
    branch_name: str  # "repoman/transform-{plan_id[:8]}"
    base_branch: str  # usually "main"
    files_changed: list[FileChange]
    labels: list[str]  # ["repoman", "automated", "enterprise-upgrade"]
    reviewers: list[str]  # optional
    draft: bool  # default True for safety
```

Use PyGithub or httpx to the GitHub REST API. Create branch, commit changes, open PR.

## SECTION 4: PROJECT STRUCTURE

```
RepoMan/
├── .github/workflows/
│   ├── ci.yml                        # existing — extend with frontend build
│   └── release.yml
├── repoman/                          # Python backend
│   ├── __init__.py
│   ├── __main__.py                   # CLI entry
│   ├── config.py                     # Pydantic Settings, model config
│   ├── constants.py
│   ├── models/                       # ALL Pydantic models (schemas)
│   │   ├── __init__.py
│   │   ├── repo.py                   # RepoSnapshot, FileNode, HealthScore
│   │   ├── audit.py                  # Finding, AgentAuditReport
│   │   ├── consensus.py              # DebateMessage, ConsensusVote, ConsensusResult
│   │   ├── plan.py                   # FileChange, TransformationPlan
│   │   ├── review.py                 # ReviewComment, ReviewResult
│   │   ├── validation.py             # ValidationResult
│   │   ├── pr.py                     # PRPayload
│   │   └── events.py                 # WebSocket event types
│   ├── llm/                          # LLM abstraction layer
│   │   ├── __init__.py
│   │   ├── base.py                   # BaseLLMClient ABC
│   │   ├── router.py                 # ModelRouter — agent→model mapping, fallback, cost
│   │   ├── providers/
│   │   │   ├── __init__.py
│   │   │   ├── anthropic_client.py   # Claude Opus 4.6 via anthropic SDK
│   │   │   ├── openai_client.py      # GPT-5.4 via openai SDK (Responses API)
│   │   │   ├── google_client.py      # Gemini 3.1 Pro via google-genai SDK
│   │   │   └── deepseek_client.py    # DeepSeek R1 via openai-compat SDK
│   │   └── cost_tracker.py           # per-agent, per-session token/cost accounting
│   ├── agents/                       # The Agent Council
│   │   ├── __init__.py
│   │   ├── base.py                   # BaseAgent ABC with audit/propose/critique/vote
│   │   ├── architect.py              # Claude-powered architecture agent
│   │   ├── auditor.py                # GPT-5.4-powered security/quality agent
│   │   ├── builder.py                # Gemini-powered implementation agent
│   │   ├── orchestrator_agent.py     # DeepSeek-powered mediator
│   │   └── prompts/                  # System prompts as markdown
│   │       ├── architect_system.md
│   │       ├── auditor_system.md
│   │       ├── builder_system.md
│   │       └── orchestrator_system.md
│   ├── consensus/                    # Debate Engine
│   │   ├── __init__.py
│   │   ├── engine.py                 # Main debate loop controller
│   │   ├── protocol.py               # Message types, rules, round management
│   │   ├── voting.py                 # Vote aggregation, consensus detection
│   │   └── transcript.py             # Debate log serialization
│   ├── pipeline/                     # 7-Phase Orchestration
│   │   ├── __init__.py
│   │   ├── orchestrator.py           # Main pipeline controller
│   │   ├── phases.py                 # Phase 1-7 implementations
│   │   └── state.py                  # Pipeline state machine
│   ├── analysis/                     # Repo Analysis (extend existing)
│   │   ├── __init__.py
│   │   ├── ingestion.py              # GitHub clone + parse (extend existing)
│   │   ├── health_scorer.py          # 8-dimension scoring (extend existing)
│   │   ├── framework_detector.py     # Detect Next.js, FastAPI, Rails, etc.
│   │   └── dependency_mapper.py      # Build dependency graph
│   ├── execution/                    # Code Changes + PR
│   │   ├── __init__.py
│   │   ├── sandbox.py                # Docker-based sandboxed execution
│   │   ├── validator.py              # Test/lint/typecheck/security runners
│   │   ├── pr_generator.py           # GitHub PR creation via API
│   │   └── diff_engine.py            # Generate unified diffs
│   ├── api/                          # FastAPI Server
│   │   ├── __init__.py
│   │   ├── server.py                 # FastAPI app with CORS, middleware
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── repos.py              # POST /api/repos/analyze, GET /api/repos/{id}
│   │   │   ├── pipelines.py          # POST /api/pipelines/start, GET /api/pipelines/{id}
│   │   │   ├── debates.py            # GET /api/debates/{id}, GET /api/debates/{id}/transcript
│   │   │   ├── reviews.py            # GET /api/reviews/{pipeline_id}
│   │   │   ├── prs.py                # POST /api/prs/create, GET /api/prs/{id}
│   │   │   ├── search.py             # existing ES search endpoints
│   │   │   └── dashboard.py          # existing dashboard endpoints
│   │   ├── websocket.py              # WS /ws/pipeline/{id} — real-time events
│   │   └── deps.py                   # Dependency injection
│   ├── elasticsearch/                # Elasticsearch (extend existing)
│   │   ├── __init__.py
│   │   ├── client.py
│   │   ├── indices.py
│   │   └── queries.py
│   └── cli/                          # CLI commands
│       ├── __init__.py
│       ├── main.py                   # typer app
│       ├── es_commands.py            # existing ES commands
│       ├── analyze.py                # repoman analyze <repo_url>
│       └── transform.py              # repoman transform <repo_url> [--auto-pr]
├── frontend/                         # React Dashboard
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── index.html
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── api/
│   │   │   ├── client.ts             # axios/fetch wrapper
│   │   │   ├── websocket.ts          # WS connection manager
│   │   │   └── types.ts              # TypeScript types matching Pydantic models
│   │   ├── stores/
│   │   │   ├── pipelineStore.ts      # zustand store for pipeline state
│   │   │   └── debateStore.ts        # zustand store for debate messages
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx         # Main landing — repo health overview
│   │   │   ├── RepoDetail.tsx        # Single repo analysis view
│   │   │   ├── PipelineView.tsx      # Live pipeline progress (7 phases)
│   │   │   ├── DebateArena.tsx       # THE HERO VIEW — live debate visualization
│   │   │   ├── CodeReview.tsx        # Side-by-side diff with agent comments
│   │   │   └── PRPreview.tsx         # Preview generated PR before submission
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── Sidebar.tsx
│   │   │   │   ├── Header.tsx
│   │   │   │   └── Layout.tsx
│   │   │   ├── debate/
│   │   │   │   ├── AgentAvatar.tsx   # Colored icon per agent/model
│   │   │   │   ├── DebateTimeline.tsx # Scrollable timeline of messages
│   │   │   │   ├── MessageBubble.tsx # Agent debate message with type badge
│   │   │   │   ├── VotePanel.tsx     # Visual vote display (approve/reject)
│   │   │   │   └── ConsensusGauge.tsx # Progress toward consensus
│   │   │   ├── code/
│   │   │   │   ├── DiffViewer.tsx    # Side-by-side or unified diff
│   │   │   │   ├── FileTree.tsx      # Changed files navigator
│   │   │   │   ├── ReviewComment.tsx # Inline review comment from agents
│   │   │   │   └── PRBody.tsx        # Rendered markdown PR body
│   │   │   ├── pipeline/
│   │   │   │   ├── PhaseTracker.tsx  # 7-phase progress bar
│   │   │   │   ├── AgentStatus.tsx   # Live status of each agent
│   │   │   │   └── CostTracker.tsx   # Real-time token/cost display
│   │   │   └── shared/
│   │   │       ├── Badge.tsx
│   │   │       ├── Card.tsx
│   │   │       ├── Modal.tsx
│   │   │       └── Spinner.tsx
│   │   └── hooks/
│   │       ├── usePipeline.ts
│   │       ├── useDebate.ts
│   │       └── useWebSocket.ts
│   └── public/
├── tests/                            # extend existing
│   ├── conftest.py
│   ├── test_agents/
│   │   ├── test_architect.py
│   │   ├── test_auditor.py
│   │   └── test_builder.py
│   ├── test_consensus/
│   │   ├── test_engine.py
│   │   └── test_voting.py
│   ├── test_pipeline/
│   │   ├── test_phases.py
│   │   └── test_orchestrator.py
│   ├── test_execution/
│   │   ├── test_sandbox.py
│   │   └── test_pr_generator.py
│   └── fixtures/
│       ├── sample_repo_snapshot.json
│       ├── sample_audit_report.json
│       └── sample_debate_transcript.json
├── .env.example
├── .dockerignore
├── Dockerfile                        # extend existing
├── docker-compose.yml                # extend existing (add Redis)
├── Makefile                          # extend existing
├── pyproject.toml                    # extend existing
├── CLAUDE.md                         # THIS FILE
├── README.md                         # extend existing
├── LICENSE                           # existing MIT
└── SECURITY.md                       # existing
```

## SECTION 5: HEALTH SCORING ALGORITHM

8-dimensional scoring (extend existing implementation):

```python
health_score = weighted_sum(
    documentation * 0.15,  # README quality, inline docs, docstrings
    testing * 0.20,  # test coverage, test quality, CI integration
    security * 0.15,  # known CVEs, secrets exposure, dependency audit
    code_quality * 0.15,  # complexity, duplication, naming, type coverage
    architecture * 0.10,  # separation of concerns, dependency management
    ci_cd * 0.10,  # build pipeline, deployment readiness
    dependency_health * 0.10,  # outdated deps, abandoned deps, version pinning
    community * 0.05,  # issues response time, PR review time, contributing guide
)
```

Each dimension scores 0-100. Overall health = weighted sum → 0-100.

## SECTION 6: API SPECIFICATION

### REST Endpoints

```
POST   /api/repos/analyze              { repo_url: str } → RepoSnapshot
GET    /api/repos/{repo_id}            → RepoSnapshot
GET    /api/repos/{repo_id}/health     → HealthScore

POST   /api/pipelines/start            { repo_url: str, auto_pr: bool } → PipelineStatus
GET    /api/pipelines/{pipeline_id}    → PipelineStatus (current phase, agents status)
DELETE /api/pipelines/{pipeline_id}    → cancel

GET    /api/debates/{pipeline_id}                    → ConsensusResult
GET    /api/debates/{pipeline_id}/transcript          → list[DebateMessage]
GET    /api/debates/{pipeline_id}/transcript/stream   → SSE stream

GET    /api/reviews/{pipeline_id}      → list[ReviewResult]
GET    /api/reviews/{pipeline_id}/comments → list[ReviewComment]

POST   /api/prs/create                 { pipeline_id: str, draft: bool } → PRPayload
GET    /api/prs/{pr_id}               → PRPayload + GitHub PR URL

GET    /api/search/repositories        → existing
GET    /api/search/issues              → existing
GET    /api/dashboard/repo-health      → existing
GET    /api/dashboard/top-languages    → existing
```

### WebSocket

```
WS /ws/pipeline/{pipeline_id}

Events streamed to client:
{
    "event": "phase_started" | "phase_completed" | "agent_thinking" |
             "debate_message" | "vote_cast" | "consensus_reached" |
             "file_changed" | "review_comment" | "validation_result" |
             "pr_created" | "error",
    "data": { ... },
    "timestamp": "ISO8601",
    "agent": "architect" | "auditor" | "builder" | "orchestrator" | null
}
```

## SECTION 7: FRONTEND — DEBATE ARENA (THE HERO VIEW)

The Debate Arena is the signature view. It shows the multi-model council debating in real-time.

### Layout

```
┌──────────────────────────────────────────────────────────────────────┐
│  ┌─────────┐  REPOMAN — Debate Arena              [Pipeline #abc]     │
│  │ Phase   │                                                         │
│  │ Tracker │  repo: wildhash/SomeProject                              │
│  │ (7 dots)│  Phase 3: Consensus — Round 2 of 5                       │
│  └─────────┘                                                         │
├──────────┬──────────────────────────────────────────┬────────────────┤
│          │                                          │                │
│  AGENT   │         DEBATE TIMELINE                  │  CONSENSUS     │
│  STATUS  │                                          │  PANEL         │
│          │  ┌─ Claude (Architect) ────────────┐     │                │
│ ┌──────┐ │  │ "The service layer should be    │     │ ┌────────────┐ │
│ │Claude│ │  │  extracted into a separate      │     │ │ Votes:     │ │
│ │ OK   │ │  │  module..."                     │     │ │ OK Claude  │ │
│ │Think │ │  └────────────────────────────────┘     │ │ ?? GPT-5.4 │ │
│ └──────┘ │                                          │ │ ?? Gemini  │ │
│ ┌──────┐ │  ┌─ GPT-5.4 (Auditor) ──[critique]─┐     │ │ ?? DeepSk  │ │
│ │GPT5.4│ │  │ "I disagree — the existing       │     │ └────────────┘ │
│ │ WAIT │ │  │  coupling is the root cause of   │     │                │
│ │Resp  │ │  │  the security vulnerability..."  │     │ ┌────────────┐ │
│ └──────┘ │  └────────────────────────────────┘     │ │ Consensus  │ │
│ ┌──────┐ │                                          │ │ ████░░ 50% │ │
│ │Gemini│ │  ┌─ DeepSeek (Orchestrator) ────────┐    │ └────────────┘ │
│ │ WAIT │ │  │ "Both valid. Proposal: extract    │    │                │
│ │Wait  │ │  │  service layer AND patch the      │    │ ┌────────────┐ │
│ └──────┘ │  │  auth bypass in the same PR..."   │    │ │ Cost: $1.42│ │
│ ┌──────┐ │  └────────────────────────────────┘     │ │ Tokens: 23K│ │
│ │DeepSk│ │                                          │ └────────────┘ │
│ │ OK   │ │                                          │                │
│ │Think │ │                                          │                │
│ └──────┘ │                                          │                │
├──────────┴──────────────────────────────────────────┴────────────────┤
│  [View Code Changes]  [View Full Transcript]  [Generate PR]          │
└──────────────────────────────────────────────────────────────────────┘
```

### Design Direction

- Dark theme with neon accent colors per agent: Claude = violet, GPT-5.4 = emerald, Gemini = blue, DeepSeek = amber
- Each debate message has a type badge (proposal, critique, defense, concession, vote)
- Messages animate in as they stream via WebSocket
- Consensus gauge fills as votes come in
- Phase tracker shows all 7 phases with current highlighted
- Cost tracker updates in real-time

## SECTION 8: CODE REVIEW VIEW

Side-by-side diff viewer with inline agent review comments:

```
┌──────────────────────────────────────────────────────────────────────┐
│  Code Review — 14 files changed (+847 / -203)                         │
├───────────────┬──────────────────────────────────────────────────────┤
│               │                                                      │
│  FILE TREE    │  DIFF VIEWER                                         │
│               │                                                      │
│  ▾ src/       │  ── src/auth/handler.py ──────────────────────       │
│    ▾ auth/    │                                                      │
│      handler  │  - def authenticate(token):           ORIGINAL       │
│      middleware│  -     if check(token):                             │
│    ▾ api/     │  -         return True                               │
│      routes   │  + def authenticate(token: str) -> AuthResult:  NEW  │
│      deps     │  +     """Validate JWT with RSA verification."""     │
│  ▾ tests/     │  +     try:                                          │
│    test_auth  │  +         payload = jwt.decode(token, ...)          │
│               │                                                      │
│  AGENT REVIEW │  ┌─ Claude (Architect) ──────────────────┐          │
│  SUMMARY      │  │ Line 12: Good — proper type annotation │          │
│               │  └────────────────────────────────────────┘          │
│  Claude: OK   │  ┌─ GPT-5.4 (Auditor) ─[blocker]────────┐           │
│  GPT-5.4: WARN│  │ Line 15: Missing rate limiting on this│           │
│  Gemini: OK   │  │ endpoint. Add @rate_limit(100/min).   │           │
│               │  └────────────────────────────────────────┘          │
│               │                                                      │
│  [Approve All] [Request Changes] [Generate PR]                       │
└───────────────┴──────────────────────────────────────────────────────┘
```

## SECTION 9: ENVIRONMENT VARIABLES

```env
# GitHub
REPOMAN_GITHUB_TOKEN=ghp_xxx              # PAT with repo scope

# LLM Providers
REPOMAN_ANTHROPIC_API_KEY=sk-ant-xxx
REPOMAN_OPENAI_API_KEY=sk-xxx
REPOMAN_GOOGLE_API_KEY=xxx                 # or GOOGLE_APPLICATION_CREDENTIALS path
REPOMAN_DEEPSEEK_API_KEY=sk-xxx

# Infrastructure
REPOMAN_ELASTICSEARCH_URL=http://localhost:9200
REPOMAN_REDIS_URL=redis://localhost:6379/0

# Server
REPOMAN_API_HOST=0.0.0.0
REPOMAN_API_PORT=8000
REPOMAN_LOG_LEVEL=INFO

# Feature flags
REPOMAN_AUTO_PR=false                      # auto-create PR after validation
REPOMAN_SANDBOX_MODE=docker                # docker | local | none
REPOMAN_MAX_CONSENSUS_ROUNDS=5
REPOMAN_CONSENSUS_THRESHOLD=0.75           # 3/4 agents must approve (if using 0.0-1.0)
```

## SECTION 10: DEPENDENCIES

### Python (pyproject.toml — extend existing)

```toml
[project]
name = "repoman-ai"
version = "0.2.0"
requires-python = ">=3.12"
dependencies = [
    # API
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "websockets>=14.0",
    # LLM SDKs
    "anthropic>=0.43.0",
    "openai>=1.65.0",
    "google-genai>=1.5.0",
    # GitHub
    "PyGithub>=2.5.0",
    "gitpython>=3.1.0",
    # Data
    "elasticsearch[async]>=8.17.0",
    "redis>=5.2.0",
    "pydantic>=2.10.0",
    "pydantic-settings>=2.7.0",
    # CLI
    "typer[all]>=0.15.0",
    "rich>=13.9.0",
    # Utilities
    "httpx>=0.28.0",
    "structlog>=24.4.0",
    "tenacity>=9.0.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.25.0",
    "pytest-cov>=6.0.0",
    "ruff>=0.8.0",
    "mypy>=1.13.0",
    "respx>=0.22.0",
]
```

### Frontend (package.json)

```json
{
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "react-router-dom": "^7.1.0",
    "zustand": "^5.0.0",
    "axios": "^1.7.0",
    "react-diff-viewer-continued": "^4.0.0",
    "react-syntax-highlighter": "^15.6.0",
    "lucide-react": "^0.468.0",
    "framer-motion": "^11.15.0",
    "date-fns": "^4.1.0"
  },
  "devDependencies": {
    "typescript": "^5.7.0",
    "vite": "^6.0.0",
    "@vitejs/plugin-react": "^4.3.0",
    "tailwindcss": "^4.0.0",
    "vitest": "^2.1.0",
    "@testing-library/react": "^16.1.0"
  }
}
```

## SECTION 11: BUILD ORDER

Execute in this exact sequence:

```
PHASE A — Foundation (extend existing)
  1. repoman/models/*.py          — all Pydantic schemas
  2. repoman/config.py            — extend with model config, Redis, feature flags
  3. repoman/llm/base.py          — BaseLLMClient ABC
  4. repoman/llm/providers/*.py   — all 4 provider clients
  5. repoman/llm/router.py        — ModelRouter with fallback + cost tracking

PHASE B — Agents
  6. repoman/agents/base.py       — BaseAgent with audit/propose/critique/vote
  7. repoman/agents/prompts/*.md  — system prompts (detailed, role-specific)
  8. repoman/agents/architect.py  — Claude-powered
  9. repoman/agents/auditor.py    — GPT-5.4-powered
  10. repoman/agents/builder.py   — Gemini-powered
  11. repoman/agents/orchestrator_agent.py — DeepSeek-powered

PHASE C — Consensus Engine
  12. repoman/consensus/protocol.py
  13. repoman/consensus/voting.py
  14. repoman/consensus/transcript.py
  15. repoman/consensus/engine.py

PHASE D — Pipeline
  16. repoman/pipeline/state.py
  17. repoman/pipeline/phases.py
  18. repoman/pipeline/orchestrator.py

PHASE E — Execution & PR
  19. repoman/execution/diff_engine.py
  20. repoman/execution/sandbox.py
  21. repoman/execution/validator.py
  22. repoman/execution/pr_generator.py

PHASE F — API (extend existing)
  23. repoman/api/websocket.py
  24. repoman/api/routes/pipelines.py
  25. repoman/api/routes/debates.py
  26. repoman/api/routes/reviews.py
  27. repoman/api/routes/prs.py
  28. repoman/api/server.py          — register new routes

PHASE G — Frontend
  29. frontend/src/api/types.ts
  30. frontend/src/api/client.ts
  31. frontend/src/api/websocket.ts
  32. frontend/src/stores/*.ts
  33. frontend/src/components/shared/*.tsx
  34. frontend/src/components/debate/*.tsx
  35. frontend/src/components/code/*.tsx
  36. frontend/src/components/pipeline/*.tsx
  37. frontend/src/pages/*.tsx
  38. frontend/src/App.tsx

PHASE H — CLI (extend existing)
  39. repoman/cli/analyze.py
  40. repoman/cli/transform.py
  41. repoman/cli/main.py

PHASE I — Tests
  42. tests/fixtures/*.json
  43. tests/test_agents/*.py
  44. tests/test_consensus/*.py
  45. tests/test_pipeline/*.py
  46. tests/test_execution/*.py

PHASE J — Infrastructure
  47. docker-compose.yml            — add Redis
  48. Dockerfile                    — extend
  49. Makefile                      — add transform/debate targets
  50. README.md                     — extend with new features
```

## SECTION 12: CRITICAL RULES

1. **Multi-model is the feature.** Every audit MUST use all 4 models. Never shortcut to single-model.
2. **Debate is the differentiator.** The consensus engine must produce readable, structured debate transcripts that demonstrate genuine multi-perspective analysis.
3. **WebSocket everything.** Every phase transition, every debate message, every code change streams to the frontend in real-time.
4. **Type everything.** Python: Pydantic v2 + mypy strict. TypeScript: strict mode. No `Any`, no `any`.
5. **Cost transparency.** Track and display per-agent, per-phase token usage and cost.
6. **Diff-first code review.** The CodeReview page must show side-by-side diffs with inline agent comments — this is how users decide to approve the PR.
7. **Draft PRs by default.** Never auto-merge. Always create as draft unless explicitly overridden.
8. **Graceful degradation.** If one model provider is down, the pipeline should still work with the remaining agents (minimum 2 for consensus).
9. **Extend, don’t rewrite.** The existing ES ingestion, health scoring, and search endpoints work. Build on top of them.
10. **Ship it.** Perfect is the enemy of shipped. Get the full pipeline running end-to-end, then polish.

*Built by Willy (wildhash) | BotSpot.trade | Beyond Greed Philosophy*

*“Point it at any repo. Get back enterprise-grade.”*
