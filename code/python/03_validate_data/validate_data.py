"""
数据完整性验证脚本（动态调度版，支持新增 SQL/JSON）

设计目标：
1. **前置完整性检查**：先确认 data/ 下的 JSON 集合等于 code/sql/ 下的 SQL 集合，
   缺一个就 hard fail，强制要求先把 run_all.py 跑完。
2. **注册表调度**：`VALIDATORS` 字典维护 `文件名 → 验证函数`，新增数据时：
   - 有验证规则 → 在 VALIDATORS 注册
   - 没规则 → 自动 [SKIP] 提示，不阻塞流程
3. **不要在这里硬编码业务字段索引**，所有索引按 `header` 真实顺序解析。
"""
import json
import re
import sys
import io
from pathlib import Path
from datetime import datetime
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 项目根：本文件位于 code/python/03_validate_data/ → parents[3]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / 'data'
SQL_DIR = PROJECT_ROOT / 'code' / 'sql'


def _is_null(v):
    return v is None or v == '' or v == 'NULL'


def _to_float(v, default=0.0):
    if _is_null(v):
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _load(filename):
    fp = DATA_DIR / filename
    if not fp.exists():
        return None
    with open(fp, 'r', encoding='utf-8') as f:
        return json.load(f)


def _expected_json_name(sql_path: Path) -> str:
    """01_s_class_all.sql → s_class_all.json（与 run_all.py 的 output_name 同步）"""
    import re
    return re.sub(r'^\d+_', '', sql_path.stem) + '.json'


# ================== 前置：完整性检查 ==================

def precheck_completeness() -> bool:
    """对比 code/sql/*.sql 与 data/*.json，必须一一对应才能继续验证。"""
    print("\n" + "=" * 60)
    print("前置：数据完整性检查（确保所有 SQL 都已落盘）")
    print("=" * 60)

    sql_files = sorted(SQL_DIR.glob('*.sql'))
    expected_jsons = {_expected_json_name(f) for f in sql_files}
    actual_jsons = {f.name for f in DATA_DIR.glob('*.json') if not f.name.startswith('_')}

    missing = expected_jsons - actual_jsons
    extra = actual_jsons - expected_jsons

    print(f"  SQL 文件: {len(sql_files)} 个 ({SQL_DIR})")
    print(f"  JSON 文件: {len(actual_jsons)} 个 ({DATA_DIR})")

    if missing:
        print(f"\n  ✗ 缺失 {len(missing)} 个 JSON（请先跑 run_all.py）：")
        for m in sorted(missing):
            print(f"      - {m}")
        return False

    if extra:
        print(f"\n  ⚠ 额外 {len(extra)} 个 JSON（无对应 SQL，可能是历史遗留）：")
        for e in sorted(extra):
            print(f"      - {e}")
        # 额外文件不阻塞，只警告

    print(f"\n  ✓ 所有 SQL 都已落盘（{len(expected_jsons)} 个 JSON）")
    return True


# ================== 各类数据验证函数 ==================

