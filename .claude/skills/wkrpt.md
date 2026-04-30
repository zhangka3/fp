---
name: wkrpt
description: 周报自动化 - SQL→JSON→校验→图表；首次须输出前置条件表（含是否满足/理由与处理方法列）并按 Skill 内分项检查体系在本机逐项自检（MCP/网络/依赖/飞书）
---

# 周报自动化完整流程

自动执行周报数据更新和图表生成的完整工作流，支持智能数据成熟度判断和月同期对比。

## 路径约定（必读）

- **项目根目录**：包含 `code/`、`data/`、`screenshots/`、`.claude/` 的目录（仓库克隆根路径）。
- 下文凡写 **`code/...`、`data/`、`screenshots/`** 等均相对于项目根，与机器上的盘符、文件夹名无关。
- 本 Skill 文件路径为 **`.claude/skills/wkrpt.md`**；文档中的跳转链接使用相对于该文件的 **`../../...`** 写法。

## 前置使用条件（必读）

### `run_all.py` 与 Cursor MCP 的约定

- `code/python/01_execute_sql/run_all.py` 会读取 **`%USERPROFILE%\.cursor\mcp.json`**（macOS/Linux：`~/.cursor/mcp.json`），且要求存在 **`mcpServers.sql`** 节点。
- `sql` 配置项内需包含 **`url`**（如 Datalumina MCP HTTP 地址）与 **`headers`**（至少含可用的 **`X-API-Key`**）。密钥无效或未配置时，步骤 1 会在提交查询时报错（如 HTTP 401）。

### 分项检查体系（A～I：Agent 首次执行时逐项照做）

以下为**每一项**的「怎么查、怎样算通过、失败写什么」。**禁止**在对话中粘贴完整 `X-API-Key` 或 `app_secret`。

**通用**：在项目根执行路径类检查时，先 `cd` 到含 `code/sql` 的目录；Python 命令优先 `python`，无效再试 `python3`。

