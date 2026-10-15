# booster commands

Run from the project root directory.

| Action | Command |
| :--- | :--- |
| One-click setup & launch | `.\start.bat` |
| CLI accelerator launch | `booster --target http://127.0.0.1:8000` |
| Run full Python tests (109 tests) | `pytest` |
| Run Node.js tests (5 suites) | `node booster-node/test/test.js` |
| Force check updates | `curl http://127.0.0.1:5050/api/check-update` |
| Clear cache & trigger CDN purge | `curl -X POST -H "X-Booster-Admin: 1" http://127.0.0.1:5050/api/clear-cache` |
| Refresh docs & CODEMAP | `python refresh_docs.py` |
| Compile & syntax verification | `python -m compileall booster tests run.py setup_plugin.py` |
| Preview a verified dev build for demo | `python -m scripts.promote_demo` |
| Promote dev to demo when explicitly requested | `python -m scripts.promote_demo --authorized` |
| Verify a compressed download | `python -m scripts.build_bundle verify PATH.zip --sha FULL_COMMIT_SHA` |

Pushes/merges on `dev` and `demo` automatically run tests and create compressed
Python/Node downloads. See [verified builds and promotion](docs/BUILDS.md).
For workload-specific recommendations, see [where Booster helps](docs/USE_CASES.md).

Dashboard: http://127.0.0.1:5050/
Accelerated Gateway: http://127.0.0.1:5051/
