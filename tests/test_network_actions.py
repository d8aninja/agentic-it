"""
Tests for actions/network_actions.py.

Mocks subprocess.run so no real system commands are executed.
"""

import subprocess
import pytest
from unittest.mock import patch, MagicMock

import actions.network_actions as na


def _good_result(stdout="Done"):
    r = MagicMock()
    r.returncode = 0
    r.stdout = stdout
    r.stderr = ""
    return r


def _bad_result(stderr="Script failed"):
    r = MagicMock()
    r.returncode = 1
    r.stdout = ""
    r.stderr = stderr
    return r


@pytest.fixture(autouse=True)
def mock_run():
    with patch("actions.network_actions.subprocess.run") as m:
        yield m


def test_reconnect_known_network_success(mock_run):
    mock_run.return_value = _good_result("Reconnected")
    result = na.reconnect_known_network()
    assert result == "Reconnected"
    mock_run.assert_called_once()


def test_restart_adapter_success(mock_run):
    mock_run.return_value = _good_result("Adapter restarted")
    result = na.restart_adapter()
    assert "restarted" in result.lower() or result == "Adapter restarted"


def test_forget_and_rejoin_success(mock_run):
    mock_run.return_value = _good_result("Rejoined")
    result = na.forget_and_rejoin()
    assert result == "Rejoined"


def test_script_failure_raises(mock_run):
    mock_run.return_value = _bad_result("Access denied")
    with pytest.raises(RuntimeError, match="Access denied"):
        na.reconnect_known_network()


def test_correct_script_extension_windows(mock_run):
    mock_run.return_value = _good_result()
    with patch("actions.network_actions.platform.system", return_value="Windows"):
        na.reconnect_known_network()
    cmd = mock_run.call_args[0][0]
    assert any(arg.endswith(".ps1") for arg in cmd)


def test_correct_script_extension_linux(mock_run):
    mock_run.return_value = _good_result()
    with patch("actions.network_actions.platform.system", return_value="Linux"):
        na.reconnect_known_network()
    cmd = mock_run.call_args[0][0]
    assert any(arg.endswith(".sh") for arg in cmd)
