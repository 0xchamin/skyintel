# PRD: LintAgent — Security Linter for MCP Servers & AI Agent Systems

**Author:** MCPShark
**Date:** March 2026  
**Status:** Draft v1.0

---

## 1. Problem Statement

The Model Context Protocol (MCP) is rapidly becoming the universal standard for connecting
AI agents to tools and data sources — adopted by Claude, ChatGPT, VS Code, Gemini, Codex,
and Cursor. Simultaneously, multi-agent systems are moving from research to production.

However, there is no security gate before MCP servers and agent systems go live:

- Developers publish MCP servers to registries with zero standardized security review
- 30+ CVEs documented in the MCP ecosystem in just 60 days, with 43% being exec/shell injection
- The first full RCE against an MCP client (CVE-2025-6514) scored CVSS 9.6
- Microsoft patched a critical SSRF in Azure MCP Server (CVE-2026-26118) in March 2026
- Only 8.5% of MCP servers implement modern OAuth authentication
- The CoSAI white paper identifies 40+ MCP threats most organizations aren't addressing
- 7.2% of 1,899 open-source MCP servers contain vulnerabilities
- The first malicious MCP server discovered in the wild was a backdoored npm package
  with dual reverse shells giving persistent remote access to agent environments
- No existing tool provides a pass/fail gate with structured remediation before publish

The ecosystem needs what ESLint did for JavaScript — a standard security linter that
runs before code ships.

---

## 2. Product Vision

A pre-publish security linter for MCP servers and AI agent systems. Scan code,
dependencies, auth compliance, and attack surface before they go live. Pass or fail.

**One-liner:** ESLint for MCP servers and AI agent systems.

**Core principle:** No MCP server or agent system should reach a registry or production
without passing a security gate.

**Three-tier value:**

| Tier | Capability | Status |
|------|-----------|--------|
| **Scan** | Detect vulnerabilities, misconfigurations, non-compliance | MVP |
| **Recommend** | Explain why, map to standards, provide fix guidance with code examples | MVP |
| **Fix** | Generate structured fix descriptors consumable by coding agents | v2 |

---

## 3. Target Users

| User | Use Case |
|------|----------|
| MCP Server Developers | Validate server security before publishing to a registry |
| AI Agent Developers | Lint multi-agent systems before deployment |
| DevSecOps Teams | Integrate as a CI/CD gate — block insecure publishes |
| Platform / Infra Teams | Assess third-party MCP servers before adoption |
| Security Engineers | Audit MCP servers and agent systems in their organization |
| Compliance Officers | Generate compliance reports against MCP spec, OWASP, CoSAI |

---

## 4. Competitive Landscape

| Capability | Snyk agent-scan | Cisco mcp-scanner | MCPShield | MintMCP Gateway | **LintAgent** |
|------------|----------------|-------------------|-----------|-----------------|---------------|
| Tool poisoning detection | ✅ | ✅ | ❌ | ❌ | ✅ |
| Dependency / supply chain | ✅ | ❌ | ✅ | ❌ | ✅ |
| MCP auth spec compliance | ❌ | ❌ | ❌ | Partial (gateway) | ✅ |
| YARA pattern matching | ❌ | ✅ | ❌ | ❌ | ✅ |
| Deep code analysis (Semgrep) | ❌ | ❌ | ❌ | ❌ | ✅ |
| Secret detection (git history) | ❌ | ❌ | ✅ | ❌ | ✅ |
| Registry gate (pass/fail) | ❌ | ❌ | ❌ | ❌ | ✅ |
| Structured fix descriptors | ❌ | ❌ | ❌ | ❌ | ✅ |
| Compliance scorecard | ❌ | ❌ | ❌ | ❌ | ✅ |
| OWASP MCP Top 10 mapping | Partial | Partial | Partial | ❌ | ✅ |
| OWASP Agentic AI Top 10 | Partial | ❌ | ❌ | ❌ | ✅ (v2) |
| CoSAI framework mapping | ❌ | ❌ | ❌ | ❌ | ✅ |
| Runtime proxy mode | ✅ | ❌ | ❌ | ✅ | ❌ (not in scope) |
| MCP-as-MCP (native in IDEs) | ❌ | ❌ | ❌ | ❌ | ✅ |
| CI/CD integration | ✅ | ❌ | ✅ | ❌ | ✅ |

