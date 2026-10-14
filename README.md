# go_fast local acceleration plugin

Place this repository in a `go_fast` folder inside your project's main folder.
Double-click `start.bat`, or run `python setup_plugin.py`. Python 3.10+ is required;
the first setup needs internet access. The launcher prepares its own `.venv`,
updates its installer, installs dependencies, and opens the dashboard. Later
launches reuse the environment; changed requirements trigger setup again.
Your application's environment and source are unchanged.

Start your application first for automatic local port detection. If it cannot
be found, enter its trusted base URL in the dashboard, or run
`python setup_plugin.py --target http://127.0.0.1:8000`.

- Dashboard: `http://127.0.0.1:5050/`
- Accelerated application: `http://127.0.0.1:5051/`
- Legacy dashboard `/site/` links redirect to the isolated gateway.
- Both ports must be free; one gateway can run at a time.
- `--check` verifies setup without launching; `--no-browser` starts without a browser.

## Public acceleration

Caching and additional compression require an origin response with
`Cache-Control: public`. Mark only data safe for every user. Authorization,
cookies, ranges, preconditions, Set-Cookie, private responses, custom Vary fields,
and explicit freshness directives bypass caching and additional transformation.
Undeclared responses pass through unchanged. Cache TTL defaults to 300 seconds;
freshness directives such as max-age are conservatively passed through.
Writes invalidate all cached reads before and after execution; pending responses
cannot refill an invalidated cache. Keys isolate scheme, host, path and query.

Each response cache has a 64 MiB body/header budget and an item limit. Gateway
uploads are limited to 8 MB. Responses exceeding approximately 2 MB plus one
64 KiB chunk stream without caching. Connections are pooled with no retained
origin cookies or environment proxies. Duplicate headers survive. Compression
reuses up to 64 small public variants. HTML/CSS remain verbatim to preserve their
semantics; JSON whitespace removal preserves numbers and strings.

For direct middleware integration, install into your application's own environment
using `python -m pip install ./go_fast` from the parent folder:
```python
from go_fast import RocketBooster
RocketBooster.attach(app)
# Public endpoints must return headers={"Cache-Control": "public"}.
```
For Django, add `go_fast.DjangoRocketMiddleware` to MIDDLEWARE. Django is optional.
The standalone gateway requires no application source changes. Built wheels
include dashboard assets and the `go-fast` command.

## Security boundary

Dashboard and upstream pages use separate origins. Loopback peer/Host checks,
Origin and Fetch Metadata checks protect local access. Management writes also
require `X-Go-Fast-Admin: 1`; management responses use no-store, anti-framing and
no-sniff headers. Telemetry does not retain request paths, queries, credentials,
headers or bodies. URL validation rejects embedded credentials and special addresses.

Use trusted local development targets. This is not an authenticated public
reverse proxy or a general SSRF firewall: private/local targets are intentional,
and DNS-based special addresses are not comprehensively blocked. A local process
with your account's privileges can access the service. The upstream application's
authentication, authorization, TLS, database security and security headers remain
its responsibility. Absolute origin URLs and secure/domain-scoped cookies may need
upstream configuration. No audit guarantees zero vulnerabilities or a fixed latency.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pip install pytest django pip-audit bandit
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip_audit --skip-editable
.\.venv\Scripts\python.exe -m bandit -r go_fast run.py setup_plugin.py -ll
python refresh_docs.py
```

The full Bandit scan reports two low-severity subprocess review notices in
setup_plugin.py. Calls use fixed interpreter paths, exact argument vectors,
checked exit codes and no shell; tests verify these boundaries. Real-socket tests
need ports 5050/5051 free. Documentation refresh generates CODEMAP.md and ignored HTML docs.
