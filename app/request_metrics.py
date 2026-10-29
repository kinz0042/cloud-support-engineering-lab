"""Small classic histogram for the local lab's bounded application routes.

The caller holds the API metrics lock during observation and rendering.
"""
import math

BUCKETS = (0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
ROUTES = frozenset(("/health", "/ready", "/v1/orders", "/v1/callbacks", "unmatched"))


class RequestDurations:
    def __init__(self):
        self.observations = {}

    def observe(self, route, seconds):
        if not math.isfinite(seconds) or seconds < 0:
            raise ValueError("Duration must be finite and nonnegative")
        route = route if route in ROUTES else "unmatched"
        sample = self.observations.setdefault(route, {"count": 0, "sum": 0.0,
                                                     "buckets": [0] * len(BUCKETS)})
        sample["count"] += 1
        sample["sum"] += seconds
        for i, upper in enumerate(BUCKETS):
            if seconds <= upper:
                sample["buckets"][i] += 1

    def render(self):
        lines = ["# TYPE relaydesk_request_duration_seconds histogram"]
        for route, sample in sorted(self.observations.items()):
            for upper, count in zip(BUCKETS, sample["buckets"]):
                lines.append(f'relaydesk_request_duration_seconds_bucket{{route="{route}",le="{upper:g}"}} {count}')
            lines.append(f'relaydesk_request_duration_seconds_bucket{{route="{route}",le="+Inf"}} {sample["count"]}')
            lines.append(f'relaydesk_request_duration_seconds_sum{{route="{route}"}} {sample["sum"]:.17g}')
            lines.append(f'relaydesk_request_duration_seconds_count{{route="{route}"}} {sample["count"]}')
        return lines
