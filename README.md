# 🚀 booster

> **Universal Ultra-Fast Caching, Minification, and Compression Engine for Python, Node.js, and Web Apps.**

[![Stable Release](https://img.shields.io/badge/release-v1.0.0%20(Stable)-brightgreen.svg)](https://github.com/Gaazi/booster/releases/tag/v1.0.0)
[![Python Tests](https://img.shields.io/badge/python%20tests-109%20passed-brightgreen.svg)](https://github.com/Gaazi/booster)
[![Node Tests](https://img.shields.io/badge/node%20tests-5%20passed-brightgreen.svg)](https://github.com/Gaazi/booster)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Node.js 18+](https://img.shields.io/badge/node-18+-green.svg)](https://nodejs.org/)

`booster` is a zero-config, ultra-lightweight performance accelerator that brings **sub-millisecond (0.1ms - 2ms) response times** to APIs and web applications. It operates in pure process memory (RAM) with zero external databases or Redis requirements, making it drop-in compatible with every hosting environment from shared cPanel to enterprise cloud clusters.

---

## 🏛️ Release & Branch Architecture

We follow a strict 3-tier release pipeline to guarantee production stability:

| Branch | Release Tag | Role & Environment | Stability |
| :--- | :--- | :--- | :--- |
| **`main`** | [**`v1.0.0`**](https://github.com/Gaazi/booster/releases/tag/v1.0.0) | **Production Official Stable Release**. The core public source code. | 🟢 100% Stable |
| **`demo`** | [**`v1.0.0-beta.1`**](https://github.com/Gaazi/booster/releases/tag/v1.0.0-beta.1) | **Staging / Beta Candidate**. Pre-release testing and client validation. | 🟡 Beta (Tested) |
| **`dev`** | [**`v1.0.0-alpha.1`**](https://github.com/Gaazi/booster/releases/tag/v1.0.0-alpha.1) | **Active Development / Alpha**. Bleeding-edge features and new language engines. | 🧪 Alpha (Active Dev) |

---

## ⚡ Superpowers

1. **Microsecond In-Memory Cache (RAM):**
   - High-throughput LRU cache with monotonic TTL expiration.
   - Microsecond reads (`~0.001ms`), up to **50x faster than Redis** with zero network hop latency.
   - Automatic cache invalidation on write mutations (`POST`, `PUT`, `DELETE`, `PATCH`).

2. **Adaptive Brotli & Gzip Compression:**
   - C-level Brotli compression (reduces text payload by up to 85%).
   - Automatic client quality negotiation and streaming fallback.

3. **On-the-fly Minification:**
   - Instant whitespace, comment, and redundant character stripping for HTML, CSS, JavaScript, and JSON.

4. **Universal Multi-CDN Integration:**
   - Automatically attaches `CDN-Cache-Control` and `Surrogate-Control` headers.
   - **Cloudflare**, **BunnyCDN**, and **Fastly** cache your pages worldwide across hundreds of edge data centers.
   - Optional automated background edge cache purging.

5. **Smart Hybrid Update Engine:**
   - **On Dashboard Open**: Instantly checks for fresh releases on GitHub without stale data.
   - **Background Monthly Heartbeat**: Quiet periodic check for headless or background server deployments.
   - **Auto-Patch**: Minor bug fixes auto-install silently without downtime.
   - **Major Notification**: Visually displays upgrade banners in the dashboard and logs.

---

## 📍 Quickstart & Integration

### 1. In a FastAPI Project

```python
# main.py
from fastapi import FastAPI
import booster

app = FastAPI(title="My Ultra-Fast API")

# ⚡ One-line acceleration:
booster.attach(app)

@app.get("/")
def read_root():
    return {"message": "Hello World! Accelerated by booster 🚀"}
```

Run with uvicorn:
```bash
uvicorn main:app --port 8000 --reload
```

---

### 2. In a Django Project

Add middleware inside `settings.py`:

```python
# my_project/settings.py
MIDDLEWARE = [
    'booster.DjangoRocketMiddleware',  # ⚡ Add near top
    'django.middleware.security.SecurityMiddleware',
    # ... other middlewares ...
]
```

---

### 3. In a Node.js / Express Project

```javascript
// server.js
const express = require('express');
const { booster } = require('booster-node');

const app = express();

// ⚡ One-line middleware:
app.use(booster());

app.get('/api/data', (req, res) => {
  res.json({ message: "Accelerated by booster-node 🚀" });
});

app.listen(3000, () => console.log('Listening on :3000'));
```

---

## 🌐 Live Hosting Deployment (Cloud, VPS & cPanel)

### A. cPanel / Shared Hosting (No Root / No Redis Needed!)
Unlike Redis or Varnish which fail on cPanel due to lack of root permissions, `booster` runs natively:
1. In cPanel, click **"Setup Python App"** (or **"Setup Node.js App"**).
2. Choose Python 3.10+ (or Node 18+).
3. In `requirements.txt`, add:
   ```text
   booster
   ```
4. In your `passenger_wsgi.py`, simply wrap your application with `booster.attach(app)`.
5. Restart the Python app in cPanel. Done!

### B. VPS Hosting (Ubuntu / Debian / CentOS)
Run as a systemd service or reverse proxy:
```bash
# Start standalone accelerator proxying to your local upstream app
booster --target http://127.0.0.1:8000
```
- Dashboard available at `http://YOUR_SERVER_IP:5050`
- Accelerated Gateway at `http://YOUR_SERVER_IP:5051`

### C. Cloud Hosting (AWS, GCP, DigitalOcean, Docker, Render, Railway)
Add `booster` to your `requirements.txt` or `package.json`. No external database, cache cluster, or Redis instance required—saving you \$15-\$50/month in managed cache fees.

---

## 🖥️ One-Click Standalone GUI Dashboard

If you want to accelerate an existing website without editing code:
1. Run `python run.py` (or double-click `start.bat` on Windows).
2. The Dashboard opens automatically at `http://127.0.0.1:5050`.
3. Click **"🔍 Auto-Detect Local Port"** (auto-detects port 8000, 3000, etc.).
4. Click **"⚡ Boost Website Now"**.
5. View real-time hit ratio, bandwidth savings, and request logs.

---

## 🧪 Comprehensive Verification & Tests

### Run Python Test Suite (109 Tests):
```bash
pytest
```

### Run Node.js Test Suite (5 Test Suites):
```bash
node booster-node/test/test.js
```

---

## 🗺️ Multi-Language Roadmap

- [Multi-Language Roadmap](plans/ROADMAP_MULTI_LANGUAGE.md)
- [Node.js Engine (booster-node)](booster-node/README.md) — *Completed (Phase 1)*
- [Go Engine Plan](plans/GO_BOOSTER_PLAN.md) — *Phase 2*
- [Rust Engine Plan](plans/RUST_BOOSTER_PLAN.md) — *Phase 3*
- [Multi-CDN Guide](plans/CDN_INTEGRATION_PLAN.md)

---

## 📄 License

MIT © [Ubaidullah Ghazi](https://github.com/Gaazi)
