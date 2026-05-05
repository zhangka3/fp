# 图表生成模块（`code/screens/`）

本目录包含周报所需的 **`screen_*.py`** 画图脚本及编排入口。**推荐**在项目根执行 **`python code/screens/run_all_screens.py`**：自动发现全部 `screen_*.py`，子进程隔离运行（单脚本超时 300s）。

```powershell
# 项目根
python code/screens/run_all_screens.py           # 全部
python code/screens/run_all_screens.py --list    # 仅列出脚本
python code/screens/run_all_screens.py screen_grp # 只跑匹配项（见脚本 --help）
```

## 脚本与数据源 / 产出（摘要）

| 脚本 | 主要数据源（`data/`） | 产出示例（`screenshots/`） |
|------|------------------------|----------------------------|
| `screen_s_class.py` | `s_class_all.json`、`s_class_new.json`、`s_class_mtd.json` | **`recovery_rate_S*.png`**（单 case / 组合 / 表图；清理时不用 `recovery_rate_*.png`，避免误删 M2/M6） |
| `screen_m1.py` | `m1_assignment_repayment.json` | `assignment_repayment_*.png`、`assignment_repayment_table_*.png`（柱线 + 表图） |
| `screen_m0.py` | **`m0_billing.json`**、**`m0_billing_grouped.json`**（与 `run_all` 命名一致） | `m0_*.png`（约 8 张） |
| `screen_grp.py` | **`grp_collector.json`** | `grp_*.png`（按数据中 `case_type`，约 12 张） |
| `screen_avg_eff_worktime.py` | `avg_eff_worktim.json` 等（存在则画） | `avg_eff_worktime.png`、`avg_eff_call_worktime.png`、`avg_eff_wa_worktime.png`（1～3 张） |
| `screen_m2_m6.py` | `M2_class_all.json`、`M6_class_all.json` | `recovery_rate_M2_*.png`、`recovery_rate_M6_*.png` 及对比表（共 4 张） |
| **`screen_case_stock.py`** | **`case_stock.json`**（需含 `case_group_type`、`col_type` 等字段） | **`case_stock_9grid.png`**（3×3 柱线 + 每列下方折线数值表；详见下文） |
| **`screen_full_call.py`** | **`full_call.json`**（`14_full_call.sql`） | **`full_call_full_rates.png`**（满频）、**`full_call_avg_calls_per_case.png`**（案均拨打）、**`full_call_avg_dur_per_case.png`**（案均有效通时）、**`full_call_eff_rates.png`**（有效接通率）；各图均为本人/非本人/整体三带；**最近 5 周**，按 `case_type` 排序（见下文） |
| **`screen_call_type_weekly.py`** | **`conect_rate.json`**（`15_conect_rate.sql`） | **`call_type_weekly_connect.png`**（周 × `call_type`：上行接通率折线、下行拨打量堆叠柱；**24×16 英寸** 与 `full_call_eff_rates.png` 同高） |
| **`screen_precall_task.py`** | **`precall_task.json`**（`16_precall_task.sql`） | **`precall_task_trends.png`**（预测试任务：**4 行指标 × 列＝手工 stage + 1 cm 空白 + 全时 stage**） |
| **`screen_precall_afterkeep.py`** | **`precall_afterkeep.json`**（`17_precall_afterkeep.sql`） | **`precall_afterkeep_trends.png`**（留案/留案后外呼：**3 行**＝留案率、案均拨次、留案后接通率；版式同 precall_task） |

视觉主题见同目录 **`chart_theme.py`**（各脚本 `import chart_theme` 后 `apply_chart_theme()`）。

## `screen_full_call.py`（满频 / 案均拨打 / 案均通时 / 有效接通）

