"""
步骤 1+2 一站式：直接通过 HTTP 调 user-sql MCP，端到端跑完所有 SQL 并落盘 JSON。

完全绕开 LLM 工具循环，10 个 SQL 端到端通常 < 5 分钟（瓶颈是 SQL 执行时间）。

用法:
    python run_all.py                    # 跑 sql/ 下所有 .sql
    python run_all.py 01_s_class_all     # 只跑指定 SQL（不带扩展名）
    python run_all.py --list             # 仅列出待执行的 SQL

产物:
    每个 sql/NN_xxx.sql → data/xxx.json，字段 = metadata + header + rowCount + rows

环境:
    依赖: requests
    MCP 配置: ~/.cursor/mcp.json 中 mcpServers.sql.{url, headers}
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import io
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# 项目根：本文件位于 code/python/01_execute_sql/
PROJECT_ROOT = Path(__file__).resolve().parents[3]
SQL_DIR = PROJECT_ROOT / "code" / "sql"
DATA_DIR = PROJECT_ROOT / "data"
MCP_CONFIG = Path.home() / ".cursor" / "mcp.json"

DATA_SOURCE_ID = 1   # hive
ENGINE_TYPE = "SMART"
POLL_INTERVAL_SEC = 5
POLL_TIMEOUT_SEC = 600


# ---------- MCP HTTP 客户端 ----------

def _load_mcp():
    cfg = json.loads(MCP_CONFIG.read_text(encoding="utf-8"))
    sql_cfg = cfg["mcpServers"]["sql"]
    return sql_cfg["url"], {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        **sql_cfg.get("headers", {}),
    }


_URL, _HEADERS = _load_mcp()
_session = requests.Session()
_rpc_id = 0


def _rpc(method: str, params: dict, timeout: int = 60) -> dict:
    global _rpc_id
    _rpc_id += 1
    payload = {"jsonrpc": "2.0", "id": _rpc_id, "method": method, "params": params}
    r = _session.post(_URL, headers=_HEADERS, json=payload, timeout=timeout)
    r.raise_for_status()
    body = r.json()
    if "error" in body:
        raise RuntimeError(f"MCP error on {method}: {body['error']}")
    return body["result"]


def _call_tool(name: str, args: dict, timeout: int = 60) -> Any:
    """调用 tools/call，自动解包 content[0].text 的 JSON。"""
    res = _rpc("tools/call", {"name": name, "arguments": args}, timeout=timeout)
    if res.get("isError"):
        raise RuntimeError(f"Tool {name} returned error: {res}")
    content = res.get("content", [])
    if not content:
        return None
    text = content[0].get("text", "")
    # 工具返回的 text 既可能是纯 JSON，也可能是已经结构化的；尝试解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


# ---------- SQL → JSON 流水线 ----------

def output_name(sql_path: Path) -> str:
    """01_s_class_all.sql → s_class_all"""
    return re.sub(r"^\d+_", "", sql_path.stem)


def extract_data_source(sql_text: str) -> str:
    """从 SQL 提取第一个 FROM 子句的表名作为 metadata.data_source。"""
    m = re.search(r"\bFROM\s+([\w\.]+)", sql_text, re.IGNORECASE)
    return m.group(1) if m else ""


def submit(sql_text: str) -> int:
    res = _call_tool("submit_query", {
        "dataSourceId": DATA_SOURCE_ID,
        "engineType": ENGINE_TYPE,
        "sql": sql_text,
    })
    qid = res.get("queryId") if isinstance(res, dict) else None
    if not qid:
        raise RuntimeError(f"submit_query 未返回 queryId: {res}")
    return int(qid)


def get_status(qid: int) -> str:
    res = _call_tool("get_query_status", {"queryId": qid})
    if isinstance(res, dict):
        return res.get("status", "UNKNOWN")
    return str(res)


def get_result(qid: int) -> dict:
    res = _call_tool("get_query_result", {"queryId": qid}, timeout=120)
    if not isinstance(res, dict):
        raise RuntimeError(f"get_query_result 返回非对象: {type(res)}")
    return res


def run_one(sql_path: Path) -> dict:
    """对单个 SQL 跑 submit→poll→fetch→save。返回汇总信息。"""
    name = output_name(sql_path)
    sql_text = sql_path.read_text(encoding="utf-8")
    out_path = DATA_DIR / f"{name}.json"

    info = {"name": name, "sql": sql_path.name, "out": str(out_path)}

    t0 = time.time()
    qid = submit(sql_text)
    info["queryId"] = qid
    print(f"[SUBMIT] {name:40s} queryId={qid}")

    deadline = time.time() + POLL_TIMEOUT_SEC
    last_status = None
    while True:
        status = get_status(qid)
        if status != last_status:
            print(f"[STATUS] {name:40s} qid={qid} {status}")
            last_status = status
        if status == "FINISHED":
            break
        if status in ("FAILED", "CANCELLED", "ERROR"):
            raise RuntimeError(f"{name} query {qid} {status}")
        if time.time() > deadline:
            raise TimeoutError(f"{name} query {qid} 超过 {POLL_TIMEOUT_SEC}s 仍未 FINISHED")
        time.sleep(POLL_INTERVAL_SEC)

    result = get_result(qid)
    if result.get("truncated"):
        print(f"[WARN]   {name} 结果被截断！请加 LIMIT 或聚合后重跑")

    now = datetime.now()
    out = {
        "metadata": {
            "data_fetch_date": now.strftime("%Y-%m-%d"),
            "query_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "query_id": str(qid),
            "data_source": extract_data_source(sql_text),
        },
        "header": result["header"],
        "rowCount": result["rowCount"],
        "rows": result["rows"],
    }
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    elapsed = time.time() - t0
    info.update({"rows": result["rowCount"], "elapsed_sec": round(elapsed, 1)})
    print(f"[SAVED]  {name:40s} rows={result['rowCount']:6d} elapsed={elapsed:.1f}s")
    return info


def list_sql_files(filter_stem: str | None = None) -> list[Path]:
    files = sorted(SQL_DIR.glob("*.sql"))
    if filter_stem:
        files = [f for f in files if f.stem == filter_stem]
        if not files:
            raise SystemExit(f"未找到 SQL: {filter_stem}.sql")
    return files


# ---------- main ----------

def main():
    parser = argparse.ArgumentParser(description="端到端跑所有 SQL → JSON")
    parser.add_argument("filter", nargs="?", default=None,
                        help="只跑指定 SQL（不带扩展名），不填则跑全部")
    parser.add_argument("--list", action="store_true", help="只列出待执行 SQL")
    parser.add_argument("--workers", type=int, default=4, help="并发线程数（默认 4）")
    args = parser.parse_args()

    files = list_sql_files(args.filter)
    print(f"待执行 SQL ({len(files)} 个):")
    for f in files:
        print(f"  - {f.name}  →  data/{output_name(f)}.json")
    if args.list:
        return 0

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n开始执行（并发 {args.workers}）...\n")
    t_start = time.time()
    successes, failures = [], []

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        future_to_sql = {pool.submit(run_one, f): f for f in files}
        for fut in as_completed(future_to_sql):
            sql_file = future_to_sql[fut]
            try:
                successes.append(fut.result())
            except Exception as e:
                msg = f"{sql_file.name}: {e!r}"
                print(f"[FAIL]   {msg}")
                failures.append(msg)

    total = time.time() - t_start
    print("\n" + "=" * 64)
    print(f"完成：成功 {len(successes)}/{len(files)}，失败 {len(failures)}，总耗时 {total:.1f}s")
    print("=" * 64)
    for s in sorted(successes, key=lambda x: x["name"]):
        print(f"  ✓ {s['name']:40s} rows={s['rows']:6d} elapsed={s['elapsed_sec']}s qid={s['queryId']}")
    for f in failures:
        print(f"  ✗ {f}")

    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
