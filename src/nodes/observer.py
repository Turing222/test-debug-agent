"""Observer nodes. 负责轻量日志探针和失败时的 sidecar MCP snapshot。"""

import os
import time
from typing import Any

from src.mcp_client import SidecarMCPClient
from src.state import PipelineState


def pre_observe(state: PipelineState) -> dict[str, dict[str, Any]]:
    """Capture cheap local context before pytest runs."""
    print("--> [pre_observe] recording local context")
    pre_snapshot = {
        "cwd": os.getcwd(),
        "pytest_target": state.get("pytest_target"),
        "started_at_monotonic": time.monotonic(),
    }
    return {"pre_snapshot": pre_snapshot}


def post_observe(state: PipelineState) -> dict[str, Any]:
    """Probe logs on pass, and collect full snapshot on failure."""
    print("--> [post_observe] evaluating sidecar snapshot need")
    test_result = state.get("test_result", {})
    exit_code = int(test_result.get("exit_code", 0))
    timed_out = bool(test_result.get("timed_out", False))
    post_snapshot: dict[str, Any] = {
        "finished_at_monotonic": time.monotonic(),
        "pytest_exit_code": exit_code,
        "pytest_timed_out": timed_out,
    }

    client = SidecarMCPClient()

    if exit_code == 0 and not timed_out:
        return _observe_passing_test(state, post_snapshot, client)

    verdict = "blocked" if timed_out else "fail"
    snapshot_result = _call_snapshot(state, client, verdict=verdict)
    post_snapshot["sidecar_snapshot"] = snapshot_result.get("status", "unknown")
    return {
        "post_snapshot": post_snapshot,
        "mcp_snapshot_summary": snapshot_result,
        "mcp_snapshot_file": snapshot_result.get("file"),
        "mcp_error": snapshot_result.get("mcp_error"),
        "observability_status": "snapshot_collected",
        "observability_evidence": "",
    }


def _observe_passing_test(
    state: PipelineState,
    post_snapshot: dict[str, Any],
    client: SidecarMCPClient,
) -> dict[str, Any]:
    logs_result = client.call_logs(
        container=state.get("container", "task_worker"),
        log_level="ERROR",
        tail=200,
    )
    if logs_result.get("mcp_error"):
        post_snapshot["sidecar_logs"] = "error"
        return {
            "post_snapshot": post_snapshot,
            "mcp_snapshot_summary": None,
            "mcp_snapshot_file": None,
            "mcp_error": logs_result["mcp_error"],
            "observability_status": "probe_failed",
            "observability_evidence": "",
        }

    evidence = str(logs_result.get("text", "")).strip()
    if _has_log_evidence(evidence):
        snapshot_result = _call_snapshot(state, client, verdict="flaky")
        post_snapshot["sidecar_logs"] = "error_detected"
        post_snapshot["sidecar_snapshot"] = snapshot_result.get("status", "unknown")
        return {
            "post_snapshot": post_snapshot,
            "mcp_snapshot_summary": snapshot_result,
            "mcp_snapshot_file": snapshot_result.get("file"),
            "mcp_error": snapshot_result.get("mcp_error"),
            "observability_status": "error_detected",
            "observability_evidence": evidence,
        }

    post_snapshot["sidecar_logs"] = "clean"
    post_snapshot["sidecar_snapshot"] = "skipped"
    return {
        "post_snapshot": post_snapshot,
        "mcp_snapshot_summary": None,
        "mcp_snapshot_file": None,
        "mcp_error": None,
        "observability_status": "clean",
        "observability_evidence": evidence,
    }


def _call_snapshot(
    state: PipelineState,
    client: SidecarMCPClient,
    *,
    verdict: str,
) -> dict[str, Any]:
    return client.call_snapshot(
        scenario=state.get("test_case_name", state.get("pytest_target", "unnamed")),
        verdict=verdict,
        container=state.get("container", "task_worker"),
        log_level=state.get("log_level", "WARNING"),
        db_query=state.get("db_query", ""),
        redis_command=state.get("redis_command", ""),
        redis_args=state.get("redis_args", ""),
        redis_db=int(state.get("redis_db", 1)),
    )


def _has_log_evidence(text: str) -> bool:
    return bool(text) and not text.startswith("(empty")
