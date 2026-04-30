#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""临时审计：只跑参数计算，对每个参数打印 含义/公式/数据源/值，不发飞书。"""
import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[3]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))
from feishu_creds import FEISHU_CREDENTIALS_HELP, load_feishu_app_credentials

from generate_feishu_report import FeishuReportGenerator

_aid, _sec = load_feishu_app_credentials(_root)
if not _aid or not _sec:
    print(FEISHU_CREDENTIALS_HELP)
    sys.exit(1)

g = FeishuReportGenerator(_aid, _sec, str(_root / "data"))
g.calculate_all_params()

print("\n" + "=" * 78)
print("最终参数表")
print("=" * 78)
for k in [
    'mm', 'mm1', 'mm2', 'DD', 'DD1',
    'rate_prin_od', 'rate_prin_od_dif',
    'rate_cnt_od', 'rate_cnt_od_dif',
    'wk_colrate7d', 'wk_colrate7d_dif',
    'wk_colrate15d', 'wk_colrate15d_dif',
    'mth_colrate7d', 'mth_colrate7d_dif',
    'mth_colrate30d', 'mth_colrate30d_dif',
]:
    v = g.params.get(k, '<MISSING>')
    print(f"  {{{k}}} = {v}")
