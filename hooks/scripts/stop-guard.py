#!/usr/bin/env python3
"""agent-morph Stop hook：阻止工作流过早停止。"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

MAX_BLOCKS = 2
STATE_FILE = Path(os.environ.get("CLAUDE_PROJECT_DIR", ".")) / ".agent-morph-state.json"


def read_stdin_json() -> dict:
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return {}


def load_state() -> dict:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    _event = read_stdin_json()
    state = load_state()

    if not state.get("active"):
        return 0

    required = [
        "confirm_design_written",
        "target_package_generated",
        "structure_validation_run",
        "validation_report_written",
    ]

    missing = [key for key in required if not state.get(key)]
    if not missing:
        return 0

    blocks = int(state.get("stop_blocks", 0))
    if blocks >= MAX_BLOCKS:
        return 0

    state["stop_blocks"] = blocks + 1
    save_state(state)

    print(
        "agent-morph 工作流尚未完成，禁止提前停止。缺失阶段：" + ", ".join(missing),
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