**Differentiation:** LintAgent does not compete on runtime monitoring. It owns the
**pre-publish gate** — scan, recommend, fix — with compliance mapping no competitor offers.

---

## 5. Standards & Compliance Framework

LintAgent validates against these standards. Specific RFC coverage to be finalized
during development based on the latest MCP authorization specification.

### 5.1 MCP Specification (Official)
Source: modelcontextprotocol.io/specification

| Area | Key Requirements |
|------|-----------------|
| **Authorization (OAuth 2.1)** | RFC 8414, RFC 9728, RFC 7591, RFC 8707, PKCE (RFC 7636), token audience binding, no token passthrough |
| **Transport Security** | HTTPS enforcement for remote, session binding and entropy, SSRF protection |
| **Official Transports** | stdio, Streamable HTTP. SSE deprecated. |
| **Well-Known Endpoints** | `/.well-known/oauth-authorization-server`, `/.well-known/oauth-protected-resource`, proper 401 + WWW-Authenticate |
| **Input Validation** | Tool input sanitization, command injection prevention, path traversal protection |

*Note: MCP auth spec references additional RFCs (OAuth 2.0 core RFC 6749/6750, etc.).
Full RFC checklist to be compiled from the latest spec during development.*

### 5.2 OWASP MCP Top 10 (v0.1, 2025)
Source: owasp.org/www-project-mcp-top-10

| ID | Risk |
|----|------|
| MCP01 | Token Mismanagement & Secret Exposure |
| MCP02 | Privilege Escalation via Scope Creep |
| MCP03 | Tool Poisoning |
| MCP04 | Software Supply Chain Attacks |
| MCP05 | Command Injection & Execution |
| MCP06 | Intent Flow Subversion |
| MCP07 | Insufficient Authentication & Authorization |
| MCP08 | Lack of Audit and Telemetry |
| MCP09 | Shadow MCP Servers |
| MCP10 | Context Injection & Over-Sharing |

*Note: Currently in Phase 3 — Beta Release and Pilot Testing. IDs may change.*

### 5.3 OWASP Top 10 for Agentic Applications (2026)
Source: genai.owasp.org

| ID | Risk |
|----|------|
| ASI01 | Agent Goal Hijacking |
| ASI02 | Tool Misuse |
| ASI03 | Privilege Escalation |
| ASI04 | Supply Chain Vulnerabilities |
| ASI05 | Impact Chain & Blast Radius |
| ASI06 | Intent Flow Subversion |
| ASI07 | Identity & Access Failures |
| ASI08 | Insufficient Logging & Monitoring |
| ASI09 | Rogue / Shadow Agents |
| ASI10 | Data Exfiltration & Leakage |

### 5.4 Additional Standards
- CoSAI MCP Security Framework (12 threat categories)
- MITRE ATLAS (Adversarial Threat Landscape for AI Systems)
- OWASP Top 10 for LLM Applications (2025) — cross-referenced where MCP-specific variants apply
- NIST AI Risk Management Framework (AI RMF)

### 5.5 OWASP Top 10 for LLM Applications (2025)
Source: owasp.org/www-project-top-10-for-large-language-model-applications

| ID | Risk |
|----|------|
| LLM01 | Prompt Injection |
| LLM02 | Sensitive Information Disclosure |
| LLM03 | Supply Chain Vulnerabilities |
| LLM04 | Data and Model Poisoning |
| LLM05 | Improper Output Handling |
| LLM06 | Excessive Agency |
| LLM07 | System Prompt Leakage |
| LLM08 | Vector and Embedding Weaknesses |
| LLM09 | Misinformation |
| LLM10 | Unbounded Consumption |

Applied where MCP-specific variants exist — particularly LLM01 (prompt injection
via tool descriptions), LLM03 (MCP supply chain), LLM05 (unsafe tool outputs),
and LLM06 (tools with excessive permissions).

---

## 6. Three-Layer Scan Pipeline

