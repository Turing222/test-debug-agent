"""Snapshot diff node. 对比测试前后的轻量上下文并输出稳定文本。"""

from typing import Any

from src.state import PipelineState


def diff_snapshot(state: PipelineState) -> dict[str, str]:
    """Compare pre and post snapshots."""
    pre = state.get("pre_snapshot", {})
    post = state.get("post_snapshot", {})

    diff_results: list[str] = []

    for key in post:
        if key not in pre:
            diff_results.append(f"[added] {key}:\n{_format_value(post[key])}")
        elif pre[key] != post[key]:
            diff_results.append(
                f"[changed] {key}:\n  before: {_format_value(pre[key])}"
                f"\n  after: {_format_value(post[key])}"
            )

    for key in pre:
        if key not in post:
            diff_results.append(f"[removed] {key}:\n{_format_value(pre[key])}")

    if not diff_results:
        final_diff = "No changes detected."
    else:
        final_diff = "\n\n".join(diff_results)

    return {"state_diff": final_diff}


def _format_value(value: Any) -> str:
    return str(value)
