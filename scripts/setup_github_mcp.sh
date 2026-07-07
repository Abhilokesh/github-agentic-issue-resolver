#!/usr/bin/env bash
# Downloads the official GitHub MCP server prebuilt Linux binary into
# scripts/bin/ -- no Docker or Go toolchain needed. Safe to re-run.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN_DIR="$REPO_ROOT/scripts/bin"
VERSION="${GITHUB_MCP_SERVER_VERSION:-v1.5.0}"
ASSET="github-mcp-server_Linux_x86_64.tar.gz"
URL="https://github.com/github/github-mcp-server/releases/download/${VERSION}/${ASSET}"

mkdir -p "$BIN_DIR"
echo "Downloading github-mcp-server ${VERSION} ..."
curl -sSL "$URL" -o "$BIN_DIR/$ASSET"
tar -xzf "$BIN_DIR/$ASSET" -C "$BIN_DIR"
rm "$BIN_DIR/$ASSET"
chmod +x "$BIN_DIR/github-mcp-server"

echo "Installed: $BIN_DIR/github-mcp-server"
"$BIN_DIR/github-mcp-server" --version || true
