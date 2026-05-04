---
name: wkrpt
description: 周报自动化 — SQL→JSON→（可选行数检查）→校验→图表→（可选飞书 Docx：默认优先 **知识库 wiki 节点整篇复制** 模板 `WHruwVACAi8nWPkXYgQcrLhHnFb` 所在空间，以保留标题多级编号、**高亮块 / 引用** 等原生样式；需应用对该知识空间具备可编辑级权限，否则常见 131006 并回退云盘复制或空白文档克隆；`FEISHU_REPORT_USE_CLONE=1` 强制克隆）。`analyze_template.py` 与 `generate_feishu_report.py` 的 Wiki URL 须保持一致。飞书插图按磁盘原文件字节上传；replace_image 显式传宽高（PNG IHDR / 可选 Pillow），避免开放平台偶发 100px 兜底导致极小图；正文 `*dif` 占位符可渲染为「上升/下降」加粗着色（`rate_prin_od_dif`/`rate_cnt_od_dif` 颜色与催回类相反）。首次须输出前置条件表并按 A～I 分项自检；可选 Git 同步前须让用户选择 GitHub / Gitee / 两者。不含 HTML 预览方案。
---

# 周报自动化（wkrpt）

端到端工作流：**数仓 SQL（MCP HTTP）→ `data/*.json` → 数据校验 → `screenshots/*.png` →（可选）飞书文档克隆与插图**。支持 M0 成熟度、月同期与 GRP 同期对齐等业务逻辑。

## 路径约定（必读）

- **项目根目录**：同时包含 `code/`、`data/`、`.claude/`（或 `.cursor/`）的仓库根（与盘符、文件夹名无关）。
- 下文 **`code/...`、`data/`、`screenshots/`** 均相对项目根。
- 本 Skill 主路径：**`.claude/skills/wkrpt.md`**；文中「相对 Skill 的链接」使用 **`../../...`**。
- **Cursor Rules / Agent Skills**：仓库内应同时保留 **`.claude/skills/wkrpt.md`**（主编辑源）与 **`.cursor/skills/wkrpt/SKILL.md`**（同文，便于 Cursor 拉规则/技能）。**不要**只改其中一份：改完后在项目根执行 **`python scripts/sync_wkrpt_skills.py`**（把主源覆盖复制到 `.cursor/...`），再一并 `git add` 提交。
- **为何以前 Gitee 里没有 `.cursor` 下 Skill**：根目录 `.gitignore` 曾使用 **`.cursor/`** 整目录忽略，Git 不会跟踪其下任何文件。现已改为「忽略 `.cursor` 下其余内容，但**例外跟踪** `skills/wkrpt/SKILL.md`」（见 `.gitignore` 中 Cursor 段注释）。

## 前置使用条件

### `run_all.py` 与 Cursor MCP

- `code/python/01_execute_sql/run_all.py` 读取 **`%USERPROFILE%\.cursor\mcp.json`**（macOS/Linux：`~/.cursor/mcp.json`），且存在 **`mcpServers.sql`**。
- `sql` 节点需含 **`url`**、**`headers`**（至少 **`X-API-Key`**，值非空）。无效或未配置时步骤 1 会失败（如 HTTP 401）。
- **禁止**在对话中粘贴完整 API Key 或 `app_secret`。

### 分项检查体系（A～I：首次在本环境跑周报时必须逐项执行）

**通用**：路径类检查前 `cd` 到项目根；Python 优先 `python`，无效再试 `python3`。

| 序号 | 检查动作 | ✅ | ❌ | ⚠️ |
|------|----------|----|----|-----|
| **A** | 项目根是否存在 `code/sql`、`code/python`、`data`；若无 `screenshots` 则**创建空目录** `screenshots`。 | 均存在 | 缺 `code/sql` 或 `data`：当前目录不是项目根 | — |
| **B** | `python --version` / `python3 --version` | 主版本 ≥3，建议次版本 ≥10 | 无命令或 &lt;3.8 | 3.8～3.9：可继续但建议升级 |
| **C** | `python -c "import requests, matplotlib, numpy, pandas; print('ok')"` | 打印 `ok` | `ModuleNotFoundError` | — |
| **D** | `~/.cursor/mcp.json` 存在；JSON 含 `mcpServers.sql`，内有非空 **`url`**、**`headers`**，且 **`headers` 含键 `X-API-Key`** 且值非空（勿打印值） | 结构满足 | 缺文件/键或值为空 | — |
| **E** | 在 D 为 ✅ 下：建议项目根执行 `python code/python/01_execute_sql/run_all.py --list`，无 401；若 `--list` 不触发鉴权，可结合「本会话或用户确认近期步骤 1 已成功」标 ✅，否则对「密钥是否真能查数」标 ⚠️；若 `--list` 即 401 → ❌ | 非空 Key +（`--list` 成功或已证实可查数） | 明确 401 | 仅配置就绪、尚未实测查数 |
| **F** | 对 `mcpServers.sql.url` 的 host 做 `requests.get(..., timeout=10)` 等**连接层**探测（200/401/405 均算可达） | 可达或用户确认代理 | 超时、`ConnectionError`、DNS 失败 | 企业网策略特殊时说明 |
| **G** | **仅飞书（可选）**：`python -c "from PIL import Image; print('ok')"` | 成功 | 无 Pillow 时步骤 7 仍可：**PNG 用文件头读宽高**；仅非标准/无法解析尺寸时需 Pillow | 不做飞书 → **N/A** |
| **H** | **仅飞书**：项目根 `feishu_app.json` 存在，且含非空 `app_id`、`app_secret`（勿输出 secret） | 满足 | 复制 `feishu_app.example.json` 填写 | 不做飞书 → **N/A** |
| **I** | **推荐**：matplotlib 是否发现中文字体（如 Microsoft YaHei / SimHei / DengXian） | 命中至少一种 | 可能乱码 | 无法枚举 → ⚠️，步骤 5 后人工看一张 PNG |

