# go_fast 🚀 Rocket Speed Accelerator

> **Universal Ultra-Fast Caching, Minification, and Compression Plugin for FastAPI, Python, and Web Apps.**

`go_fast` is a drop-in performance engine designed to make your web applications and APIs **blazing fast (0.5ms - 2ms response times)** with zero configuration headaches.

---

## ⚡ Key Superpowers

1. **Microsecond In-Memory Cache (RAM):**
   - High-throughput LRU cache with TTL expiration.
   - Cached API endpoints respond in less than **1 millisecond**.
   - Automatic cache invalidation on write mutations (`POST`, `PUT`, `DELETE`, `PATCH`).

2. **Adaptive Brotli & Gzip Compression:**
   - C-level Brotli compression (reduces payload by up to 85%).
   - Automatic fallback to standard Gzip/Deflate.

3. **On-the-fly Minification:**
   - Instant whitespace and comment stripping for HTML, CSS, JavaScript, and JSON.

4. **HTTP 304 & ETag Engine:**
   - Automatically generates Blake2b ETags.
   - Returns `304 Not Modified` with zero bytes transferred when client already has the data.

5. **Two Execution Modes:**
   - **Mode A (FastAPI / ASGI Drop-in):** Add 1 line in your Python codebase.
   - **Mode B (One-Click Standalone Gateway):** Double-click `start.bat` to boost any local or remote website without modifying a single line of code!

---

## 🚀 Quickstart

### 1. One-Click Standalone Mode (Windows)
Double-click `start.bat` (or run `python run.py`).
- The **Cyberpunk Dark-Themed Dashboard** automatically launches at: `http://localhost:5050`
- Hit **"Auto-Detect Local Port"** or enter your app URL (e.g. `http://localhost:8000`).
- Access your accelerated app at: `http://localhost:5050/site/`
- Watch live latency drop and bandwidth saved in real time!

---

### 2. FastAPI Drop-In Plugin (1 Line of Code)

```python
from fastapi import FastAPI
from go_fast import RocketBooster

app = FastAPI()

# ⚡ One-line activation:
RocketBooster.attach(app)

@app.get("/items")
def get_items():
    return [{"id": i, "name": f"Product {i}"} for i in range(100)]
```

---

### 3. Django Setup

Add `DjangoRocketMiddleware` to your `settings.py`:

```python
MIDDLEWARE = [
    'go_fast.DjangoRocketMiddleware',
    # ... other middlewares ...
]
```

---

## 🧪 Running Tests

```bash
python -m pytest tests/
```


### Reliability and verification

Run `python -m pytest -q` for regression coverage. Run `python refresh_docs.py`
to regenerate `CODEMAP.md` and the ignored browsable `docs/index.html`.
Shared caches bypass authenticated/cookie requests, private responses, custom
Vary fields, and explicit cache directives. ASGI streaming responses pass through.
Compression respects quality values and reuses up to 64 small payload variants.
The dashboard gateway is intended for local development and binds to loopback.
