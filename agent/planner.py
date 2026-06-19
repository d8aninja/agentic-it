"""
Decides which action to run based on the parsed diagnosis.
Enforces guardrails before handing off to the executor.
"""

import logging
from dataclasses import dataclass

from agent.intent_parser import Diagnosis
from actions.guardrails import is_action_allowed

logger = logging.getLogger(__name__)


@dataclass
class Plan:
    action: str
    diagnosis: str
    confidence: str
    skip_reason: str = ""


def build_plan(diagnosis: Diagnosis) -> Plan:
    if not diagnosis.issue_detected:
        logger.info("No Wi-Fi issue detected, skipping action")
        return Plan(
            action="none",
            diagnosis=diagnosis.diagnosis,
            confidence=diagnosis.confidence,
            skip_reason="No issue detected by LLM",
        )

    action = diagnosis.recommended_action

    if not is_action_allowed(action):
        logger.warning("LLM recommended disallowed action %r — blocking", action)
        return Plan(
            action="none",
            diagnosis=diagnosis.diagnosis,
            confidence=diagnosis.confidence,
            skip_reason=f"Action '{action}' is not in the guardrails allow-list",
        )

    logger.info("Plan approved: action=%r confidence=%s", action, diagnosis.confidence)
    return Plan(
        action=action,
        diagnosis=diagnosis.diagnosis,
        confidence=diagnosis.confidence,
    )
