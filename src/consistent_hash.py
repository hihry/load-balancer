import hashlib
import bisect

class ConsistentHashRing:
    """
    Maps IPs to nodes using consistent hashing.

    How it works:
    - Each node is placed at multiple positions on a virtual ring (0 to 2^32 - 1)
      using virtual nodes (replicas). More replicas = more even distribution.
    - An incoming IP is hashed to a position on the ring.
    - We walk clockwise to find the nearest node.
    - Same IP always lands on the same ring position → same node.
    - Adding/removing a node only remaps IPs near that node's ring slots.
    """

    def __init__(self, nodes: list[str], replicas: int = 100):
        """
        Args:
            nodes:    List of node names e.g. ["Node-A", "Node-B", "Node-C"]
            replicas: Virtual copies per node on the ring (higher = more even spread)
        """
        self.replicas = replicas
        self.ring: dict[int, str] = {}   # hash position → node name
        self.sorted_keys: list[int] = [] # sorted list of all positions on the ring

        for node in nodes:
            self.add_node(node)

    # ── Ring management ──────────────────────────────────────────────────────

    def _hash(self, key: str) -> int:
        """Stable 32-bit hash of any string using MD5."""
        return int(hashlib.md5(key.encode()).hexdigest(), 16) % (2**32)

    def add_node(self, node: str) -> None:
        """Place a node on the ring at `replicas` positions."""
        for i in range(self.replicas):
            position = self._hash(f"{node}:{i}")
            self.ring[position] = node
            bisect.insort(self.sorted_keys, position)

    def remove_node(self, node: str) -> None:
        """Remove all ring positions belonging to this node."""
        for i in range(self.replicas):
            position = self._hash(f"{node}:{i}")
            if position in self.ring:
                del self.ring[position]
                index = bisect.bisect_left(self.sorted_keys, position)
                self.sorted_keys.pop(index)

    # ── Routing ──────────────────────────────────────────────────────────────

    def get_node(self, ip: str) -> str | None:
        """
        Route an IP to a node.
        - Hash the IP to a ring position.
        - Walk clockwise to the nearest node slot.
        - Wrap around if we pass the end of the ring.
        Returns None if the ring is empty.
        """
        if not self.ring:
            return None

        ip_position = self._hash(ip)

        # bisect_right finds the first slot AFTER the IP's position (clockwise)
        index = bisect.bisect_right(self.sorted_keys, ip_position)

        # Wrap around to the start of the ring if past the last slot
        if index == len(self.sorted_keys):
            index = 0

        return self.ring[self.sorted_keys[index]]

    # ── Utility ──────────────────────────────────────────────────────────────

    def get_distribution(self) -> dict[str, int]:
        """Return how many ring slots each node owns."""
        distribution: dict[str, int] = {}
        for node in self.ring.values():
            distribution[node] = distribution.get(node, 0) + 1
        return distribution