# Project State
Updated: 2026-10-15 19:03
## Done
- At the user explicit request, promoted verified dev bbaa523f79583dc3d6ed7332a013404bd8d00e72 to demo by fast-forward and immediately pushed. Verified the exact-commit compressed bundle before promotion; source CI 38743133151 succeeded.
- Demo CI 38743619845 succeeded. Requested demo-to-dev synchronization was already up to date; origin/dev and origin/demo both matched bbaa523 at the sync checkpoint. Returned to dev; this state record is a subsequent documentation-only dev commit.
- Runtime/privacy fixes at fd7bffb make canonical TypeScript the distributed Node runtime/declarations. Legacy JavaScript is excluded from package exports/files. Review evidence: docs/REVIEW_2026-10-15.md.
- Worker revision e57558e passed CI 38741590575 and local Python tests: 185 passed, 1 existing Starlette warning. Two actual-process tests prove local-only invalidation, credential bypass on stale peers, all-worker-clear recovery and static-only freshness.
- Node source/installed-package suites passed 31 each. CI covers Python core 3.10, full Python 3.11/3.14 and Node 22/24, builds compressed distributions and verifies installed packages. Prior syntax, changed-file audit, diff, pip check, type checks and npm audit passed.
## Pending
- Shared invalidation remains unimplemented: exclude mutable cached routes with multiple workers until coordination is tested. Physical-phone/production checks and complete Node/framework/HTTP parity remain unproven. Existing nonfatal warnings remain.
- No main merge, production deployment or restart performed. Invite remains with its agent.
## Next Step
- Use the verified bbaa523 compressed artifact on demo for deliberate consumer integration; measure real workloads and physical-phone performance. Any later promotion or production change requires a new explicit request.
