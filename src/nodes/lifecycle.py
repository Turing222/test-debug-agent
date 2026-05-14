"""Lifecycle nodes. 负责加载 pytest 目标、执行测试和输出流程收尾摘要。"""

import subprocess
import time

from src.state import PipelineState

DEFAULT_PYTEST_TIMEOUT_SECONDS = 120


def load_case(state: PipelineState) -> dict[str, str]:
    """Load the pytest target from CLI state."""
    pytest_target = state["pytest_target"]
    case_name = pytest_target.rsplit("/", maxsplit=1)[-1]
    print(f"--> [load_case] preparing pytest target: {pytest_target}")
    return {"test_case_name": case_name}


def run_test(state: PipelineState) -> dict[str, dict[str, object]]:
    """Run pytest for the requested target."""
    pytest_target = state["pytest_target"]
    command = ["uv", "run", "pytest", pytest_target, "-xvs"]
    started_at = time.monotonic()
    print(f"--> [run_test] running: {' '.join(command)}")
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=DEFAULT_PYTEST_TIMEOUT_SECONDS,
        )
        duration_seconds = time.monotonic() - started_at
        test_result = {
            "command": command,
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "duration_seconds": round(duration_seconds, 3),
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        duration_seconds = time.monotonic() - started_at
        test_result = {
            "command": command,
            "exit_code": 124,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or f"pytest exceeded {DEFAULT_PYTEST_TIMEOUT_SECONDS}s",
            "duration_seconds": round(duration_seconds, 3),
            "timed_out": True,
        }
    return {"test_result": test_result}


def finish(state: PipelineState) -> dict[str, object]:
    """Print the final summary."""
    test_result = state.get("test_result", {})
    exit_code = test_result.get("exit_code", "unknown")
    report_path = state.get("report_path")
    print(f"--> [finish] done; pytest exit_code={exit_code}")
    if report_path:
        print(f"--> [finish] report: {report_path}")
    return {}