```
  Target MCP Server / Agent System
                │
                ▼
  ┌─────────────────────────┐
  │  Layer 1: YARA           │  Fast pattern matching
  │  - Malicious signatures  │  (~seconds)
  │  - Obfuscated code       │
  │  - Known attack patterns │
  └───────────┬─────────────┘
              ▼
  ┌─────────────────────────┐
  │  Layer 2: Semgrep +      │  Deep code analysis
  │           ast-grep       │  (~seconds)
  │  - Auth compliance       │
  │  - Injection patterns    │
  │  - OWASP rule matching   │
  │  - MCP spec violations   │
  └───────────┬─────────────┘
              ▼
  ┌─────────────────────────┐
  │  Layer 3: Gitleaks +     │  Secrets + dependencies
  │           pip-audit      │  (~seconds)
  │  - Secrets in code/git   │
  │  - CVEs in dependencies  │
  │  - Typosquat detection   │
  └───────────┬─────────────┘
              ▼
  ┌─────────────────────────┐
  │  LLM Classification      │  Optional enrichment
  │  (opt-in)                │
  │  - Tool poisoning review │
  │  - Fix recommendations   │
  │  - Report narrative      │
  └───────────┬─────────────┘
              ▼
        PASS / FAIL
```

Each layer runs independently. Findings from all layers are aggregated, deduplicated,
and severity-ranked into a unified result.

---

## 7. What It Checks

### 7.1 Auth & Token Auditing
- OAuth 2.1 compliance against MCP spec
- Protected Resource Metadata (`/.well-known/oauth-protected-resource`)
- Authorization Server Metadata (`/.well-known/oauth-authorization-server`)
- PKCE support verification
- Token passthrough detection (forbidden by spec)
- Audience binding validation
- Dynamic Client Registration support
- Long-lived token detection
- Static secret / API key detection in configs
- Zero-auth Streamable HTTP servers flagged

### 7.2 Transport & Session Security
- HTTPS enforcement for remote servers
- Deprecated SSE transport detection
- SSRF-vulnerable metadata URLs (private IPs, link-local, cloud metadata 169.254.169.254)
- Session ID entropy analysis
- Session binding verification

### 7.3 Authorization & Scope
- Scope-based authorization on tools
- Tag-based access control on components
- Admin/privileged tools without authorization checks
- Wildcard or overly broad scope definitions
- Per-tool auth granularity vs blanket server-level auth
- Privilege escalation paths

### 7.4 Tool Security
- Tool description poisoning detection (LLM classifier)
- Input schema validation
- Command injection patterns in tool definitions
- Dangerous tool names that could mislead agents
- Scope/permission analysis per tool

### 7.5 Configuration
- MCP config file analysis (mcp.json, claude_desktop_config.json, settings.json)
- Suspicious startup commands (shell injection via args)
- Hardcoded credentials and API keys
- Overly permissive settings
- Server command path verification (symlink attacks, PATH hijacking)

### 7.6 Supply Chain
- Dependency CVE scanning via pip-audit against OSV.dev
- Typosquat package detection
- Unpinned dependency version detection
- Secret detection in code and git history via Gitleaks

### 7.7 Agent-Specific (v2)
- Agent card validation
- Resource access scope analysis
- Multi-agent trust boundary verification
- Agent-to-agent communication security
- MCP and multi-agent graph analysis (dynamic)

---

## 8. Registry Gate

LintAgent's core output is a **pass/fail decision** for pre-publish gating.

```
Developer writes MCP server
        │
        ▼
  lintagent scan ./my-server
        │
        ▼
   ┌─────────┐     ┌──────────────────────────┐
   │  PASS    │────▶│ Publish to registry       │
   └─────────┘     │ (Smithery, mcp.run, npm)  │
                   └──────────────────────────┘
   ┌─────────┐     ┌──────────────────────────┐
   │  FAIL    │────▶│ Commit to git only        │
   └─────────┘     │ + remediation report      │
                   └──────────────────────────┘
```

**Severity threshold configuration:**
- `--fail-on critical` — only fail on critical findings
- `--fail-on high` — fail on high and above
- `--fail-on medium` — fail on medium and above (default)
- `--fail-on low` — strict mode, fail on any finding

---

## 9. Delivery Modes

### 9.1 CLI
```bash
lintagent scan <path-or-url>         # Full scan, pass/fail
lintagent scan --depth quick <url>   # Fast scan
lintagent scan --depth thorough <path> # Deep scan with LLM
lintagent auth <url>                 # Auth-only audit
lintagent tools <url>                # Tool-only audit
lintagent dependencies <path>        # Dependency-only audit
lintagent report <scan-id> --format html
lintagent compare <scan-a> <scan-b>  # Diff two scans
lintagent ci --fail-on high          # CI mode, exit code based
```
BYOK via LiteLLM — auto-detects ANTHROPIC_API_KEY, OPENAI_API_KEY, etc.
Override with `--model` or `LINTAGENT_LLM_MODEL` env var.