| 序号 | 检查动作（Agent 执行） | 判定为 ✅ | 判定为 ❌ | 判定为 ⚠️（允许的情况） |
|------|------------------------|-----------|-----------|---------------------------|
| **A** | 在项目根检查路径是否存在：`code/sql`、`code/python`、`data`；若缺 `screenshots` 则 **创建空目录** `screenshots`（仅新增空文件夹，不删不改其它结构）。可用终端：`Test-Path code/sql; Test-Path data`（PowerShell）或 `test -d code/sql`（bash）。 | 三者均存在；`screenshots` 已存在或已创建 | 找不到 `code/sql` 或 `data`：说明当前工作区不是项目根 | — |
| **B** | 执行 `python --version` 或 `python3 --version`。 | 主版本 ≥ 3，且次版本建议 ≥ 10（3.10+） | 命令不存在或版本 &lt; 3.8 | 3.8～3.9：标 ⚠️，理由写「建议升级 3.10+」，仍可尝试后续步骤 |
| **C** | 执行：`python -c "import requests, matplotlib, numpy, pandas; print('ok')"`（与 B 使用同一解释器）。 | 无报错打印 `ok` | `ModuleNotFoundError`：记下缺哪个包 | — |
| **D** | 确认文件存在：`%USERPROFILE%\.cursor\mcp.json`（Mac/Linux：`$HOME/.cursor/mcp.json`）。若有读取权限，解析 JSON：**存在键路径** `mcpServers` → `sql`，且 `sql` 内含 **`url`**（非空字符串）、**`headers`**（字典）。再确认 **`headers` 中存在键 `X-API-Key`** 且其值为**非空字符串**（不要输出值）。 | 文件存在且结构满足 | 文件不存在 / 不是合法 JSON / 缺少 `mcpServers.sql` / 缺少 `url` 或 `X-API-Key` | — |
| **E** | （1）在 **D 为 ✅** 前提下，确认 Key **非空**即可。（2）**强烈建议**在项目根执行：`python code/python/01_execute_sql/run_all.py --list`：若进程启动且打印 SQL 列表、**无** `401`/`Unauthorized`（该命令会加载 MCP 配置；若实现上仍会请求鉴权失败则看stderr）。若 `--list` 不触发鉴权：**在本会话或用户确认近期曾成功跑通步骤1** 可标 ✅；否则对「密钥是否真能查数」标 **⚠️**，理由写「配置已就绪，最终以步骤1首次 `submit_query` 为准」。（3）若直接执行 `--list` 即出现 **401**：标 ❌。 | 非空 Key +（`--list` 成功 **或** 已证实近期可查数） | `--list` 或等价探测明确返回 401 / 鉴权失败 | 仅完成非空与 D，尚未实际查数 |
| **F** | 从 `mcp.json` 读出 `mcpServers.sql.url` 的 **主机**（勿整段敏感路径贴给用户时可适当省略路径参数）。用 `python -c` 发 **HTTPS 连接探测**：例如 `requests.get(url, timeout=10)` 仅看是否 **连接层成功**（不要求业务成功），或 `ping`/系统工具测 DNS。若企业网需代理：询问用户是否已设系统/环境代理。 | `requests` 能连上 host（如 200/401/405 均说明网络可达）；或用户确认代理已配置且同类工具可用 | 超时、`ConnectionError`、`Name or service not known` | 防火墙限制仅允许 Cursor 内置 MCP：说明「须本机对当前终端开放同一出口」 |
| **G** | **仅当用户本次要做飞书写文档时检查**：`python -c "import requests_toolbelt; print('ok')"`。若用户明确不做飞书，本行填 **—（跳过）**，「是否满足」可写 **N/A**。 | 导入成功 | 失败则建议：`pip install requests-toolbelt` | 用户未决定是否飞书：标 ⚠️「待用户确认是否跑飞书」 |
| **H** | **仅飞书流程**：项目根 `feishu_app.json` 存在；解析 JSON 含非空 `app_id`、`app_secret`（**勿输出 secret**）。不做飞书则 **N/A**。 | 文件存在且两字段非空 | 缺失文件或字段为空：说明复制 `feishu_app.example.json` 并填写 | — |
| **I** | **推荐**：`python -c "from matplotlib import font_manager; names={f.name for f in font_manager.fontManager.ttflist}; need=('Microsoft YaHei','SimHei','DengXian'); hit=[n for n in need if any(n.lower() in x.lower() for x in names)]; print(hit or 'none')"`。若输出含任一字体名则 ✅。Windows 也可检查字体文件是否存在（可选）。 | 至少命中一种常见中文字体 | 输出 `none`：图表可能乱码 | 无法枚举字体时标 ⚠️，理由写「请在步骤5后肉眼看一张 PNG」 |

### 前置条件检查表（首次执行时必须输出；须含自检结果）

**Agent 流程**：先根据上表 **逐项在本机执行检查**，再向下表中填入 **是否满足** 与 **理由与处理方法**。

- **是否满足** 取值：**✅** / **❌** / **⚠️** / **N/A**（不适用，如不做飞书时的 G/H）。
- **理由与处理方法**：
  - 为 **✅** 或 **N/A** 时：可写 **「—」** 或一句确认（勿泄露密钥）。
  - 为 **❌** 或 **⚠️**：必须写清**依据哪一步检查**、**失败现象**、**建议用户操作**（命令、配置路径、安装包名等）。

**输出模板（复制后填空）：**

| 序号 | 条件 | 是否必需 | 用于哪些步骤 | 不满足时典型现象 | 是否满足 | 理由与处理方法 |
|------|------|----------|--------------|------------------|----------|----------------|
| A | 工作区为项目根（含 `code/`、`data/`、`screenshots`） | 必需 | 全部 | 找不到 SQL 或 data |  |  |
| B | Python 3（建议 3.10+） | 必需 | 全部 | 无 python |  |  |
| C | `requests`、`matplotlib`、`numpy`、`pandas` | 必需 | 1～5 | `ModuleNotFoundError` |  |  |
| D | `~/.cursor/mcp.json` 含 `mcpServers.sql` + `url` + `X-API-Key` | 必需 | 步骤 1 | 启动即报错 |  |  |
| E | API Key 有效、可查数（见分项表） | 必需 | 步骤 1 | HTTP 401 |  |  |
| F | 本机网络可达 MCP `url` | 必需 | 步骤 1 | 超时 |  |  |
| G | `requests_toolbelt` | 仅飞书 | 飞书传图 | 上传失败 |  |  |
| H | `feishu_app.json` | 仅飞书 | 飞书脚本 | 无凭证 |  |  |
| I | 中文字体（ matplotlib 可发现） | 推荐 | 步骤 5 | 乱码 |  |  |

