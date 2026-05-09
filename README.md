# Load Balancer — Python / FastAPI

A consistent hashing load balancer with health checks, rate limiting, and a live metrics dashboard.

---

## Algorithm

This load balancer uses **Consistent Hashing** instead of random or round-robin selection.

- Every node is placed at 100 virtual positions on a hash ring (0 to 2^32) by hashing `NodeName:index`
- An incoming IP is hashed to a position on the ring and routed to the nearest node clockwise
- The same IP always produces the same hash, same position, same node — every time
- When a node is added or removed, only the IPs near that node's ring slots get remapped — all others are unaffected

---

## Project Structure

```
load-balancer/
├── src/
│   ├── __init__.py
│   ├── consistent_hash.py   # Hash ring — core routing algorithm
│   ├── health_check.py      # Tracks node UP/DOWN status
│   ├── rate_limiter.py      # Sliding window rate limiter per IP
│   ├── metrics.py           # Request counters and recent logs
│   └── load_balancer.py     # Wires all modules together
├── main.py                  # FastAPI server — all API endpoints
├── requirements.txt
└── README.md
```

---

## Setup and Run

**Requirements:** Python 3.10 or higher

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd load-balancer
```

### 2. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Start the server

```bash
uvicorn main:app --reload
```

Server runs at `http://localhost:8000`

Interactive API docs at `http://localhost:8000/docs`

---

## Configuration

Edit the `LoadBalancer` constructor in `main.py` to change defaults:

```python
lb = LoadBalancer(
    nodes=["Node-A", "Node-B", "Node-C"],  # starting nodes
    replicas=100,                           # virtual slots per node on the ring
    rate_limit=10,                          # max requests per IP per window
    rate_window=60,                         # sliding window in seconds
)
```

---

## API Endpoints

### General

#### `GET /`
Confirms the server is running.

```bash
curl http://localhost:8000/
```

```json
{ "status": "ok", "message": "Load Balancer is running" }
```

---

### Routing

#### `POST /route`
Route a specific IP to a node. The same IP always returns the same node.
Returns `429` if rate limited or no healthy nodes exist.

```bash
curl -X POST http://localhost:8000/route \
  -H "Content-Type: application/json" \
  -d '{"ip": "192.168.1.5"}'
```

```json
{
  "ip": "192.168.1.5",
  "routed_to": "Node-C",
  "blocked": false,
  "reason": null
}
```

---

#### `POST /simulate`
Simulate N requests with randomly generated IPs. Mirrors the task's `simulateTraffic()` function. Max 500 per call.

```bash
curl -X POST http://localhost:8000/simulate \
  -H "Content-Type: application/json" \
  -d '{"count": 10}'
```

```json
{
  "total": 10,
  "routed": 10,
  "blocked": 0,
  "results": [
    { "ip": "93.67.24.106", "routed_to": "Node-C", "blocked": false, "reason": null },
    { "ip": "76.33.176.4",  "routed_to": "Node-B", "blocked": false, "reason": null }
  ]
}
```

---

### Health

#### `GET /health`
Returns current UP/DOWN status of all nodes.

```bash
curl http://localhost:8000/health
```

```json
{
  "nodes": [
    { "node": "Node-A", "status": "UP", "last_changed": "2026-05-09T10:00:00" },
    { "node": "Node-B", "status": "UP", "last_changed": "2026-05-09T10:00:00" },
    { "node": "Node-C", "status": "UP", "last_changed": "2026-05-09T10:00:00" }
  ],
  "healthy_count": 3
}
```

---

#### `POST /health/down`
Mark a node as DOWN. Load balancer immediately stops routing to it.

```bash
curl -X POST http://localhost:8000/health/down \
  -H "Content-Type: application/json" \
  -d '{"node": "Node-B"}'
```

```json
{ "node": "Node-B", "status": "DOWN" }
```

---

#### `POST /health/up`
Bring a node back UP.

```bash
curl -X POST http://localhost:8000/health/up \
  -H "Content-Type: application/json" \
  -d '{"node": "Node-B"}'
```

```json
{ "node": "Node-B", "status": "UP" }
```

---

### Nodes

#### `GET /nodes`
List all nodes with health status and ring slot count.

```bash
curl http://localhost:8000/nodes
```

```json
{
  "nodes": [
    { "name": "Node-A", "status": "UP",   "ring_slots": 100 },
    { "name": "Node-B", "status": "DOWN", "ring_slots": 100 },
    { "name": "Node-C", "status": "UP",   "ring_slots": 100 }
  ]
}
```

