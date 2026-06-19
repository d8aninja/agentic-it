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