### 9.2 MCP Server
```bash
lintagent serve --transport http --host 127.0.0.1 --port 8000
```
Built with FastMCP. Exposes scan tools via Streamable HTTP.
Leverages the MCP client's underlying LLM (Claude, GPT, Codex) via
passthrough — no BYOK needed in this mode.

**Compatible with:** Claude Code, VS Code Copilot, Codex, Cursor, Gemini CLI,
ChatGPT, any Streamable HTTP MCP client.

### 9.3 GitHub Action (CI/CD Gate)
```yaml
- name: LintAgent Security Scan
  uses: lintagent/lintagent-action@v1
  with:
    path: ./my-mcp-server
    fail-on: high
    format: sarif
- name: Upload SARIF
  uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: lintagent-results.sarif
```
SARIF output integrates with GitHub's Security tab — findings show inline on PRs.

### 9.4 `lintagent serve` (Team Mode)
```bash
lintagent serve --transport http --host 0.0.0.0 --port 8000
```
Shared instance for teams. Multiple developers/IDE clients connect to one
LintAgent server. Future: OAuth-protected for enterprise use.

---

## 10. Reports

Reports are comprehensive, explainable, and actionable — not just a list of pass/fail.

### 10.1 Output Formats
- **Markdown (.md)** — human-readable, embeds in PRs and docs
- **HTML (.html)** — interactive dashboard with charts, dark theme, self-contained
- **SARIF (.sarif)** — machine-readable, GitHub Security tab integration

### 10.2 Report Contents

**Compliance Scorecard:**
- Overall score (0-100)
- MCP Spec compliance score
- OWASP MCP Top 10 coverage (0/10 risks addressed)
- CoSAI framework coverage
- Per-auditor breakdown
- Grade (A-F)

**Findings Detail (per finding):**

| Field | Description |
|-------|-------------|
| Finding ID | e.g. AUTH-001, TOOL-003, SC-002 |
| Title | Human-readable name |
| Severity | Critical / High / Medium / Low / Info |
| Classification | Why it was classified at this severity — rule-based reasoning or LLM explanation |
| Standard Reference | MCP Spec section, OWASP ID, CoSAI category, MITRE ATLAS technique |
| Evidence | What was detected (code snippet, endpoint response, dependency version) |
| Risk Explanation | Why this matters — attack scenario in plain language |
| Recommended Fix | Step-by-step remediation guidance |
| Code Example | Working code snippet demonstrating the fix |
| Fix Priority | Suggested fix order based on severity × effort |

**MCP & Agent Graph (dynamic):**
- Visual graph of scanned MCP server topology
- Tool → permission → resource mappings
- Agent-to-agent communication paths (v2)
- Trust boundaries highlighted
- Vulnerability hotspots marked on graph

**Scan Comparison:**
- Diff two scans to track improvement over time
- New findings, resolved findings, unchanged findings
- Score trend

### 10.3 LLM-Enhanced Report (opt-in)
When LLM is enabled (BYOK or passthrough):
- Natural language narrative summarizing overall security posture
- Contextual fix recommendations tailored to the specific codebase
- Tool poisoning analysis with reasoning chain
- Priority-ranked remediation roadmap

---

## 11. Tech Stack

| Component | Technology | Role |
|-----------|-----------|------|
| **Framework** | FastMCP | MCP server mode |
| **Language** | Python 3.12 | Core scanner |
| **LLM Access** | LiteLLM (BYOK) | CLI mode LLM calls |
| **LLM Passthrough** | FastMCP client LLM | MCP server mode — uses client's own LLM |
| **Static Analysis** | Semgrep + custom rules | Deep AST-based code analysis |
| **AST Search** | ast-grep | Lightweight pattern matching |
| **Pattern Matching** | YARA | Fast first-pass malicious pattern detection |
| **Secret Detection** | Gitleaks | Secrets in code + git history |
| **Dependency Scanning** | pip-audit | Python CVE scanning via OSV.dev |
| **HTTP Probing** | httpx | Endpoint verification, auth checks |
| **Data Models** | Pydantic | Finding, ScanResult, Scorecard models |
| **Storage** | SQLite | Scan history (~/.lintagent/scans.db) |
| **Reports** | Built-in generators | Markdown, HTML (Chart.js), SARIF v2.1.0 |
| **CI/CD** | GitHub Action | Pre-publish gate |

