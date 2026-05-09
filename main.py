from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from src.load_balancer import LoadBalancer

# ── App setup ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Load Balancer API",
    description="Consistent hashing load balancer with health checks, rate limiting and metrics.",
    version="1.0.0",
)

# Single shared instance — all endpoints use this
lb = LoadBalancer(
    nodes=["Node-A", "Node-B", "Node-C"],
    replicas=100,
    rate_limit=10,
    rate_window=60,
)

# ── Request models ────────────────────────────────────────────────────────────

class RouteRequest(BaseModel):
    ip: str

class SimulateRequest(BaseModel):
    count: int = 10

class NodeRequest(BaseModel):
    node: str

class BlockRequest(BaseModel):
    ip: str

# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", tags=["General"])
def root():
    """Health ping — confirms the server is running."""
    return {"status": "ok", "message": "Load Balancer is running"}


@app.post("/route", tags=["Routing"])
def route_ip(body: RouteRequest):
    """
    Route a specific IP to a node.

    - Same IP will always return the same node.
    - Blocked if rate limit is exceeded.
    - Blocked if no healthy nodes are available.
    """
    result = lb.route(body.ip)
    if result["blocked"]:
        raise HTTPException(status_code=429, detail=result)
    return result


@app.post("/simulate", tags=["Routing"])
def simulate(body: SimulateRequest):
    """
    Simulate N requests with randomly generated IPs.
    Mirrors the task's simulateTraffic() function.
    """
    if body.count < 1 or body.count > 500:
        raise HTTPException(status_code=400, detail="count must be between 1 and 500")
    results = lb.simulate_traffic(body.count)
    routed  = [r for r in results if not r["blocked"]]
    blocked = [r for r in results if r["blocked"]]
    return {
        "total": body.count,
        "routed": len(routed),
        "blocked": len(blocked),
        "results": results,
    }


@app.get("/metrics", tags=["Dashboard"])
def metrics():
    """
    Live metrics dashboard.
    Shows total requests, per-node hits, top IPs, block rate, and recent logs.
    """
    return lb.metrics.dashboard()


@app.get("/health", tags=["Health"])
def health():
    """Show current health status of all nodes."""
    return {
        "nodes": lb.health.report(),
        "healthy_count": len(lb.health.healthy_nodes()),
    }


@app.post("/health/down", tags=["Health"])
def mark_down(body: NodeRequest):
    """Mark a node as DOWN — it will be skipped by the load balancer."""
    success = lb.health.mark_down(body.node)
    if not success:
        raise HTTPException(status_code=404, detail=f"Node '{body.node}' not found")
    return {"node": body.node, "status": "DOWN"}


@app.post("/health/up", tags=["Health"])
def mark_up(body: NodeRequest):
    """Bring a node back UP."""
    success = lb.health.mark_up(body.node)
    if not success:
        raise HTTPException(status_code=404, detail=f"Node '{body.node}' not found")
    return {"node": body.node, "status": "UP"}


@app.get("/nodes", tags=["Nodes"])
def list_nodes():
    """List all nodes with their health status and ring slot count."""
    distribution = lb.ring.get_distribution()
    return {
        "nodes": [
            {
                "name": node,
                "status": "UP" if lb.health.is_healthy(node) else "DOWN",
                "ring_slots": distribution.get(node, 0),
            }
            for node in lb.nodes
        ]
    }


@app.post("/nodes/add", tags=["Nodes"])
def add_node(body: NodeRequest):
    """Add a new node to the load balancer at runtime."""
    if body.node in lb.nodes:
        raise HTTPException(status_code=400, detail=f"Node '{body.node}' already exists")
    lb.add_node(body.node)
    return {"message": f"Node '{body.node}' added", "nodes": lb.nodes}


@app.post("/nodes/remove", tags=["Nodes"])
def remove_node(body: NodeRequest):
    """Remove a node from the load balancer at runtime."""
    if body.node not in lb.nodes:
        raise HTTPException(status_code=404, detail=f"Node '{body.node}' not found")
    lb.remove_node(body.node)
    return {"message": f"Node '{body.node}' removed", "nodes": lb.nodes}


@app.post("/ratelimit/block", tags=["Rate Limiting"])
def block_ip(body: BlockRequest):
    """Permanently block an IP address."""
    lb.limiter.block_ip(body.ip)
    return {"message": f"IP '{body.ip}' permanently blocked"}


@app.post("/ratelimit/unblock", tags=["Rate Limiting"])
def unblock_ip(body: BlockRequest):
    """Remove a permanent block from an IP address."""
    lb.limiter.unblock_ip(body.ip)
    return {"message": f"IP '{body.ip}' unblocked"}


@app.get("/ratelimit/status", tags=["Rate Limiting"])
def ratelimit_status():
    """Show current rate limiter config and blocked IPs."""
    return lb.limiter.report()


@app.post("/metrics/reset", tags=["Dashboard"])
def reset_metrics():
    """Reset all metrics counters to zero."""
    lb.metrics.reset()
    return {"message": "Metrics reset successfully"}