### 首次执行（新设备 / 新用户 / 本会话第一次跑 wkrpt）——Agent 必须做的事

**触发**：用户第一次在本环境跑周报流程、或明确表示「新电脑 / 刚 clone / 没跑通过」，或你无法确认环境已就绪时——**一律先做自检**。

1. **输出**上方 **「前置条件检查表（模板）」** 的完整表格骨架。
2. **按「分项检查体系」表格**，在本机逐项执行检查，将结果填入 **是否满足**、**理由与处理方法** 两列。
3. **阻塞规则**：
   - **A～D、B、C** 任一为 **❌**：**禁止**执行步骤 1～5，只输出修复指引。
   - **E** 为 **❌**（明确 401 等）：同上。
   - **E** 为 **⚠️**、其余必需项均为 **✅**：可执行步骤 1，但若步骤 1 首次提交仍失败，停止并让用户轮换 Key/权限。
   - **F** 为 **❌**：禁止步骤 1，先解决网络/DNS/代理。
   - **G/H**：仅当用户要做飞书时不得为 **❌**；否则标 **N/A** 跳过。
4. **必需项（A～F，且 G/H 在飞书场景下）均为 ✅ 或可接受的 ⚠️（仅 E 允许待步骤1验证）** 后，再进入核心流程。

### 与用户说明的简短话术示例

> 首次在本机跑 wkrpt：下面是前置条件检查表（含是否满足与处理方法）。若有 ❌，请先按「理由与处理方法」修复；⚠️ 表示有风险或待后续步骤确认。

---

## 快速使用

```bash
/wkrpt
```

## 凭证与交接（必读）

周报主流程（SQL → 校验 → 图表）**不依赖**飞书；若后续要跑「模板分析」「飞书文档生成」等脚本，需要飞书应用凭证。

**推荐做法（接收方零环境变量）：**

1. 在本项目**根目录**复制 `feishu_app.example.json` 为 `feishu_app.json`，填入 `app_id`、`app_secret`（与飞书开放平台该自建应用一致）。
2. `feishu_app.json` 已被 `.gitignore` 忽略，**不会**随 Git 推送；**交接时请用安全方式**（加密渠道、U 盘、内网盘等）将 `feishu_app.json` 一并交给接收方，对方放到自己 clone 下来的**同一项目根目录**即可，**无需**再设系统环境变量或 PowerShell 里的 `$env:...`。
3. 可选：若更习惯环境变量，仍可设置 `FEISHU_APP_ID`、`FEISHU_APP_SECRET`（会覆盖文件未填的情况；实际以代码加载顺序为准：先读 `feishu_app.json`，再读环境变量）。

根目录 `get_token.ps1.example` 演示了如何基于 `feishu_app.json` 拉取 token；你可复制为本地 `get_token.ps1` 使用（`get_token.ps1` 勿提交 Git）。

## 核心流程

### 步骤1：执行SQL查询
- 读取 `code/sql/` 目录下全部 `.sql`（当前仓库一般为 **10** 个，含人均工时等；以 `python code/python/01_execute_sql/run_all.py --list` 为准）
- 使用 MCP HTTP（`run_all.py` 读取 `~/.cursor/mcp.json` 中的 **`mcpServers.sql`**）调用 **`submit_query` / `get_query_status` / `get_query_result`**，引擎 **SMART**
- 自动等待所有查询完成
- SQL使用动态日期函数，无需手动更新日期

### 步骤2：保存JSON数据
将查询结果保存为标准JSON格式到 `data/` 目录：

