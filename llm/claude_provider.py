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
