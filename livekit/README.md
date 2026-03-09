## LiveKit server

This folder contains configuration for running a **self-hosted LiveKit server** locally using Docker.

### Prerequisites

- Docker and Docker Compose installed on the host machine.

### Configuration

- `docker-compose.yml` – runs the `livekit/livekit-server` image with:
  - HTTP/WebSocket on `localhost:7880`
  - TURN on `localhost:7881` (can be disabled in `livekit.yaml`)
  - RTP ports `50000-60000/udp`
- `livekit.yaml` – minimal LiveKit configuration for **local audio-only development**.
  - Default dev API key: `devkey`
  - Default secret: `secret`
  - WebSocket URL: `ws://localhost:7880`

You can override API key/secret using environment variables when running Docker:

```bash
export LIVEKIT_API_KEY=mykey
export LIVEKIT_API_SECRET=mysecret
cd livekit
docker compose up -d
```

Once the server is running, the backend and frontend should use:

- **WS URL**: `ws://localhost:7880`
- **API key/secret**: the same values configured here

