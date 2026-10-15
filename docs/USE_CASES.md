# Where Booster is useful

Reviewed: 2026-10-15. These are workload-based recommendations, not measured
speed promises. Read [INTEGRATION.md](INTEGRATION.md) for actual engine policies
and [BUILDS.md](BUILDS.md) for verified compressed distributions.

## Choose by response, not just by website category

| Website/workload | Likely benefit | Safe starting scope | Other work still needed |
| :--- | :--- | :--- | :--- |
| Blogs, news, documentation, educational content | Repeated public assets; genuinely identical public pages may reduce rendering work | Start with CSS/JS/fonts; add public HTML only after privacy and freshness checks | Publishing invalidation, editorial freshness, image delivery |
| Invite and personalized cards | Shared styles, scripts and fonts can avoid repeated origin file reads | Public versioned assets; keep guest HTML, signed links and personal data outside shared caching | Measure real-phone card opening while retaining styles, music and animations |
| Account dashboards and private portals | Public interface assets can benefit across visits/users | Public assets only; never shared-cache account/admin/session responses | Database/query tuning, authorization, private browser policy |
| Shops and booking sites | Product images/static assets and selected public catalog responses | Start with assets; opt into public catalog freshness deliberately | Price/stock/currency/location rules, cart and checkout isolation; revalidate transaction data at the authoritative backend |
| Public read-heavy APIs | Repeated identical unauthenticated GET responses can reduce repeated work | Explicitly public endpoints without credentials, user scope or unsupported variation | Mutation invalidation, quotas, query cost and response freshness |
| Forms, uploads and write-heavy apps | Static assets can benefit; frequent writes may repeatedly invalidate RAM cache | Assets; bypass writes, uploads and signed URLs | Upload validation, storage and database performance |
| Video, music, live feeds and large downloads | Small interface assets can benefit | Keep range requests, streams and large media on their existing delivery path | Media CDN/object storage, proper range/streaming support |
| Static sites already well served by browser/CDN caching | Additional origin RAM benefit may be small | Measure origin traffic first; retain versioned assets and correct HTTP headers | Image sizing, JavaScript work and network latency |

For all cases, origin responses must explicitly be eligible/public. Route names
or file extensions alone do not prove privacy. Current conservative policies
bypass credentials, user/session scope, ranges and varying responses; they do
not implement arbitrary personalized cache partitions.

Public-page caching is useful only when visitors receive the same representation
and the website can tolerate the configured freshness. Do not cache a logged-in
navigation bar, CSRF token, customer-specific price or guest name as shared HTML.
Use `private` to prohibit shared storage; use `no-store` when storage anywhere is
unwanted. `no-cache` means revalidate before reuse, not "never store".
These distinctions come from [HTTP Caching, RFC 9111](https://www.rfc-editor.org/rfc/rfc9111.html).

Shopify's own guidance distinguishes catalog queries from carts/customer sessions
and supports explicit freshness strategies. Applying that distinction to Booster
is a design recommendation, not evidence that Booster is a drop-in Shopify
plugin. See [Shopify query caching](https://shopify.dev/docs/storefronts/hydrogen/data-fetching/caching)
and [price vs. personalized data](https://shopify.dev/docs/storefronts/headless/hydrogen/performance/data-loading).

## Compression, hosting and practical limits

- A compressed wheel/Node archive simplifies distribution and installation.
  It does not automatically reduce a website's HTTP responses or browser work.
- HTTP GZip/Brotli mainly helps suitable text payloads. Keep one compression
  owner. Preserve negotiated encodings and decoded bytes. Build-time minification
  and precompressed stable assets can avoid repeated request-time work;
  [NGINX documents precompressed GZip delivery](https://nginx.org/en/docs/http/ngx_http_gzip_static_module.html).
- Cache versioned CSS/JS in the browser as well as at the origin. A browser/CDN
  hit can avoid reaching Booster altogether. Update asset URLs when their bytes
  change; see [versioned HTTP caching](https://web.dev/articles/codelab-http-cache).
- Multi-worker RAM caches are independent. Plan invalidation across processes
  before relying on fresh public HTML/API values. Count the RAM budget per worker,
  plus Python/Node runtime and cache metadata overhead.
- First requests and restarts have cold caches. On already fast/static workloads,
  middleware/compression overhead may outweigh avoided reads; compare both modes.
- Media seeking and resumable downloads depend on partial responses. Booster's
  range/stream bypass must remain intact; see [HTTP Range semantics](https://www.rfc-editor.org/rfc/rfc9110.html#name-range-requests).
- Direct integrations exist for the documented Python ASGI/Django and Node
  runtimes. PHP/WordPress, managed storefronts and browser-only sites do not gain
  native support merely because they serve HTML. Review their hosting/adapters
  separately; do not promise universal plug-and-play compatibility.

## Decide with evidence

Measure the same routes and dataset with Booster disabled/enabled:

1. First request after restart, repeated warm requests and concurrent traffic:
   p50/p95 latency, origin calls/file reads, CPU, process RAM and response size.
2. Private pages and two different users: correct decoded content, headers,
   no cross-user reuse; publishing/writes must respect freshness expectations.
3. Real mobile/desktop use: loading (LCP), interaction (INP), layout stability
   (CLS) and card-specific readiness when relevant. Local server milliseconds
   cannot substitute for real-user experience; see [Google Web Vitals](https://web.dev/articles/vitals).

Keep a configuration only when it improves the measured bottleneck without
hurting correctness or resource use. Do not infer whole-page speedups from
cache-hit time alone. Booster cannot fix slow SQL, oversized images, blocking
third-party scripts or expensive browser animation merely by caching responses.
