"""Wires the official GitHub MCP server (downloaded binary, run via
stdio -- see scripts/setup_github_mcp.sh) into ADK as a toolset.

Only the `issues`, `pull_requests`, and `repos` toolsets are enabled --
least-privilege: the PRAgent only ever needs to read an issue, push a
branch, and open a PR against the single sandbox repo the fine-grained
PAT is scoped to.
"""

from __future__ import annotations

import os
from pathlib import Path

from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from mcp import StdioServerParameters

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
GITHUB_MCP_BINARY = REPO_ROOT / "scripts" / "bin" / "github-mcp-server"


def build_github_toolset() -> MCPToolset:
    token = os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN")
    if not token:
        raise RuntimeError(
            "GITHUB_PERSONAL_ACCESS_TOKEN is not set -- required to start the "
            "GitHub MCP server. See .env.example."
        )
    if not GITHUB_MCP_BINARY.exists():
        raise RuntimeError(
            f"{GITHUB_MCP_BINARY} not found -- run scripts/setup_github_mcp.sh first."
        )

    return MCPToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command=str(GITHUB_MCP_BINARY),
                args=["stdio", "--toolsets=issues,pull_requests,repos", "--read-only=false"],
                env={"GITHUB_PERSONAL_ACCESS_TOKEN": token},
            ),
            timeout=30,
        ),
    )