def validate_s_class(filename, desc=""):
    """S 类案件验证（ALL/NEW/MTD 三个口径共用）"""
    print(f"\n[{desc or filename}]")
    data = _load(filename)
    if data is None:
        print("  ✗ 文件不存在")
        return False

    header = data['header']
    rows = data['rows']
    idx = {name: i for i, name in enumerate(header)}
    print(f"  行数: {len(rows)}")

    months = defaultdict(int)
    for row in rows:
        months[row[idx['p_month']]] += 1
    print("  月份分布: " + ", ".join(f"{m}:{c}" for m, c in sorted(months.items())))

    per_day = defaultdict(int)
    for row in rows:
        per_day[(row[idx['p_month']], row[idx['day']])] += 1
    bad_days = [k for k, v in per_day.items() if v != 3]
    if bad_days:
        print(f"  ✗ 有 {len(bad_days)} 天非 3 条记录: {bad_days[:3]}...")
        return False
    print(f"  ✓ 全部 {len(per_day)} 天均为 3 条 (S1/S2/S3)")

    types = {row[idx['case_type']] for row in rows}
    if types != {'S1', 'S2', 'S3'}:
        print(f"  ✗ 案件类型异常: {types}")
        return False

    is_mtd = ('mtd' in filename.lower())
    invalid = []
    for row in rows:
        assigned = _to_float(row[idx['assigned_principal']])
        repaid = _to_float(row[idx['repaid_principal']])
        if assigned <= 0:
            continue
        rate = repaid / assigned * 100
        if not is_mtd and rate > 100:
            invalid.append((row[idx['p_month']], row[idx['day']],
                            row[idx['case_type']], rate))
    if invalid:
        print(f"  ⚠ 有 {len(invalid)} 条回款率 > 100%（ALL/NEW 口径罕见）")
        for m, d, c, r in invalid[:3]:
            print(f"      {m}-{d} {c}: {r:.2f}%")
    else:
        print("  ✓ 回款率正常" + (" (MTD 允许 > 100%)" if is_mtd else "（≤ 100%）"))
    return True


def validate_m2_class_all(filename, desc="M2·ALL"):
    """M2 单类型：每日每月份唯一一行，case_type 均为 M2。"""
    print(f"\n[{desc}] {filename}")
    data = _load(filename)
    if data is None:
        print("  ✗ 文件不存在")
        return False
    header = data["header"]
    rows = data["rows"]
    idx = {name: i for i, name in enumerate(header)}
    need = ("p_month", "day", "case_type", "assigned_principal", "overdue_added_principal", "repaid_principal")
    if any(k not in idx for k in need):
        print(f"  ✗ 缺少列: {need}")
        return False
    print(f"  行数: {len(rows)}")
    types = {row[idx["case_type"]] for row in rows}
    if types != {"M2"}:
        print(f"  ✗ case_type 应为 M2，实际 {types}")
        return False
    per_day = defaultdict(int)
    for row in rows:
        per_day[(row[idx["p_month"]], row[idx["day"]])] += 1
    bad = [k for k, v in per_day.items() if v != 1]
    if bad:
        print(f"  ✗ 有 {len(bad)} 个 (月,日) 重复或非 1 行: {bad[:5]}...")
        return False
    print(f"  ✓ 每日每月份 1 行，共 {len(per_day)} 个日切片")
    return True


def validate_m6_class_all(filename, desc="M2-M6账龄31-180天·ALL"):
    """无 case_type：汇总序列，每日每月份唯一一行。"""
    print(f"\n[{desc}] {filename}")
    data = _load(filename)
    if data is None:
        print("  ✗ 文件不存在")
        return False
    header = data["header"]
    rows = data["rows"]
    idx = {name: i for i, name in enumerate(header)}
    if "case_type" in idx:
        print("  ⚠ 存在 case_type 列（预期为汇总无案件类型列）")
    need = ("p_month", "day", "assigned_principal", "overdue_added_principal", "repaid_principal")
    if any(k not in idx for k in need):
        print(f"  ✗ 缺少列: {need}")
        return False
    print(f"  行数: {len(rows)}")
    per_day = defaultdict(int)
    for row in rows:
        per_day[(row[idx["p_month"]], row[idx["day"]])] += 1
    bad = [k for k, v in per_day.items() if v != 1]
    if bad:
        print(f"  ✗ 有 {len(bad)} 个 (月,日) 重复或非 1 行: {bad[:5]}...")
        return False
    print(f"  ✓ 每日每月份 1 行，共 {len(per_day)} 个日切片")
    return True