```json
{
  "metadata": {
    "data_fetch_date": "2026-04-20",
    "query_time": "2026-04-20 08:30:00",
    "query_id": "953982"
  },
  "header": ["field1", "field2", ...],
  "rows": [[value1, value2, ...], ...],
  "rowCount": 234
}
```

**重要**：`metadata.data_fetch_date` 用于M0数据的成熟度判断和月同期对比。

### 步骤3：数据验证
运行 `validate_data.py` 验证数据质量：
- ✓ 时间范围检查（S类3个月、M1≥3个月、M0全年、GRP 2个月、人均有效工作时长3个月）
- ✓ 回款率约束（≤100%，MTD除外）
- ✓ 字段完整性（必填字段、数据类型）

### 步骤4：确认继续
- 如果验证失败，暂停并报告问题详情
- 等待用户确认后再继续后续步骤

### 步骤5：生成图表
- 清除旧图表（按类型分组清理）
- 依次运行5个图表生成脚本
- 输出39张PNG图表到 `screenshots/` 目录

## 数据映射

### SQL → JSON

| SQL文件 | 输出JSON | 行数 | 说明 | Query ID |
|---------|---------|------|------|----------|
| 01_s_class_all.sql | s_class_all.json | ~234 | S类案件-ALL口径 | 953982 |
| 02_s_class_new.sql | s_class_new.json | ~234 | S类案件-NEW口径 | 953983 |
| 03_s_class_mtd.sql | s_class_mtd.json | ~234 | S类案件-MTD口径 | 953984 |
| 04_m1_assignment_repayment.sql | m1_assignment_repayment.json | 156+ | M1分案回款数据 | 953985 |
| 05_m0_billing.sql | m0_billing.json | ~360+ | M0账单明细 | 953986 |
| 06_m0_billing_grouped.sql | m0_billing_grouped.json | ~720+ | M0分组统计 | 953987 |
| 07_grp_collector.sql | grp_collector.json | ~1000+ | GRP催收员业绩 | 953988 |
| 08_avg_eff_worktim.sql | avg_eff_worktim.json | 643 | 人均有效工作时长（按模块-队列） | 963926 |

### JSON → 图表

| 生成脚本 | 数据源 | 输出图表 | 数量 | 说明 |
|---------|--------|---------|------|------|
| screen_s_class.py | s_class_*.json | recovery_rate_*.png | 15张 | 3种口径×5个case_type |
| screen_m1.py | m1_assignment_repayment.json | m1_*.png | 3张 | 分案/回款/回款率 |
| screen_m0.py | m0_billing*.json | m0_*.png | 8张 | 逾期率/催回率/用户分析 |
| screen_grp.py | grp_collector.json | grp_*.png | 12张 | 催收员业绩对比 |
| screen_avg_eff_worktime.py | avg_eff_*.json（多条） | avg_eff_*.png | 至多 3 张 | 人均有效/Call/WA 工时（以数据文件是否存在为准） |

**图表总数**：以 `code/screens/run_all_screens.py` 实际产出为准（文档示例曾写 39 张；含多条 avg_eff 时可能 **40+**）。

## 关键业务逻辑

### M0数据成熟度判断 ⭐ 核心逻辑

**成熟度定义**：一个billing_date的账单，需要等待N天后，才能观察到其N天后的业务指标。

#### 数据获取时间识别

1. **优先从metadata读取**：
   ```json
   "metadata": {
     "data_fetch_date": "2026-04-20"
   }
   ```

2. **兼容旧数据（自动推断）**：
   - 找到最后一个 `principal_pastdue_1d > 0` 的billing_date
   - 数据获取时间 = 最后有效日期 + 1天
   - 例如：最后有效日期=04-19 → 数据获取时间=04-20

#### 成熟期要求

| 指标 | 成熟期 | 计算公式 | 示例（数据获取04-20） |
|------|--------|---------|---------------------|
| 逾期1d | 1天 | billing_date ≤ fetch_date - 1 | billing_date ≤ 04-19 |
| 7d催回率 | 8天 | billing_date ≤ fetch_date - 8 | billing_date ≤ 04-12 |
| 30d催回率 | 31天 | billing_date ≤ fetch_date - 31 | billing_date ≤ 03-20 |

