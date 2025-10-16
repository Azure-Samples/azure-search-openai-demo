# Run the MCP (backend) server

This document explains how to run only the backend (MCP/SSE) server locally or inside Docker. The backend exposes the SSE endpoint `/chat/stream` which can be used by an external connector.

Prerequisites
- Python 3.10+ (for local run)
- Docker (optional)
- cloudflared (optional) to create a public tunnel

## Option A — Run locally (recommended)

From the repository root:

```bash
./run_mcp.sh 50505
```

This will:
- create `.venv` if not present
- install backend requirements from `app/backend/requirements.txt`
- start the Quart backend on `0.0.0.0:50505`

Test endpoints:

```bash
curl http://localhost:50505/config
```

SSE endpoint (use this for connectors):

```
http://localhost:50505/chat/stream
```

## Option B — Run with Docker

Build image:

```bash
docker build -t azure-search-mcp .
```

Run container:

```bash
docker run -d --name azure-search-mcp -p 50505:50505 azure-search-mcp
```

Then the same endpoints are available on the host.

## Expose a public HTTPS tunnel (Cloudflare Tunnel)

Install `cloudflared` and run:

```bash
cloudflared tunnel --url http://localhost:50505
```

The command prints a public URL like `https://xxxx.trycloudflare.com`. Use the SSE path when registering the connector:

```
https://xxxx.trycloudflare.com/chat/stream
```

Note: if your connector expects a different path (e.g., `/sse`), create a small proxy or add a redirect handler in `app/backend/app.py`.