def validate_m1(filename, desc="M1分案回款"):
    print(f"\n[{desc}] {filename}")
    data = _load(filename)
    if data is None:
        print("  ✗ 文件不存在"); return False
    header = data['header']
    rows = data['rows']
    idx = {name: i for i, name in enumerate(header)}
    print(f"  行数: {len(rows)}")

    months = defaultdict(int)
    for row in rows:
        months[row[idx['assigned_month']]] += 1
    print("  月份分布: " + ", ".join(f"{m}:{c}" for m, c in sorted(months.items())))

    if len(months) < 3:
        print(f"  ✗ 月份不足 3 个: {sorted(months)}"); return False
    print(f"  ✓ 覆盖 {len(months)} 个月")

    types = {row[idx['case_type']] for row in rows}
    if types != {'新案', '老案'}:
        print(f"  ✗ 案件类型异常: {types}"); return False
    print("  ✓ 案件类型: 新案 / 老案")

    null_count = sum(1 for r in rows
                     if _is_null(r[idx['repaid_principal']]) or _is_null(r[idx['repaid_case_cnt']]))
    if null_count:
        print(f"  ⚠ 有 {null_count} 条 repaid_* 为 NULL（多为最新尚未成熟数据）")
    else:
        print("  ✓ repaid_* 均非空")

    invalid = []
    for row in rows:
        assigned = _to_float(row[idx['assigned_principal']])
        repaid = _to_float(row[idx['repaid_principal']])
        if assigned <= 0 or _is_null(row[idx['repaid_principal']]):
            continue
        rate = repaid / assigned * 100
        if rate > 100:
            invalid.append((row[idx['assigned_month']], row[idx['month_day']],
                            row[idx['case_type']], rate))
    if invalid:
        print(f"  ✗ 有 {len(invalid)} 条回款率 > 100%")
        for m, d, c, r in invalid[:3]:
            print(f"      {m} {d} {c}: {r:.2f}%")
        return False
    print("  ✓ 回款率均 ≤ 100%")
    return True


def validate_m0(filename, desc="M0账单"):
    print(f"\n[{desc}] {filename}")
    data = _load(filename)
    if data is None:
        print("  ✗ 文件不存在"); return False

    header = data['header']
    rows = data['rows']
    idx = {name: i for i, name in enumerate(header)}
    print(f"  行数: {len(rows)}")

    is_grouped = 'grouped' in filename.lower()
    dates = set()
    per_date = defaultdict(int)
    for row in rows:
        d = row[idx['billing_date']]
        dates.add(d)
        per_date[d] += 1

    min_d, max_d = min(dates), max(dates)
    print(f"  日期范围: {min_d} ~ {max_d}, 独立日期 {len(dates)} 天")

    start = datetime.strptime(min_d, '%Y-%m-%d')
    end = datetime.strptime(max_d, '%Y-%m-%d')
    expected_days = (end - start).days + 1
    if len(dates) != expected_days:
        print(f"  ✗ 日期不连续: 期望 {expected_days} 天，实际 {len(dates)} 天")
        return False
    print(f"  ✓ 日期连续 ({expected_days} 天)")

    expected_per_day = 2 if is_grouped else 1
    bad = [d for d, c in per_date.items() if c != expected_per_day]
    if bad:
        print(f"  ✗ 有 {len(bad)} 天每日记录数不是 {expected_per_day}: {bad[:3]}...")
        return False
    print(f"  ✓ 每天 {expected_per_day} 条记录")
    return True


def validate_grp(filename, desc="GRP催收员"):
    print(f"\n[{desc}] {filename}")
    data = _load(filename)
    if data is None:
        print("  ✗ 文件不存在"); return False
    header = data['header']
    rows = data['rows']
    idx = {name: i for i, name in enumerate(header)}
    print(f"  行数: {len(rows)}")

    months = defaultdict(int)
    for row in rows:
        months[row[idx['mth']]] += 1
    print("  月份分布: " + ", ".join(f"{m}:{c}" for m, c in sorted(months.items())))
    if len(months) < 2:
        print(f"  ✗ 月份不足 2 个: {sorted(months)}"); return False
    print(f"  ✓ 覆盖 {len(months)} 个月")

    types = sorted({row[idx['case_type']] for row in rows})
    print(f"  案件类型 ({len(types)}): {types}")
    collectors = sorted({row[idx['collector_ins']] for row in rows})
    print(f"  催收员 ({len(collectors)}): {collectors}")

    null_count = sum(1 for r in rows
                     if _is_null(r[idx['repaid_principal']]) or _is_null(r[idx['mtd_daily_assign_amt']]))
    if null_count:
        print(f"  ⚠ 有 {null_count} 条记录 repaid_principal / mtd_daily_assign_amt 为空")
    else:
        print("  ✓ 必填字段完整")
    return True


