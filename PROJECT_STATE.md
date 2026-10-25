# Project State
Updated: 2026-10-25 10:20
## Done
- Focused review of new work 8655226..447693df1cb87b45280eb8f67becda0a497c6fb0; reproduced and fixed shared-invalidation rotation loss, Node in-flight cache refill, explicit local-bus crashes and scaffolded adapters silently ignoring the configured shared bus. Evidence: docs/REVIEW_2026-10-25.md.
- Python/Node now share a generation-tagged JSON journal and bounded directory lock. Actual concurrent Python/Node publishers retain all notices. Two-process worker tests remain in place. All workers must upgrade together; network filesystems remain unsupported.
- Rejected malformed boolean/path/numeric settings, fixed invalid and duplicate Age headers with a shared Python age helper, corrected Django age advancement and escaped generated Python path literals.
- Fixed real Node measure CLI default sampling, count validation and bounded request failures. Its verdict now calls runtime admission policy. Python URL classification now parses the URL path. Updated promotion wrapper for explicit authorization notes and annotated merge commits.
- Local release gate: 261 Python tests and 57 Node tests passed. TypeScript build/public types, syntax, changed-file audit, pip check and npm audit (0 reported findings) passed. Python 1.0.4.dev1 and Node 1.0.1; source map refreshed and global rules sync updated the managed pointer.
- Fix commit d2d429b3ce12de4d54396662f00a5b10bfbd69e0 passed GitHub run 40163337136, including installed packages. Extended the read-only build gate to main and explicitly selected Node 24 in full Python jobs for deterministic cross-runtime coverage.
- Existing plugin recipes, scaffolding, operator snapshots, measurement/doctor commands and conformance examples remain. Host installation is an operator action; this task changed no consuming website or live service.
## Pending
- User explicitly requested dev-to-demo then demo-to-main if checks pass. Require successful exact-commit CI/package verification after the workflow update before promotion; do not deploy or restart a website.
- Physical-phone/public-network, real load-balancer/container-restart and production validation remain unproven. A crashed directory-lock owner needs explicit operator recovery. Existing nonfatal Starlette/module-detection warnings remain.
## Next Step
- After successful dev CI, promote dev to demo with the user instruction recorded, wait for successful demo CI, then promote demo to main and immediately push each merge.
