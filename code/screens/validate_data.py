"""
数据验证入口（兼容旧路径）。

实际校验逻辑在 `code/python/03_validate_data/validate_data.py`（按 SQL 落盘结果动态注册、
与 `run_all.py` 输出的 JSON 文件名一致）。本文件保留在 `code/screens/` 仅便于与 Skill
文档中的「在 screens 目录执行」习惯一致。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
REAL = ROOT / "code" / "python" / "03_validate_data" / "validate_data.py"


def main() -> int:
    if not REAL.is_file():
        print(f"找不到验证脚本: {REAL}", file=sys.stderr)
        return 2
    return subprocess.call([sys.executable, str(REAL)])


if __name__ == "__main__":
    sys.exit(main())