def validate_avg_eff_worktim(filename, desc="人均工作时长"):
    print(f"\n[{desc}] {filename}")
    data = _load(filename)
    if data is None:
        print("  ✗ 文件不存在"); return False

    header = data['header']
    rows = data['rows']
    idx = {name: i for i, name in enumerate(header)}
    print(f"  行数: {len(rows)}")

    months = defaultdict(int)
    for row in rows:
        months[row[idx['p_month']]] += 1
    print("  月份分布: " + ", ".join(f"{m}:{c}" for m, c in sorted(months.items())))

    area_types = sorted({row[idx['area_type']] for row in rows})
    print(f"  area_type: {area_types}")

    empty_curr = sum(1 for r in rows if _is_null(r[idx['avg_eff_worktime']]))
    if empty_curr:
        print(f"  ✗ 有 {empty_curr} 条当月 avg_eff_worktime 为空")
        return False
    print("  ✓ 当月 avg_eff_worktime 均非空")
    return True


def validate_conect_rate(filename, desc="拨打模式周度接通率"):
    """15_conect_rate → conect_rate.json：周 × call_type 粒度。"""
    print(f"\n[{desc}] {filename}")
    data = _load(filename)
    if data is None:
        print("  ✗ 文件不存在")
        return False
    header = data["header"]
    rows = data["rows"]
    idx = {name: i for i, name in enumerate(header)}
    need = ("year", "week_num", "call_type", "connect_rate", "call_cnt")
    missing = [k for k in need if k not in idx]
    if missing:
        print(f"  ✗ 缺少字段: {missing}")
        return False
    print(f"  行数: {len(rows)}")
    if not rows:
        print("  ✗ 无数据")
        return False
    print("  ✓ 关键列存在且有行")
    return True


def validate_full_call(filename, desc="全量外呼生产力"):
    """14_full_call → full_call.json：周粒度 + 复合 case_type；含环比 lag/dif（比率列允许 NULL）。"""
    print(f"\n[{desc}] {filename}")
    data = _load(filename)
    if data is None:
        print("  ✗ 文件不存在"); return False
    header = data['header']
    rows = data['rows']
    idx = {name: i for i, name in enumerate(header)}
    need = (
        'year', 'weeknum', 'case_type', 'call_cnt', 'self_full_rate_dif',
        'avg_dur_per_case',
    )
    missing = [k for k in need if k not in idx]
    if missing:
        print(f"  ✗ 缺少字段: {missing}"); return False
    print(f"  行数: {len(rows)}")
    if len(rows) < 20:
        print(f"  ⚠ 行数偏少（<20），请确认时间窗与过滤条件")
    null_call = sum(1 for r in rows if _is_null(r[idx['call_cnt']]))
    if null_call == len(rows):
        print("  ✗ call_cnt 全为空"); return False
    print("  ✓ 关键列存在且 call_cnt 非全空")
    return True


def validate_case_stock(filename, desc="人均库存·九宫格"):
    """13_case_stock → case_stock.json：九宫格粒度字段存在且有行。"""
    print(f"\n[{desc}] {filename}")
    data = _load(filename)
    if data is None:
        print("  ✗ 文件不存在"); return False
    header = data['header']
    rows = data['rows']
    idx = {name: i for i, name in enumerate(header)}
    need = ('mth', 'case_group_type', 'col_type')
    missing = [k for k in need if k not in idx]
    if missing:
        print(f"  ✗ 缺少字段: {missing}"); return False
    print(f"  行数: {len(rows)}")
    if not rows:
        print("  ✗ 无数据"); return False
    groups = {(r[idx['mth']], r[idx['case_group_type']], r[idx['col_type']]) for r in rows}
    print(f"  ✓ 粒度组合数: {len(groups)}")
    return True


