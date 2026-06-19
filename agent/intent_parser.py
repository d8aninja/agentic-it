"""
Parses the user's natural-language input into a structured diagnosis
by sending it through the LLM with the Wi-Fi diagnosis system prompt.
"""

import json
import logging
import pathlib
from dataclasses import dataclass

from llm.factory import get_llm_provider
from llm.base import LLMProviderError

logger = logging.getLogger(__name__)

PROMPT_PATH = pathlib.Path(__file__).parent / "prompts" / "wifi_diagnosis_prompt.md"


@dataclass
class Diagnosis:
    issue_detected: bool
    diagnosis: str
    recommended_action: str
    confidence: str
    raw_text: str


def parse_intent(user_input: str) -> Diagnosis:
    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
    provider = get_llm_provider()
    logger.info("Using provider: %s", provider.__class__.__name__)

    try:
        response = provider.generate(system_prompt=system_prompt, user_input=user_input)
    except LLMProviderError as exc:
        logger.error("LLM call failed: %s", exc)
        raise

    raw = response.text.strip()
    logger.debug("Raw LLM response: %s", raw)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Try extracting JSON from within the response if the model leaked extra text
        import re
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            data = json.loads(match.group())
        else:
            logger.error("Could not parse JSON from LLM response: %s", raw)
            raise ValueError(f"LLM response was not valid JSON: {raw!r}")

    return Diagnosis(
        issue_detected=bool(data.get("issue_detected", False)),
        diagnosis=data.get("diagnosis", ""),
        recommended_action=data.get("recommended_action", "unknown"),
        confidence=data.get("confidence", "low"),
        raw_text=raw,
    )
