"""Measure the example host with and without Booster and print the comparison."""

import statistics
import time

from examples.host_app import ORIGIN_CALLS, app, engine, origin_app, request

PUBLIC_PATH = "/static/app.v1.css"
ITERATIONS = 200


def measure(application) -> tuple[float, float, int, int]:
    """Return cold latency, warm latency, origin calls and served bytes."""
    durations: list[float] = []
    ORIGIN_CALLS["total"] = 0
    for index in range(ITERATIONS):
        start = time.perf_counter()
        _, body, _ = request("GET", PUBLIC_PATH, application=application)
        durations.append((time.perf_counter() - start) * 1000)
        if index == 0:
            served = len(body)
    warm = durations[1:] or durations
    return durations[0], statistics.median(warm), ORIGIN_CALLS["total"], served


def main() -> None:
    """Print a before/after comparison for the example host."""
    engine.cache.clear()
    without = measure(origin_app)
    with_booster = measure(app)
    print(f"requests per run: {ITERATIONS}  path: {PUBLIC_PATH}")
    print(f"cold p50 (ms)      without {without[0]:.3f}   with {with_booster[0]:.3f}")
    print(f"warm p50 (ms)      without {without[1]:.3f}   with {with_booster[1]:.3f}")
    print(f"origin calls       without {without[2]}   with {with_booster[2]}")
    print(f"served bytes       without {without[3]}   with {with_booster[3]}")


if __name__ == "__main__":
    main()