#### 月同期对比 ⭐ 重要

**所有标题包含"月同期"的图表**，各月统计周期必须一致：

```
数据获取时间：2026-04-20
月内截止日期：19号

4月统计：4月1-19日（19天）
3月统计：3月1-19日（19天）← 同期！
2月统计：2月1-19日（19天）← 同期！
```

**涉及的图表（5张）**：
1. M0金额逾期率（按月同期）
2. M0单量逾期率（按月同期）
3. M0金额催回率（7d/30d，按月同期）
4. M0金额催回率（7d/30d，非合并订单用户，按月同期）
5. M0金额催回率（7d/30d，合并订单用户，按月同期）

**关键点**：
- ✓ 分子分母同步过滤
- ✓ 所有月份用相同天数对比
- ✓ 避免最新月数据不完整导致指标被稀释

### GRP同期对比

历史月份截至与最新月份相同日期：
- 最新月202604数据到19号 → 历史月202603也取到19号
- 在 `process_grp_data()` 中自动实现
- 避免月末效应影响对比

### GRP催收员动态适配

支持各月催收员数量变化：
- **显示逻辑**：两个月的并集（3月有PM就显示，4月没有就不显示）
- **排序逻辑**：仅统计最新月份存在的催收员
- **缺失数据**：自动填充为0

## 图表特性

### S类图表 (15张)
- 3种口径（ALL/NEW/MTD）× 5个case_type
- 柱状图 + 折线图组合
- 自动月份对比
- MTD口径回款率允许>100%

### M1图表 (3张)
- 分案金额、回款金额、回款率
- 多月趋势对比
- 自动计算同比环比

### M0图表 (8张) ⭐ 成熟度逻辑
- **逾期率图表**（3张）：使用1天成熟期，启用月同期对比
- **催回率图表**（3张）：使用8天/31天成熟期，启用月同期对比
- **用户分析图表**（2张）：合并订单用户vs非合并订单用户
- 按周统计（周日起始）
- 智能过滤未成熟数据

### GRP图表 (12张) ⭐ 已美化
- 催收员/区域业绩对比（12个case_type）
- 现代化配色方案（14种颜色）
- 增强视觉效果：粗线条(3.0)、大标记点(5)、阴影效果
- 智能布局：自动适配催收员数量变化（1-20+人）
- 排序展示：底部显示回款率排名（带百分比）
- 动态标签间隔：防止文字重叠

### 人均有效工作时长图表 (1张)
- **数据分组**：按模块-队列组合分组（S1-RA、S1-RB、S1-RC、S1-RD、S2-RA、S2-RB、S2-RC、S3、S3-RB）
- **数据过滤**：仅保留S1、S2、S3模块，过滤M2和NULL
- **双层布局**：
  - 上半部分：折线图显示3个月的人均有效工作时长趋势
  - 下半部分：柱状图显示最新月份的环比差值
- **视觉优化**：
  - 空值处理：折线在空值处自动断开，不强行连接
  - 背景色：各分组间交替使用浅灰/白色背景
  - X轴标签：保留WK-WD原始格式（如WK1-WD2），按周添加分隔线
  - 无留白：图表左右边界紧贴数据区域
- **字段说明**：
  - area_type：模块（S1/S2/S3）
  - area_ranking_type：队列（如S1RA、S2RC等）
  - scope_x：横坐标分类（WK{n}-WD{d}，WK表示月内第几周，WD表示周几）
  - avg_eff_worktime：人均有效工作时长（分钟）
  - diff_avg_eff_worktime：环比差值（分钟，青色表示增长，红色表示下降）

## 关键注意事项

### ⚠️ SQL文件管理

**不要随意修改SQL文件！** 所有SQL已使用动态日期函数：

