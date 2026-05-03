#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""将 .claude/skills/wkrpt.md 同步为 .cursor/skills/wkrpt/SKILL.md（UTF-8）。

编辑 wkrpt 主稿后在本脚本所在仓库根执行：
    python scripts/sync_wkrpt_skills.py
再 git add .claude/skills/wkrpt.md .cursor/skills/wkrpt/SKILL.md 一并提交。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / ".claude" / "skills" / "wkrpt.md"
DST = ROOT / ".cursor" / "skills" / "wkrpt" / "SKILL.md"


def main() -> int:
    if not SRC.is_file():
        print(f"[ERR] 缺少主源: {SRC}", file=sys.stderr)
        return 1
    text = SRC.read_text(encoding="utf-8")
    DST.parent.mkdir(parents=True, exist_ok=True)
    DST.write_text(text, encoding="utf-8")
    print(f"[OK] {SRC} -> {DST} ({len(text)} chars)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
