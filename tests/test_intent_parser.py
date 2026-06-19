"""
Tests for agent/intent_parser.py.

Uses a stub LLM provider so no real API calls are made.
"""

import json
import pytest
from unittest.mock import patch, MagicMock

from llm.base import LLMResponse
from agent.intent_parser import parse_intent, Diagnosis


def _make_response(data: dict) -> LLMResponse:
    return LLMResponse(
        text=json.dumps(data),
        model_name="stub",
        provider_name="stub",
    )


@pytest.fixture(autouse=True)
def stub_provider(tmp_path):
    provider = MagicMock()
    with patch("agent.intent_parser.get_llm_provider", return_value=provider):
        yield provider


def test_wifi_issue_detected(stub_provider):
    stub_provider.generate.return_value = _make_response({
        "issue_detected": True,
        "diagnosis": "Cannot associate with AP",
        "recommended_action": "reconnect_known_network",
        "confidence": "high",
    })
    result = parse_intent("wifi won't connect")
    assert result.issue_detected is True
    assert result.recommended_action == "reconnect_known_network"
    assert result.confidence == "high"


def test_non_wifi_input(stub_provider):
    stub_provider.generate.return_value = _make_response({
        "issue_detected": False,
        "diagnosis": "Not a network issue",
        "recommended_action": "unknown",
        "confidence": "high",
    })
    result = parse_intent("my printer is broken")
    assert result.issue_detected is False
    assert result.recommended_action == "unknown"


def test_json_embedded_in_extra_text(stub_provider):
    """LLM sometimes leaks text before/after JSON — parser should recover."""
    payload = {
        "issue_detected": True,
        "diagnosis": "DHCP failure",
        "recommended_action": "restart_adapter",
        "confidence": "medium",
    }
    stub_provider.generate.return_value = LLMResponse(
        text=f"Sure! Here is the JSON:\n{json.dumps(payload)}\nHope that helps!",
        model_name="stub",
        provider_name="stub",
    )
    result = parse_intent("no ip address")
    assert result.recommended_action == "restart_adapter"


def test_invalid_json_raises(stub_provider):
    stub_provider.generate.return_value = LLMResponse(
        text="This is not JSON at all.",
        model_name="stub",
        provider_name="stub",
    )
    with pytest.raises(ValueError, match="not valid JSON"):
        parse_intent("something")
