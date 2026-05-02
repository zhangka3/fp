# FP (Financial Processing)

Financial Data Processing and Reporting Automation System

## Project Overview

FP is a financial data processing and reporting automation system designed specifically for credit collection operations. The system automates the entire workflow from SQL query execution and data validation to chart generation and Feishu report publishing, supporting data analysis and visualization for multiple case types including S-Class, M0, M1, and GRP.

## Features

- **Automated SQL Execution**: Automatically execute queries from SQL files and save results as JSON
- **Data Validation**: Comprehensive data integrity checks to ensure accuracy
- **Multi-Type Chart Generation**: Supports charts for S-Class, M0, M1, GRP, and average labor hours
- **Feishu Integration**: Automatically generate Feishu document reports with image uploads
- **Weekly Report Automation**: Full automation pipeline (SQL → JSON → Validation → Charts)

## Directory Structure

```
.
├── code/
│   ├── python/
│   │   ├── 01_execute_sql/        # SQL Execution Module
│   │   ├── 025_check_rowcount/    # Row Count Validation
│   │   ├── 03_validate_data/      # Data Validation
│   │   ├── 055_analyze_template/  # Template Analysis
│   │   ├── 05_generate_charts/    # Chart Generation (Reference)
│   │   └── 06_generate_feishu/    # Feishu Report Generation
│   ├── sql/                       # SQL Query Files
│   └── screens/                   # Chart Generation Scripts
├── feishu_app.example.json       # Feishu App Configuration Example
├── feishu_creds.py                # Feishu Credentials Loader
└── template_blocks.json            # Feishu Document Template
```

## Quick Start

### 1. Environment Setup

```bash
# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Feishu App

Copy and fill in your credentials:

```bash
cp feishu_app.example.json feishu_app.json
```

Fill in your `app_id` and `app_secret` in `feishu_app.json`.

### 3. Execute SQL Queries

```bash
cd code/python/01_execute_sql
python run_all.py
```

### 4. Validate Data

```bash
cd code/python/03_validate_data
python validate_data.py
```

### 5. Generate Charts

```bash
cd code/screens
python screen_s_class.py   # S-Class Charts
python screen_m1.py       # M1 Charts
python screen_m0.py       # M0 Charts
python screen_grp.py      # GRP Charts
```

Or use the one-click generation script:

```bash
# Linux/Mac
bash run_all.sh

# Windows
run_all.bat
```

### 6. Generate Feishu Report

```bash
cd code/python/06_generate_feishu
python generate_feishu_report.py
```

## Data Type Definitions

| Type | Description |
|------|-------------|
| S-CLASS-ALL | All S-Class cases |
| S-CLASS-NEW | Newly assigned S-Class cases |
| S-CLASS-MTD | S-Class case collection statistics |
| M1 | Case collection data |
| M0 | Billing data |
| GRP | Collection agent data |
| AVG_EFF_WORKTIM | Average effective working hours per person |

## Chart List

- **S-Class Charts**: 15 charts
- **M1 Charts**: 3 charts
- **M0 Charts**: 8 charts
- **GRP Charts**: 12 charts
- **Average Labor Hours Chart**: 1 chart

## Dependencies

- pandas
- matplotlib
- numpy
- requests (Feishu API)

## License

MIT License