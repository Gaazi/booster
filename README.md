# 🚀 booster

> **Universal Ultra-Fast Caching, Minification, and Compression Booster for FastAPI, Python, Node.js, and Web Apps.**

[![Tests](https://img.shields.io/badge/tests-101%20passed-brightgreen.svg)](https://github.com/Gaazi/booster)
[![Node Tests](https://img.shields.io/badge/node%20tests-5%20passed-brightgreen.svg)](https://github.com/Gaazi/booster)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Node.js 18+](https://img.shields.io/badge/node-18+-green.svg)](https://nodejs.org/)

`booster` is a drop-in, zero-bloat performance engine designed to make your web applications and APIs **blazing fast (0.5ms - 2ms response times)** with zero configuration headaches.

---

## ⚡ Superpowers

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
   - Automatically generates Blake2b/SHA256 ETags.
   - Returns `304 Not Modified` with zero bytes transferred when client already has the data.

5. **Universal Zero-Config CDN Ready:**
   - Automatically attaches `CDN-Cache-Control`, `Surrogate-Control`, and `ETag` headers.
   - **Cloudflare**, **BunnyCDN**, and **Fastly** cache your website automatically without writing any API code!

---

## 📍 Where and in Which File to Add the Code?

### 1. In a FastAPI Project

In any FastAPI project, you add this in your **main application entry file** (usually named `main.py`, `app.py`, or `server.py`), right where you initialize `app = FastAPI()`.

#### Typical Project Structure:
```text
my_fastapi_project/
├── main.py          <--- 📍 ADD IT HERE!
├── models.py
├── routers/
└── requirements.txt
```

#### Exact Code Example (`main.py`):
```python
from fastapi import FastAPI
from booster import RocketBooster  # 1. Import booster

app = FastAPI(title="My Ultra-Fast API")

# ⚡ 2. Add this single line right below app = FastAPI():
RocketBooster.attach(app)

# 3. Your regular routes remain completely untouched:
@app.get("/")
def read_root():
    return {"message": "Hello World! Accelerated by booster 🚀"}

@app.get("/products")
def get_products():
    return [{"id": i, "name": f"Product {i}"} for i in range(100)]
```

Run your FastAPI app as usual:
```bash
uvicorn main:app --port 8000 --reload
```

---

### 2. In a Django Project

In Django, add the booster middleware to your `settings.py` inside `MIDDLEWARE`:

```python
# my_project/settings.py

MIDDLEWARE = [
    'booster.DjangoRocketMiddleware',  # <--- 📍 Add at or near the top
    'django.middleware.security.SecurityMiddleware',
    # ... other middlewares ...
]
```

---

### 3. In a Node.js / Express Project

In Node.js, add it to your main server file (e.g. `server.js` or `app.js`):

```javascript
// server.js
const express = require('express');
const { booster } = require('booster-node'); // 1. Import booster-node

const app = express();

// ⚡ 2. Add this single line:
app.use(booster());

app.get('/api/users', (req, res) => {
  res.json({ users: [{ id: 1, name: "Ali" }] });
});

app.listen(3000, () => console.log('Rocket server listening on :3000'));
```

---

## 🖱️ One-Click Standalone Mode (Zero Code Changes)

If you don't want to edit any project files or want to accelerate a legacy website:

1. Double-click **`start.bat`** (or run `python run.py`).
2. The **Cyberpunk Dark Dashboard** automatically opens at `http://127.0.0.1:5050`.
3. Hit **"🔍 Auto-Detect Local Port"** (auto-finds port 8000, 3000, etc.).
4. Click **"⚡ Boost Website Now"**!
5. Your accelerated site runs with real-time latency graphs and analytics.

---

## 🌐 Automatic Multi-CDN Integration (Cloudflare, BunnyCDN, Fastly)

When you point your domain to **Cloudflare** or **BunnyCDN**:
* `booster` automatically emits standardized headers:
  * `CDN-Cache-Control: public, max-age=300, stale-while-revalidate=60`
  * `Surrogate-Control: max-age=300`
* Cloudflare and BunnyCDN will **automatically detect and cache your pages globally** across edge nodes without any API configuration!

If you want automated background CDN cache purging when you clear cache:
Set environment variables:
```bash
export CLOUDFLARE_ZONE_ID="your-zone-id"
export CLOUDFLARE_API_TOKEN="your-api-token"
```
Or for BunnyCDN:
```bash
export BUNNY_ACCESS_KEY="your-access-key"
export BUNNY_PULL_ZONE_ID="your-pull-zone-id"
```
`booster` will automatically purge the CDN edge cache in the background with zero latency overhead.

---

## 🧪 Automated Testing

### Run Python Test Suite (101 Tests):
```bash
python -m pytest tests/
```

### Run Node.js Test Suite (5 Test Suites):
```bash
node --test booster-node/test/test.js
```

---

## 🗺️ Multi-Language Roadmap

Detailed architectural plans for extending `booster` without code bloat:
* [Multi-Language Roadmap](plans/ROADMAP_MULTI_LANGUAGE.md)
* [Node.js Plan](plans/NODEJS_BOOSTER_PLAN.md) — *Completed (Phase 1)*
* [Go Plan](plans/GO_BOOSTER_PLAN.md) — *Phase 2*
* [Rust Plan](plans/RUST_BOOSTER_PLAN.md) — *Phase 3*
* [CDN Integration Guide](plans/CDN_INTEGRATION_PLAN.md)

---

## 📄 License

MIT © [Ubaidullah Ghazi](https://github.com/Gaazi)
