# 🚀 booster-node

> **Zero-Dependency Ultra-Fast Caching, Minification, and Compression Booster for Node.js, Express, and Next.js.**

---

## ⚡ Superpowers

* **Zero Dependencies:** Pure Node.js standard library (`zlib`, `crypto`, `http`). Installs in 0.1s.
* **Microsecond Cache:** In-memory LRU cache with TTL expiration.
* **C++ Brotli & Gzip:** Uses Node's built-in V8/C++ `zlib` engine.
* **On-the-fly Minification:** HTML, CSS, and JSON compressed before transmission.
* **Universal CDN Ready:** Injects `CDN-Cache-Control`, `Surrogate-Control`, and `ETag` headers automatically.

---

## 📦 Quickstart (Express.js)

```javascript
const express = require('express');
const { booster } = require('booster-node');

const app = express();

// ⚡ 1-line rocket acceleration:
app.use(booster());

app.get('/api/users', (req, res) => {
  res.json({ users: [{ id: 1, name: "Ali" }] });
});

app.listen(3000, () => console.log('Rocket server running on :3000'));
```

## 📦 Quickstart (TypeScript / Express.js)

```typescript
import express, { Request, Response } from 'express';
import { booster, BoosterOptions } from 'booster-node';

const app = express();

const options: BoosterOptions = {
  maxItems: 5000,
  ttl: 600, // 10 minutes
  minCompressSize: 256
};

// ⚡ 1-line rocket acceleration with full type-safety:
app.use(booster(options));

app.get('/api/users', (req: Request, res: Response) => {
  res.json({ users: [{ id: 1, name: "Ali" }] });
});

app.listen(3000, () => console.log('Rocket server running on :3000'));
```

---

## 🧪 Testing

```bash
npm test
```