---

#### `POST /nodes/add`
Add a new node at runtime. Immediately joins the hash ring and receives traffic.

```bash
curl -X POST http://localhost:8000/nodes/add \
  -H "Content-Type: application/json" \
  -d '{"node": "Node-D"}'
```

```json
{ "message": "Node 'Node-D' added", "nodes": ["Node-A", "Node-B", "Node-C", "Node-D"] }
```

---

#### `POST /nodes/remove`
Remove a node at runtime. Ring slots deleted, traffic redistributes automatically.

```bash
curl -X POST http://localhost:8000/nodes/remove \
  -H "Content-Type: application/json" \
  -d '{"node": "Node-D"}'
```

```json
{ "message": "Node 'Node-D' removed", "nodes": ["Node-A", "Node-B", "Node-C"] }
```

---

### Rate Limiting

#### `GET /ratelimit/status`
Shows rate limiter config and permanently blocked IPs.

```bash
curl http://localhost:8000/ratelimit/status
```

```json
{
  "limit": 10,
  "window_seconds": 60,
  "tracked_ips": 4,
  "blocked_ips": ["1.2.3.4"]
}
```

---

#### `POST /ratelimit/block`
Permanently block an IP. Always rejected regardless of the sliding window.

```bash
curl -X POST http://localhost:8000/ratelimit/block \
  -H "Content-Type: application/json" \
  -d '{"ip": "1.2.3.4"}'
```

```json
{ "message": "IP '1.2.3.4' permanently blocked" }
```

---

#### `POST /ratelimit/unblock`
Remove a permanent block from an IP.

```bash
curl -X POST http://localhost:8000/ratelimit/unblock \
  -H "Content-Type: application/json" \
  -d '{"ip": "1.2.3.4"}'
```

```json
{ "message": "IP '1.2.3.4' unblocked" }
```

---

### Metrics Dashboard

#### `GET /metrics`
Full live dashboard — total requests, block rate, per-node hits, top IPs, and the 50 most recent logs.

```bash
curl http://localhost:8000/metrics
```

```json
{
  "uptime_since": "2026-05-09T10:00:00",
  "total_requests": 20,
  "total_routed": 18,
  "total_blocked": 2,
  "block_rate_percent": 10.0,
  "node_hits": { "Node-A": 6, "Node-B": 5, "Node-C": 7 },
  "top_ips": [
    { "ip": "192.168.1.5", "requests": 4 },
    { "ip": "10.0.0.22",   "requests": 2 }
  ],
  "recent_logs": [
    { "time": "2026-05-09T10:01:00", "ip": "192.168.1.5", "routed_to": "Node-C", "blocked": false, "reason": null },
    { "time": "2026-05-09T10:00:58", "ip": "1.2.3.4",     "routed_to": null,     "blocked": true,  "reason": "rate_limit_exceeded" }
  ]
}
```

---

#### `POST /metrics/reset`
Reset all counters to zero.

```bash
curl -X POST http://localhost:8000/metrics/reset
```

```json
{ "message": "Metrics reset successfully" }
```

---

## Sample CLI Demo

```bash
# 1. Start the server
uvicorn main:app --reload

# 2. Simulate 10 requests
curl -X POST http://localhost:8000/simulate \
  -H "Content-Type: application/json" \
  -d '{"count": 10}'

# 3. Route same IP twice — confirm same node both times
curl -X POST http://localhost:8000/route -H "Content-Type: application/json" -d '{"ip": "10.10.10.10"}'
curl -X POST http://localhost:8000/route -H "Content-Type: application/json" -d '{"ip": "10.10.10.10"}'

# 4. Take Node-A down
curl -X POST http://localhost:8000/health/down -H "Content-Type: application/json" -d '{"node": "Node-A"}'

# 5. Route same IP — now goes to a different node
curl -X POST http://localhost:8000/route -H "Content-Type: application/json" -d '{"ip": "10.10.10.10"}'

# 6. Bring Node-A back up
curl -X POST http://localhost:8000/health/up -H "Content-Type: application/json" -d '{"node": "Node-A"}'

# 7. Check the metrics dashboard
curl http://localhost:8000/metrics
```

---

## Requirements

```
fastapi==0.111.0
uvicorn==0.29.0
```

```bash
pip install -r requirements.txt
```