- **依赖**：`data/full_call.json`（`code/sql/14_full_call.sql` → `run_all.py`）。
- **输出**：`screenshots/full_call_full_rates.png`、`screenshots/full_call_avg_calls_per_case.png`、`screenshots/full_call_avg_dur_per_case.png`、`screenshots/full_call_eff_rates.png`（生成顺序同左：**满频→案均拨打→案均通时→接通率**）。
- **时间范围**：按 `(year, weeknum)` 排序取**最新 5 个自然周**（不足则全用）。
- **折线**：**每个 `case_type` 一条线**，只在该类型自己的 5 个周坐标上连线，**不跨类型**；颜色按类型区分；**无图例**。
- **柱图**：每个 `case_type` 下 **每周一根柱**，高度为该周 `*_dif`：满频/接通率图 **×100 为 pp**；案均拨打/案均通时为**原单位周差**（次/案、秒/案）；最近 **3** 周在柱顶标注 `+/-` 数值。
- **上图标注**：仅在**最近 3 周**的点上标注具体数值——满频/接通率为 **%**；案均拨打为**次/案**；案均有效通时为**秒/案**（与数仓 duration 一致）；无底色、无边框；**不**在上图写环比增量。
- **过滤**：若某 `case_type` 在**全局最近一周**无记录，则**整类不画**（该周缺数即剔除）。
- **坐标轴**：**纵轴不显示刻度数字**；**横轴**刻度与 `YYYY-Www` 标签**仅第三带（整体）的下图**展示，前两带的上下图均不展示横轴刻度。
- **`case_type` 标题**：置于**上子图绘图区上方**（轴外），避免遮挡折线上的数值标注。
- **排序**：以末尾 **`-RA`/`-RB`/`-RC`/`-RD`** 解析 `case_type` 前缀；**S1→S2→S3**，再 **M 按数字升序**（同档 **无「+」先于「+」**，如 M2 先于 M2+），故 **M4+ 恒在 M5+ 前**；组内 **RA→RB→RC→RD**。
- **字段**：满频三带 `self_*` / `contact_*` / `total_*`；接通率三带 `eff_self_*` / `eff_cont_*` / `eff_*`；案均拨打三带 `avg_self_call_cnt_per_case` / `avg_noself_call_cnt_per_case` / `avg_call_cnt_per_case` 及 `*_dif`；案均有效通时三带 `avg_self_dur_per_case` / `avg_noself_dur_per_case` / `avg_dur_per_case` 及 `*_dif`（释义见 `code/sql/README.md`）。

单独调试：

```powershell
cd code/screens
python screen_full_call.py
```

## `screen_call_type_weekly.py`（拨打模式 × 周）

- **依赖**：`data/conect_rate.json`（`code/sql/15_conect_rate.sql` → `run_all.py`）。
- **输出**：`screenshots/call_type_weekly_connect.png`。
- **结构**：**上下两行**，高度比 **4:3**（`GridSpec` `height_ratios=[4,3]`），**行间约 0.5 cm**（由 `hspace` 换算）；**上行**各 `call_type` **接通率**折线（`connect_rate×100`，纵轴 **%**），**不显示横轴刻度/标签**；**下行**同周 **`call_cnt` 堆叠柱**（自下而上：`预测外呼`→`IVR`→`一键多呼`→`手拨`→`其他`，其余类型按名字接在末尾）；**横轴**为自然周 **`year` + `week_num`**，**升序**（左旧右新），且**仅取数据中最近 12 周**；刻度格式 **`YY-W周`**（如 `26-W1`），**水平**、**16pt**、无底部「自然周…」轴标题；画布 **24×16 英寸**、`dpi=150`，与 **`full_call_eff_rates.png`** 一致。
- **坐标轴**：**纵轴刻度与数字均不显示**（上下两行）；仍保留横向参考网格（仅 **Y 向**）。  
- **标注**：上行每个数据点在**折线点下方**约 **0.2 cm** 处标接通率（如 `12.34%`），字号 **18pt**，**与同系列折线同色**；同一周内多系列时在 0.2 cm 基础上**略增下移/横移**防重叠。下行在**柱段内部**标该段拨打量（**千分位**，过薄段省略以免重叠），字号为**上行的 80%**（约 **14.4pt**），柱内数字带描边。
- **大标题间距**：标题下沿至作图区约 **0.5 cm**（与 `screen_full_call` 的 `TITLE_TO_CHART_GAP_CM` 思路一致）；`hspace` / `bottom` 略调以给柱内标注留高。
- **图例**：**左上角**（`loc='upper left'`）。
- **配色**：`call_type` 使用脚本内**专用高对比色板**（与全局 `SERIES_COLORS` 马卡龙区分）；柱内数字为白字 + 细描边以保证可读性。

