#!/usr/bin/env bash
# A quick validation path: the model's internal identities, the economic scenarios' published
# numbers, and the quit order the tables require, without the upstream downloads or the site
# build.
set -euo pipefail
cd "$(dirname "$0")"
uv sync
uv run pytest -q code/tests/test_model.py code/tests/test_tables.py code/tests/test_quit_order.py
