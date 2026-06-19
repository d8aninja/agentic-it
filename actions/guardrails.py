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