### 前置条件检查表（首次必须输出并填空）

| 序号 | 条件 | 是否必需 | 用于哪些步骤 | 不满足时典型现象 | 是否满足 | 理由与处理方法 |
|------|------|----------|----------------|------------------|----------|----------------|
| A | 工作区为项目根 | 必需 | 全部 | 找不到 SQL 或 data |  |  |
| B | Python 3（建议 3.10+） | 必需 | 全部 | 无 python |  |  |
| C | requests / matplotlib / numpy / pandas | 必需 | 1～5 | `ModuleNotFoundError` |  |  |
| D | `~/.cursor/mcp.json` → `mcpServers.sql` + url + `X-API-Key` | 必需 | 步骤 1 | 启动即失败 |  |  |
| E | Key 有效可查数 | 必需 | 步骤 1 | HTTP 401 |  |  |
| F | 网络可达 MCP | 必需 | 步骤 1 | 超时 |  |  |
| G | `Pillow`（可选，非 PNG 或无法从头解析尺寸时的兜底） | 仅飞书·可选 | 步骤 7 | 标准 PNG 可不装 |  |  |
| H | `feishu_app.json` | 仅飞书 | 飞书脚本 | 无凭证 |  |  |
| I | 中文字体 | 推荐 | 步骤 5 | 乱码 |  |  |

**阻塞规则**

- **A～D、B、C** 任一 **❌**：不执行步骤 1～5，只给修复指引。
- **E** 为 **❌**：同上。
- **E** 为 **⚠️**、其余必需为 **✅**：可跑步骤 1；若首次 `submit_query` 仍失败，停止并让用户轮换 Key/权限。
- **F** 为 **❌**：不跑步骤 1。
- **H**：要做飞书时不得为 **❌**；**G**（Pillow）可选，标准 PNG 插图不依赖 Pillow；不做飞书标 **N/A**。

### 与用户说明的简短话术

> 首次在本机跑 wkrpt：下面是前置条件检查表。若有 ❌ 请先按「理由与处理方法」修复；⚠️ 表示有风险或待后续步骤确认。

---

## 一键速查（均在项目根执行）

```powershell
# 0) 若刚编辑了 .claude/skills/wkrpt.md，先同步 Cursor 端再提交
python scripts/sync_wkrpt_skills.py

# 1) SQL → JSON（并发轮询 MCP，引擎 SMART，dataSourceId=1）
python code/python/01_execute_sql/run_all.py

# 2.5 可选：rowCount 与 rows 长度一致性
python code/python/025_check_rowcount/check_rows.py

# 3) 业务校验（主实现；screens 下为兼容入口）
python code/python/03_validate_data/validate_data.py

# 5) 全部图表（自动发现 code/screens/screen_*.py）
python code/screens/run_all_screens.py

# 5.5 推荐（飞书前）：拉取 wiki 模板结构，比对占位符与 screenshots/*.png，输出 template_analysis.json
python code/python/055_analyze_template/analyze_template.py

# 7) 可选：飞书周报（需 H/G；会打开浏览器到新文档）
python code/python/06_generate_feishu/generate_feishu_report.py
```

---

## 凭证与交接（飞书）

主流程（SQL→图表）**不依赖**飞书。

1. 根目录复制 `feishu_app.example.json` → `feishu_app.json`，填写 `app_id`、`app_secret`（与开放平台应用一致）。
2. `feishu_app.json` 已被 `.gitignore` 忽略；交接用安全渠道单独传递。
3. 可选环境变量 `FEISHU_APP_ID`、`FEISHU_APP_SECRET`（与文件并存时的优先级以 `feishu_creds.py` 为准）。
4. `get_token.ps1.example` 可复制为本地 `get_token.ps1`（勿提交含密钥脚本）。

---

## 核心流程（步骤编号与仓库脚本一致）

