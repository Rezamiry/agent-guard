"""Base import stays independent of optional frameworks and detector packages."""

import os
import subprocess
import sys
from importlib import metadata
from pathlib import Path


def test_base_package_imports_without_site_packages() -> None:
    project_root = Path(__file__).resolve().parents[2]
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(project_root / "src")
    process = subprocess.run(
        [sys.executable, "-S", "-c", "import agent_guard; print(agent_guard.Guard.__name__)"],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    assert process.returncode == 0, process.stderr
    assert process.stdout.strip() == "Guard"


def test_each_optional_extra_is_declared_independently() -> None:
    extras = set(metadata.distribution("agent-guard").metadata.get_all("Provides-Extra", []))
    assert {"pii", "jev", "langchain", "langgraph", "microsoft", "all"} <= extras
