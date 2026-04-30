# -*- coding: utf-8 -*-
"""飞书应用凭证加载：供各 Python 脚本共用。"""
from __future__ import annotations

import json
import os
from pathlib import Path

FEISHU_CREDENTIALS_HELP = """未找到飞书应用凭证。请在本项目根目录放置 feishu_app.json：
  1. 复制 feishu_app.example.json 为 feishu_app.json
  2. 填写其中的 app_id、app_secret（与飞书开放平台应用一致）

交接项目时：将 feishu_app.json 一并交给接收方（该文件已被 .gitignore 忽略，不会进入 Git）。
接收方把文件放在项目根目录后即可运行相关脚本，无需配置系统环境变量。

可选：若不便使用文件，可设置环境变量 FEISHU_APP_ID、FEISHU_APP_SECRET。"""


def load_feishu_app_credentials(project_root: Path) -> tuple[str, str]:
    """优先读取项目根 feishu_app.json，其次环境变量。返回 (app_id, app_secret)，缺失则为空字符串。"""
    cfg_path = project_root / "feishu_app.json"
    if cfg_path.is_file():
        try:
            data = json.loads(cfg_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise RuntimeError(f"无法解析 {cfg_path}: {e}") from e
        aid = str(data.get("app_id", "")).strip()
        sec = str(data.get("app_secret", "")).strip()
        if aid and sec:
            return aid, sec
    aid = os.environ.get("FEISHU_APP_ID", "").strip()
    sec = os.environ.get("FEISHU_APP_SECRET", "").strip()
    if aid and sec:
        return aid, sec
    return "", ""
