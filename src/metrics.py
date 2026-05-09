"""
Metrics Module
Tracks request metrics and performance statistics
"""

from typing import Dict, List
from time import time


class Metrics:
    def __init__(self):
        """Initialize metrics tracker"""
        self.request_count = 0
        self.total_response_time = 0
        self.server_metrics: Dict[str, dict] = {}
        self.status_codes: Dict[int, int] = {}
        self.start_time = time()

    def record_request(self, server, status_code, response_time):
        """
        Record a request
        
        Args:
            server: Backend server address
            status_code: HTTP status code
            response_time: Response time in milliseconds
        """
        self.request_count += 1
        self.total_response_time += response_time

        # Track per-server metrics
        if server not in self.server_metrics:
            self.server_metrics[server] = {
                "requests": 0,
                "total_time": 0,
                "errors": 0,
            }

        metrics = self.server_metrics[server]
        metrics["requests"] += 1
        metrics["total_time"] += response_time
        if status_code >= 400:
            metrics["errors"] += 1

        # Track status codes
        if status_code not in self.status_codes:
            self.status_codes[status_code] = 0
        self.status_codes[status_code] += 1

    def get_average_response_time(self):
        """
        Get average response time
        
        Returns:
            Average response time in milliseconds
        """
        if self.request_count == 0:
            return 0
        return round(self.total_response_time / self.request_count)

    def get_server_metrics(self, server):
        """
        Get metrics for a specific server
        
        Args:
            server: Backend server address
            
        Returns:
            Server metrics dictionary
        """
        if server not in self.server_metrics:
            return None

        metrics = self.server_metrics[server]
        avg_response_time = (
            round(metrics["total_time"] / metrics["requests"])
            if metrics["requests"] > 0
            else 0
        )
        error_rate = (
            f"{(metrics['errors'] / metrics['requests']) * 100:.2f}%"
            if metrics["requests"] > 0
            else "0%"
        )

        return {
            "server": server,
            "requests": metrics["requests"],
            "avg_response_time": avg_response_time,
            "errors": metrics["errors"],
            "error_rate": error_rate,
        }

    def get_metrics(self):
        """
        Get overall metrics
        
        Returns:
            Dictionary of all metrics
        """
        uptime = round((time() - self.start_time))
        server_stats = []

        for server in self.server_metrics:
            server_stats.append(self.get_server_metrics(server))

        return {
            "total_requests": self.request_count,
            "avg_response_time": self.get_average_response_time(),
            "uptime": f"{uptime}s",
            "status_codes": dict(self.status_codes),
            "servers": server_stats,
        }

    def reset(self):
        """Reset all metrics"""
        self.request_count = 0
        self.total_response_time = 0
        self.server_metrics.clear()
        self.status_codes.clear()
        self.start_time = time()
