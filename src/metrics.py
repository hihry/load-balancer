from datetime import datetime

class Metrics:
    """
    Tracks everything happening inside the load balancer.

    Collects:
    - Total requests received
    - Total requests blocked (rate limited)
    - Per-node request counts
    - Per-IP request counts
    - Last 50 request logs (for live dashboard)
    - Uptime (since the server started)
    """

    def __init__(self):
        self.started_at: str = datetime.now().isoformat(timespec="seconds")
        self.total_requests: int = 0
        self.total_blocked: int = 0
        self.node_hits: dict[str, int] = {}       # node  → request count
        self.ip_hits: dict[str, int] = {}         # ip    → request count
        self.recent_logs: list[dict] = []         # last 50 request records
        self._max_logs: int = 50

    # ── Recording ─────────────────────────────────────────────────────────────

    def record_routed(self, ip: str, node: str) -> None:
        """Call this every time a request is successfully routed."""
        self.total_requests += 1
        self.node_hits[node] = self.node_hits.get(node, 0) + 1
        self.ip_hits[ip] = self.ip_hits.get(ip, 0) + 1
        self._log(ip, node, blocked=False)

    def record_blocked(self, ip: str, reason: str) -> None:
        """Call this every time a request is blocked (rate limit / no healthy node)."""
        self.total_requests += 1
        self.total_blocked += 1
        self.ip_hits[ip] = self.ip_hits.get(ip, 0) + 1
        self._log(ip, reason, blocked=True)

    def _log(self, ip: str, destination: str, blocked: bool) -> None:
        """Append to the rolling log, keeping only the last 50 entries."""
        entry = {
            "time": datetime.now().isoformat(timespec="seconds"),
            "ip": ip,
            "routed_to": destination if not blocked else None,
            "blocked": blocked,
            "reason": destination if blocked else None,
        }
        self.recent_logs.append(entry)
        if len(self.recent_logs) > self._max_logs:
            self.recent_logs.pop(0)

    # ── Dashboard ─────────────────────────────────────────────────────────────

    def dashboard(self) -> dict:
        """Full metrics snapshot — used by the /metrics API endpoint."""
        routed = self.total_requests - self.total_blocked
        block_rate = (
            round(self.total_blocked / self.total_requests * 100, 1)
            if self.total_requests > 0 else 0.0
        )
        return {
            "uptime_since": self.started_at,
            "total_requests": self.total_requests,
            "total_routed": routed,
            "total_blocked": self.total_blocked,
            "block_rate_percent": block_rate,
            "node_hits": self.node_hits,
            "top_ips": self._top_ips(5),
            "recent_logs": list(reversed(self.recent_logs)),  # newest first
        }

    def _top_ips(self, n: int) -> list[dict]:
        """Return top N IPs by request count."""
        sorted_ips = sorted(self.ip_hits.items(), key=lambda x: x[1], reverse=True)
        return [{"ip": ip, "requests": count} for ip, count in sorted_ips[:n]]

    def reset(self) -> None:
        """Clear all counters (useful for testing)."""
        self.__init__()