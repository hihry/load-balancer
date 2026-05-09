from datetime import datetime, timedelta

class RateLimiter:
    """
    Blocks IPs that exceed a set number of requests within a time window.

    Strategy: Sliding Window
    - Each IP gets a list of timestamps for its recent requests.
    - On every new request, we drop timestamps older than the window.
    - If the remaining count >= limit, the IP is blocked.

    Example: limit=5, window=60s
      → An IP can make 5 requests per minute.
      → The 6th request within that minute is blocked.
      → After 60s, the window slides forward and the IP is unblocked.
    """

    def __init__(self, limit: int = 10, window_seconds: int = 60):
        """
        Args:
            limit:          Max requests allowed per IP within the window.
            window_seconds: How long the sliding window lasts (in seconds).
        """
        self.limit = limit
        self.window = timedelta(seconds=window_seconds)

        # ip → list of datetime timestamps for recent requests
        self.requests: dict[str, list[datetime]] = {}

        # IPs manually blocked by admin (permanent until unblocked)
        self.blocked: set[str] = set()

    # ── Core check ────────────────────────────────────────────────────────────

    def is_allowed(self, ip: str) -> bool:
        """
        Check if the IP is allowed to make a request.
        - Permanently blocked IPs are always rejected.
        - Otherwise apply the sliding window check.
        Does NOT record the request — call record() separately.
        """
        if ip in self.blocked:
            return False

        now = datetime.now()
        window_start = now - self.window

        # Keep only timestamps within the current window
        recent = [t for t in self.requests.get(ip, []) if t > window_start]
        self.requests[ip] = recent

        return len(recent) < self.limit

    def record(self, ip: str) -> None:
        """Record a request timestamp for this IP."""
        if ip not in self.requests:
            self.requests[ip] = []
        self.requests[ip].append(datetime.now())

    # ── Admin controls ────────────────────────────────────────────────────────

    def block_ip(self, ip: str) -> None:
        """Permanently block an IP (overrides sliding window)."""
        self.blocked.add(ip)

    def unblock_ip(self, ip: str) -> None:
        """Remove permanent block from an IP."""
        self.blocked.discard(ip)

    # ── Info ──────────────────────────────────────────────────────────────────

    def request_count(self, ip: str) -> int:
        """How many requests this IP has made in the current window."""
        now = datetime.now()
        window_start = now - self.window
        return len([t for t in self.requests.get(ip, []) if t > window_start])

    def report(self) -> dict:
        """Summary of rate limiter state."""
        return {
            "limit": self.limit,
            "window_seconds": int(self.window.total_seconds()),
            "tracked_ips": len(self.requests),
            "blocked_ips": list(self.blocked),
        }