# 📋 go_fast Terminal Command Sheet

This cheat sheet contains all essential terminal and CLI commands for running, testing, benchmarking, and integrating `go_fast`.

---

## 1. 🚀 Launching the Dashboard & Accelerator

| Action | Command |
| :--- | :--- |
| **One-Click Start (Windows)** | `.\start.bat` |
| **Run Accelerator via Python** | `python run.py` |
| **Run via Uvicorn directly** | `uvicorn run:app --host 127.0.0.1 --port 5050` |
| **Run with auto-reload (Dev)** | `uvicorn run:app --host 127.0.0.1 --port 5050 --reload` |

---

## 2. 📦 Installation & Setup

| Action | Command |
| :--- | :--- |
| **Install in editable mode** | `python -m pip install -e .` |
| **Install required dependencies** | `python -m pip install fastapi uvicorn httpx brotli` |
| **Verify global import** | `python -c "import go_fast; print(go_fast.__version__)"` |

---

## 3. 🧪 Running Tests & Verification

| Action | Command |
| :--- | :--- |
| **Run full test suite** | `python -m pytest tests/` |
| **Run with verbose output** | `python -m pytest tests/ -v` |
| **Run specific test file** | `python -m pytest tests/test_booster.py` |
| **Run with test summary** | `python -m pytest tests/ -ra` |

---

## 4. ⚡ FastAPI Project Integration

In your FastAPI project (`main.py`):
```python
from fastapi import FastAPI
from go_fast import RocketBooster

app = FastAPI()
RocketBooster.attach(app)
```

Run your FastAPI project:
```bash
uvicorn main:app --port 8000 --reload
```

---

## 5. 🔍 Testing & Benchmarking Endpoints

### Test Caching & Compression with `curl`
```bash
# 1. First Request (Prime Cache + Brotli compression)
curl -i -H "Accept-Encoding: br, gzip" http://127.0.0.1:5050/site/

# 2. Second Request (Check Cache Hit & ETag)
curl -i -H "Accept-Encoding: br, gzip" http://127.0.0.1:5050/site/

# 3. Test HTTP 304 Not Modified
curl -i -H 'If-None-Match: W/"your-etag-hash"' http://127.0.0.1:5050/site/
```

### Inspect Live Telemetry via API
```bash
# Get live performance stats
curl http://127.0.0.1:5050/api/stats

# Auto-detect running local ports
curl http://127.0.0.1:5050/api/detect-local

# Clear cache on demand
curl -X POST http://127.0.0.1:5050/api/clear-cache
```

---

## 6. 🛠️ Git & Project Management

```bash
# Check status
git status

# View commit history
git log --oneline -n 5
```