def validate_precall_task(filename, desc="预测试任务·日×类型×账龄"):
    """16_precall_task → precall_task.json：MM-dd × pre_type × stage；比率列合理范围。"""
    print(f"\n[{desc}] {filename}")
    data = _load(filename)
    if data is None:
        print("  ✗ 文件不存在")
        return False
    header = data["header"]
    rows = data["rows"]
    named = {
        "pre_type",
        "stage",
        "conn_loss_ratio",
        "conn_ratio",
        "eff_duration_ratio",
        "vm_ratio_agent_conn",
    }
    idx = {name: i for i, name in enumerate(header)}
    missing = [k for k in named if k not in idx]
    if missing:
        print(f"  ✗ 缺少字段: {missing}")
        return False
    extra_idx = [i for i, h in enumerate(header) if h not in named]
    if len(extra_idx) != 1:
        print(f"  ✗ 预期除已知列外恰有 1 列日期(MM-dd)，实际额外列索引: {extra_idx}")
        return False
    i_mmdd = extra_idx[0]
    print(f"  行数: {len(rows)}")
    if not rows:
        print("  ✗ 无数据")
        return False

    mmdd_re = re.compile(r"^\d{2}-\d{2}$")
    allowed_pre = {"全时", "手工"}
    keys_seen = set()
    bad_mmdd = []
    bad_pre = []
    bad_stage = []
    bad_ratio = []
    for row in rows:
        mmdd = row[i_mmdd]
        if not mmdd_re.match(str(mmdd).strip()):
            bad_mmdd.append(mmdd)
        pt = row[idx["pre_type"]]
        if pt not in allowed_pre:
            bad_pre.append(pt)
        st = row[idx["stage"]]
        if _is_null(st):
            bad_stage.append(st)
        k = (mmdd, pt, st)
        if k in keys_seen:
            bad_ratio.append(("dup", k))
            continue
        keys_seen.add(k)

        cl = _to_float(row[idx["conn_loss_ratio"]])
        cr = _to_float(row[idx["conn_ratio"]])
        er = _to_float(row[idx["eff_duration_ratio"]])
        vm = _to_float(row[idx["vm_ratio_agent_conn"]])
        if cr < 0 or cr > 1 or vm < 0 or vm > 1:
            bad_ratio.append(("conn/vm range", (cr, vm)))
        if cl < 0 or cl > 1:
            bad_ratio.append(("conn_loss range", cl))
        if er < 0 or er > 10:
            bad_ratio.append(("eff_duration range", er))

    if bad_mmdd:
        print(f"  ✗ MM-dd 格式异常样例: {bad_mmdd[:3]}")
        return False
    if bad_pre:
        print(f"  ✗ pre_type 非 全时/手工: {sorted(set(map(str, bad_pre)))[:5]}")
        return False
    if bad_stage:
        print(f"  ✗ stage 存在空值: {len(bad_stage)} 条")
        return False
    if len(keys_seen) != len(rows):
        print(f"  ✗ (日期, pre_type, stage) 重复，期望 {len(rows)} 唯一键，实际 {len(keys_seen)}")
        return False
    if bad_ratio:
        print(f"  ✗ 比率越界或重复键样例: {bad_ratio[:5]}")
        return False

    pre_counts = defaultdict(int)
    stage_counts = defaultdict(int)
    for row in rows:
        pre_counts[row[idx["pre_type"]]] += 1
        stage_counts[row[idx["stage"]]] += 1
    print(f"  pre_type: {dict(sorted(pre_counts.items()))}")
    print(f"  stage 档位数: {len(stage_counts)}")
    print("  ✓ 粒度唯一，MM-dd / pre_type / stage / 比率范围正常")
    return True


