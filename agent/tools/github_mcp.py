"""Wires the official GitHub MCP server (downloaded binary, run via
stdio -- see scripts/setup_github_mcp.sh) into ADK as a toolset.

Only the `issues`, `pull_requests`, and `repos` toolsets are enabled.

Two separate tokens are supported, on purpose:
- GITHUB_PERSONAL_ACCESS_TOKEN: fine-grained, scoped to the single sandbox
  repo the benchmark demo mode (agent/cli.py `resolve`) owns and writes to.
- GITHUB_PAT_BROAD: fine-grained but scoped to "All repositories", needed
  by the real-issue dry-run mode (`try-real-issue`) since `fork_repository`
  has to work against repos the user doesn't own yet (the fork doesn't
  exist until created, so a repo-specific token can't cover it). Kept
  separate so the sandbox demo's least-privilege token is never widened.
"""

from __future__ import annotations

import os
from pathlib import Path

from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from mcp import StdioServerParameters

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
GITHUB_MCP_BINARY = REPO_ROOT / "scripts" / "bin" / "github-mcp-server"


def build_github_toolset(token_env_var: str = "GITHUB_PERSONAL_ACCESS_TOKEN") -> MCPToolset:
    token = os.environ.get(token_env_var)
    if not token:
        raise RuntimeError(
            f"{token_env_var} is not set -- required to start the "
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
