# import hashlib
# import bisect

# class ConsistentHashRing:
#     """
#     Maps IPs to nodes using consistent hashing.

#     How it works:
#     - Each node is placed at multiple positions on a virtual ring (0 to 2^32 - 1)
#       using virtual nodes (replicas). More replicas = more even distribution.
#     - An incoming IP is hashed to a position on the ring.
#     - We walk clockwise to find the nearest node.
#     - Same IP always lands on the same ring position → same node.
#     - Adding/removing a node only remaps IPs near that node's ring slots.
#     """

#     def __init__(self, nodes: list[str], replicas: int = 100):
#         """
#         Args:
#             nodes:    List of node names e.g. ["Node-A", "Node-B", "Node-C"]
#             replicas: Virtual copies per node on the ring (higher = more even spread)
#         """
#         self.replicas = replicas
#         self.ring: dict[int, str] = {}   # hash position → node name
#         self.sorted_keys: list[int] = [] # sorted list of all positions on the ring

#         for node in nodes:
#             self.add_node(node)

#     # ── Ring management ──────────────────────────────────────────────────────

#     def _hash(self, key: str) -> int:
#         """Stable 32-bit hash of any string using MD5."""
#         return int(hashlib.md5(key.encode()).hexdigest(), 16) % (2**32)

#     def add_node(self, node: str) -> None:
#         """Place a node on the ring at `replicas` positions."""
#         for i in range(self.replicas):
#             position = self._hash(f"{node}:{i}")
#             self.ring[position] = node
#             bisect.insort(self.sorted_keys, position)

#     def remove_node(self, node: str) -> None:
#         """Remove all ring positions belonging to this node."""
#         for i in range(self.replicas):
#             position = self._hash(f"{node}:{i}")
#             if position in self.ring:
#                 del self.ring[position]
#                 index = bisect.bisect_left(self.sorted_keys, position)
#                 self.sorted_keys.pop(index)

#     # ── Routing ──────────────────────────────────────────────────────────────

#     def get_node(self, ip: str) -> str | None:
#         """
#         Route an IP to a node.
#         - Hash the IP to a ring position.
#         - Walk clockwise to the nearest node slot.
#         - Wrap around if we pass the end of the ring.
#         Returns None if the ring is empty.
#         """
#         if not self.ring:
#             return None

#         ip_position = self._hash(ip)

#         # bisect_right finds the first slot AFTER the IP's position (clockwise)
#         index = bisect.bisect_right(self.sorted_keys, ip_position)

#         # Wrap around to the start of the ring if past the last slot
#         if index == len(self.sorted_keys):
#             index = 0

#         return self.ring[self.sorted_keys[index]]

#     # ── Utility ──────────────────────────────────────────────────────────────

#     def get_distribution(self) -> dict[str, int]:
#         """Return how many ring slots each node owns."""
#         distribution: dict[str, int] = {}
#         for node in self.ring.values():
#             distribution[node] = distribution.get(node, 0) + 1
#         return distribution


import hashlib
import bisect

class ConsistentHashRing:
    """
    Maps IPs to nodes using consistent hashing with optional weighted routing.

    How it works:
    - Each node is placed at multiple positions on a virtual ring (0 to 2^32)
      using virtual nodes (replicas). More replicas = more traffic share.
    - An incoming IP is hashed to a position on the ring.
    - We walk clockwise to find the nearest node.
    - Same IP always lands on the same ring position → same node.
    - Adding/removing a node only remaps IPs near that node's ring slots.

    Weighted Routing:
    - Each node has a weight (default 1).
    - A node with weight 2 gets 2x the ring slots of a node with weight 1.
    - More slots = higher probability of receiving traffic.
    - Example: Node-A weight=2, Node-B weight=1, Node-C weight=1
        → Node-A handles ~50% of traffic, B and C ~25% each.
    """

    def __init__(self, nodes: list[str], replicas: int = 100, weights: dict[str, float] | None = None):
        """
        Args:
            nodes:    List of node names e.g. ["Node-A", "Node-B", "Node-C"]
            replicas: Base virtual slots per node (scaled by weight)
            weights:  Optional dict of node → weight e.g. {"Node-A": 2, "Node-B": 1}
                      Unspecified nodes default to weight 1.
        """
        self.replicas = replicas
        self.weights: dict[str, float] = weights or {}
        self.ring: dict[int, str] = {}   # hash position → node name
        self.sorted_keys: list[int] = [] # sorted list of all positions on the ring

        for node in nodes:
            self.add_node(node)

    # ── Ring management ──────────────────────────────────────────────────────

    def _hash(self, key: str) -> int:
        """Stable 32-bit hash of any string using MD5."""
        return int(hashlib.md5(key.encode()).hexdigest(), 16) % (2**32)

    def _slot_count(self, node: str) -> int:
        """
        How many ring slots this node gets.
        Weight 1 → replicas slots (default)
        Weight 2 → replicas * 2 slots (gets ~2x the traffic)
        """
        weight = self.weights.get(node, 1)
        return max(1, int(self.replicas * weight))

    def add_node(self, node: str, weight: float | None = None) -> None:
        """
        Place a node on the ring.
        Optionally set or override its weight at the same time.
        """
        if weight is not None:
            self.weights[node] = weight
        for i in range(self._slot_count(node)):
            position = self._hash(f"{node}:{i}")
            self.ring[position] = node
            bisect.insort(self.sorted_keys, position)

    def remove_node(self, node: str) -> None:
        """Remove all ring positions belonging to this node."""
        for i in range(self._slot_count(node)):
            position = self._hash(f"{node}:{i}")
            if position in self.ring:
                del self.ring[position]
                index = bisect.bisect_left(self.sorted_keys, position)
                self.sorted_keys.pop(index)
        self.weights.pop(node, None)

    def set_weight(self, node: str, weight: float) -> bool:
        """
        Change a node's weight at runtime.
        Rebuilds that node's ring slots to reflect the new share.
        Returns False if node is not on the ring.
        """
        if not any(n == node for n in self.ring.values()):
            return False
        # Remove old slots, re-add with new weight
        old_slots = self._slot_count(node)
        for i in range(old_slots):
            position = self._hash(f"{node}:{i}")
            if position in self.ring:
                del self.ring[position]
                index = bisect.bisect_left(self.sorted_keys, position)
                self.sorted_keys.pop(index)
        self.weights[node] = weight
        for i in range(self._slot_count(node)):
            position = self._hash(f"{node}:{i}")
            self.ring[position] = node
            bisect.insort(self.sorted_keys, position)
        return True

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
        """Return how many ring slots each node currently owns."""
        distribution: dict[str, int] = {}
        for node in self.ring.values():
            distribution[node] = distribution.get(node, 0) + 1
        return distribution

    def get_weights(self) -> dict[str, float]:
        """Return current weight of every node on the ring."""
        all_nodes = set(self.ring.values())
        return {node: self.weights.get(node, 1) for node in all_nodes}