def validate_precall_afterkeep(filename, desc="留案后外呼·日×类型×账龄"):
    """17_precall_afterkeep → precall_afterkeep.json：日 × (pre_type|type) × stage；留案率/接通率∈[0,1]，案均拨次非负。

    日期列可为 **mm_dd**（MM-dd）或 **dt**（yyyyMMdd）；类型列可为 **pre_type** 或 **type**。
    """
    print(f"\n[{desc}] {filename}")
    data = _load(filename)
    if data is None:
        print("  ✗ 文件不存在")
        return False
    header = data["header"]
    rows = data["rows"]
    idx = {name: i for i, name in enumerate(header)}
    for k in ("stage", "keep_rate", "avg_callcnt_percase_afterkeep", "conn_rate_afterkeep"):
        if k not in idx:
            print(f"  ✗ 缺少字段: {k}")
            return False
    if "pre_type" in idx:
        i_pre = idx["pre_type"]
        pre_label = "pre_type"
    elif "type" in idx:
        i_pre = idx["type"]
        pre_label = "type"
    else:
        print("  ✗ 缺少 pre_type 或 type")
        return False
    if "mm_dd" in idx:
        i_date = idx["mm_dd"]
        date_kind = "mm_dd"
    elif "dt" in idx:
        i_date = idx["dt"]
        date_kind = "dt"
    else:
        print("  ✗ 缺少 mm_dd 或 dt")
        return False

    print(f"  行数: {len(rows)} (日期列={date_kind}, 类型列={pre_label})")
    if not rows:
        print("  ✗ 无数据")
        return False

    mmdd_re = re.compile(r"^\d{2}-\d{2}$")
    dt_re = re.compile(r"^\d{8}$")
    allowed_pre = {"全时", "手工"}
    keys_seen = set()
    bad_date = []
    bad_pre = []
    bad_stage = []
    bad_val = []

    def _norm_date_key(raw) -> str:
        s = str(raw).strip().replace("-", "")
        if date_kind == "mm_dd":
            return s if mmdd_re.match(str(raw).strip()) else ""
        return s if dt_re.match(s) else ""

    for row in rows:
        raw_d = row[i_date]
        dk = _norm_date_key(raw_d)
        if not dk:
            bad_date.append(raw_d)
        pt = row[i_pre]
        if pt not in allowed_pre:
            bad_pre.append(pt)
        st = row[idx["stage"]]
        if _is_null(st):
            bad_stage.append(st)
        k = (dk or str(raw_d), pt, st)
        if k in keys_seen:
            bad_val.append(("dup", k))
            continue
        keys_seen.add(k)

        kr = _to_float(row[idx["keep_rate"]], default=float("nan"))
        av = _to_float(row[idx["avg_callcnt_percase_afterkeep"]], default=float("nan"))
        cr = _to_float(row[idx["conn_rate_afterkeep"]], default=float("nan"))
        if kr == kr and (kr < 0 or kr > 1):
            bad_val.append(("keep_rate", kr))
        if av == av and av < 0:
            bad_val.append(("avg_callcnt", av))
        if cr == cr and (cr < 0 or cr > 1):
            bad_val.append(("conn_rate_afterkeep", cr))

    if bad_date:
        print(f"  ✗ 日期格式异常样例: {bad_date[:3]}")
        return False
    if bad_pre:
        print(f"  ✗ 类型非 全时/手工: {sorted(set(map(str, bad_pre)))[:5]}")
        return False
    if bad_stage:
        print(f"  ✗ stage 存在空值: {len(bad_stage)} 条")
        return False
    if len(keys_seen) != len(rows):
        print(f"  ✗ (日期, 类型, stage) 重复，期望 {len(rows)} 唯一键，实际 {len(keys_seen)}")
        return False
    if bad_val:
        print(f"  ✗ 数值越界或重复键样例: {bad_val[:5]}")
        return False

    pre_counts = defaultdict(int)
    stage_counts = defaultdict(int)
    for row in rows:
        pre_counts[row[i_pre]] += 1
        stage_counts[row[idx["stage"]]] += 1
    print(f"  类型分布: {dict(sorted(pre_counts.items()))}")
    print(f"  stage 档位数: {len(stage_counts)}")
    print("  ✓ 粒度唯一，日期/类型/stage / 数值范围正常")
    return True


