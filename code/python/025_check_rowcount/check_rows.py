#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
步骤2.5: 自动检查JSON行数一致性
检查 data/ 目录下所有 JSON 文件的 rowCount 与实际 rows 长度是否一致
"""

import sys, io, json
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 项目根：本文件位于 code/python/025_check_rowcount/
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data"

# 自动发现 data/ 目录下所有标准格式的 JSON 文件
def discover_json_files():
    files = []
    for fp in sorted(DATA_DIR.glob("*.json")):
        if fp.name.startswith("_"):
            continue  # 跳过临时文件
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if "metadata" in data and "rows" in data and "rowCount" in data:
                files.append((fp.name, data))
        except:
            pass
    return files


def main():
    print("=" * 60)
    print("步骤2.5: 检查JSON行数一致性")
    print("=" * 60)
    
    files = discover_json_files()
    if not files:
        print("[ERR] 未找到有效的JSON数据文件")
        return False
    
    all_ok = True
    for fname, data in files:
        expected = data.get("rowCount", -1)
        actual = len(data.get("rows", []))
        qid = data.get("metadata", {}).get("query_id", "?")
        
        if expected == actual:
            print(f"[OK] {fname}: Query {qid} | Expected {expected} | Actual {actual}")
        else:
            print(f"[ERR] {fname}: Query {qid} | Expected {expected} | Actual {actual} (不匹配!)")
            all_ok = False
    
    print()
    if all_ok:
        print(f"[OK] 全部 {len(files)} 个文件验证通过!")
        return True
    else:
        print(f"[ERR] 存在 {sum(1 for _,d in files if d['rowCount']!=len(d['rows']))} 个文件需要修复!")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
