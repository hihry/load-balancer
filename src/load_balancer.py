"""
Load Balancer Module
Wires together consistent hashing, health checks, rate limiting, and metrics
"""

import httpx
from typing import Dict, List, Tuple
from .consistent_hash import ConsistentHash
from .health_check import HealthCheck
from .rate_limiter import RateLimiter
from .metrics import Metrics


class LoadBalancer:
    def __init__(self, servers=None, options=None):
        """
        Initialize load balancer
        
        Args:
            servers: List of backend server addresses
            options: Configuration options
        """
        self.servers = servers or []
        options = options or {}

        # Initialize components
        self.consistent_hash = ConsistentHash(
            self.servers,
            virtual_nodes=options.get("virtual_nodes", 150),
        )

        self.health_check = HealthCheck(
            self.servers,
            interval=options.get("health_check_interval", 5),
            timeout=options.get("health_check_timeout", 3),
        )

        self.rate_limiter = RateLimiter(
            max_requests=options.get("max_requests", 100),
            window_ms=options.get("rate_limit_window", 60000),
        )

        self.metrics = Metrics()

    def start(self):
        """Start the load balancer"""
        self.health_check.start()
        print(f"[LoadBalancer] Started with servers: {self.servers}")

    def stop(self):
        """Stop the load balancer"""
        self.health_check.stop()
        print("[LoadBalancer] Stopped")

    def get_server(self, client_ip: str) -> Dict[str, str]:
        """
        Get the best server for routing a request
        
        Args:
            client_ip: Client IP address
            
        Returns:
            Dictionary with server address and reason
        """
        # Check rate limit first
        if not self.rate_limiter.is_allowed(client_ip):
            return {"server": None, "reason": "RATE_LIMIT_EXCEEDED"}

        # Get all healthy servers
        healthy_servers = self.health_check.get_healthy_servers(self.servers)

        if not healthy_servers:
            return {"server": None, "reason": "NO_HEALTHY_SERVERS"}

        # Use consistent hash to select server
        server = self.consistent_hash.get_server(client_ip)

        if not self.health_check.is_healthy(server):
            # If selected server is down, find next healthy one
            next_server = next((s for s in healthy_servers if s != server), None)
            return {"server": next_server, "reason": "FAILOVER"}

        return {"server": server, "reason": "OK"}

    async def forward_request(self, method: str, url: str, target_server: str, headers: dict = None, body: bytes = None) -> Tuple[int, dict, bytes]:
        """
        Forward request to backend server
        
        Args:
            method: HTTP method
            url: Request URL
            target_server: Target server address
            headers: Request headers
            body: Request body
            
        Returns:
            Tuple of (status_code, response_headers, response_body)
        """
        import time
        start_time = time.time()

        try:
            target_url = f"http://{target_server}{url}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.request(
                    method,
                    target_url,
                    headers=headers,
                    content=body,
                )
            
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            self.metrics.record_request(target_server, response.status_code, response_time)
            
            return response.status_code, dict(response.headers), response.content
        except Exception as e:
            print(f"[LoadBalancer] Error forwarding to {target_server}: {e}")
            response_time = (time.time() - start_time) * 1000
            self.metrics.record_request(target_server, 503, response_time)
            return 503, {"content-type": "application/json"}, b'{"error": "Service Unavailable"}'

    def add_server(self, server: str):
        """
        Add a new server
        
        Args:
            server: Server address to add
        """
        if server not in self.servers:
            self.servers.append(server)
            self.consistent_hash.add_server(server)
            self.health_check.add_server(server)
            print(f"[LoadBalancer] Added server: {server}")

    def remove_server(self, server: str):
        """
        Remove a server
        
        Args:
            server: Server address to remove
        """
        if server in self.servers:
            self.servers.remove(server)
            self.consistent_hash.remove_server(server)
            self.health_check.remove_server(server)
            print(f"[LoadBalancer] Removed server: {server}")

    def get_status(self) -> dict:
        """
        Get current state and metrics
        
        Returns:
            Status dictionary
        """
        return {
            "servers": self.servers,
            "healthy_servers": self.health_check.get_healthy_servers(self.servers),
            "metrics": self.metrics.get_metrics(),
        }
