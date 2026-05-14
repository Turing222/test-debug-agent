"""Sidecar MCP client. 通过 stdio MCP 协议调用 Dewflow 旁路观测工具。"""

import asyncio
import json
import os
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SIDECAR_MCP_DIR_ENV = "SIDECAR_MCP_DIR"


def default_sidecar_mcp_dir() -> str:
    """Resolve the sidecar MCP directory from env or repo-relative layout."""
    env_value = os.environ.get(SIDECAR_MCP_DIR_ENV)
    if env_value:
        return env_value
    repo_root = Path(__file__).resolve().parents[2]
    return str(repo_root / "tools" / "sidecar-mcp")


class SidecarMCPClient:
    """Small wrapper around the sidecar MCP snapshot tool."""

    def __init__(self, sidecar_dir: str | None = None) -> None:
        self.sidecar_dir = sidecar_dir or default_sidecar_mcp_dir()

    def call_snapshot(
        self,
        *,
        scenario: str,
        verdict: str,
        container: str,
        log_level: str,
        db_query: str = "",
        redis_command: str = "",
        redis_args: str = "",
        redis_db: int = 1,
    ) -> dict[str, Any]:
        """Call the sidecar snapshot tool and return a structured result."""
        try:
            return asyncio.run(
                self._call_snapshot(
                    scenario=scenario,
                    verdict=verdict,
                    container=container,
                    log_level=log_level,
                    db_query=db_query,
                    redis_command=redis_command,
                    redis_args=redis_args,
                    redis_db=redis_db,
                )
            )
        except Exception as exc:
            return {
                "status": "error",
                "mcp_error": {
                    "error_code": "MCP_SNAPSHOT_FAILED",
                    "message": str(exc),
                    "type": type(exc).__name__,
                },
            }

    def call_logs(
        self,
        *,
        container: str,
        log_level: str = "ERROR",
        tail: int = 200,
        filter_pattern: str = "",
    ) -> dict[str, Any]:
        """Call the sidecar query_logs tool and return text evidence."""
        try:
            text = asyncio.run(
                self._call_tool_text(
                    "query_logs",
                    {
                        "container": container,
                        "log_level": log_level,
                        "tail": tail,
                        "filter_pattern": filter_pattern,
                    },
                )
            )
            return {"status": "ok", "text": text}
        except Exception as exc:
            return {
                "status": "error",
                "mcp_error": {
                    "error_code": "MCP_QUERY_LOGS_FAILED",
                    "message": str(exc),
                    "type": type(exc).__name__,
                },
            }

    async def _call_snapshot(self, **kwargs: Any) -> dict[str, Any]:
        text = await self._call_tool_text("snapshot", kwargs)
        return self.parse_snapshot_text(text)

    async def _call_tool_text(self, tool_name: str, arguments: dict[str, Any]) -> str:
        server = StdioServerParameters(
            command="uv",
            args=[
                "--directory",
                self.sidecar_dir,
                "run",
                "python",
                "-m",
                "src.server",
            ],
        )
        async with stdio_client(server) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                return self.extract_text(result)

    @staticmethod
    def extract_text(result: Any) -> str:
        """Extract text payload from a MCP CallToolResult-like object."""
        content = getattr(result, "content", None) or []
        text_parts = [
            item.text
            for item in content
            if getattr(item, "type", "") == "text" and hasattr(item, "text")
        ]
        return "\n".join(text_parts)

    @staticmethod
    def parse_snapshot_text(text: str) -> dict[str, Any]:
        """Parse snapshot JSON text into a stable result shape."""
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return {
                "status": "error",
                "raw_text": text,
                "mcp_error": {
                    "error_code": "MCP_SNAPSHOT_NON_JSON",
                    "message": "sidecar snapshot returned non-JSON text",
                },
            }
        if not isinstance(payload, dict):
            return {
                "status": "error",
                "raw_text": text,
                "mcp_error": {
                    "error_code": "MCP_SNAPSHOT_INVALID_JSON",
                    "message": "sidecar snapshot returned non-object JSON",
                },
            }
        return payload
