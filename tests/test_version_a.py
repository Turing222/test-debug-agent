"""Version A tests. 验证 pytest 执行、sidecar snapshot 调用和报告生成。"""

import subprocess
from types import SimpleNamespace
from typing import cast

from src.mcp_client import (
    SIDECAR_MCP_DIR_ENV,
    SidecarMCPClient,
    default_sidecar_mcp_dir,
)
from src.nodes import lifecycle, observer
from src.nodes.analyzer import evaluate_or_analyze, generate_report
from src.nodes.gatekeeper import rule_gate
from src.state import PipelineState


def test_mcp_client_parses_snapshot_json() -> None:
    payload = SidecarMCPClient.parse_snapshot_text(
        '{"status":"saved","file":"/tmp/snapshot.json"}'
    )

    assert payload == {"status": "saved", "file": "/tmp/snapshot.json"}


def test_mcp_client_non_json_returns_error() -> None:
    payload = SidecarMCPClient.parse_snapshot_text("not json")

    assert payload["status"] == "error"
    assert payload["mcp_error"]["error_code"] == "MCP_SNAPSHOT_NON_JSON"


def test_mcp_client_subprocess_error_returns_error(monkeypatch) -> None:
    async def fake_call_snapshot(self: SidecarMCPClient, **_kwargs: object) -> object:
        raise RuntimeError("boom")

    monkeypatch.setattr(SidecarMCPClient, "_call_snapshot", fake_call_snapshot)

    payload = SidecarMCPClient().call_snapshot(
        scenario="unit",
        verdict="fail",
        container="api",
        log_level="ERROR",
    )

    assert payload["status"] == "error"
    assert payload["mcp_error"]["error_code"] == "MCP_SNAPSHOT_FAILED"


def test_mcp_client_logs_error_returns_error(monkeypatch) -> None:
    async def fake_call_tool_text(
        self: SidecarMCPClient,
        *_args: object,
        **_kwargs: object,
    ) -> str:
        raise RuntimeError("boom")

    monkeypatch.setattr(SidecarMCPClient, "_call_tool_text", fake_call_tool_text)

    payload = SidecarMCPClient().call_logs(container="api")

    assert payload["status"] == "error"
    assert payload["mcp_error"]["error_code"] == "MCP_QUERY_LOGS_FAILED"


def test_mcp_client_uses_env_sidecar_dir(monkeypatch) -> None:
    monkeypatch.setenv(SIDECAR_MCP_DIR_ENV, "/custom/sidecar")

    assert default_sidecar_mcp_dir() == "/custom/sidecar"
    assert SidecarMCPClient().sidecar_dir == "/custom/sidecar"


def test_mcp_client_default_sidecar_dir_is_repo_relative(monkeypatch) -> None:
    monkeypatch.delenv(SIDECAR_MCP_DIR_ENV, raising=False)

    assert default_sidecar_mcp_dir().endswith("dewflow-backend/tools/sidecar-mcp")


def test_mcp_client_accepts_explicit_sidecar_dir(monkeypatch) -> None:
    monkeypatch.setenv(SIDECAR_MCP_DIR_ENV, "/custom/sidecar")

    assert SidecarMCPClient(sidecar_dir="/explicit/sidecar").sidecar_dir == (
        "/explicit/sidecar"
    )


