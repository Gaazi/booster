"""Measure a live URL and report whether Booster could store the response.

The report uses the engine's own privacy and freshness rules, so a route that
the engine would never cache is never reported as cacheable. The module uses
only the standard library, so a consumer can run it on a server, a laptop or a
phone without installing the extras.
"""

import statistics
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Mapping, Optional

from booster.http_policy import is_static_asset, response_cacheable, response_ttl

USER_AGENT = "booster-measure/1.0"
DEFAULT_REQUESTS = 20
DEFAULT_TIMEOUT = 15.0


def _headers(raw: Mapping[str, str]) -> Dict[str, str]:
    """Lowercase the response headers for the engine's policy rules."""
    return {name.lower(): value for name, value in raw.items()}


def fetch_once(url: str, timeout: float = DEFAULT_TIMEOUT) -> Dict[str, Any]:
    """Fetch the URL once and return its status, headers, size and duration."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"})
    start = time.perf_counter()
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read()
        duration = (time.perf_counter() - start) * 1000
        headers = dict(response.headers.items())
    return {"status": response.status, "headers": headers, "bytes": len(body),
            "duration_ms": round(duration, 2)}


def percentile(values: List[float], fraction: float) -> float:
    """Return one percentile of the measured durations."""
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(fraction * (len(ordered) - 1))))
    return round(ordered[index], 2)


def cache_verdict(url: str, headers: Mapping[str, str], status: int) -> Dict[str, Any]:
    """Explain whether the engine could store this response and for how long."""
    lowered = _headers(headers)
    path = urllib.parse.urlsplit(url).path
    static = is_static_asset(path)
    if status != 200:
        return {"cacheable": False, "reason": "status_not_cacheable", "ttl_seconds": 0}
    if not response_cacheable(lowered, is_static=static):
        return {"cacheable": False, "reason": "response_not_public", "ttl_seconds": 0}
    return {"cacheable": True, "reason": "stored",
            "ttl_seconds": response_ttl(lowered, 300)}


def measure(url: str, requests: int = DEFAULT_REQUESTS,
            timeout: float = DEFAULT_TIMEOUT) -> Dict[str, Any]:
    """Measure one URL repeatedly and return a structured report."""
    first = fetch_once(url, timeout)
    durations = [first["duration_ms"]]
    for _ in range(max(0, requests - 1)):
        durations.append(fetch_once(url, timeout)["duration_ms"])
    headers = first["headers"]
    verdict = cache_verdict(url, headers, first["status"])
    return {
        "url": url,
        "status": first["status"],
        "bytes": first["bytes"],
        "content_type": headers.get("Content-Type", headers.get("content-type", "")),
        "cache_control": headers.get("Cache-Control", headers.get("cache-control", "")),
        "etag": headers.get("ETag", headers.get("etag", "")),
        "p50_ms": percentile(durations, 0.5),
        "p95_ms": percentile(durations, 0.95),
        "samples": len(durations),
        "verdict": verdict,
        "hint": hosting_hint(url, headers, verdict),
    }


def hosting_hint(url: str, headers: Mapping[str, str], verdict: Mapping[str, Any]) -> str:
    """Explain a refusal that an upstream proxy may have caused."""
    if verdict.get("cacheable"):
        return ""
    lowered = _headers(headers)
    vary = {part.strip().lower() for part in lowered.get("vary", "").split(",") if part.strip()}
    extra = sorted(vary - {"accept-encoding"})
    if extra:
        return (f"the hosting layer adds Vary: {', '.join(extra)}; check that the bytes are "
                "identical for every user agent before allowing that field")
    if lowered.get("age"):
        return "the hosting layer already aged this response; the engine stores it only while its remaining freshness is positive"
    if "cache-control" not in lowered:
        return "this response carries no cache policy; the origin never declared it public"
    return ""


def format_report(report: Mapping[str, Any]) -> str:
    """Render the report as a short operator-friendly text block."""
    verdict = report["verdict"]
    lines = [
        f"url            {report['url']}",
        f"status         {report['status']}",
        f"bytes          {report['bytes']}",
        f"content-type   {report['content_type']}",
        f"cache-control  {report['cache_control']}",
        f"etag           {report['etag']}",
        f"p50 / p95 ms   {report['p50_ms']} / {report['p95_ms']}  ({report['samples']} samples)",
        f"booster        {verdict['reason']}  (ttl {verdict['ttl_seconds']}s)",
    ]
    hint = report.get("hint", "")
    if hint:
        lines.append(f"hint           {hint}")
    return "\n".join(lines)


def measure_or_error(url: str, requests: int = DEFAULT_REQUESTS,
                      timeout: float = DEFAULT_TIMEOUT) -> Optional[Dict[str, Any]]:
    """Measure the URL and return None when it cannot be reached."""
    try:
        return measure(url, requests, timeout)
    except (urllib.error.URLError, OSError, ValueError):
        return None
