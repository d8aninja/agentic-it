# agentic-it

An AI agent-driven IT operations system built for edge devices. Agents run as Docker containers directly on endpoint machines, orchestrated centrally by K3s/Kubernetes. Designed to operate fully offline — the agent diagnoses and remediates issues using a local LLM, with no dependency on cloud infrastructure at runtime.

---

## What it does (POC scope)

A user types a natural-language complaint — `ollama the wifi won't connect, fix it` — and the agent:

1. Parses the intent using an LLM (local Ollama model, no internet required)
2. Produces a structured diagnosis and recommended action
3. Checks the action against an explicit allow-list (guardrails)
4. Runs the appropriate remediation script (PowerShell on Windows, bash on Linux)
5. Logs the issue, diagnosis, action taken, and result to a local SQLite database

POC capabilities are intentionally narrow — Wi-Fi reconnection only. The architecture is designed to expand to other IT operations tasks (health checks, Defender remediation, log collection) without structural changes.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Edge Device                          │
│                                                         │
│   ┌─────────────────────┐   ┌─────────────────────┐    │
│   │   agent container   │   │   ollama container  │    │
│   │                     │   │                     │    │
│   │  agent/main.py      │──▶│  llama3.2:3b        │    │
│   │  intent_parser.py   │   │  (baked in at       │    │
│   │  planner.py         │   │   build time)       │    │
│   │  executor.py        │   │                     │    │
│   │  actions/           │   │  localhost:11434    │    │
│   │  scripts/           │   └─────────────────────┘    │
│   └─────────────────────┘                               │
│            │                                            │
│            ▼                                            │
│   scripts/reconnect_wifi.ps1  (Windows)                 │
│   scripts/reconnect_wifi.sh   (Linux)                   │
│            │                                            │
│            ▼                                            │
│   logs/agent_runs.db  (SQLite)                          │
└─────────────────────────────────────────────────────────┘
                         │
                         │ K3s DaemonSet
                         │ (one agent pod per node)
                         ▼
              ┌─────────────────────┐
              │   K3s Control Plane │
              │                     │
              │  DaemonSets         │
              │  ConfigMaps         │
              │  Secrets            │
              │  Liveness probes    │
              └─────────────────────┘
```

### Two containers, one purpose

**`agentic-it-ollama`** — built from `docker/ollama.Dockerfile`. Runs the Ollama LLM server with `llama3.2:3b` baked in at image build time. No internet access required at runtime. Exposes the model on port `11434`.

**`agentic-it-agent`** — built from `docker/agent.Dockerfile`. Runs the Python agent. Reads user input, calls the LLM, checks guardrails, executes remediation scripts. Talks to the Ollama container via `http://ollama:11434` (Docker internal network) or `http://localhost:11434` (local dev).

---

## LLM abstraction layer

The agent is model-agnostic. All LLM calls go through `llm/factory.py`, which returns a provider based on `LLM_PROVIDER` in `.env`:

```
llm/
├── base.py              # Abstract LLMProvider interface (generate, is_available)
├── factory.py           # Reads config, returns the active provider
├── claude_provider.py   # Anthropic Claude API (requires internet + API key)
└── local_provider.py    # Ollama HTTP client (fully offline)
```

**For this POC**, `LLM_PROVIDER=local` is hardcoded in `.env` — Ollama always handles inference. Claude is available as a future swap by changing one env var; no code changes required.

| `LLM_PROVIDER` | Provider used | Requires |
|---|---|---|
| `local` | Ollama (`llama3.2:3b`) | Ollama container running |
| `claude` | Anthropic Claude API | Internet + `ANTHROPIC_API_KEY` |
| `auto` | Claude if reachable, else Ollama | Either |

---

## Request flow

```
User input (stdin)
       │
       ▼
agent/main.py
  └── strips "ollama, " prefix, passes raw complaint
       │
       ▼
agent/intent_parser.py
  └── calls llm/factory.get_llm_provider().generate()
  └── system prompt: agent/prompts/wifi_diagnosis_prompt.md
  └── returns structured JSON:
      {
        "issue_detected": true,
        "diagnosis": "adapter not associated with known network",
        "recommended_action": "reconnect_known_network",
        "confidence": "high"
      }
       │
       ▼
agent/planner.py
  └── checks actions/guardrails.is_action_allowed(recommended_action)
  └── blocks anything not in config/guardrails.yaml
       │
       ▼
agent/executor.py
  └── calls actions/network_actions.py
  └── detects OS (Windows → .ps1, Linux → .sh)
  └── runs scripts/reconnect_wifi.ps1 or reconnect_wifi.sh
       │
       ▼
data/db.py
  └── logs to logs/agent_runs.db (SQLite)
```

---

## Guardrails

The agent will only ever execute actions that appear in `config/guardrails.yaml`. The LLM cannot instruct the agent to run anything outside this list, regardless of what it returns.

```yaml
allowed_actions:
  - reconnect_known_network
  - restart_adapter
  - forget_and_rejoin
```

This is intentional and is a core design principle — the constrained action surface is not an afterthought. Adding new capabilities requires a deliberate change to both the allow-list and the corresponding action implementation in `actions/network_actions.py`.

---

## Ollama Docker image

The Ollama image uses a single-layer `RUN` pattern to bake the model in at build time:

```dockerfile
RUN ollama serve &
    SERVER_PID=$! &&
    # poll until server ready
    for i in $(seq 1 60); do
      ollama list >/dev/null 2>&1 && break; sleep 1
    done &&
    ollama pull llama3.2:3b &&
    kill $SERVER_PID &&
    wait $SERVER_PID 2>/dev/null || true
```

Everything — server start, model pull, server shutdown — happens in one `RUN` instruction so the model weights persist in the final image layer. The result is a ~5GB image that requires zero internet access at container startup.

**Tradeoff:** larger image size in exchange for guaranteed offline operation on any device that receives the image.

---

## Running locally (dev)

### Prerequisites
- Docker Desktop
- Python 3.11+
- `pip install -r requirements.txt`

### With docker-compose (recommended)

```bash
# copy and fill in your settings
cp .env.example .env

# start both containers
docker-compose up

# in a separate terminal, run the agent
python -m agent.main "ollama the wifi won't connect, fix it"
```

### Manual (Ollama container only)

```bash
# build the ollama image (one-time, takes ~10 min — downloads 2GB model)
docker build -f docker/ollama.Dockerfile -t agentic-it-ollama .

# run it
docker run --rm -p 11434:11434 agentic-it-ollama

# verify model is present (no download should occur)
curl http://localhost:11434/api/tags

# run the agent against it
LLM_PROVIDER=local python -m agent.main "ollama the wifi won't connect, fix it"
```

### Run tests

```bash
pytest tests/ -v
```

Tests mock both the LLM and subprocess calls — no real network adapter or API key required to pass them.

---

## Kubernetes deployment (K3s)

Manifests are in `k3s/`. The agent runs as a DaemonSet — one pod per node — so every edge device gets its own agent instance managed by the control plane.

```bash
kubectl apply -f k3s/namespace.yaml
kubectl apply -f k3s/configmap.yaml
kubectl apply -f k3s/secret.yaml        # copy from secret.yaml.example first
kubectl apply -f k3s/ollama-deployment.yaml
kubectl apply -f k3s/agent-daemonset.yaml
```

Node labels control which nodes get the agent:
- `node-role=windows` → runs `reconnect_wifi.ps1`
- `node-role=linux` → runs `reconnect_wifi.sh`

OS detection happens at runtime inside the agent, not at the manifest level.

---

## Configuration

All configuration lives in `.env` (never committed — see `.gitignore`):

```env
LLM_PROVIDER=local                        # local | claude | auto
ANTHROPIC_API_KEY=your-key-here           # only needed for LLM_PROVIDER=claude
CLAUDE_MODEL=claude-sonnet-4-6            # only used when provider=claude
OLLAMA_BASE_URL=http://localhost:11434    # points to ollama container
OLLAMA_MODEL=llama3.2:3b                  # model baked into ollama image
LOG_LEVEL=INFO
```

---

## Repository structure

```
agentic-it/
├── docker/
│   ├── agent.Dockerfile       # Python agent container
│   ├── ollama.Dockerfile      # Ollama + llama3.2:3b baked in
│   └── README.md
├── k3s/                       # Kubernetes manifests
│   ├── namespace.yaml
│   ├── agent-daemonset.yaml
│   ├── ollama-deployment.yaml
│   ├── configmap.yaml
│   └── secret.yaml.example
├── agent/                     # AI planner / decision engine
│   ├── main.py
│   ├── intent_parser.py
│   ├── planner.py
│   ├── executor.py
│   └── prompts/
│       └── wifi_diagnosis_prompt.md
├── llm/                       # Model-agnostic LLM abstraction
│   ├── base.py
│   ├── factory.py
│   ├── claude_provider.py
│   └── local_provider.py
├── actions/                   # Safe callable tools
│   ├── network_actions.py
│   └── guardrails.py
├── scripts/                   # Remediation scripts
│   ├── reconnect_wifi.ps1     # Windows
│   └── reconnect_wifi.sh      # Linux
├── config/
│   ├── settings.py
│   └── guardrails.yaml        # Action allow-list
├── data/
│   └── db.py                  # SQLite logging
├── logs/                      # Runtime logs (gitignored)
├── tests/
│   ├── test_intent_parser.py
│   └── test_network_actions.py
├── docker-compose.yml
├── .env                       # Local config (gitignored)
├── .env.example
├── requirements.txt
└── README.md
```

---

## Design principles

**Offline-first is a hard constraint.** Every POC capability works without internet. Cloud-dependent features (Microsoft Graph, SharePoint, Entra ID) are deferred to a future phase and will be additive, not a retrofit.

**Model-agnostic by design.** Swapping the LLM is a one-line config change. The agent code has no knowledge of which model is running.

**Constrained action surface.** The guardrails allow-list is the boundary between "the model suggested X" and "the system does X." It is intentionally small and grows deliberately.

**Edge-native lifecycle.** K3s manages agent health, restarts, and configuration. No bespoke agent management layer — Kubernetes handles it.

---

## What's next (beyond POC)

- Additional local task modules: health checks (CPU/memory/disk), Defender status, log collection
- Cloud integration phase: Microsoft Graph API, SharePoint, Entra ID/Managed Identity — all offline-optional
- Helm charts for production rollout packaging
- Docker pre-installation strategy for devices without Docker
- Voice input (speech-to-text front door to the agent)