### 步骤 1：执行 SQL 并落盘 JSON

- 脚本：`code/python/01_execute_sql/run_all.py`
- 行为：读取 `code/sql/` 下**全部** `*.sql`（当前 **15** 条，含 `14_full_call.sql` → `full_call.json`、`15_conect_rate.sql` → `conect_rate.json`），经 MCP **`tools/call`** 调用 **`submit_query` → `get_query_status` → `get_query_result`**，写入 `data/<basename>.json`（文件名形如 `NN_xxx.sql` 时去掉数字前缀 → `xxx.json`，与脚本内规则一致）。
- 常用：`--list` 列 SQL；`python run_all.py 01_s_class_all` 单跑一条。
- SQL 使用 Hive 侧动态日期，一般**无需手改日期**。

### 步骤 2：JSON 形态

标准结构含 **`metadata`**（至少建议含 `data_fetch_date`，供 M0 成熟度）、`header`、`rows`、`rowCount`。`run_all.py` 会写入 `query_time`、`query_id`、`data_source` 等（以实际输出为准）。

### 步骤 2.5（可选）：行数一致性

- `code/python/025_check_rowcount/check_rows.py`：检查各 JSON 的 `rowCount` 与 `len(rows)` 是否一致。

### 步骤 3：数据验证

- **主脚本**：`code/python/03_validate_data/validate_data.py`  
  - 先校验「SQL 集合与 `data/*.json` 集合」是否对齐（缺 JSON 会 hard fail）。  
  - 按注册表对 S/M0/M1/GRP/人均工时、**`case_stock.json`（九宫格）**、**`full_call.json`（全量外呼）** 等做时间窗、回款率或列完整性校验（细节见脚本内注释与 `VALIDATORS`）。
- **兼容入口**：`code/screens/validate_data.py`（内部转调上述主脚本）。

### 步骤 4：确认继续

验证失败时**暂停**，输出明细，待用户确认是否继续（不建议跳过校验直接画图）。

### 步骤 5：生成图表

- **编排脚本**：`code/screens/run_all_screens.py`  
  - 自动发现 `code/screens/screen_*.py`，子进程独立运行，超时 300s/脚本。  
  - `python code/screens/run_all_screens.py --list` 列出脚本；可传过滤参数只跑其一（见脚本 `--help`）。
- **输出目录**：项目根 `screenshots/`（各 `screen_*.py` 内定义文件名）。
- **图表数量**：以 `run_all_screens.py` 当次汇总为准（人均模块最多 **3** 张 PNG，取决于 `data/` 中是否存在对应 JSON）。含 **M2 / M2–M6**（`screen_m2_m6.py`，4 张）、**`screen_case_stock.py`（1 张九宫格）**、**`screen_full_call.py`（4 张）**、**`screen_call_type_weekly.py`（1 张）** 等后，`screenshots/` 常见合计约 **40～55** 张；**飞书 wiki 当前模板**插图占位约 **38** 处（以步骤 **5.5** 的 `template_analysis.json` 为准）。

### 步骤 6（可选）：Git 推远端

见文末 **「Git 同步」**。推送前须让用户选择 **仅 GitHub / 仅 Gitee / 两者**。

### 步骤 5.5（推荐）：飞书模板预检（生成文档前）

- **脚本**：`code/python/055_analyze_template/analyze_template.py`
- **依赖**：与步骤 7 相同（`feishu_app.json`、`requests`）；需可访问飞书开放平台。
- **行为**：读取 wiki 模板（**须与** `generate_feishu_report.py` 的 `main()` 内 wiki URL **一致**；当前默认 **`https://fintopia.feishu.cn/wiki/WHruwVACAi8nWPkXYgQcrLhHnFb`**，见 `code/python/055_analyze_template/analyze_template.py` 顶部 `WIKI_URL`），汇总块结构、`{参数}`、`[*.png]` 占位符，并核对 **`screenshots/` 是否缺文件**。
- **产出**：项目根 **`template_analysis.json`**（便于 diff / 排查模板变更）。**注意**：该脚本**不**覆盖仓库中的 `template_blocks.json`（若存在，多为历史导出备份；以 `template_analysis.json` 为本次分析结果为准）。

### 步骤 7（可选）：飞书 Docx 周报

