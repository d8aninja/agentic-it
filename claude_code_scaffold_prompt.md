# Claude Code Scaffolding Prompt — agentic-it (Wi-Fi Fix POC)

Paste everything below into Claude Code (`claude`) from an empty project directory.

---

Create a new repository called `agentic-it` with the following structure and file
contents. This is a proof-of-concept for an edge-deployed IT agent that listens for
a natural-language request like "ollama the wifi won't connect, fix it", diagnoses
the problem using an LLM, and runs a constrained set of Wi-Fi remediation actions.
The LLM backend must be swappable (Claude when online, a local Ollama model when
offline) without changing any code outside the `llm/` package.

Create this exact directory structure:

```
agentic-it/
├── docker/
│   ├── agent.Dockerfile
│   └── ollama.Dockerfile
├── k3s/
│   ├── namespace.yaml
│   ├── agent-daemonset.yaml
│   ├── ollama-deployment.yaml
│   ├── configmap.yaml
│   ├── secret.yaml.example
│   └── README.md
├── docker-compose.yml
├── .env
├── .env.example
├── agent/
│   ├── main.py
│   ├── intent_parser.py
│   ├── planner.py
│   ├── executor.py
│   └── prompts/
│       └── wifi_diagnosis_prompt.md
├── llm/
│   ├── base.py
│   ├── claude_provider.py
│   ├── local_provider.py
│   └── factory.py
├── actions/
│   ├── network_actions.py
│   └── guardrails.py
├── scripts/
│   ├── reconnect_wifi.ps1
│   └── reconnect_wifi.sh
├── config/
│   ├── settings.py
│   └── guardrails.yaml
├── data/
│   └── db.py
├── logs/
│   └── .gitkeep
├── tests/
│   ├── test_intent_parser.py
│   └── test_network_actions.py
├── requirements.txt
└── README.md
```