# ================== 注册表 ==================
# key = JSON 文件名（与 run_all.py 输出一致）
# value = (验证函数, 描述)
# 新增数据时：写好验证函数，在这里注册一行即可
VALIDATORS = {
    's_class_all.json':              (validate_s_class,         'S类·ALL口径'),
    's_class_new.json':              (validate_s_class,         'S类·NEW口径'),
    's_class_mtd.json':              (validate_s_class,         'S类·MTD口径'),
    'm1_assignment_repayment.json':  (validate_m1,              'M1分案回款'),
    'm0_billing.json':               (validate_m0,              'M0账单'),
    'm0_billing_grouped.json':       (validate_m0,              'M0账单·分组'),
    'grp_collector.json':            (validate_grp,             'GRP催收员'),
    'avg_eff_worktim.json':          (validate_avg_eff_worktim, '人均有效工时'),
    'avg_eff_call_worktim.json':     (validate_avg_eff_worktim, '人均通话工时'),
    'avg_eff_wa_worktim.json':       (validate_avg_eff_worktim, '人均WA工时'),
    'M2_class_all.json':             (validate_m2_class_all,    'M2·ALL'),
    'M6_class_all.json':             (validate_m6_class_all,    'M2-M6账龄31-180天'),
    'case_stock.json':               (validate_case_stock,      '人均库存·九宫格'),
    'full_call.json':                (validate_full_call,       '全量外呼生产力'),
    'conect_rate.json':              (validate_conect_rate,     '拨打模式周度接通率'),
    'precall_task.json':             (validate_precall_task,    '预测试任务·日×类型×账龄'),
    'precall_afterkeep.json':        (validate_precall_afterkeep, '留案后外呼·日×类型×账龄'),
}


# ================== 主流程 ==================

def main():
    print("=" * 60)
    print("数据完整性 + 业务规则验证")
    print("=" * 60)
    print(f"  数据目录: {DATA_DIR}")
    print(f"  SQL 目录: {SQL_DIR}")

    # 步骤 1: 前置完整性检查（缺文件直接退出）
    if not precheck_completeness():
        print("\n" + "=" * 60)
        print("✗ 数据不完整，请先跑 run_all.py 落盘缺失的 JSON")
        print("=" * 60)
        return 2

    # 步骤 2: 按注册表调度验证
    print("\n" + "=" * 60)
    print("业务规则验证（按注册表）")
    print("=" * 60)

    actual_jsons = sorted(f.name for f in DATA_DIR.glob('*.json') if not f.name.startswith('_'))
    results = {}
    skipped = []

    for jname in actual_jsons:
        if jname in VALIDATORS:
            fn, desc = VALIDATORS[jname]
            try:
                results[jname] = fn(jname, desc)
            except Exception as e:
                print(f"\n[ERR] {jname} 验证抛出异常: {e!r}")
                results[jname] = False
        else:
            skipped.append(jname)

    # 步骤 3: 汇总
    print("\n" + "=" * 60)
    print("验证结果汇总")
    print("=" * 60)
    for jname, ok in results.items():
        print(f"  {'✓ 通过' if ok else '✗ 失败'}  {jname}")
    if skipped:
        print(f"\n  [SKIP] 以下 {len(skipped)} 个文件无验证规则（如需校验，请在 VALIDATORS 注册）：")
        for s in skipped:
            print(f"      - {s}")

    all_passed = all(results.values()) if results else False
    print("\n" + "=" * 60)
    if all_passed:
        print(f"✓ 全部 {len(results)} 个文件验证通过，可以开始画图")
        return 0
    print("✗ 数据验证失败，请检查上方 ✗ 项")
    return 1


if __name__ == '__main__':
    sys.exit(main())
