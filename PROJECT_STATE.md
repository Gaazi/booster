# Project State
Updated: 2026-10-15 08:21
## Done
- Completed lightweight dependency-free core and lazy server/cdn/brotli extras; server extra requires Python 3.11+, core remains 3.10+. Invite remains the other agent responsibility.
- GitHub run 38672868256 succeeded for commit 39082e6: core 3.10, full Python 3.11/3.14, Node 22/24, compressed packages and clean core/server/Node installations. Its downloaded bundle passed commit/checksum verification locally.
- Local current checks: 183 Python tests passed; prior unchanged Node JS/TS checks passed 7/3. Syntax, diff, function-size/types, pip checks and actual wheel/tarball installs passed.
- Pinned current official Node24 actions by commit SHA. Promotion previews only verify/download; authorized promotion safely catches up an old local demo, preserves unpublished work, then fast-forwards and immediately pushes.
- Research, limits and workload recommendations are in docs/USE_CASES.md; compressed build/download and promotion guidance is in docs/BUILDS.md.
## Pending
- No demo/main promotion, deployment or repository-protection change performed. Node parity, multi-worker invalidation and real-phone/production measurements remain follow-ups.
- Invite integration was recorded at a7aa413 with 358 application tests; coordinate future package pin updates with its agent.
## Next Step
- Use the successful current dev CI artifact; promote via python -m scripts.promote_demo --authorized only on a current explicit request.
