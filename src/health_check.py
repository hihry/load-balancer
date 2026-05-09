"""
Health Check Module
Periodically checks the health status of backend servers
"""

import asyncio
import aiohttp
from typing import Dict, List
from datetime import datetime


class HealthCheck:
    def __init__(self, servers=None, interval=5, timeout=3):
        """
        Initialize health checker
        
        Args:
            servers: List of backend server addresses
            interval: Health check interval in seconds
            timeout: Request timeout in seconds
        """
        self.servers = servers or []
        self.interval = interval
        self.timeout = timeout
        self.health_status: Dict[str, bool] = {}
        self.check_task = None

        # Initialize all servers as healthy
        for server in self.servers:
            self.health_status[server] = True

    async def check_server_health(self, server):
        """
        Check health of a single server
        
        Args:
            server: Server address to check
            
        Returns:
            True if healthy, False otherwise
        """
        url = f"http://{server}/health"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=self.timeout)) as response:
                    return 200 <= response.status < 300
        except Exception as e:
            return False

    async def perform_check(self, server):
        """
        Perform a single health check
        
        Args:
            server: Server address to check
        """
        is_healthy = await self.check_server_health(server)
        was_healthy = self.health_status.get(server, True)

        if is_healthy != was_healthy:
            status = "UP" if is_healthy else "DOWN"
            print(f"[HealthCheck] Server {server} is now {status}")
            self.health_status[server] = is_healthy

    async def start_health_checks(self):
        """Start periodic health checks"""
        print("[HealthCheck] Started health checks")
        try:
            while True:
                tasks = [self.perform_check(server) for server in self.servers]
                await asyncio.gather(*tasks)
                await asyncio.sleep(self.interval)
        except asyncio.CancelledError:
            print("[HealthCheck] Stopped health checks")

    def start(self):
        """Start health checks in background"""
        if not self.check_task:
            self.check_task = asyncio.create_task(self.start_health_checks())

    def stop(self):
        """Stop health checks"""
        if self.check_task:
            self.check_task.cancel()
            self.check_task = None

    def is_healthy(self, server):
        """
        Check if server is healthy
        
        Args:
            server: Server address
            
        Returns:
            True if healthy, False otherwise
        """
        return self.health_status.get(server, True)

    def get_healthy_servers(self, all_servers: List[str]) -> List[str]:
        """
        Get list of healthy servers
        
        Args:
            all_servers: List of all servers
            
        Returns:
            List of healthy servers
        """
        return [server for server in all_servers if self.is_healthy(server)]

    def add_server(self, server):
        """
        Add a server to health checks
        
        Args:
            server: Server address to add
        """
        if server not in self.servers:
            self.servers.append(server)
            self.health_status[server] = True

    def remove_server(self, server):
        """
        Remove a server from health checks
        
        Args:
            server: Server address to remove
        """
        if server in self.servers:
            self.servers.remove(server)
            self.health_status.pop(server, None)
