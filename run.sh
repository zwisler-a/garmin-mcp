#!/usr/bin/env bash
# Runs the Garmin MCP server directly over stdio (used by Claude Code / .mcp.json).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
exec .venv/bin/python server.py
