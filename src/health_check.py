from datetime import datetime

class HealthChecker:
    """
    Tracks the health status of each node (UP or DOWN).
    The load balancer skips DOWN nodes automatically.

    Features:
    - Mark any node UP or DOWN manually (via API)
    - Track when the status last changed
    - Get a full health report of all nodes
    """

    def __init__(self, nodes: list[str]):
        """
        Args:
            nodes: List of node names e.g. ["Node-A", "Node-B", "Node-C"]
                   All nodes start as UP by default.
        """
        self.status: dict[str, bool] = {node: True for node in nodes}
        self.last_changed: dict[str, str] = {
            node: datetime.now().isoformat(timespec="seconds")
            for node in nodes
        }

    # ── Status control ────────────────────────────────────────────────────────

    def mark_down(self, node: str) -> bool:
        """Mark a node as DOWN. Returns False if node doesn't exist."""
        if node not in self.status:
            return False
        self.status[node] = False
        self.last_changed[node] = datetime.now().isoformat(timespec="seconds")
        return True

    def mark_up(self, node: str) -> bool:
        """Mark a node as UP. Returns False if node doesn't exist."""
        if node not in self.status:
            return False
        self.status[node] = True
        self.last_changed[node] = datetime.now().isoformat(timespec="seconds")
        return True

    def toggle(self, node: str) -> bool | None:
        """Flip a node's status. Returns new status, or None if not found."""
        if node not in self.status:
            return None
        if self.status[node]:
            self.mark_down(node)
        else:
            self.mark_up(node)
        return self.status[node]

    # ── Queries ───────────────────────────────────────────────────────────────

    def is_healthy(self, node: str) -> bool:
        """Returns True if the node is UP."""
        return self.status.get(node, False)

    def healthy_nodes(self) -> list[str]:
        """Returns list of all nodes currently UP."""
        return [node for node, up in self.status.items() if up]

    def report(self) -> list[dict]:
        """Full health report for all nodes."""
        return [
            {
                "node": node,
                "status": "UP" if up else "DOWN",
                "last_changed": self.last_changed[node],
            }
            for node, up in self.status.items()
        ]