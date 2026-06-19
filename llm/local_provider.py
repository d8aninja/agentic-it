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
