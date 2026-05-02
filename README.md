

# FP (Financial Processing)

金融数据处理与报表自动化系统

## 项目简介

FP 是一个专为信贷催收业务设计的金融数据处理与报表自动化系统。该系统实现了从 SQL 查询执行、数据验证到图表生成、飞书报告发布的完整自动化流程，支持 S 类、M0、M1、GRP 等多种案件类型的数据分析与可视化。

## 功能特性

- **SQL 执行自动化**：支持从 SQL 文件自动执行查询并保存 JSON 结果
- **数据校验**：完整的数据完整性校验，确保数据准确性
- **多类型图表生成**：支持 S 类、M0、M1、GRP、人均工时等多种图表
- **飞书集成**：自动生成飞书文档报告，支持图片上传
- **周报自动化**：完整的周报生成流程（SQL→JSON→校验→图表）

## 目录结构

```
.
├── code/
│   ├── python/
│   │   ├── 01_execute_sql/        # SQL 执行模块
│   │   ├── 025_check_rowcount/    # 行数校验
│   │   ├── 03_validate_data/      # 数据验证
│   │   ├── 055_analyze_template/  # 模板分析
│   │   ├── 05_generate_charts/    # 图表生成（参考）
│   │   └── 06_generate_feishu/    # 飞书报告生成
│   ├── sql/                       # SQL 查询文件
│   └── screens/                   # 图表生成脚本
├── feishu_app.example.json       # 飞书应用配置示例
├── feishu_creds.py                # 飞书凭证加载
└── template_blocks.json            # 飞书文档模板
```

## 快速开始

### 1. 环境配置

```bash
# 安装依赖
pip install -r requirements.txt
```

### 2. 配置飞书应用

复制配置示例并填写凭证：

```bash
cp feishu_app.example.json feishu_app.json
```

在 `feishu_app.json` 中填入您的 `app_id` 和 `app_secret`。

### 3. 执行 SQL 查询

```bash
cd code/python/01_execute_sql
python run_all.py
```

### 4. 数据验证

```bash
cd code/python/03_validate_data
python validate_data.py
```

### 5. 生成图表

```bash
cd code/screens
python screen_s_class.py   # S 类图表
python screen_m1.py       # M1 图表
python screen_m0.py       # M0 图表
python screen_grp.py      # GRP 图表
```

或使用一键生成脚本：

```bash
# Linux/Mac
bash run_all.sh

# Windows
run_all.bat
```

### 6. 生成飞书报告

```bash
cd code/python/06_generate_feishu
python generate_feishu_report.py
```

## 数据类型说明

| 类型 | 说明 |
|------|------|
| S-CLASS-ALL | 全部 S 类案件 |
| S-CLASS-NEW | 新分配 S 类案件 |
| S-CLASS-MTD | S 类案件回款统计 |
| M1 | 分案回款数据 |
| M0 | 账单数据 |
| GRP | 催收员数据 |
| AVG_EFF_WORKTIM | 人均有效工作时长 |

## 图表清单

- **S 类图表**：15 张
- **M1 图表**：3 张
- **M0 图表**：8 张
- **GRP 图表**：12 张
- **人均工时图表**：1 张

## 依赖库

- pandas
- matplotlib
- numpy
- requests（飞书 API）

## 许可证

MIT License