```powershell
cd code/screens
python screen_call_type_weekly.py
```

## `screen_precall_task.py`（预测试任务 · 手工/全时 × stage）

- **依赖**：`data/precall_task.json`（`code/sql/16_precall_task.sql` → `run_all.py`）。
- **输出**：`screenshots/precall_task_trends.png`（画布宽度随列数 **`10 + 2.35 × n_col`** 英寸封顶 **44**，高度约 **11～22** 英寸、`dpi=150`）。
- **版式**：**行＝四指标**（接通率 / 呼损率 / 有效时间利用率 / 人工接通中的语音信箱比例）；**列＝「手工」下各 stage + 中间固定 1 cm 空白 + 「全时」下各 stage**（figure 坐标换算，与 **`GAP_CM`** 常量一致）。
- **stage 列顺序**（每个 type 内仅排数据中存在的项）：**RA → RB → RC → RD → S2 → S3 → M2 → M4 → M5**；其余代号排在末尾并按名称排序。
- **折线**：**仅连接源数据中存在的日历点**，不向序列插入日期、不插值；缺日无点，相邻有值日直线相连（跨缺口不代表中间日有观测）。线宽偏细，`chart_theme.polish_ax_lines`；**无图例**；横轴**无刻度**；最左列 **ylabel** 为指标中文名。
- **列标题**：**「手工」「全时」**大号加粗居中于各自列组上方；其下 **每个 stage** 列顶小字加粗。
- **竖向分隔**：相邻 **stage** 列之间 **细**线（`STAGE_DIVIDER_LW`）；**手工块与全时块**（含 1 cm 空隙两侧边界）**粗**线（`PRE_TYPE_DIVIDER_LW`）。
- **标注**：按既有规则（最近点、每 7 天、窗口内最高/最低），见脚本内 `_annotation_days`。

```powershell
cd code/screens
python screen_precall_task.py
```

## `screen_precall_afterkeep.py`（留案 / 留案后外呼 · 手工/全时 × stage）

- **依赖**：`data/precall_afterkeep.json`（`code/sql/17_precall_afterkeep.sql` → `run_all.py`）。
- **输出**：`screenshots/precall_afterkeep_trends.png`（画布宽高规则与 **`screen_precall_task.py`** 同类：`10 + 2.35 × n_col` 宽、`6.8 + 1.55 × 3` 高三行）。
- **版式**：**行＝三指标**——留案率、留案后案均拨次、留案后接通率；列、分隔线、折线规则与 **`precall_task_trends.png`** 一致（见上节）。

```powershell
cd code/screens
python screen_precall_afterkeep.py
```

## `screen_case_stock.py`（人均库存看板）

- **依赖**：`data/case_stock.json`（由 `code/sql/13_case_stock.sql` 经 `run_all.py` 导出）。
- **输出**：`screenshots/case_stock_9grid.png`（画布 **24×16 英寸**、`dpi=150`，与 **`full_call_full_rates.png`** 等 `screen_full_call` 产出一致，便于飞书插图对齐）。
- **结构**：3 行 × 3 列——行：**人均库存 / 案件数 / 分案人数**；列：**非预测外呼 / 预测外呼 / 整体**。
- **柱**：前两列为按 **`case_group_type`** 堆叠（顺序 S1→S2→S3，组内 RA→RB→RC→RD）；**整体**列在案件数/分案人数行按 **`col_type`** 两叠；人均库存行整体列为「非预测 / 预测」两叠，高度取自 **第 1、2 列折线序列**（分列 `line_metrics` 人均库存）。
- **折线**：仅 **第一行人均库存** 绘制，透明度约 50%；**第三列**折线点为 **不拆分 `col_type`** 的整体 **`line_metrics`**（与该行第三列表格一致）；第二、三行不画折线。
- **表格**：每个子图下方一行表，填对应折线各月取值（四舍五入整数、完整数字无 k/M）；第三列第一行表 = 整体人均库存折线，与图中红线一致。
- **坐标**：图上不显示月份（表格表头为月份）；同一行内 **第 1、2 列共用 Y 轴量程**，第 3 列独立；左轴无刻度。

