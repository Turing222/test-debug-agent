"""CLI entrypoint. 从命令行启动 pytest 调试图并打印最终摘要。"""

import argparse
import sys
from typing import Any

from src.graph import build_graph


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(description="Run pytest with sidecar MCP evidence.")
    parser.add_argument("pytest_target")
    parser.add_argument("--report-dir", default=".traces/test-debug-agent")
    parser.add_argument("--container", default="task_worker")
    parser.add_argument("--log-level", default="WARNING")
    parser.add_argument("--db-query", default="")
    parser.add_argument("--redis-command", default="")
    parser.add_argument("--redis-args", default="")
    parser.add_argument("--redis-db", type=int, default=1)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the agent."""
    args = build_parser().parse_args(argv)
    initial_state: dict[str, Any] = {
        "pytest_target": args.pytest_target,
        "report_dir": args.report_dir,
        "container": args.container,
        "log_level": args.log_level,
        "db_query": args.db_query,
        "redis_command": args.redis_command,
        "redis_args": args.redis_args,
        "redis_db": args.redis_db,
    }
    app = build_graph()
    final_state = app.invoke(initial_state)
    test_result = final_state.get("test_result", {})
    exit_code = int(test_result.get("exit_code", 1))
    report_path = final_state.get("report_path")
    gate_decision = final_state.get("gate_decision", "UNKNOWN")
    print(f"test-debug-agent: gate={gate_decision}, pytest_exit_code={exit_code}")
    if report_path:
        print(f"test-debug-agent: report={report_path}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
