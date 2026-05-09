"""
Rate Limiter Module
Implements per-IP rate limiting using token bucket algorithm
"""

from typing import Dict
from time import time


class RateLimiter:
    def __init__(self, max_requests=100, window_ms=60000):
        """
        Initialize rate limiter
        
        Args:
            max_requests: Maximum requests allowed per window
            window_ms: Time window in milliseconds
        """
        self.max_requests = max_requests
        self.window_ms = window_ms / 1000  # Convert to seconds
        self.clients: Dict[str, dict] = {}

    def is_allowed(self, client_ip):
        """
        Check if request is allowed using token bucket algorithm
        
        Args:
            client_ip: Client IP address
            
        Returns:
            True if request is allowed, False otherwise
        """
        now = time()

        if client_ip not in self.clients:
            # New client: initialize bucket
            self.clients[client_ip] = {
                "tokens": self.max_requests,
                "last_refill": now,
            }
            return True

        bucket = self.clients[client_ip]

        # Calculate tokens to add based on time elapsed
        time_passed = now - bucket["last_refill"]
        tokens_to_add = (time_passed / self.window_ms) * self.max_requests

        bucket["tokens"] = min(self.max_requests, bucket["tokens"] + tokens_to_add)
        bucket["last_refill"] = now

        if bucket["tokens"] >= 1:
            bucket["tokens"] -= 1
            return True

        return False

    def get_remaining_requests(self, client_ip):
        """
        Get remaining requests for a client
        
        Args:
            client_ip: Client IP address
            
        Returns:
            Number of remaining requests
        """
        if client_ip not in self.clients:
            return self.max_requests
        return int(self.clients[client_ip]["tokens"])

    def reset(self):
        """Reset all rate limits"""
        self.clients.clear()

    def reset_client(self, client_ip):
        """
        Reset rate limit for a specific client
        
        Args:
            client_ip: Client IP address
        """
        self.clients.pop(client_ip, None)

    def get_stats(self):
        """
        Get stats for all clients
        
        Returns:
            Dictionary of client stats
        """
        stats = {}
        for client_ip, bucket in self.clients.items():
            stats[client_ip] = {
                "tokens": int(bucket["tokens"]),
                "limit": self.max_requests,
            }
        return stats
