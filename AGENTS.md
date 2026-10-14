<!-- shared-agent:start -->
Read `~/.agents/global-agent-rules/AGENTS.md` before project rules.
Read `PROJECT_STATE.md` first. Update it after each completed task.
On first visit or a changed master, run `python ~/.agents/manage_agents.py project sync --repo <project-root>`.
Shared master SHA256: `e845210408af1e492c66a3599e1e4f4e15e5644a7ff049aac6807d4ffcbb97be`.
<!-- shared-agent:end -->

# Project Instructions: Booster

## Autonomous Agent Directives (MANDATORY FOR ALL AGENTS)

> **ATTENTION VISITING AGENT**:
> To conserve context window tokens and prevent memory bloat, follow this strict protocol without requiring explicit user reminders.

### 1. Permitted Reading Scope (Documentation First)
- **Primary Entry Points**: Read ONLY:
  1. `PROJECT_STATE.md` (Check current status, pending tasks, and next steps).
  2. `README.md` (System architecture, high-level features, and usage).
  3. Relevant files in `docs/` or `COMMANDS.md` (Commands, API specs, and technical references).
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
