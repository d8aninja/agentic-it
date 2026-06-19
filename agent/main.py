"""
Entry point for the agentic-it Wi-Fi fix agent.

Run:
    python -m agent.main

The agent reads one line from stdin, diagnoses it, plans an action, executes
it, and logs everything to the local SQLite database.
"""

import logging
import sys

from config.settings import settings
from agent.intent_parser import parse_intent
from agent.planner import build_plan
from agent.executor import execute_plan
from data.db import log_run

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def run_once(user_input: str) -> None:
    logger.info("User input: %r", user_input)

    diagnosis = parse_intent(user_input)
    logger.info(
        "Diagnosis: issue=%s action=%r confidence=%s",
        diagnosis.issue_detected,
        diagnosis.recommended_action,
        diagnosis.confidence,
    )

    plan = build_plan(diagnosis)
    result = execute_plan(plan)

    log_run(
        user_input=user_input,
        diagnosis=diagnosis.diagnosis,
        action=result.action,
        success=result.success,
        output=result.output,
    )

    if result.success:
        print(f"[OK] {result.action}: {result.output}")
    else:
        print(f"[FAIL] {result.action}: {result.output}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    if len(sys.argv) > 1:
        user_input = " ".join(sys.argv[1:])
    else:
        print("agentic-it> ", end="", flush=True)
        user_input = sys.stdin.readline().strip()

    if not user_input:
        print("No input provided.", file=sys.stderr)
        sys.exit(1)

    run_once(user_input)


if __name__ == "__main__":
    main()
