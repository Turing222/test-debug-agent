"""Analyzer and report nodes. 生成版本 A 的确定性诊断摘要和 Markdown 报告。"""

import re
import time
from pathlib import Path

from src.state import PipelineState

TAIL_CHARS = 4000


def evaluate_or_analyze(state: PipelineState) -> dict[str, str]:
    """Create a deterministic version A analysis."""
    print("--> [analyzer] building deterministic analysis")
    test_result = state.get("test_result", {})
    mcp_error = state.get("mcp_error")
    timed_out = bool(test_result.get("timed_out", False))
    lines = [
        "Version A does not enable LLM deep diagnosis.",
        f"Pytest exit code: {test_result.get('exit_code', 'unknown')}.",
    ]
    if timed_out:
        lines.append("Pytest timed out; sidecar verdict is blocked.")
    if state.get("mcp_snapshot_file"):
        lines.append(f"Sidecar snapshot saved: {state['mcp_snapshot_file']}.")
    if state.get("observability_status") == "error_detected":
        lines.append("Pytest passed, but sidecar ERROR log probe found evidence.")
    if mcp_error:
        lines.append(
            "Sidecar observation failed; this is an observation failure, "
            "not proof of an application failure."
        )
        lines.append(f"MCP error: {mcp_error}.")
    analysis_result = "\n".join(lines)
    return {"analysis_result": analysis_result}


def generate_report(state: PipelineState) -> dict[str, str]:
    """Generate a Markdown report and write it to disk."""
    print("--> [generate_report] writing Markdown report")
    report_dir = Path(state.get("report_dir", ".traces/test-debug-agent"))
    report_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    case_slug = _slugify(state.get("test_case_name", "pytest-target"))
    report_path = report_dir / f"{timestamp}-{case_slug}.md"

    test_result = state.get("test_result", {})
    command = " ".join(str(part) for part in test_result.get("command", []))
    stderr_tail = _tail(str(test_result.get("stderr", "")))
    stdout_tail = _tail(str(test_result.get("stdout", "")))
    snapshot_summary = state.get("mcp_snapshot_summary")

    report = f"""# test-debug-agent Report

## Pytest
- Target: `{state.get("pytest_target", "")}`
- Command: `{command}`
- Exit code: `{test_result.get("exit_code", "unknown")}`
- Duration seconds: `{test_result.get("duration_seconds", "unknown")}`
- Timed out: `{test_result.get("timed_out", False)}`

## Sidecar MCP
- Snapshot file: `{state.get("mcp_snapshot_file") or ""}`
- MCP error: `{state.get("mcp_error") or ""}`
- Observability status: `{state.get("observability_status", "")}`

```text
{snapshot_summary or ""}
```

## Observability evidence
```text
{_tail(state.get("observability_evidence", "")) or "(empty)"}
```

## stderr tail
```text
{stderr_tail or "(empty)"}
```

## stdout tail
```text
{stdout_tail or "(empty)"}
```

## Snapshot diff
```text
{state.get("state_diff", "")}
```

## Analysis
```text
{state.get("analysis_result", "")}
```
"""
    report_path.write_text(report, encoding="utf-8")
    return {"final_report": report, "report_path": str(report_path)}


def _tail(text: str) -> str:
    return text[-TAIL_CHARS:]


def _slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-")
    return slug[:120] or "pytest-target"
