"""
Executes the approved action by calling into actions/network_actions.py.
"""

import logging
from dataclasses import dataclass

from agent.planner import Plan
from actions.network_actions import reconnect_known_network, restart_adapter, forget_and_rejoin

logger = logging.getLogger(__name__)

ACTION_MAP = {
    "reconnect_known_network": reconnect_known_network,
    "restart_adapter": restart_adapter,
    "forget_and_rejoin": forget_and_rejoin,
}


@dataclass
class ExecutionResult:
    action: str
    success: bool
    output: str


def execute_plan(plan: Plan) -> ExecutionResult:
    if plan.action == "none":
        reason = plan.skip_reason or "No action needed"
        logger.info("Execution skipped: %s", reason)
        return ExecutionResult(action="none", success=True, output=reason)

    fn = ACTION_MAP.get(plan.action)
    if fn is None:
        msg = f"No handler registered for action '{plan.action}'"
        logger.error(msg)
        return ExecutionResult(action=plan.action, success=False, output=msg)

    logger.info("Executing action: %s", plan.action)
    try:
        output = fn()
        logger.info("Action %r completed: %s", plan.action, output)
        return ExecutionResult(action=plan.action, success=True, output=output)
    except Exception as exc:
        logger.error("Action %r raised: %s", plan.action, exc)
        return ExecutionResult(action=plan.action, success=False, output=str(exc))
