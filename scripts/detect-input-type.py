#!/usr/bin/env python3
"""检测 agent-morph 用户输入类型。"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


def detect_input_type(raw: str) -> dict[str, object]:
    value = raw.strip()

    if not value:
        return {"type": "natural_language", "value": value, "confidence": 0.5}

    if re.match(r"^https?://(www\.)?github\.com/[^/\s]+/[^/\s#?]+", value):
        return {"type": "github_repo", "value": value, "confidence": 0.96}

    if re.match(r"^https?://", value):
        lower = value.lower()
        file_extensions = (
            ".pdf", ".docx", ".pptx", ".xlsx", ".csv", ".json", ".yaml", ".yml",
            ".txt", ".md", ".zip", ".tar", ".gz", ".py", ".js", ".ts"
        )
        clean_url = lower.split("?", 1)[0].split("#", 1)[0]
        if clean_url.endswith(file_extensions):
            return {"type": "file_url", "value": value, "confidence": 0.9}
        return {"type": "web_url", "value": value, "confidence": 0.88}

    expanded = os.path.expanduser(value)
    path = Path(expanded)
    if path.exists() and path.is_dir():
        return {"type": "local_path", "value": str(path), "confidence": 0.95}
    if path.exists() and path.is_file():
        return {"type": "local_file", "value": str(path), "confidence": 0.95}

    if value.startswith(("/", "./", "../", "~/")):
        return {"type": "local_path", "value": expanded, "confidence": 0.65}

    return {"type": "natural_language", "value": value, "confidence": 0.82}


def main() -> int:
    raw = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else sys.stdin.read()
    print(json.dumps(detect_input_type(raw), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
