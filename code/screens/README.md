# Screenshots生成模块

本目录包含4个画图脚本，用于生成周报所需的所有图表。

## 文件说明

### 1. screen_s_class.py
生成S类回款率图表（共15张）

**数据源:**
- `../../data/s_class_all.json` - S类整体数据
- `../../data/s_class_new.json` - S类新案数据
- `../../data/s_class_mtd.json` - S类老案数据

**输出图表:**
- S1/S2/S3 各3张单独图表 (ALL/NEW/MTD) - 共9张
- S类组合图3张 (recovery_rate_S_combined_*.png)
- S类对比表3张 (recovery_rate_S_table_*.png)

**运行方法:**
```bash
# 在项目根目录下执行
cd code/screens
python screen_s_class.py
```

### 2. screen_m1.py
生成M1分案回款图表（共3张）

**数据源:**
- `../../data/m1_assignment_repayment.json`

**输出图表:**
- assignment_repayment_overall.png - 整体分案回款
- assignment_repayment_new.png - 新案分案回款
- assignment_repayment_old.png - 老案分案回款

**运行方法:**
```bash
cd code/screens
python screen_m1.py
```

### 3. screen_m0.py
生成M0逾期图表（共8张）

**数据源:**
- `../../data/m0_data.json` - M0每日数据
- `../../data/m0_data_grouped.json` - M0分组数据（按首逾标识）

**输出图表:**
- m0_principal_overdue_rate_monthly.png - 金额逾期率（月）
- m0_count_overdue_rate_monthly.png - 单量逾期率（月）
- m0_principal_overdue_rate_weekly.png - 金额逾期率（周）
- m0_collection_rate_weekly.png - 金额催回率（周）
- m0_collection_rate_7d_30d_monthly.png - 7d/30d催回率（月）
- m0_ind1_ratio.png - 首逾用户占比
- m0_collection_rate_7d_30d_monthly_ind0.png - 非首逾用户催回率
- m0_collection_rate_7d_30d_monthly_ind1.png - 首逾用户催回率

**运行方法:**
```bash
cd code/screens
python screen_m0.py
```

### 4. screen_grp.py
生成GRP催收员图表（共12张）

**数据源:**
- `../../data/grp_data.json`

**输出图表:**
- grp_API-M1.png
- grp_M2.png
- grp_M5+.png
- grp_S1RA.png, grp_S1RB.png, grp_S1RC.png, grp_S1RD.png
- grp_S2RA.png, grp_S2RB.png, grp_S2RC.png
- grp_S3.png, grp_S3RB.png
- （实际生成的图表取决于grp_data.json中的case_type）

**运行方法:**
```bash
cd code/screens
python screen_grp.py
```

## 一键生成所有图表

可以创建一个批处理脚本来一次性生成所有图表：

```bash
# run_all.sh (Linux/Mac)
#!/bin/bash
cd "$(dirname "$0")"
python screen_s_class.py
python screen_m1.py
python screen_m0.py
python screen_grp.py
```

```batch
# run_all.bat (Windows)
@echo off
cd /d %~dp0
python screen_s_class.py
python screen_m1.py
python screen_m0.py
python screen_grp.py
pause
```

## 数据格式说明

所有JSON数据文件采用统一格式：
```json
{
  "header": ["field1", "field2", ...],
  "rows": [
    [value1, value2, ...],
    ...
  ],
  "rowCount": N
}
```

## 输出目录

所有图表保存到 `../../screenshots/` 目录

## 依赖库

- matplotlib
- numpy
- pandas (仅screen_grp.py使用)

安装依赖：
```bash
pip install matplotlib numpy pandas
```

## 注意事项

1. 确保数据文件存在于 `../../data/` 目录
2. 确保安装了中文字体（SimHei、Microsoft YaHei或DengXian）
3. 图表生成可能需要几秒钟时间，请耐心等待
4. 如果遇到字体问题，可以在代码中调整字体设置

## 图表样式

- 使用bar+line组合图（左轴柱状图，右轴折线图）
- 颜色统一：2月=#FF6B6B, 3月=#4ECDC4, 4月=#45B7D1
- 金额单位：百万或万
- 百分比保留2位小数
- 所有图表包含中文标题和标签
