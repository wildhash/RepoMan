# Security Policy

## Reporting a vulnerability

If you believe you’ve found a security vulnerability in RepoMan:

1. Prefer reporting it via a GitHub Security Advisory (private disclosure), if enabled for this repo.
2. If advisories aren’t available, open an issue with minimal detail and clearly mark it as a security concern.

Please include:

- A clear description of the issue and impact
- Steps to reproduce
- Any suggested mitigation

## Threat model notes

RepoMan interacts with several high-privilege systems:

- **GitHub tokens** (`REPOMAN_GITHUB_TOKEN`) can provide access to private repos and org data.
- **LLM API keys** (Anthropic/OpenAI) are secrets and can incur cost.
- **Elasticsearch credentials** (Cloud ID / API key) grant access to indexed data.

Guidelines:

- Use least-privilege credentials (scope tokens to read-only when possible).
- Avoid running RepoMan against untrusted repos unless you understand the execution surface.
- When enabling sandbox execution, treat containers as a mitigation, not a guarantee.
