"""
Network remediation actions. Each function executes the appropriate platform
script (PowerShell on Windows, bash on Linux/macOS) and returns a string
describing what happened.
"""

import logging
import platform
import subprocess
import pathlib

logger = logging.getLogger(__name__)

SCRIPTS_DIR = pathlib.Path(__file__).parent.parent / "scripts"


def _run_script(script_name_no_ext: str, *args: str) -> str:
    system = platform.system()
    if system == "Windows":
        script = SCRIPTS_DIR / f"{script_name_no_ext}.ps1"
        cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(script), *args]
    else:
        script = SCRIPTS_DIR / f"{script_name_no_ext}.sh"
        cmd = ["bash", str(script), *args]

    logger.debug("Running: %s", cmd)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

    output = result.stdout.strip() or result.stderr.strip()
    if result.returncode != 0:
        raise RuntimeError(
            f"Script exited {result.returncode}: {output}"
        )
    return output or "Done"


def reconnect_known_network() -> str:
    return _run_script("reconnect_wifi", "reconnect")


def restart_adapter() -> str:
    return _run_script("reconnect_wifi", "restart")


def forget_and_rejoin() -> str:
    return _run_script("reconnect_wifi", "forget_and_rejoin")