---

## 12. Architecture

```
                    ┌──────────────────────────────┐
                    │  Target MCP Server /          │
                    │  Agent System                 │
                    └──────────────┬───────────────┘
                                   │
               ┌───────────────────▼───────────────────┐
               │          Scanner Engine                │
               │                                        │
               │  ┌──────────────────────────────────┐  │
               │  │ Layer 1: YARA                     │  │
               │  │ - Malicious signatures            │  │
               │  │ - Obfuscation detection           │  │
               │  │ - Known attack patterns           │  │
               │  └──────────────┬───────────────────┘  │
               │                 ▼                       │
               │  ┌──────────────────────────────────┐  │
               │  │ Layer 2: Semgrep + ast-grep       │  │
               │  │ - MCP auth spec compliance        │  │
               │  │ - OWASP pattern matching          │  │
               │  │ - Injection detection             │  │
               │  │ - CoSAI / MITRE ATLAS mapping     │  │
               │  └──────────────┬───────────────────┘  │
               │                 ▼                       │
               │  ┌──────────────────────────────────┐  │
               │  │ Layer 3: Gitleaks + pip-audit     │  │
               │  │ - Secrets in code + git history   │  │
               │  │ - Dependency CVEs (OSV.dev)       │  │
               │  │ - Typosquat detection             │  │
               │  └──────────────┬───────────────────┘  │
               │                 ▼                       │
               │  ┌──────────────────────────────────┐  │
               │  │ Auditors                          │  │
               │  │ - Auth Auditor                    │  │
               │  │ - Transport Auditor               │  │
               │  │ - Authorization Auditor            │  │
               │  │ - Tool Auditor                    │  │
               │  │ - Config Auditor                  │  │
               │  │ - Supply Chain Auditor            │  │
               │  └──────────────┬───────────────────┘  │
               │                 ▼                       │
               │  ┌──────────────────────────────────┐  │
               │  │ LLM Classifier (opt-in)           │  │
               │  │ - Rule-based first pass           │  │
               │  │ - LLM second pass (BYOK/passthru) │  │
               │  │ - Tool poisoning analysis         │  │
               │  │ - Report narrative generation     │  │
               │  └──────────────┬───────────────────┘  │
               └────────────────┬──────────────────────┘
                                │
               ┌────────────────▼──────────────────────┐
               │  Results & Reports                     │
               │  - SQLite scan history                 │
               │  - Compliance scorecard                │
               │  - Findings + recommendations + code   │
               │  - MCP & agent graph (dynamic)         │
               │  - Markdown / HTML / SARIF             │
               │  - Scan comparison / trends            │
               └────────────────┬──────────────────────┘
                                │
               ┌────────────────▼──────────────────────┐
               │  LintAgent Interface Layer             │
               │                                        │
               │  ┌────────┐ ┌────────┐ ┌────────────┐ │
               │  │  CLI   │ │  MCP   │ │  GitHub    │ │
               │  │        │ │ Server │ │  Action    │ │
               │  │ (BYOK) │ │(pass-  │ │  (CI/CD)   │ │
               │  │        │ │ thru)  │ │            │ │
               │  └───┬────┘ └───┬────┘ └─────┬──────┘ │
               └──────┼──────────┼────────────┼────────┘
                      │          │            │
            ┌─────────┘    ┌─────┘     ┌──────┘
            ▼              ▼           ▼
       Terminal     Claude Code    GitHub PR
                    VS Code        (SARIF inline
                    Codex          findings)
                    Cursor
```

---

## 13. MCP Tools (Server Mode)