def test_run_test_success_uses_uv_pytest(monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake_run(command: list[str], **_kwargs: object) -> SimpleNamespace:
        calls.append(command)
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = lifecycle.run_test({"pytest_target": "tests/unit/test_demo.py"})

    assert calls == [["uv", "run", "pytest", "tests/unit/test_demo.py", "-xvs"]]
    assert result["test_result"]["exit_code"] == 0
    assert result["test_result"]["timed_out"] is False


def test_run_test_timeout_sets_blocked_result(monkeypatch) -> None:
    def fake_run(*_args: object, **_kwargs: object) -> object:
        raise subprocess.TimeoutExpired(cmd=["uv"], timeout=120, output="out")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = lifecycle.run_test({"pytest_target": "tests/unit/test_demo.py"})

    assert result["test_result"]["exit_code"] == 124
    assert result["test_result"]["timed_out"] is True


def test_post_observe_clean_pass_skips_snapshot(monkeypatch) -> None:
    class FakeClient:
        def call_logs(self, **_kwargs: object) -> dict[str, object]:
            return {"status": "ok", "text": "(empty - no logs)"}

        def call_snapshot(self, **_kwargs: object) -> dict[str, object]:
            raise AssertionError("snapshot should not be called")

    monkeypatch.setattr(observer, "SidecarMCPClient", FakeClient)

    result = observer.post_observe({"test_result": {"exit_code": 0}})

    assert result["mcp_snapshot_summary"] is None
    assert result["post_snapshot"]["sidecar_snapshot"] == "skipped"
    assert result["observability_status"] == "clean"


def test_post_observe_pass_with_error_logs_collects_flaky_snapshot(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    class FakeClient:
        def call_logs(self, **_kwargs: object) -> dict[str, object]:
            return {"status": "ok", "text": "ERROR worker failed"}

        def call_snapshot(self, **kwargs: object) -> dict[str, object]:
            calls.append(kwargs)
            return {"status": "saved", "file": "/tmp/flaky.json"}

    monkeypatch.setattr(observer, "SidecarMCPClient", FakeClient)

    result = observer.post_observe({"test_result": {"exit_code": 0}})

    assert calls[0]["verdict"] == "flaky"
    assert result["observability_status"] == "error_detected"
    assert result["observability_evidence"] == "ERROR worker failed"
    assert result["mcp_snapshot_file"] == "/tmp/flaky.json"


def test_post_observe_pass_log_probe_error_sets_mcp_error(monkeypatch) -> None:
    class FakeClient:
        def call_logs(self, **_kwargs: object) -> dict[str, object]:
            return {
                "status": "error",
                "mcp_error": {"error_code": "MCP_QUERY_LOGS_FAILED"},
            }

    monkeypatch.setattr(observer, "SidecarMCPClient", FakeClient)

    result = observer.post_observe({"test_result": {"exit_code": 0}})

    assert result["observability_status"] == "probe_failed"
    assert result["mcp_error"]["error_code"] == "MCP_QUERY_LOGS_FAILED"


def test_post_observe_calls_snapshot_on_failure(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    class FakeClient:
        def call_logs(self, **_kwargs: object) -> dict[str, object]:
            raise AssertionError("logs should not be called on failure")

        def call_snapshot(self, **kwargs: object) -> dict[str, object]:
            calls.append(kwargs)
            return {"status": "saved", "file": "/tmp/snapshot.json"}

    monkeypatch.setattr(observer, "SidecarMCPClient", FakeClient)
    state = cast(PipelineState, {
        "test_case_name": "case",
        "test_result": {"exit_code": 1},
        "container": "api",
        "log_level": "ERROR",
    })

    result = observer.post_observe(state)

    assert calls[0]["verdict"] == "fail"
    assert calls[0]["container"] == "api"
    assert result["mcp_snapshot_file"] == "/tmp/snapshot.json"
    assert result["observability_status"] == "snapshot_collected"


def test_post_observe_timeout_uses_blocked_verdict(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    class FakeClient:
        def call_logs(self, **_kwargs: object) -> dict[str, object]:
            raise AssertionError("logs should not be called on timeout")

        def call_snapshot(self, **kwargs: object) -> dict[str, object]:
            calls.append(kwargs)
            return {"status": "timeout"}

    monkeypatch.setattr(observer, "SidecarMCPClient", FakeClient)

    observer.post_observe({"test_result": {"exit_code": 124, "timed_out": True}})

    assert calls[0]["verdict"] == "blocked"


def test_gate_fails_when_observability_detects_error() -> None:
    result = rule_gate({
        "test_result": {"exit_code": 0},
        "observability_status": "error_detected",
    })

    assert result == {"gate_decision": "FAIL"}


def test_generate_report_contains_pytest_and_snapshot(tmp_path) -> None:
    state = cast(PipelineState, {
        "pytest_target": "tests/unit/test_demo.py::test_demo",
        "test_case_name": "test_demo",
        "report_dir": str(tmp_path),
        "test_result": {
            "command": ["uv", "run", "pytest", "target", "-xvs"],
            "exit_code": 1,
            "stderr": "AssertionError",
            "stdout": "stdout",
            "duration_seconds": 1.25,
            "timed_out": False,
        },
        "state_diff": "diff",
        "mcp_snapshot_summary": {"status": "saved", "file": "/tmp/snapshot.json"},
        "mcp_snapshot_file": "/tmp/snapshot.json",
        "mcp_error": None,
    })
    state.update(evaluate_or_analyze(state))

    result = generate_report(state)

    report_path = tmp_path / result["report_path"].rsplit("/", maxsplit=1)[-1]
    report = report_path.read_text(encoding="utf-8")
    assert "AssertionError" in report
    assert "/tmp/snapshot.json" in report
    assert "Exit code: `1`" in report
