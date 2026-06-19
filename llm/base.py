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
