import random
from src.consistent_hash import ConsistentHashRing
from src.health_check import HealthChecker
from src.rate_limiter import RateLimiter
from src.metrics import Metrics

# ── Required functions ported from JS (as per task) ───────────────────────────

def generate_random_ip() -> str:
    """
    Port of the JS function from the task:
        function generateRandomIP() {
            return Array.from({ length: 4 }, () =>
                Math.floor(Math.random() * 256)).join(".");
        }
    """
    return ".".join(str(random.randint(0, 255)) for _ in range(4))


def identify_node(ip: str, selected_node: str) -> None:
    """
    Port of the JS function from the task:
        function identifyNode(ip, selectedNode) {
            console.log(`Incoming IP: ${ip} → Routed to: ${selectedNode}`);
        }
    """
    print(f"Incoming IP: {ip} → Routed to: {selected_node}")


# ── Load Balancer ─────────────────────────────────────────────────────────────

class LoadBalancer:
    """
    Wires together all four modules:
      1. ConsistentHashRing  — deterministic IP → node mapping
      2. HealthChecker       — skips DOWN nodes
      3. RateLimiter         — blocks IPs exceeding request limits
      4. Metrics             — records every routing decision

    Flow for each request:
      is_allowed(ip)?  →  No  → record_blocked → return error
           ↓ Yes
      healthy_nodes()  →  []  → record_blocked → return error
           ↓
      rebuild ring with only healthy nodes
           ↓
      get_node(ip)     → node
           ↓
      identify_node()  → log to console
           ↓
      record_routed()  → update metrics
           ↓
      return node
    """

    def __init__(
        self,
        nodes: list[str] | None = None,
        replicas: int = 100,
        rate_limit: int = 10,
        rate_window: int = 60,
    ):
        """
        Args:
            nodes:       List of node names. Defaults to ["Node-A", "Node-B", "Node-C"].
            replicas:    Virtual nodes per server on the hash ring.
            rate_limit:  Max requests per IP within the window.
            rate_window: Sliding window size in seconds.
        """
        self.nodes: list[str] = nodes or ["Node-A", "Node-B", "Node-C"]

        self.ring = ConsistentHashRing(self.nodes, replicas=replicas)
        self.health = HealthChecker(self.nodes)
        self.limiter = RateLimiter(limit=rate_limit, window_seconds=rate_window)
        self.metrics = Metrics()

    # ── Core routing ──────────────────────────────────────────────────────────

    def route(self, ip: str) -> dict:
        """
        Route an incoming IP to a node.
        Returns a dict describing the outcome (success or blocked).
        """

        # Step 1: Rate limit check
        if not self.limiter.is_allowed(ip):
            self.metrics.record_blocked(ip, "rate_limit_exceeded")
            return {
                "ip": ip,
                "routed_to": None,
                "blocked": True,
                "reason": "rate_limit_exceeded",
            }
        self.limiter.record(ip)

        # Step 2: Get only healthy nodes and rebuild ring if needed
        healthy = self.health.healthy_nodes()
        if not healthy:
            self.metrics.record_blocked(ip, "no_healthy_nodes")
            return {
                "ip": ip,
                "routed_to": None,
                "blocked": True,
                "reason": "no_healthy_nodes",
            }

        # Build a temporary ring with only healthy nodes
        active_ring = ConsistentHashRing(healthy, replicas=100)

        # Step 3: Consistent hash → node
        node = active_ring.get_node(ip)

        # Step 4: Log to console (required by task)
        identify_node(ip, node)

        # Step 5: Record in metrics
        self.metrics.record_routed(ip, node)

        return {
            "ip": ip,
            "routed_to": node,
            "blocked": False,
            "reason": None,
        }

    # ── Simulation (required by task) ─────────────────────────────────────────

    def simulate_traffic(self, request_count: int = 10) -> list[dict]:
        """
        Port of the JS simulateTraffic() function from the task.
        Generates random IPs and routes each one.
        """
        results = []
        for _ in range(request_count):
            ip = generate_random_ip()
            result = self.route(ip)
            results.append(result)
        return results

    # ── Node management ───────────────────────────────────────────────────────

    def add_node(self, node: str) -> None:
        """Add a new node to the balancer (ring + health tracker)."""
        self.nodes.append(node)
        self.ring.add_node(node)
        self.health.status[node] = True

    def remove_node(self, node: str) -> None:
        """Remove a node from the balancer entirely."""
        if node in self.nodes:
            self.nodes.remove(node)
            self.ring.remove_node(node)
            self.health.status.pop(node, None)