- **脚本**：`code/python/06_generate_feishu/generate_feishu_report.py`
- **依赖**：步骤 1～5 已完成；**建议先跑步骤 5.5**，确认占位图齐全；`feishu_app.json`；**`requests`（插图上传使用内置 multipart：`files` + `data`，无需 `requests_toolbelt`）**；可选 **`Pillow`**（仅在无法从 PNG 文件头解析宽高时起兜底作用）。
- **生成策略（默认优先「整篇复制模板」）**  
  脚本会**先尝试保留模板文档级样式**（含客户端侧的 **标题多级编号**、有序列表样式等），失败后再回退到「空白文档 + 逐块克隆」。
  1. **知识库模板（URL 含 `/wiki/`）**  
     - 调用 **`wiki/v2/spaces/{space_id}/nodes/{node_token}/copy`** 复制节点；请求体带 **`target_space_id`**，若有 **`parent_node_token`** 则一并传入，复制到与模板相同的知识空间目录。  
     - **权限**：应用需对该知识空间具备**可编辑级**能力；否则常见 **`131006 wiki space permission denied`**。须在知识库中将应用加入为成员，并在开放平台开通 **`wiki:node:copy` / `wiki:wiki`** 等（详见 [知识库常见问题](https://open.feishu.cn/document/ukTMukTMukTM/uUDN04SN0QjL1QDN/wiki-v2/wiki-qa)）。**模板若迁到新 wiki 空间，须在该空间重新授权**；成功时日志含 **`[copy] 已通过知识库复制模板（保留原生编号）`**。  
     - **样式**：整篇复制可保留飞书原生 **高亮块、引用、标题多级编号** 等；若回退到空白文档 + 逐块克隆，则 API 不继承文档级编号，且未在 `BT_MAP` 的块类型可能丢失（见步骤 7 回退说明）。  
     - 复制成功后：按原逻辑删除「插入参数」说明段、将 **`[*.png]`** 文本块替换为图片块并上传、`PATCH` 替换各块中的 **`{参数}`**（含引用块等文本类；高亮块内子块递归处理）。  
  2. **云盘兜底**  
     - 若配置了 **`FEISHU_DST_FOLDER_TOKEN`**，且能从 **`drive/v1/files/{模板token}`** 读到 **`parent_token`**，则尝试 **`drive` 复制接口**（explorer v2 / v1）再在副本上编辑。  
  3. **回退：`FEISHU_REPORT_USE_CLONE=1` 或上述复制均失败**  
     - **`create_document` 空白文档 + `add_children` 按模板结构重建**。此时 **API 不会继承文档级「标题编号」样式**；脚本**不会**再往标题正文里拼接数字序号（避免与飞书自带编号冲突）。  
     - 克隆路径已实现：**`heading4`～`heading9`（block_type 6～11）** 与 **`ordered.style.sequence`**（缺省时补 `"auto"`）、文本类块 **`deepcopy`** 载荷等，尽量减少列表序号等字段丢失。
- **行为概要（与策略无关的共性）**  
  - 正文中 **`{占位符}`** 与 **`[xxx.png]`** 分别替换为计算参数与 `screenshots/` 上图（上传后 `replace_image`）。  
  - **插图字节与尺寸**：上传 **`screenshots/` 内文件的原始字节**，不做缩放、不重新编码。`replace_image` **必须**携带 **`width`、`height`（像素）** 与素材一致（优先读 PNG **IHDR**，否则尝试 Pillow）；否则开放平台在「检测失败」时可能将块兜底为 **100×100px**，表现为**偶发整图极小**。对齐方式当前固定 **`align: 2`（居中）**。  
  - **同一段落内多个 `[*.png]`**（如 `[a.png][b.png]` 紧挨在同一文本块、中间可空白）：按从左到右顺序识别，**一次删块插入多张图**，避免只认「整段恰好一对括号」导致漏图。  
  - 默认新文档标题：**`催收周报（yyyy-MM-dd）_{Unix时间戳}`**（未显式传入 `output_title` 时，见 `generate_report`），减少与历史副本重名。  
  - **`{参数}` 富文本替换（复制模式 `dfs_patch` 与克隆 `_clone_elements` 共用 `_param_replace_text_runs`）**  
    - 占位符名以 **`dif` 结尾**（如 `wk_colrate7d_dif`、`mth_ind1_ratio_dif`）：若替换值可解析为**数字**（去 `%`、逗号，支持 Unicode 负号），则输出 **`上升` 或 `下降` + 原参数字符串**（**≥0 → 上升**，**&lt;0 → 下降**）；**紧跟占位符后的字面量 `pp`（若模板中有）**一并纳入同一 `text_run`，**加粗**并着色：**≥0 绿（`text_color` 枚举 4）**、**&lt;0 红（枚举 1）**。  
    - **例外（逾期率差分，与催回类「好绿坏红」相反）**：**`rate_prin_od_dif`**、**`rate_cnt_od_dif`** 仍为上述「上升/下降」文案，但颜色为 **≥0 红、&lt;0 绿**。  
    - **非数值**的 `*dif`：不做上升/下降、不着色，仅普通文本替换。  
    - **不以 `dif` 结尾**的参数：普通替换，继承原 `text_run` 样式。  
  - 运行开始会打印 **`[doc-guide]`** 与飞书 block/Markdown 差异相关的**自检说明**（与 Cursor 内 **feishu-cli-doc-guide** Skill 对齐思路）；模板中请勿依赖本脚本不支持的 Markdown 围栏（如 mermaid）作为唯一呈现手段。
- **Wiki 地址**：`generate_feishu_report.py` → `main()` 内默认 **`https://fintopia.feishu.cn/wiki/WHruwVACAi8nWPkXYgQcrLhHnFb`**。更换模板时请同步修改 **`code/python/055_analyze_template/analyze_template.py`** 的 **`WIKI_URL`**，再跑步骤 5.5。
- **说明**：飞书 **Docx 不支持嵌入自定义 HTML 整页**；周报以 **飞书原生块 + 上传 PNG** 为准，**无**仓库内 HTML 镜像生成步骤。**标题编号**：要与模板完全一致，依赖 **复制模板** 成功；仅克隆模式下勿指望客户端多级标题编号自动出现。

---

## 数据映射

### SQL → JSON（`run_all.py` 命名规则）

| SQL 文件 | 输出 JSON | 说明 |
|----------|-----------|------|
| `01_s_class_all.sql` | `s_class_all.json` | S 类 ALL |
| `02_s_class_new.sql` | `s_class_new.json` | S 类 NEW |
| `03_s_class_mtd.sql` | `s_class_mtd.json` | S 类 MTD |
| `04_m1_assignment_repayment.sql` | `m1_assignment_repayment.json` | M1 分案回款 |
| `05_m0_billing.sql` | `m0_billing.json` | M0 日账单（**含 metadata.data_fetch_date**，成熟度核心） |
| `06_m0_billing_grouped.sql` | `m0_billing_grouped.json` | M0 分组（首逾等） |
| `07_grp_collector.sql` | `grp_collector.json` | GRP 催收员/区域 |
| `08_avg_eff_worktim.sql` | `avg_eff_worktim.json` | 人均有效工时（整体） |
| `09_avg_eff_call_worktim.sql` | `avg_eff_call_worktim.json` | Call 维度（有 SQL 才有 JSON） |
| `10_avg_eff_wa_worktim.sql` | `avg_eff_wa_worktim.json` | WA 维度（有 SQL 才有 JSON） |
| `11_M2_class_all.sql` | `M2_class_all.json` | M2 单类型累积回款（整体） |
| `12_M6_class_all.sql` | `M6_class_all.json` | M2–M6 账龄段（逾期 31–180 天）累积回款 |
| `13_case_stock.sql` | `case_stock.json` | 人均库存 / 分案人力（含 `mth`、`case_group_type`、`col_type`，供九宫格大屏） |
| `14_full_call.sql` | `full_call.json` | 生产力周表：`tmp_export.case_productivity_2025`，**`year`+周+`concat(case_type,'-',rank_type)` 作 `case_type`**，含 **`lag`/周环比 `*_dif`**；出图 **`screen_full_call.py`**（详见 `code/sql/README.md`） |
| `15_conect_rate.sql` | `conect_rate.json` | 拨打模式周度：`tmp_export.col_phone_quality`，**`year`+`week_num`+`call_type`**；出图 **`screen_call_type_weekly.py`** |

历史 Query ID 可参考 `code/sql/README.md`，**以线上查询计划为准**，不必与文档表逐字一致。

### JSON → 图表脚本

| 脚本 | 主要数据源 | 输出示例 | 张数（约） |
|------|------------|----------|-----------|
| `screen_s_class.py` | `s_class_*.json` | `recovery_rate_*.png`、三张对比表 `recovery_rate_S_table_*.png`（样式见 `chart_theme`：`TABLE_AX_BBOX`、`set_screen_table_title`） | 15 |
| `screen_m1.py` | `m1_assignment_repayment.json` | `assignment_repayment_*.png`（3 柱线 + `assignment_repayment_table_*.png` 三表） | 6 |
| `screen_m0.py` | `m0_billing.json`、`m0_billing_grouped.json` | `m0_*.png` | 8 |
| `screen_grp.py` | `grp_collector.json` | `grp_*.png` | 12 |
| `screen_avg_eff_worktime.py` | `avg_eff_worktim.json` 等（存在则画） | `avg_eff_worktime.png`、`avg_eff_call_worktime.png`、`avg_eff_wa_worktime.png` | 1～3 |
| `screen_m2_m6.py` | `M2_class_all.json`、`M6_class_all.json` | `recovery_rate_M2_ALL.png`、`recovery_rate_M2_table_ALL.png`、`recovery_rate_M6_ALL.png`、`recovery_rate_M6_table_ALL.png`（风格对齐 S 类：组合图 + 对比表） | 4 |
| `screen_case_stock.py` | `case_stock.json` | `case_stock_9grid.png`（3×3 人均库存 / 案件数 / 分案人数 × 非预测 / 预测 / 整体；下行表格填折线数值） | 1 |
| `screen_full_call.py` | `full_call.json` | `full_call_full_rates.png`、`full_call_avg_calls_per_case.png`、`full_call_avg_dur_per_case.png`、`full_call_eff_rates.png`（满频 / 案均拨打 / 案均通时 / 接通率，最近 5 周；见 `code/screens/README.md`） | 4 |
| `screen_call_type_weekly.py` | `conect_rate.json` | `call_type_weekly_connect.png` | 1 |

**PNG 总量**：以 `run_all_screens.py` 当次汇总为准；在含 M2/M6、人均、`case_stock`、**`full_call` 四图** 与 **`call_type_weekly_connect`** 等前提下 **`screenshots/`** 常见 **40～55** 张；**飞书模板**插图数以 **`template_analysis.json`** 为准（当前约 **38**）。

---

## 关键业务逻辑（摘要）

### M0 成熟度与月同期

- **数据获取日**：优先 `m0_billing.json` → `metadata.data_fetch_date`；缺失时代码会按「最后一笔有效账单」启发式推断（不如 metadata 准）。
- **成熟期示例**：逾期 1d 口径成熟 **1** 天；7d 催回率成熟 **8** 天；30d 催回率成熟 **31** 天（与 `screen_m0.py` 一致）。
- **月同期**：标题含「月同期」的图，各月截取到**与最新月相同的月内日**（如统一截至 19 日），避免最新月天数不足稀释对比。

### GRP 同期

- **作图口径**：`screen_grp.py` 在作图前会按 `mth` 排序，**只保留数据中最近的两个自然月**做对比与出图；若 SQL 返回多于 2 个月，较早月份会被丢弃（仅影响图表，不改变 `grp_collector.json` 文件本身）。
- 历史月与最新月对齐到**相同日切**（见 `process_grp_data`），减轻月末效应。

### GRP 催收员集合变化

- 展示两个月并集；排序侧以**最新月**出现过的催收员为主；缺失补零（详见 `GRP_ROBUSTNESS.md`）。

### 飞书插入参数（`generate_feishu_report.py` 计算项摘要）

除日期 **`mm` / `mm1` / `mm2` / `DD` / `DD1`** 与逾期率、周/月催回率等外，若模板含 **合并/非合并 7d 月催回**、**IND1 占比**，脚本从 **`m0_billing_grouped.json`** 与既有月催回逻辑对齐计算：

| 占位符 | 含义（摘要） |
|--------|----------------|
| `mth_colrate7d_ind0` / `mth_colrate7d_ind0_dif` | 非合并用户 7d 月催回率及环比差（与 `m0_collection_rate_7d_30d_monthly_ind0.png` 口径一致） |
| `mth_colrate7d_ind1` / `mth_colrate7d_ind1_dif` | 合并用户 7d 月催回率及环比差（与 `ind1` 图一致） |
| `mth_ind1_ratio` / `mth1_ind1_ratio` / `mth_ind1_ratio_dif` | 当前月 / 上一月 IND1 金额占比（%）及差（百分点，非 `dif` 着色规则时仍可能以 `dif` 结尾走着色逻辑） |

审计用：`python code/python/06_generate_feishu/_audit_params.py`（仅打印，不发飞书）。

---

## 图表与样式要点

- **S 类**：3 口径 × 多 case_type；组合图与**对比纯表**（双行表头 S1/S2/S3 与下方月份列 **1–3 / 4–6 / 7–9** 对齐）；MTD 回款率允许 &gt;100%。
- **M1**：整体 / 新案 / 老案各一张柱线组合图，另有三张与 S 类 `recovery_rate_S_table_*` 风格一致的**纯表图**（日 1–31 × 最近三月累积回款率）。
- **M0**：逾期率（月/周）、催回率（周/月，7d/30d）、首逾占比、分首逾催回等；周起始与成熟度逻辑与数据脚本一致。
- **GRP**：多 case_type 柱状/折线、配色与标签防叠处理。
- **人均工时**：整体 / Call / WA 三套数据独立成图（数据存在才出图）。
- **M2 / M2–M6**：`screen_m2_m6.py`；分母 **assigned_principal + overdue_added_principal**；多月堆叠柱 + 双轴累积回款率折线 + 日 1–31 × 最近三月对比表。
- **case_stock**：`screen_case_stock.py`；堆叠顺序 **S1→S2→S3**，组内 **RA→RB→RC→RD**；第一行第三列 **堆叠**用第 1、2 列「折线」人均库存序列，**红线与该行第三列表**为 **不拆分 `col_type`** 的整体 `line_metrics`（与柱总高度不一定相等）；第二、三行仅柱、无折线；详见 `code/screens/README.md`。
- **full_call**：`screen_full_call.py`；**最近 5 周**；**每 `case_type` 单独折线**（不跨类）、**每类每周一柱**为 `*_dif`；**最近一周无数据则剔除该类型**；**上图**最近 3 周标具体值（满频/接通为 **%**，案均拨打为**次/案**，案均通时为**秒/案**）无框无底、**下图**最近 3 周标环比（率类为 pp，案均类为原单位差）；**无图例**；**`case_type` 写在轴框上方**免挡标注；**纵轴无刻度字**、**仅第三带下图**显示横轴周标签；详见 `code/screens/README.md`。

---

## 注意事项

- **勿随意改 SQL** 中的日期与窗口逻辑，除非业务方确认；改完需重跑 1→3→5。
- **必须**保证 `m0_billing.json`（及 grouped）带正确 **`metadata.data_fetch_date`**，否则 M0 月同期与成熟度可能偏差。
- 流水线顺序：**1 →（2.5）→ 3 → 5 →（5.5）→（7）**；跳过 3 可能把脏数据画进 PNG；模板或插图有变动时务必 **5.5** 再 **7**。

---

## 故障排查（简表）

| 现象 | 常见原因 | 处理 |
|------|----------|------|
| 步骤 1 401 | Key 失效或未写入 mcp.json | 更新 `X-API-Key`，再 `--list` / 重跑 |
| 步骤 3 报缺 JSON | 未跑全 `run_all.py` | 重新执行步骤 1 |
| M0 图异常 | `data_fetch_date` 错或缺失 | 检查 metadata，必要时重拉数 |
| 中文方块 | 无中文字体 | 安装雅黑/黑体等 |
| 飞书 429 | API 限流 | 脚本内已有退避；稍后重试 |
| 飞书占位图未替换 | `screenshots` 缺对应 PNG 或文件名与模板 `[...]` 不一致 | 对齐文件名或补跑步骤 5；跑 **5.5** 看 `template_analysis.json` 中 `missing_files` |
| 同一段两个 `[*.png]` 未替换 | 旧版仅识别「整段 = 单一对括号」 | 已支持同块多图；仍异常则将两图拆成两个独立段落块 |
| 飞书里某张图偶发「突然变得极小」 | 旧逻辑仅传 `replace_image.token`，开放平台宽高检测失败时兜底 **100px** | 当前脚本已：**原文件上传 + 显式传 width/height**；仍异常则检查模板是否把大图放在**极窄分栏**（列宽导致视觉上缩小） |
| 日志 `[copy] wiki copy … 131006 permission denied` | 应用无知识库编辑/复制权限 | 将应用加入目标知识空间成员并开通 `wiki:node:copy` 等；见开放平台 wiki 文档 |
| 日志 `[copy] …跳过复制模式` 后走克隆 | 复制失败（权限或文件夹 token） | 接受克隆（标题编号不继承），或配置 **`FEISHU_DST_FOLDER_TOKEN`** / 修好 wiki 权限后再跑 |
| 强制始终用空白文档克隆 | 调试或与复制路径无关 | 环境变量 **`FEISHU_REPORT_USE_CLONE=1`** |

---

## 执行输出示例（节选）

```
[第1步] 执行 SQL…（`code/sql/*.sql` 全部）
[第2步] 写入 data/*.json，metadata.data_fetch_date: …
[第3步] 验证通过 / 或列出失败项
[第5步] run_all_screens：各 screen_*.py 成功，screenshots PNG 数量汇总
```

---

## 相关文件与可选工具

| 用途 | 路径 |
|------|------|
| `code/` 总索引 | `../../code/README.md` |
| SQL 说明 | `../../code/sql/README.md` |
| 图表模块说明 | `../../code/screens/README.md` |
| GRP 鲁棒性 | `../../code/screens/GRP_ROBUSTNESS.md` |
| 飞书模板预检（推荐每次发文档前） | `../../template_analysis.json`（运行 `code/python/055_analyze_template/analyze_template.py` 生成） |
| 飞书块结构历史/大块快照（可选） | `../../template_blocks.json`（若仓库内有，非 analyze 脚本默认产出） |

---

## 单步手动执行（调试）

```powershell
cd code/screens   # 或始终在根目录用 python 绝对路径调用
python screen_s_class.py
python screen_m1.py
python screen_m0.py
python screen_grp.py
python screen_avg_eff_worktime.py
python screen_m2_m6.py
python screen_case_stock.py
python screen_full_call.py
python screen_call_type_weekly.py
```

---

## Git 同步到远端（GitHub / Gitee）

- **不要**提交：`data/**/*.json`、`screenshots/**`、密钥、`feishu_app.json` 等（以根目录 `.gitignore` 为准）；勿 `git add -f` 强行纳入。
- **推送前自动 `git add -A`（可选）**：仓库提供 **`.githooks/pre-push`**，在项目根**一次性**执行 **`powershell -ExecutionPolicy Bypass -File scripts/install_git_hooks.ps1`**（或手动 `git config core.hooksPath .githooks`）。之后每次 **`git push`** 会先 **`git add -A`**（仍遵守 `.gitignore`，不会加入 data/screenshots/密钥文件）；若此时相对 **`HEAD` 仍有未提交变更，hook 会阻断 push**，提示你先 **`git commit`**——仅有 add 无法把新文件推上远端。
- **任何 `git push` 前**（人机协作场景）仍建议确认：**仅 origin（GitHub）/ 仅 gitee / 两者依次 push**。
- 远程名常见：`origin` → GitHub，`gitee` → Gitee；`git remote -v` 查看。分支名以本地为准（多为 `main`）。

---

## 更新记录

- **2026-05-04（飞书 Docx 文本与模板）**：步骤 7 补充 **`*dif` 上升/下降 + 加粗着色**、**`rate_prin_od_dif` / `rate_cnt_od_dif` 颜色与催回类相反**、**同段多 `[*.png]`**、**默认标题** `催收周报（日期）_{Unix时间戳}`；关键业务增加 **`m0_billing_grouped` 派生占位符** 表；故障表增加多图说明；步骤 5 / PNG 总量区分 **全量出图张数** vs **wiki 模板插图位**（以 `template_analysis.json` 为准）。
- **2026-05-03（`.cursor` Skill 纳入 Git + 同步脚本）**：`.gitignore` 取消对 **整个** `.cursor/` 的无差别忽略，改为跟踪 **`.cursor/skills/wkrpt/SKILL.md`**；新增 **`scripts/sync_wkrpt_skills.py`**；路径约定写明「改 wkrpt 后先同步脚本再提交」及此前 Gitee 无 Cursor 端文件的原因。
- **2026-05-03（飞书 wiki 模板 + `full_call` SQL）**：默认 wiki 模板改为 **`WHruwVACAi8nWPkXYgQcrLhHnFb`**（与 `generate_feishu_report.py` / `analyze_template.py` 对齐）；步骤 7 / 5.5 写明知识库复制成功日志、**高亮块/引用** 依赖整篇复制、新空间须重新授权；步骤 1 写明当前 **14** 条 SQL；数据映射增加 **`14_full_call` → `full_call.json`**。
- **2026-05-03（文档：`case_stock` + `code/` README）**：数据映射补充 **`13_case_stock` / `case_stock.json`**；图表表补充 **`screen_case_stock.py`**；步骤 5 PNG 改为约 **50** 张量级；图表要点补充 **case_stock** 口径说明；相关文件表增加 **`code/README.md`**；单步调试增加 `screen_case_stock.py`。同步刷新 **`code/README.md`**、**`code/sql/README.md`**、**`code/screens/README.md`**。
- **2026-05-02（飞书原图上传 + replace_image 宽高 + M2/M6）**：步骤 7 写明插图 **原文件字节上传**、`replace_image` **显式 width/height** 避免 **100px** 兜底；移除已废弃的 **`FEISHU_IMG_TARGET_WIDTH`**；分项 **G** / 前置表 **G** 改为「PNG 可用 IHDR，Pillow 可选兜底」。步骤 1 为 **`code/sql/*.sql` 全量**。数据映射与图表表补充 **`11_M2` / `12_M6`**、**`screen_m2_m6.py`**；步骤 5 PNG 约 **49**；故障表补充「极小图」；单步调试增加 `screen_m2_m6.py`。
- **2026-05-02（飞书策略整理）**：步骤 7 写明 **默认 wiki 节点复制 → 云盘复制兜底 → `FEISHU_REPORT_USE_CLONE` 强制克隆**；**不在标题正文拼接序号**（原生编号仅复制模式）；克隆侧支持 **heading4～9** 与 **ordered.sequence** 等；故障表补充 **131006** 与 **`FEISHU_DST_FOLDER_TOKEN`**；路径约定增加 **`.cursor/skills/wkrpt/SKILL.md`** 可选同步说明。
- **2026-05-02**：补充步骤 **5.5**（`analyze_template.py` → `template_analysis.json`）；飞书步骤建议「先 5.5 再 7」；修正模板产物说明（与 `template_blocks.json` 区分）；S/M1 六张对比表与约 **45** 张 PNG 提示；表头列对齐与 `chart_theme` 标题收紧说明；**`generate_feishu_report` 插图上传改为仅用 `requests` multipart，不再依赖 `requests_toolbelt`**；分项 **G** 改为可选 Pillow。
- **2026-05-01**：按当前仓库重写 Skill — 10 条 SQL 与 JSON 命名、`03_validate_data` 为主校验、`run_all_screens` 动态发现、`m0_billing` / `grp_collector` / M1 PNG 命名修正；新增步骤 2.5、7（飞书）与 doc-guide 对齐说明；**移除** HTML 文档/镜像方案描述。
- **2026-04-30**：Git 同步须用户选择远端；`screenshots` 不纳入版本库。
- **2026-04-27 及更早**：人均工时 SQL/图表、metadata、M0 成熟度、GRP 美化等（详见历史提交与旧版 Skill）。

**最后更新**：2026-05-04（见上条「飞书 Docx 文本与模板」；仓库 README / `_audit_params` 同步）