Use the following content for these specific files (write these exactly as given,
don't paraphrase or simplify the logic — these encode real design decisions):

## llm/base.py

```python
"""
Abstract interface every LLM provider must implement.

This is the seam that makes the agent model-agnostic. agent/intent_parser.py
and agent/planner.py should only ever import LLMProvider from this file —
never a concrete provider directly. Swapping models means writing a new
provider class here and registering it in factory.py. Nothing else changes.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMResponse:
    text: str
    model_name: str
    provider_name: str


class LLMProvider(ABC):
    """Common contract for any LLM backend (cloud or local)."""

    @abstractmethod
    def generate(self, system_prompt: str, user_input: str) -> LLMResponse:
        """
        Send a system prompt + user input, return a single completion.
        Implementations must be synchronous and raise LLMProviderError
        (not a provider-specific exception) on failure, so callers can
        handle failures uniformly regardless of backend.
        """
        raise NotImplementedError

    @abstractmethod
    def is_available(self) -> bool:
        """
        Cheap health check used by factory.py to decide whether this
        provider can currently be used (e.g. can the Claude API be
        reached right now, or is Ollama responding on localhost).
        Must not raise; return False on any failure.
        """
        raise NotImplementedError


class LLMProviderError(Exception):
    """Raised by any provider implementation on generation failure."""
    pass
```

## llm/factory.py

```python
"""
Selects the active LLMProvider at runtime.

Connectivity-aware: prefers Claude when reachable, falls back to the local
Ollama provider when offline. This is what lets the agent work whether or
not the device currently has internet, without the rest of the codebase
knowing or caring which backend answered.
"""

import logging

from config.settings import settings
from llm.base import LLMProvider
from llm.claude_provider import ClaudeProvider
from llm.local_provider import LocalOllamaProvider

logger = logging.getLogger(__name__)


def get_llm_provider() -> LLMProvider:
    """
    Returns the LLMProvider to use for this request.

    Selection logic:
    1. If settings.LLM_PROVIDER is explicitly set to "claude" or "local",
       honor that — but still verify availability and fall back if the
       forced choice isn't actually reachable.
    2. If set to "auto" (default), try Claude first, fall back to local.
    """
    forced = settings.LLM_PROVIDER.lower()

    claude = ClaudeProvider()
    local = LocalOllamaProvider()

    if forced == "claude":
        if claude.is_available():
            return claude
        logger.warning("LLM_PROVIDER=claude but Claude API unreachable, falling back to local")
        return local

    if forced == "local":
        return local

    # auto mode: prefer Claude, fall back to local Ollama
    if claude.is_available():
        logger.info("Using Claude provider (online)")
        return claude

    logger.info("Claude unavailable, using local Ollama provider (offline mode)")
    return local
```

## llm/claude_provider.py

```python
"""
Claude API provider. Used when the device has internet connectivity.
"""

import logging

import anthropic

from config.settings import settings
from llm.base import LLMProvider, LLMResponse, LLMProviderError

logger = logging.getLogger(__name__)


class ClaudeProvider(LLMProvider):
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = settings.CLAUDE_MODEL  # e.g. "claude-sonnet-4-6"

    def generate(self, system_prompt: str, user_input: str) -> LLMResponse:
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=512,
                system=system_prompt,
                messages=[{"role": "user", "content": user_input}],
            )
            text = "".join(
                block.text for block in response.content if block.type == "text"
            )
            return LLMResponse(text=text, model_name=self.model, provider_name="claude")
        except Exception as exc:
            logger.error("Claude generation failed: %s", exc)
            raise LLMProviderError(str(exc)) from exc

    def is_available(self) -> bool:
        try:
            # Lightweight reachability check — short timeout, minimal call.
            self.client.messages.create(
                model=self.model,
                max_tokens=1,
                messages=[{"role": "user", "content": "ping"}],
            )
            return True
        except Exception as exc:
            logger.debug("Claude availability check failed: %s", exc)
            return False
```

## llm/local_provider.py

```python
"""
Local Ollama provider. Used when the device is offline.
Default model: llama3.2:3b — small enough to run on CPU-only edge hardware.
"""

import logging

import requests

from config.settings import settings
from llm.base import LLMProvider, LLMResponse, LLMProviderError

logger = logging.getLogger(__name__)


class LocalOllamaProvider(LLMProvider):
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL  # e.g. "http://localhost:11434"
        self.model = settings.OLLAMA_MODEL        # e.g. "llama3.2:3b"

    def generate(self, system_prompt: str, user_input: str) -> LLMResponse:
        try:
            resp = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": f"{system_prompt}\n\nUser: {user_input}",
                    "stream": False,
                },
                timeout=30,
            )
            resp.raise_for_status()
            text = resp.json().get("response", "")
            return LLMResponse(text=text, model_name=self.model, provider_name="ollama")
        except Exception as exc:
            logger.error("Ollama generation failed: %s", exc)
            raise LLMProviderError(str(exc)) from exc

    def is_available(self) -> bool:
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return resp.status_code == 200
        except Exception as exc:
            logger.debug("Ollama availability check failed: %s", exc)
            return False
```

## agent/prompts/wifi_diagnosis_prompt.md

```markdown
You are a Wi-Fi diagnostic assistant running on a local device. You only handle
Wi-Fi connectivity issues. You do not have general conversation ability and you
must not attempt to help with anything outside network connectivity.

Given the user's description of their problem, respond with ONLY a JSON object,
no other text, in this exact shape:

{
  "issue_detected": true | false,
  "diagnosis": "short description of what's likely wrong",
  "recommended_action": "reconnect_known_network" | "restart_adapter" | "forget_and_rejoin" | "unknown",
  "confidence": "high" | "medium" | "low"
}

Rules:
- If the user's message is not about Wi-Fi or network connectivity, set
  "issue_detected" to false and "recommended_action" to "unknown".
- "recommended_action" must be one of the four listed values, nothing else.
- Do not invent actions outside that list, even if you think they'd help.
- Do not include explanation text outside the JSON object.
```

## actions/guardrails.py

```python
"""
Validates that whatever action the LLM recommended is actually one this
agent is allowed to run. This is the safety boundary between "the model
said to do X" and "the system actually does X" — never execute an action
that isn't explicitly allow-listed here, regardless of what the LLM returns.
"""

import yaml

ALLOWED_ACTIONS_PATH = "config/guardrails.yaml"


def load_allowed_actions() -> set[str]:
    with open(ALLOWED_ACTIONS_PATH, "r") as f:
        config = yaml.safe_load(f)
    return set(config.get("allowed_actions", []))


def is_action_allowed(action_name: str) -> bool:
    return action_name in load_allowed_actions()
```

## config/guardrails.yaml

```yaml
# Only these actions may ever be executed, regardless of what the LLM
# recommends. This list should only grow deliberately, not automatically.
allowed_actions:
  - reconnect_known_network
  - restart_adapter
  - forget_and_rejoin
```

## config/settings.py

```python
"""
Central settings, loaded from environment variables (see .env.example).
"""

import os
from dataclasses import dataclass


@dataclass
class Settings:
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "auto")  # "auto" | "claude" | "local"
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
```

## .env.example

```
LLM_PROVIDER=auto
ANTHROPIC_API_KEY=your-key-here
CLAUDE_MODEL=claude-sonnet-4-6
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
LOG_LEVEL=INFO
```

---

For all other files (agent/main.py, agent/intent_parser.py, agent/planner.py,
agent/executor.py, actions/network_actions.py, scripts/reconnect_wifi.ps1,
scripts/reconnect_wifi.sh, docker/agent.Dockerfile, docker/ollama.Dockerfile,
docker-compose.yml, k3s/*.yaml, data/db.py, tests/*, requirements.txt, README.md):

Write working, reasonably complete implementations, not empty stubs. Wire them
together so this actually runs end-to-end as a CLI loop:

1. `agent/main.py` reads a line of text from stdin (simulating the user saying
   "ollama, the wifi won't connect, fix it").
2. `agent/intent_parser.py` calls `llm/factory.get_llm_provider()`, sends the
   wifi_diagnosis_prompt.md system prompt plus the user's text, parses the JSON
   response.
3. `agent/planner.py` takes the parsed diagnosis and checks
   `actions/guardrails.is_action_allowed()` before deciding what to run.
4. `agent/executor.py` calls the corresponding function in
   `actions/network_actions.py`, which on Linux shells out to
   `scripts/reconnect_wifi.sh` and on Windows to `scripts/reconnect_wifi.ps1`
   (detect OS at runtime).
5. Log the user's report, the diagnosis, the action taken, and the result to
   a local SQLite db via `data/db.py`.

Keep requirements.txt minimal: anthropic, requests, pyyaml, pytest — nothing
unused. Write a README.md that explains how to run this locally with
docker-compose (agent + ollama containers) and how it would later deploy via
the k3s manifests as a DaemonSet.