```sql
-- 自动获取昨天的日期
date_format(date_sub(current_date(), 1), 'yyyy-MM-dd')

-- 自动获取最近2个月
WHERE mth IN (
  date_format(date_sub(current_date(), 30), 'yyyyMM'),
  date_format(date_sub(current_date(), 1), 'yyyyMM')
)
```

无需手动更新日期，每次运行自动获取最新数据。

### 数据流完整性

必须按顺序执行，不可跳过中间步骤：

```
SQL查询 → JSON保存(+metadata) → 数据验证 → 图表生成
```

- 跳过验证可能导致图表数据错误
- JSON必须包含metadata字段（用于M0成熟度判断）
- 所有字段类型必须正确

### 环境要求

- **MCP SQL Server**：已配置并有数据库访问权限
- **Python 3.x**：matplotlib, numpy, pandas 库
- **中文字体**：SimHei / Microsoft YaHei / DengXian
- **查询时间**：单个查询约30-120秒，总计1-2分钟

## JSON格式规范

### 标准格式（必须包含metadata）

```json
{
  "metadata": {
    "data_fetch_date": "2026-04-20",
    "query_time": "2026-04-20 08:30:00",
    "query_id": "953982",
    "data_source": "tmp_export.s_class_all"
  },
  "header": ["p_month", "day", "case_type", "assigned_principal", ...],
  "rows": [
    ["2026-02", "2026-02-01", "S1", "17142803496.000000", ...],
    ["2026-02", "2026-02-02", "S1", "6149470974.000000", ...]
  ],
  "rowCount": 234
}
```

### metadata字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| data_fetch_date | string | **是** | 数据获取日期（YYYY-MM-DD），用于M0成熟度判断 |
| query_time | string | 否 | 查询执行时间（YYYY-MM-DD HH:MM:SS） |
| query_id | string | 否 | Query ID，用于追踪 |
| data_source | string | 否 | 数据表名 |

**重要**：
- M0数据（m0_data.json、m0_data_grouped.json）**必须**包含 `data_fetch_date`
- 如果没有metadata，代码会自动推断（兼容旧数据），但不够准确
- 其他数据源的JSON可选metadata，但建议统一添加

## 故障排查

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| SQL查询超时 | 数据量大/网络慢 | 检查网络连接，必要时增加超时参数 |
| JSON格式错误 | 查询结果列不一致 | 检查SQL的SELECT字段顺序和类型 |
| 缺少metadata | 旧格式JSON | 重新执行SQL查询，添加metadata字段 |
| 数据验证失败 | 时间范围/回款率异常 | 检查SQL的WHERE条件和日期函数 |
| 图表生成报错 | JSON字段不匹配 | 重新执行SQL查询，确保字段完整 |
| M0逾期率异常 | 成熟度判断错误 | 检查metadata.data_fetch_date是否正确 |
| 月同期对比不一致 | 各月天数不同 | 正常现象，代码已启用same_period=True |
| 催收员显示异常 | 各月collector数量不同 | 正常现象，代码已支持动态适配 |
| 中文显示乱码 | 字体未安装 | 安装 SimHei/Microsoft YaHei 字体 |

## 执行输出示例

