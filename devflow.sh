#!/bin/bash
# DevFlow CLI - Shell 入口
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/devflow-cli.py" "$@"
