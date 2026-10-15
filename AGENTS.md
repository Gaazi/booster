<!-- shared-agent:start -->
Read `~/.agents/global-agent-rules/AGENTS.md` before project rules.
Read `PROJECT_STATE.md` first. Update it after each completed task.
On first visit or a changed master, run `python ~/.agents/manage_agents.py project sync --repo <project-root>`.
Shared master SHA256: `e845210408af1e492c66a3599e1e4f4e15e5644a7ff049aac6807d4ffcbb97be`.
<!-- shared-agent:end -->

# Project Instructions: Booster

## Booster integration reference

Booster is the single reusable engine; consumers import it instead of copying
its caching/compression code.
- **Full Architecture & Features**: [docs/FEATURES_AND_ARCHITECTURE.md](docs/FEATURES_AND_ARCHITECTURE.md) contains the exhaustive specification, request lifecycles, caching mechanics, privacy boundaries, and module map.
- **Integration & Review**: [docs/INTEGRATION.md](docs/INTEGRATION.md) covers route selection, privacy boundaries, middleware order, installation, and verification.
- **Handoff & Priorities**: [docs/NEXT_STEPS.md](docs/NEXT_STEPS.md) defines the next agent's prioritized tasks.
- **Workloads & Limits**: [docs/USE_CASES.md](docs/USE_CASES.md) provides workload suitability recommendations.

### Core Facilities at a Glance
1. **In-Memory Cache (RAM)**: Microsecond LRU cache (`FastMemoryCache`) bounded by size and bytes (`max_cache_bytes`), monotonic TTL, ETag generation, 304 conditional responses.
2. **HTTP RFC 9111 Privacy**: Automatic bypass for cookies, `Authorization`, session tokens, private/no-store responses, and hop-by-hop headers.
3. **Adaptive Compression**: Client-negotiated Brotli (`br`) and Gzip (`gzip`) with textual MIME filtering and minimum payload thresholds.
4. **Conservative Minification**: Lossless UTF-8 JSON minification (`FastMinifier`); HTML/CSS formatting is preserved intact to avoid layout bugs.
5. **Mutation Invalidation**: Automatic pre- and post-write cache invalidation on `POST`, `PUT`, `DELETE`, `PATCH`.
6. **Multi-CDN Integration**: Standard edge headers (`CDN-Cache-Control`, `Surrogate-Control`) and zero-overhead purging for Cloudflare, BunnyCDN, and Fastly.
7. **Standalone Gateway & Dashboard**: Reverse proxy on port 5051 with local telemetry GUI on port 5050, secured by `LocalAccessGuard` and `X-Booster-Admin`.

## Autonomous Agent Directives (MANDATORY FOR ALL AGENTS)

> **ATTENTION VISITING AGENT**:
> To conserve context window tokens and prevent memory bloat, follow this strict protocol without requiring explicit user reminders.

### 1. Permitted Reading Scope (Documentation First)
- **Primary Entry Points**: Read ONLY:
  1. `PROJECT_STATE.md` (Check current status, pending tasks, and next steps).
  2. `README.md` (High-level features, quickstart, and deployment).
  3. `docs/FEATURES_AND_ARCHITECTURE.md` (Comprehensive deep-dive: complete features, request lifecycles, caching mechanics, privacy rules, and module index).
  4. Relevant specialized files in `docs/` (`INTEGRATION.md`, `USE_CASES.md`, `NEXT_STEPS.md`, `BUILDS.md`) or `COMMANDS.md`.
- **DO NOT Read Entire Codebase**:
  - Never recursively scan or bulk-read source code directories (`booster/`, `booster-node/`, `tests/`) upon arrival.
  - Indiscriminate code scanning unnecessarily wastes context window tokens when documentation already defines the system.

### 2. On-Demand Surgical Code Inspection
- Code reading is **STRICTLY ON-DEMAND**:
  - Inspect source files ONLY when actively working on an explicit coding, debugging, or refactoring task requested by the user.
  - Use `rg <symbol>` to pinpoint the exact location.
  - Read only the specific line range (e.g., target function/class) needed for the edit.

### 3. Agent Ignore & Exclusions
- Always honor `.agentignore`, `.cursorignore`, and `.gitignore`.
- Never inspect dependencies or build artifacts (`.venv`, `node_modules`, `build`, `dist`, `.trash`, caches).

### 4. Mandatory State Maintenance
- After completing every task or conversation, you MUST update `PROJECT_STATE.md`.
- Keep `PROJECT_STATE.md` under 50 lines with current Done, Pending, and Next Step.
- Commit each completed task and push immediately to the authorized branch (`dev`).

### 5. Node.js & TypeScript Mandate (STRICTLY ENFORCED)
- **Full TypeScript Transition**: The project has completely migrated from JavaScript to TypeScript for Node.js (`booster-node`).
- **NO Vanilla JavaScript (`.js`) Development**: Agents must NEVER write, modify, or add new features or tests in JavaScript (`.js`). All Node.js logic and tests MUST be implemented strictly in TypeScript (`src/*.ts`, `test/test-ts.ts`).
- **Native TypeScript Test Runner**: All Node tests execute via `node --test booster-node/test/test-ts.ts`.

