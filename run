#!/bin/bash
cd "$(dirname "$0")"
find ./ -name "__pycache__" -exec rm -rf {} \; 2>/dev/null
PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python3 main.py $1
