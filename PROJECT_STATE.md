# Project State
Updated: 2026-10-15 09:55
## Done
- Authored comprehensive features, architecture, and facilities reference in docs/FEATURES_AND_ARCHITECTURE.md, detailing in-memory caching, HTTP RFC 9111 compliance, mutation invalidation, compression, minification, CDN purging, proxy gateway, module map, and Mermaid request lifecycles.
- Updated README.md and AGENTS.md with prominent references, summaries, and direct links to FEATURES_AND_ARCHITECTURE.md to enable instant agent onboarding without broad codebase scans.
- Lightweight dependency-free core and lazy server/cdn/brotli extras completed. Core supports Python 3.10+; current server extra requires 3.11+.
- GitHub run 38673219129 succeeded for 9e3cf675: core Python 3.10, full server 3.11/3.14, Node 22/24, compressed packaging and clean installed-package checks.
- Local full suite: 183 Python tests passed; Node checks passed 7 JS and 3 TS tests.
## Pending
- No demo/main promotion, deployment or protection-setting change performed. Node parity, multi-worker invalidation and real-phone/production measurements remain follow-ups.
- Invite integration was recorded at a7aa413 with 358 app tests; coordinate future package pin updates with its agent.
## Next Step
- Consume a successful verified dev CI artifact; use python -m scripts.promote_demo --authorized only on a current explicit promotion request.
