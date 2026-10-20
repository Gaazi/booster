# 🚀 booster

> **Universal Ultra-Fast Caching, Minification, and Compression Engine for Python, Node.js, and Web Apps.**

[![Stable Release](https://img.shields.io/badge/release-v1.0.0%20(Stable)-brightgreen.svg)](https://github.com/Gaazi/booster/releases/tag/v1.0.0)
[![Python Tests](https://img.shields.io/badge/python%20tests-183%20passed-brightgreen.svg)](https://github.com/Gaazi/booster)
[![Node Tests](https://img.shields.io/badge/TypeScript%20tests-31%20passed-brightgreen.svg)](https://github.com/Gaazi/booster)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Node.js 18+](https://img.shields.io/badge/node-18+-green.svg)](https://nodejs.org/)

`booster` accelerates eligible public responses with bounded process-memory caching,
optional minification and negotiated compression. It needs no external cache
database or Redis. Performance depends on the application and hosting; verify
middleware ordering, privacy and deployment compatibility before rollout.

---

## 🏛️ Release & Branch Architecture

We follow a strict 3-tier release pipeline to guarantee production stability:

| Branch | Release Tag | Role & Environment | Stability |
| :--- | :--- | :--- | :--- |
| **`main`** | [**`v1.0.0`**](https://github.com/Gaazi/booster/releases/tag/v1.0.0) | **Production Official Stable Release**. The core public source code. | 🟢 100% Stable |
| **`demo`** | [**`v1.0.0-beta.1`**](https://github.com/Gaazi/booster/releases/tag/v1.0.0-beta.1) | **Staging / Beta Candidate**. Pre-release testing and client validation. | 🟡 Beta (Tested) |
| **`dev`** | [**`v1.0.0-alpha.1`**](https://github.com/Gaazi/booster/releases/tag/v1.0.0-alpha.1) | **Active Development / Alpha**. Bleeding-edge features and new language engines. | 🧪 Alpha (Active Dev) |

---

## 📖 Documentation & Architecture

Before diving in, consult our architectural specifications and guides:
- 🏛️ **[Comprehensive Features & System Architecture](docs/FEATURES_AND_ARCHITECTURE.md)** — In-depth technical breakdown of caching mechanics, HTTP RFC 9111 privacy boundaries, mutation invalidation, module map, and Mermaid request lifecycles.
- 🧩 **[Plugin Recipe](docs/PLUGIN_RECIPE.md)** — Embed Booster as middleware inside any project: adapter file, registration order, route policy and rollout checks.
- ✅ **[Conformance Checklist](docs/CONFORMANCE_CHECKLIST.md)** — Copy-paste privacy and correctness tests each host project runs before rollout.
- 🛠️ **[Integration & Review Guide](docs/INTEGRATION.md)** — Safe website integration, framework setup (FastAPI, Django, Node.js), route policies, and middleware ordering.
- 🎯 **[Workload Recommendations & Use Cases](docs/USE_CASES.md)** — Decision matrix for blogs, APIs, ecommerce, and dynamic sites.
- 📦 **[Verified Compressed Builds](docs/BUILDS.md)** — Ready-to-install wheel/Node package downloads and verification.

---

## ⚡ Superpowers

Core caching and standard GZip require zero external dependencies and run on Python 3.10+.
The standalone GUI dashboard and proxy gateway use the optional `server` extra (Python 3.11+);
CDN HTTP calls and Brotli compression use the `cdn` and `brotli` extras.
Pin a reviewed revision as described in the [Integration Guide](docs/INTEGRATION.md).

1. **Microsecond In-Memory Cache (RAM):**
   - High-throughput LRU cache with monotonic TTL expiration.
   - RAM reads avoid an external cache database and its network round trip.
   - Automatic cache invalidation on write mutations (`POST`, `PUT`, `DELETE`, `PATCH`).

2. **Adaptive Brotli & Gzip Compression:**
   - C-level Brotli compression (reduces text payload by up to 85%).
   - Automatic client quality negotiation and streaming fallback.

3. **On-the-fly Minification:**
   - Conservative JSON whitespace minification; HTML/CSS formatting is preserved.
   - Frontend bundling and CSS/JavaScript minification remain build-tool responsibilities.

4. **Universal Multi-CDN Integration:**
   - Automatically attaches `CDN-Cache-Control` and `Surrogate-Control` headers.
   - **Cloudflare**, **BunnyCDN**, and **Fastly** cache your pages worldwide across hundreds of edge data centers.
   - Optional automated background edge cache purging.

5. **Smart Hybrid Update Engine:**
   - **On Dashboard Open**: Instantly checks for fresh releases on GitHub without stale data.
   - **Background Monthly Heartbeat**: Quiet periodic check for headless or background server deployments.
   - **Reviewed updates**: Auto-install is disabled by default; pinned consumers update after verification.
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

### Run Python Test Suite:
```bash
pytest
```

### Run Node.js Test Suite (Native TypeScript):
```bash
node --test booster-node/test/test-ts.ts
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
