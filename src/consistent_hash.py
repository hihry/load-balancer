"""
Consistent Hash Implementation
Maps requests to backend servers using consistent hashing algorithm
"""

import hashlib
from bisect import bisect_right


class ConsistentHash:
    def __init__(self, servers=None, virtual_nodes=150):
        """
        Initialize consistent hash ring
        
        Args:
            servers: List of backend server addresses
            virtual_nodes: Number of virtual nodes per server
        """
        self.servers = servers or []
        self.virtual_nodes = virtual_nodes
        self.ring = {}
        self.sorted_keys = []
        self.build_ring()

    def hash(self, key):
        """
        Hash function using MD5
        
        Args:
            key: String to hash
            
        Returns:
            Integer hash value
        """
        return int(hashlib.md5(key.encode()).hexdigest(), 16)

    def build_ring(self):
        """Build the hash ring with virtual nodes"""
        self.ring = {}
        self.sorted_keys = []

        for server in self.servers:
            for i in range(self.virtual_nodes):
                virtual_key = f"{server}:{i}"
                hash_value = self.hash(virtual_key)
                self.ring[hash_value] = server

        self.sorted_keys = sorted(self.ring.keys())

    def add_server(self, server):
        """
        Add a new server to the ring
        
        Args:
            server: Server address to add
        """
        if server not in self.servers:
            self.servers.append(server)
            self.build_ring()

    def remove_server(self, server):
        """
        Remove a server from the ring
        
        Args:
            server: Server address to remove
        """
        if server in self.servers:
            self.servers.remove(server)
            self.build_ring()

    def get_server(self, key):
        """
        Get server for a given key
        
        Args:
            key: Request identifier (usually client IP)
            
        Returns:
            Server address or None
        """
        if not self.servers:
            return None

        hash_value = self.hash(key)
        index = bisect_right(self.sorted_keys, hash_value)

        if index == len(self.sorted_keys):
            index = 0

        return self.ring[self.sorted_keys[index]]

    def get_servers(self):
        """Get list of all servers"""
        return self.servers.copy()
