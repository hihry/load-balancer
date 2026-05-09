# Load Balancer

A high-performance load balancer built with Python and FastAPI featuring consistent hashing, health checks, rate limiting, and comprehensive metrics.

## Features

- **Consistent Hashing** - Efficient request distribution across backend servers with minimal redistribution
- **Health Checks** - Periodic health monitoring of backend servers with automatic failover
- **Rate Limiting** - Per-IP rate limiting using token bucket algorithm
- **Metrics** - Request metrics, response times, and error tracking
- **Admin API** - Dynamic server management and monitoring endpoints

## Project Structure

```
LoadBalancer/
├── src/
│   ├── consistent_hash.py   - Consistent hashing algorithm
│   ├── health_check.py      - Server health monitoring
│   ├── rate_limiter.py      - Per-IP rate limiting
│   ├── metrics.py           - Request metrics tracking
│   └── load_balancer.py     - Main load balancer orchestrator
├── main.py                  - FastAPI server with API routes
├── requirements.txt
└── README.md
```

## Prerequisites

- Python 3.8+
- pip

## Installation

```bash
# Clone or navigate to the repository
cd LoadBalancer

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

Edit `main.py` to configure backend servers:

```python
BACKEND_SERVERS = [
    "localhost:3001",
    "localhost:3002",
    "localhost:3003",
]
```

Configure load balancer options:

```python
load_balancer = LoadBalancer(BACKEND_SERVERS, {
    "virtual_nodes": 150,           # Virtual nodes per server (consistency)
    "health_check_interval": 5,     # Health check interval (seconds)
    "health_check_timeout": 3,      # Health check timeout (seconds)
    "max_requests": 100,            # Rate limit: requests per window
    "rate_limit_window": 60000,     # Rate limit window (milliseconds)
})
```

## Running the Server

### Development Mode (with auto-reload)

```bash
uvicorn main:app --reload --port 3000
```

### Production Mode

```bash
python main.py
```

Or with Gunicorn:

```bash
gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:3000
```

The load balancer will start on `http://localhost:3000` by default.

## API Endpoints

### Request Routing

- `GET/POST/PUT/DELETE /api/*` - All requests are load balanced to backend servers

**Example:**
```bash
curl http://localhost:3000/api/users
```

### Health & Status

- `GET /health` - Load balancer health check
- `GET /status` - Current load balancer state and healthy servers
- `GET /metrics` - Request metrics and performance stats
- `GET /rate-limits` - Current rate limit stats by IP

### Admin Endpoints

#### Manage Backend Servers

**Add a server:**
```bash
curl -X POST http://localhost:3000/admin/servers \
  -H "Content-Type: application/json" \
  -d '{"server": "localhost:3004"}'
```

**Remove a server:**
```bash
curl -X DELETE http://localhost:3000/admin/servers/localhost--3001
```

Note: Use `--` instead of `:` in the URL path for port specification.

**List all servers:**
```bash
curl http://localhost:3000/admin/servers
```

#### Reset Data

**Reset metrics:**
```bash
curl -X POST http://localhost:3000/admin/reset-metrics
```

**Reset rate limits:**
```bash
curl -X POST http://localhost:3000/admin/reset-rate-limits
```

## Example Response - Status

```json
{
  "servers": ["localhost:3001", "localhost:3002", "localhost:3003"],
  "healthy_servers": ["localhost:3001", "localhost:3002"],
  "metrics": {
    "total_requests": 450,
    "avg_response_time": 125,
    "uptime": "323s",
    "status_codes": {
      "200": 440,
      "500": 10
    },
    "servers": [
      {
        "server": "localhost:3001",
        "requests": 150,
        "avg_response_time": 120,
        "errors": 2,
        "error_rate": "1.33%"
      },
      {
        "server": "localhost:3002",
        "requests": 140,
        "avg_response_time": 130,
        "errors": 3,
        "error_rate": "2.14%"
      },
      {
        "server": "localhost:3003",
        "requests": 160,
        "avg_response_time": 125,
        "errors": 5,
        "error_rate": "3.13%"
      }
    ]
  }
}
```

## Testing with Backend Servers

Create simple backend servers to test the load balancer:

```bash
# Terminal 1: Load Balancer
python main.py

# Terminal 2: Backend Server 1
python -m http.server 3001

# Terminal 3: Backend Server 2
python -m http.server 3002

# Terminal 4: Backend Server 3
python -m http.server 3003

# Terminal 5: Test requests
curl http://localhost:3000/api/
```

## Performance Tuning

- **Virtual Nodes**: Increase for better distribution with many servers
- **Health Check Interval**: Decrease for faster failure detection
- **Rate Limit**: Adjust based on expected traffic
- **Workers**: Use Gunicorn with multiple workers for production

## Monitoring

Check metrics regularly:

```bash
# View metrics
curl http://localhost:3000/metrics | python -m json.tool

# Monitor in real-time
watch -n 1 'curl -s http://localhost:3000/metrics | python -m json.tool | grep total_requests'
```

## License

MIT

## Author

Your Name
