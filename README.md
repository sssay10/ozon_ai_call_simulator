# Ozon AI Call Simulator

## Environment configuration

- **`.env.example`**: template with all required variables. Copy it to `.env.development` or `.env.production` and fill in real values.
- **`.env.development`**: used for local development together with `docker-compose.dev.yml`.
- **`.env.production`**: used for production / remote deployment together with `docker-compose.yml`.

### Environment variables reference

- **`OPENROUTER_API_KEY` / `OPENAI_API_KEY`**: API key(s) for your LLM provider (OpenRouter / OpenAI).
- **`OPENROUTER_MODEL_DEFAULT`**: default model used by the frontend when calling the LLM.
- **`FRONTEND_ORIGIN`**: base URL where the frontend is served (e.g. `http://localhost:3000` or your production domain).
- **`LIVEKIT_URL`**: WebSocket URL of the LiveKit server used for audio/video sessions.
- **`LIVEKIT_API_KEY` / `LIVEKIT_API_SECRET`**: credentials for authenticating against LiveKit.
- **`POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB`**: Postgres credentials and database name.
- **`TONE_MODELS_DIR`**: path to the T-One STT models directory used by `stt_service`.
- **`DATABASE_URL`**: full Postgres connection string used by judge, auth, and agent services.
- **`AUTH_JWT_SECRET`**: secret key for signing auth JWT tokens (must be strong in production).
- **`AUTH_TOKEN_TTL_HOURS`**: lifetime of issued auth tokens in hours.
- **`LLM_PROVIDER`**: which LLM backend to use (`openrouter` or `ollama`).
- **`OPENROUTER_BASE_URL`**: base URL for the OpenRouter API.
- **`JUDGE_OPENROUTER_MODEL`**: OpenRouter model used by `judge_service`.
- **`AGENT_OPENROUTER_MODEL`**: OpenRouter model used by `agent_service`.
- **`JUDGE_OLLAMA_BASE_URL` / `JUDGE_OLLAMA_MODEL`**: Ollama base URL and model used by `judge_service`.
- **`AGENT_OLLAMA_BASE_URL` / `AGENT_OLLAMA_MODEL`**: Ollama base URL and model used by `agent_service`.

### Using Ollama instead of OpenRouter

- **Install Ollama** on your machine and pull a model, for example:
  - `ollama pull qwen2:7b-instruct-q4_K_M`
- **Set env vars** in `.env.development` or `.env.production`:
  - `LLM_PROVIDER=ollama`
  - `OLLAMA_BASE_URL=http://host.docker.internal:11434` (or your Ollama host)
  - `OLLAMA_MODEL` to the model name you pulled (e.g. `qwen2:7b-instruct-q4_K_M`)
- **Restart Docker services** so `judge_service` and `agent_service` pick up the new configuration.

### LiveKit server configuration (`livekit.yaml`)

- **File locations**:
  - `livekit/livekit.dev.yaml`: used by `docker-compose.dev.yml` for local development.
  - `livekit/livekit.yaml`: used by `docker-compose.yml` for production.
- **Ports**:
  - `port`: HTTP/WebSocket signaling port (matches `7880` in `docker-compose*`).
  - `rtc.port_range_start` / `rtc.port_range_end`: UDP port range for media (exposed in docker).
  - `rtc.tcp_port` (prod only): TCP fallback port for WebRTC (matches `7881` in `docker-compose.yml`).
- **Networking / TURN**:
  - `rtc.use_external_ip` / `rtc.node_ip`: how the node advertises its IP in ICE candidates.
  - `turn.enabled`, `turn.udp_port`, `turn.domain`: built-in TURN server for clients that cannot use direct UDP.
- **Auth keys**:
  - `keys`: API key / secret pairs; must match `LIVEKIT_API_KEY` / `LIVEKIT_API_SECRET` in your env files.

## How to run for development

### Download T-One models from cloud and place them to stt_service/tone_models
https://drive.google.com/drive/folders/1VPnN8XAr2ads2HqjbrIMEPqXgaOvNW4u?usp=sharing

### Export environment variables
```bash
source .env.development
```

### Run services
```bash
docker compose -f docker-compose.dev.yml up -d
```

### Open localhost in browser and enjoy

## How to run for production

### Export environment variables
```bash
source .env.production
```

### Run services
```bash
docker compose up -d
```

### Open your production domain in browser
