"""
Load Balancer Server
FastAPI server with integrated load balancing and all API routes
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import os
from src.load_balancer import LoadBalancer

# Backend servers configuration
BACKEND_SERVERS = [
    "localhost:3001",
    "localhost:3002",
    "localhost:3003",
]

# Initialize load balancer
load_balancer = LoadBalancer(BACKEND_SERVERS, {
    "virtual_nodes": 150,
    "health_check_interval": 5,
    "health_check_timeout": 3,
    "max_requests": 100,
    "rate_limit_window": 60000,
})


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown"""
    # Startup
    load_balancer.start()
    yield
    # Shutdown
    load_balancer.stop()


app = FastAPI(title="Load Balancer", version="1.0.0", lifespan=lifespan)


def get_client_ip(request: Request) -> str:
    """Extract client IP from request"""
    x_forwarded_for = request.headers.get("x-forwarded-for")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@app.api_route("/api/{path_name:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def load_balance_request(request: Request, path_name: str):
    """
    Load balancing route
    All requests to /api/* are load balanced to backend servers
    """
    client_ip = get_client_ip(request)
    selection = load_balancer.get_server(client_ip)

    if not selection["server"]:
        print(f"[LB] Request rejected - Reason: {selection['reason']}, IP: {client_ip}")
        status_code = 429 if selection["reason"] == "RATE_LIMIT_EXCEEDED" else 503
        error_msg = (
            "Rate limit exceeded"
            if selection["reason"] == "RATE_LIMIT_EXCEEDED"
            else "Service unavailable"
        )
        return JSONResponse(
            status_code=status_code,
            content={
                "error": error_msg,
                "reason": selection["reason"],
            },
        )

    print(f"[LB] Routing {request.method} /api/{path_name} to {selection['server']}")

    # Get request body if exists
    body = await request.body() if request.method in ["POST", "PUT", "PATCH"] else None

    # Forward request
    status_code, response_headers, response_body = await load_balancer.forward_request(
        request.method,
        f"/api/{path_name}",
        selection["server"],
        dict(request.headers),
        body,
    )

    # Filter response headers
    filtered_headers = {k: v for k, v in response_headers.items()
                       if k.lower() not in ["transfer-encoding", "content-encoding"]}

    return JSONResponse(
        status_code=status_code,
        content=response_body if not response_body else None,
        headers=filtered_headers,
    )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "UP", "service": "Load Balancer"}


@app.get("/status")
async def get_status():
    """Status endpoint - returns load balancer state and metrics"""
    return load_balancer.get_status()


@app.get("/metrics")
async def get_metrics():
    """Metrics endpoint - returns detailed metrics"""
    return load_balancer.metrics.get_metrics()


@app.get("/rate-limits")
async def get_rate_limits():
    """Rate limit stats endpoint"""
    return load_balancer.rate_limiter.get_stats()


@app.post("/admin/servers")
async def add_server(request: Request):
    """Add a new backend server"""
    try:
        data = await request.json()
        server = data.get("server")
        if not server:
            return JSONResponse(
                status_code=400,
                content={"error": "Server address required"},
            )
        load_balancer.add_server(server)
        return {
            "message": f"Server {server} added",
            "servers": load_balancer.servers,
        }
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)},
        )


@app.delete("/admin/servers/{server}")
async def remove_server(server: str):
    """Remove a backend server"""
    # Replace -- with : (for localhost:port format)
    server = server.replace("--", ":")
    load_balancer.remove_server(server)
    return {
        "message": f"Server {server} removed",
        "servers": load_balancer.servers,
    }


@app.get("/admin/servers")
async def list_servers():
    """Get all servers"""
    status = load_balancer.get_status()
    return {
        "total": len(status["servers"]),
        "healthy": len(status["healthy_servers"]),
        "servers": [
            {
                "address": server,
                "healthy": server in status["healthy_servers"],
            }
            for server in status["servers"]
        ],
    }


@app.post("/admin/reset-metrics")
async def reset_metrics():
    """Reset metrics"""
    load_balancer.metrics.reset()
    return {"message": "Metrics reset"}


@app.post("/admin/reset-rate-limits")
async def reset_rate_limits():
    """Reset rate limits"""
    load_balancer.rate_limiter.reset()
    return {"message": "Rate limits reset"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 3000))
    uvicorn.run(app, host="0.0.0.0", port=port)
