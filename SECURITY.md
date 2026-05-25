# Security policy

**Matryca Plumber** is a **local-first autonomous background AI daemon** (with an optional MCP sidecar for tool hosts) that can **read and write Markdown files** under your Logseq graph path and uses **credentials** (for example `LOGSEQ_API_TOKEN` and any LLM provider keys in your environment or host). Treating those surfaces carefully is a top priority for the maintainers.

## Please do not file public issues for vulnerabilities

**Do not** open a regular GitHub issue to report a security vulnerability. Public issues disclose the problem before a fix is available and put all users at risk.

## How to report a vulnerability privately

1. **Preferred:** Use [GitHub Security Advisories](https://github.com/MarcoPorcellato/matryca-plumber/security/advisories/new) for this repository and submit a **private** security advisory with reproduction steps, impact, and versions affected.  
2. If you cannot use GitHub advisories, contact the repository maintainers through a **private** channel (for example email) and include the same detail you would put in an advisory. Do not paste secrets or real tokens in the report; use redacted examples.

We aim to acknowledge valid reports in a reasonable timeframe and coordinate disclosure after a fix or mitigation is available.

## Scope we care about

Examples include unauthorized file access outside the intended graph, credential leakage via logs or error messages, unsafe defaults that enable destructive writes without user intent, and protocol or transport issues in the daemon, HTTP surfaces, or optional MCP sidecar that could harm the host machine.

## Operator hardening (built-in)

Matryca Plumber ships several **defense-in-depth** controls you should configure via `.env` (see `.env.example`):

| Control | Variable | Default | Purpose |
|---------|----------|---------|---------|
| MCP stdio gate | `MATRYCA_MCP_ENABLED` | `false` | Prevents accidental FastMCP startup unless you explicitly enable Claude Desktop / Cursor integration. |
| UI bearer token | `MATRYCA_UI_TOKEN` | auto per process | Set a long random value if you enable LAN binding. |
| LAN UI bind | `MATRYCA_UI_ALLOW_LAN` | `false` | Refuses `0.0.0.0` unless set; `/api/auth/session` stays loopback-only even when LAN is on. |
| LLM SSRF guard | `LLM_BASE_URL` / `MATRYCA_LM_BASE_URL` | localhost | Shared validation in UI and daemon blocks cloud metadata and arbitrary egress URLs. |
| Graph path allowlist | `MATRYCA_ALLOWED_GRAPH_ROOTS` | (optional) | Settings UI cannot point `LOGSEQ_GRAPH_PATH` outside home, repo, temp, or declared roots. |
| UI rate limits | `MATRYCA_UI_RATE_LIMIT_*` | 120 / 30 | Separate budgets for authenticated vs probing traffic on `/api/*`. |
| Log redaction | `MATRYCA_PLUMBER_LOG_REDACT_SECRETS` | `true` | Masks Bearer tokens, `sk-*` keys, and JWT-shaped material in ops logs. |
| MCP error sanitization | `MATRYCA_DEBUG` | `false` | When off, MCP tools do not return raw OS paths in error strings. |

**Recommended local setup:** loopback UI only, `MATRYCA_MCP_ENABLED=true` only on machines where you trust the MCP host, test graphs via `LOGSEQ_GRAPH_PATH` clones, and never commit `.env`.

## Non-goals

Misconfiguration on your machine (for example sharing your `.env`, running untrusted optional MCP hosts, or exposing the daemon to untrusted networks) is outside the scope of this policy, though documentation improvements to reduce that risk are welcome as regular contributions.