```
============================================================
周报自动化流程开始
============================================================

[第1步] 执行SQL查询
  查询 01_s_class_all.sql (Query ID: 953982)...
  ✓ 查询完成: 234 行
  查询 02_s_class_new.sql (Query ID: 953983)...
  ✓ 查询完成: 234 行
  ... (共8个查询)

[第2步] 保存JSON文件
  ✓ s_class_all.json (28.0 KB)
    - metadata.data_fetch_date: 2026-04-20
  ✓ s_class_new.json (27.9 KB)
  ✓ s_class_mtd.json (28.1 KB)
  ✓ m1_assignment_repayment.json (19.5 KB)
  ✓ m0_data.json (45.2 KB)
    - metadata.data_fetch_date: 2026-04-20 ← 用于成熟度判断
  ✓ m0_data_grouped.json (88.7 KB)
    - metadata.data_fetch_date: 2026-04-20
  ✓ grp_data.json (127.3 KB)
  ✓ avg_eff_worktim.json (78.5 KB)
    - 643行数据，按模块-队列分组

[第3步] 数据验证
  验证 S类案件数据...
    ✓ 时间范围: 3个月
    ✓ 回款率约束: 全部 ≤ 100%
  验证 M1分案回款数据...
    ✓ 时间范围: ≥ 3个月
  验证 M0账单数据...
    ✓ 数据连续性: 从2025-01-01开始
    ✓ 数据获取时间: 2026-04-20
  验证 GRP催收员数据...
    ✓ 时间范围: 2个月
  验证 人均有效工作时长数据...
    ✓ 时间范围: 3个月
    ✓ 数据行数: 643行

  [验证通过] 所有数据符合要求

[第5步] 生成图表
  生成S类图表...
    [清除旧图表] 15 张
    ✓ recovery_rate_S1RA_ALL.png
    ... (共15张)

  生成M1图表...
    [清除旧图表] 3 张
    ✓ m1_assignment.png
    ... (共3张)

  生成M0图表...
    [清除旧图表] 8 张
    数据获取时间（从metadata读取）: 2026-04-20
    月内截止日期: 每月19号（用于月同期对比）
    ✓ m0_principal_overdue_rate_monthly.png
    ✓ m0_count_overdue_rate_monthly.png
    ✓ m0_principal_overdue_rate_weekly.png
    ✓ m0_collection_rate_weekly.png
    ✓ m0_collection_rate_7d_30d_monthly.png
    ✓ m0_ind1_ratio.png
    ✓ m0_collection_rate_7d_30d_monthly_ind0.png
    ✓ m0_collection_rate_7d_30d_monthly_ind1.png

  生成GRP图表...
    [清除旧图表] 12 张
    ✓ grp_S1RA.png
    ... (共12张)

  生成人均有效工作时长图表...
    [清除旧图表] 1 张
    ✓ avg_eff_worktime.png

============================================================
周报自动化流程完成！共生成 39 张图表
输出目录: <项目根>/screenshots
============================================================
```

## 技术配置

### SQL查询
- 引擎：SMART
- 数据源：datasource=1
- 超时：120秒/查询
- 动态日期：使用 `date_format(date_sub(current_date(), N), 'yyyy-MM-dd')`

### 图表样式
- DPI：100-150
- 格式：PNG
- 字体：DengXian / SimHei / Microsoft YaHei
- 背景：白色
- 图例：带阴影、圆角边框
- 标题：24号字体，加粗，黑色（fig.suptitle）

## 相关文档

- [SQL查询说明](../../code/sql/README.md)
- [图表生成文档](../../code/screens/README.md)
- [GRP鲁棒性文档](../../code/screens/GRP_ROBUSTNESS.md)
- [数据验证脚本](../../code/screens/validate_data.py)

## 手动执行

如需单独执行某个步骤：

```bash
# 在项目根目录下进入图表脚本目录（路径相对于项目根）
cd code/screens

# 数据验证
python validate_data.py

# 生成S类图表
python screen_s_class.py

# 生成M1图表
python screen_m1.py

# 生成M0图表（会自动读取metadata.data_fetch_date）
python screen_m0.py

# 生成GRP图表
python screen_grp.py

# 生成人均有效工作时长图表
python screen_avg_eff_worktime.py
```

## 更新记录

**2026-04-27**
- ✓ 新增人均有效工作时长图表（08_avg_eff_worktim.sql）
- ✓ 支持按模块-队列组合分组（S1-RA、S1-RB、S2-RC等）
- ✓ 折线图空值自动断开，避免误导
- ✓ 图表左右无留白，数据区域占满宽度
- ✓ 更新总图表数量：38张 → 39张

**2026-04-21**
- ✓ 添加JSON metadata字段支持
- ✓ 实现M0数据成熟度自动判断
- ✓ 实现月同期对比逻辑
- ✓ GRP图表全面美化
- ✓ 支持催收员数量动态变化

**2026-04-20**
- ✓ 完成初始版本

---

**维护者**：Claude Code
**最后更新**：2026-04-30（补充前置条件表与首次自检指令；校正 SQL/JSON 文件名与图表数量说明）
