# agentic-it — Edge-Deployed Wi-Fi Fix Agent

A proof-of-concept IT agent that listens for a natural-language request like
"ollama, the wifi won't connect, fix it", diagnoses the problem using an LLM,
and runs a constrained set of Wi-Fi remediation actions.

The LLM backend is swappable: Claude when online, a local Ollama model when
offline — with no code changes outside the `llm/` package.

## Architecture

```
stdin ──► main.py
            │
            ▼
      intent_parser.py  ──► llm/factory.py ──► ClaudeProvider (online)
            │                                └─► LocalOllamaProvider (offline)
            ▼
        planner.py  ──► actions/guardrails.py (allow-list check)
            │
            ▼
       executor.py  ──► actions/network_actions.py
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
         scripts/reconnect_wifi.ps1   scripts/reconnect_wifi.sh
                    │
                    ▼
                data/db.py  ──► logs/agent_runs.db
```

## Quick start (local, no Docker)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Copy and configure environment
cp .env.example .env
# Edit .env — set ANTHROPIC_API_KEY if you want the Claude provider

# 3. Run
python -m agent.main "the wifi won't connect, fix it"
```

## Running with Docker Compose (agent + Ollama)

```bash
# Build and start both containers
docker compose up --build

# In another terminal, send a request
docker exec -i agentic-it-agent python -m agent.main "wifi won't connect"
```

The `ollama` service starts, pulls `llama3.2:3b` on first boot, and stays
running. The `agent` service connects to it via `http://ollama:11434`.

If `ANTHROPIC_API_KEY` is set in `.env`, the agent tries Claude first and
only falls back to Ollama when offline (`LLM_PROVIDER=auto`).

## Running tests

```bash
pytest tests/
```

## k3s deployment (edge cluster)

See [`k3s/README.md`](k3s/README.md). The agent runs as a **DaemonSet** — one
pod per node — so every machine in the cluster can self-remediate. Ollama runs
as a shared **Deployment** with a PVC for model storage.

Apply order:

```bash
kubectl apply -f k3s/namespace.yaml
kubectl apply -f k3s/configmap.yaml
kubectl apply -f k3s/secret.yaml       # copy from secret.yaml.example
kubectl apply -f k3s/ollama-deployment.yaml
kubectl apply -f k3s/agent-daemonset.yaml
```

## Guardrails

The agent will **only ever execute** the three actions listed in
`config/guardrails.yaml`:

- `reconnect_known_network`
- `restart_adapter`
- `forget_and_rejoin`

The LLM cannot cause any other action to run, regardless of what it returns.
This allow-list is checked in `actions/guardrails.py` before any script is
called.

## Extending

- **New LLM backend**: implement `LLMProvider` in `llm/`, register in `llm/factory.py`.
- **New action**: add to `config/guardrails.yaml`, implement in `actions/network_actions.py`,
  add a handler in `agent/executor.py`, and update the prompt in
  `agent/prompts/wifi_diagnosis_prompt.md`.
