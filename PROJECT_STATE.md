# Project State
Updated: 2026-10-15 08:25
## Done
- Lightweight dependency-free core and lazy server/cdn/brotli extras completed. Core supports Python 3.10+; current server extra requires 3.11+. Invite remains the other agent responsibility.
- GitHub run 38673219129 succeeded for 9e3cf675: core Python 3.10, full server 3.11/3.14, Node 22/24, compressed packaging and clean installed-package checks. Current official actions are pinned by full SHA on Node24.
- Local full suite: 183 Python tests passed; unchanged Node checks passed 7 JS and 3 TS tests. Syntax, changed-file/function audit, pip checks and wheel/Node tarball installations passed.
- Downloaded current successful bundle to build/promotion-38673219129-0ql3admt/booster-9e3cf675506d6da8d4da395137b2bc39398a117a.zip; full commit, inventory and SHA-256 checks passed. Promotion preview passed and changed no demo refs.
- Automatic dev/demo builds reuse only successful exact-commit dev artifacts. Authorized promotion safely catches up an old local demo, preserves unpublished work, fast-forwards and immediately pushes.
- Research and workload limits are in docs/USE_CASES.md; package/download and promotion instructions are in docs/BUILDS.md.
## Pending
- No demo/main promotion, deployment or protection-setting change performed. Node parity, multi-worker invalidation and real-phone/production measurements remain follow-ups.
- Invite integration was recorded at a7aa413 with 358 app tests; coordinate future package pin updates with its agent.
## Next Step
- Consume a successful verified dev CI artifact; use python -m scripts.promote_demo --authorized only on a current explicit promotion request.
