# go_fast commands

Run from the plugin folder unless using an absolute script path.

| Action | Command |
| :--- | :--- |
| One-click setup and launch | `.\start.bat` |
| Terminal setup and launch | `python setup_plugin.py` |
| Choose upstream | `python setup_plugin.py --target http://127.0.0.1:8000` |
| Verify setup only | `python setup_plugin.py --check` |
| Launch without browser | `python setup_plugin.py --no-browser` |
| Start prepared environment | `.\.venv\Scripts\python.exe run.py` |
| Installed command | `go-fast --target http://127.0.0.1:8000` |
| Install into host environment | `python -m pip install ./go_fast` from its parent |
| Test | `.\.venv\Scripts\python.exe -m pytest -q` |
| Dependency audit | `.\.venv\Scripts\python.exe -m pip_audit --skip-editable` |
| Static medium/high audit | `.\.venv\Scripts\python.exe -m bandit -r go_fast run.py setup_plugin.py -ll` |
| Refresh map and docs | `python refresh_docs.py` |

Dashboard: http://127.0.0.1:5050/. Accelerated app: http://127.0.0.1:5051/.
First setup needs internet; later launches reuse the isolated environment.
Start the origin first for automatic port detection.
Public caching requires Cache-Control: public.

```powershell
curl.exe -i -H "Accept-Encoding: br, gzip" http://127.0.0.1:5051/public-items
curl.exe http://127.0.0.1:5050/api/stats
curl.exe -X POST -H "X-Go-Fast-Admin: 1" http://127.0.0.1:5050/api/clear-cache
git status
```