单独调试：

```powershell
cd code/screens
python screen_case_stock.py
```

## 输出目录与依赖

- 所有 PNG 默认写入项目根 **`screenshots/`**（脚本内 `Path(__file__).resolve().parent.parent.parent / "screenshots"`）。
- **Python**：`matplotlib`、`numpy`；`screen_grp.py` 另需 **`pandas`**。
- **字体**：需系统中文字体（如 Microsoft YaHei / SimHei / DengXian），否则标题可能方块字。

## 批处理（可选）

同目录提供 **`run_all.bat`** / **`run_all.sh`**、以及 **`run_all_screens.py`**（动态发现，新增 `screen_*.py` 会自动纳入）。**首选 `run_all_screens.py`**。

- **全量**（不带参数）：开始前 **一次性删除 `screenshots/*.png`**，各 `screen_*.py` **不再各自 cleanup**，只覆盖写入。  
- **部分脚本**（如 `run_all_screens.py screen_grp`）：**不**做全量删除，只覆盖本次脚本生成的文件。  
- **`--no-clean`**：全量跑图时也跳过删除（保留目录里已有 PNG，仅覆盖同名输出）。

## 更多文档

- [`GRP_ROBUSTNESS.md`](GRP_ROBUSTNESS.md) — GRP 催收员缺失与对齐逻辑  
- [`MIGRATION_NOTES.md`](MIGRATION_NOTES.md) — 迁移备忘  

## 最后更新

2026-05-02 — 重写为与当前脚本一致；修正 M0/GRP 文件名；补充 `screen_m2_m6`、`screen_case_stock` 与 `run_all_screens` 推荐用法。  
2026-05-03 — 新增 **`screen_full_call.py`**（`full_call_full_rates.png` / `full_call_eff_rates.png`）及本节说明。  
2026-05-03 — **`screen_full_call.py`** 增加 **`full_call_avg_calls_per_case.png`**（本人 / 非本人 / 整体案均拨打，次/案与周环比差）。  
2026-05-04 — 增加 **`full_call_avg_dur_per_case.png`**（案均有效通时，秒/案）；生成顺序为满频→案均拨打→案均通时→接通率。  
2026-05-04 — 新增 **`screen_call_type_weekly.py`** → **`call_type_weekly_connect.png`**（`15_conect_rate` / `conect_rate.json`）。  
2026-05-03 — **`case_type` 横轴排序** 改为按末尾档位解析 + **M 档位数值序**（M4+ 在 M5+ 前）；三张图生成顺序为 **满频→案均→接通**。  
2026-05-04 — 飞书：`generate_feishu_report` 对正文 **`{…dif}`** 做「上升/下降」加粗着色（**`rate_prin_od_dif` / `rate_cnt_od_dif` 颜色与催回类相反**）；同一段可连续 **`[*.png][*.png]`** 占位；详见根目录 **wkrpt** Skill。  
2026-05-06 — 新增 **`screen_precall_task.py`** → **`precall_task_trends.png`**（`16_precall_task` / `precall_task.json`）；版式、分隔线与 stage 顺序见本节。  
2026-04-30 — 新增 **`screen_precall_afterkeep.py`** → **`precall_afterkeep_trends.png`**（`17_precall_afterkeep` / `precall_afterkeep.json`）；三行指标对齐 precall_task 版式。
