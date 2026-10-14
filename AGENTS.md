<!-- shared-agent:start -->
Read `~/.agents/global-agent-rules/AGENTS.md` before project rules.
Read `PROJECT_STATE.md` first. Update it after each completed task.
On first visit or a changed master, run `python ~/.agents/manage_agents.py project sync --repo <project-root>`.
Shared master SHA256: `e845210408af1e492c66a3599e1e4f4e15e5644a7ff049aac6807d4ffcbb97be`.
<!-- shared-agent:end -->

# Project Instructions: Booster

## Context & Token Optimization Protocol (MANDATORY)

- **Default Reading Scope**:
  - Any visiting AI agent MUST ONLY read `PROJECT_STATE.md`, `README.md`, and relevant files in `docs/` or `COMMANDS.md`.
  - Do NOT read or scan the entire codebase or load whole directories into context upon arrival.
  - Do NOT waste context window tokens reading arbitrary files without an active task.

- **On-Demand Code Inspection**:
  - Source code reading is strictly restricted to situations where an active task or explicit user request requires modifying or debugging specific logic.
  - When code inspection is genuinely necessary:
    1. Use `rg` to find the exact target symbol or module.
    2. Read only the specific line ranges or function definitions needed.
    3. Do NOT load full files unless a complete rewrite of that file is explicitly required.
