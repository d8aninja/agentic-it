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