| # | Tool | Description |
|---|------|-------------|
| 1 | `scan_server(url)` | Full scan of a remote MCP server |
| 2 | `scan_local(path)` | Full scan of a local MCP server codebase |
| 3 | `scan_auth(url)` | OAuth 2.1 / MCP auth compliance audit |
| 4 | `scan_transport(url)` | Transport & session security checks |
| 5 | `scan_authorization(url)` | Scope & permission model audit |
| 6 | `scan_tools(url)` | Tool metadata & poisoning analysis |
| 7 | `scan_config(path)` | Local config file auditing |
| 8 | `scan_dependencies(path)` | Dependency CVE + secret scanning |
| 9 | `generate_report(scan_id, format)` | Generate report (md/html/sarif) |
| 10 | `get_recommendations(scan_id)` | Get fix recommendations for all findings |
| 11 | `list_scans()` | List previous scan results |
| 12 | `compare_scans(scan_a, scan_b)` | Diff two scans to track improvement |

### Future Tools (v2 — Auto-Fix)
| # | Tool | Description |
|---|------|-------------|
| 13 | `get_fixes(scan_id)` | Structured fix descriptors for all findings |
| 14 | `get_fix(finding_id)` | Fix descriptor for a specific finding |
| 15 | `export_fixes(scan_id, format)` | Export fixes as JSON/diff/patch |

---

## 14. Milestones

| Milestone | Scope |
|-----------|-------|
| **M1: Core Scanner** | Three-layer pipeline (YARA + Semgrep/ast-grep + Gitleaks/pip-audit), auth + transport auditors, CLI with pass/fail, Markdown reports |
| **M2: Full Auditors** | All 6 auditors (auth, transport, authorization, tools, config, supply chain), LLM hybrid classifier (BYOK), HTML + SARIF reports, compliance scorecard |
| **M3: MCP Server + CI/CD** | FastMCP server mode with LLM passthrough, `lintagent serve`, GitHub Action, SARIF → GitHub Security tab, MCP & agent graph in reports |
| **M4: Auto-Fix (Tier 3)** | Structured fix descriptors, code diffs/patches, consumable by coding agents (Claude Code, Cursor, Copilot) |
| **M5: Agent Scanner** | OWASP Agentic AI Top 10 coverage, agent card validation, multi-agent graph analysis, trust boundary verification |
| **M6: Enterprise** | OAuth-protected team server, policy engine, custom rules, trend dashboards, registry integrations (Smithery, mcp.run) |

---

## 15. Success Metrics

| Metric | Target |
|--------|--------|
| Scan completion time (single server) | < 30 seconds (without LLM), < 60 seconds (with LLM) |
| False positive rate | < 10% |
| MCP Spec checks covered | > 90% of spec requirements |
| OWASP MCP Top 10 coverage | 10/10 risks addressed |
| CoSAI framework coverage | > 80% of threat categories |
| Findings with code fix examples | > 80% |
| Report generation time | < 10 seconds |
| CI/CD integration | GitHub Actions (M3), GitLab CI (M6) |
| MCP client compatibility | 5+ clients (Claude Code, VS Code, Codex, Cursor, Gemini) |
| Registry gate adoption | At least 1 registry integration by M6 |

---

## 16. Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Target servers block scanning | Graceful degradation, report partial results |
| MCP spec still evolving | Modular auditors, easy to update per-check |
| OWASP MCP Top 10 still in beta | Track updates, modular architecture |
| CoSAI framework evolves | Separate mapping layer, easy to update |
| False positives erode trust | Conservative severity, evidence-based findings, tunable thresholds |
| LLM costs for classification | Rule-based first pass, LLM opt-in only, caching |
| Scanning could trigger server-side effects | Read-only probing, no destructive actions in default mode |
| Competitors (Snyk, Cisco) have enterprise distribution | Differentiate on remediation layer + MCP-as-MCP distribution |
| YARA/Semgrep rule maintenance burden | Community contribution model, auto-update from threat feeds |
| Privacy concerns (code leaving machine) | Fully local by default, LLM calls opt-in, no telemetry |

---

## 17. Open Questions

1. **Registry partnerships** — pursue integration with Smithery, mcp.run, or build own registry with gate built-in?
2. **Rule contribution model** — open-source the YARA/Semgrep rules for community contribution?
3. **Pricing model** — open-source core scanner, paid enterprise features (team server, policy engine)?
4. **Agent scanner scope** — separate MCP server (like MCPSec design) or integrated into LintAgent?
5. **npm/TypeScript support** — many MCP servers are TypeScript. When to add JS/TS scanning alongside Python?
