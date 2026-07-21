#!/usr/bin/env bash
# Launches the MCP Inspector against the Garmin MCP server for interactive testing.
# Opens a local web UI where you can call each tool and inspect its output.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
export PATH="$PWD/.venv/bin:$PATH"
exec .venv/bin/mcp dev server.py
