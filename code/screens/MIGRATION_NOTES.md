# 画图代码迁移说明

从旧项目（周报自动化2）到新项目（周报自动化3）的画图代码整合迁移。

## 变化总结

### 1. 文件结构优化

**旧项目:**
- 多个独立脚本分散在根目录
- `generate_all_charts_final.py` - S类图表
- `generate_s_combined_v2.py` - S类组合图
- `generate_s_table_v2.py` - S类对比表
- `generate_assignment_repayment_charts.py` - M1图表
- `generate_m0_overdue_charts.py` - M0图表
- `generate_grp_charts_v2.py` - GRP图表

**新项目:**
- 4个整合的脚本放在 `code/screens/` 目录
- `screen_s_class.py` - S类所有图表（包含单独图、组合图、对比表）
- `screen_m1.py` - M1所有图表
- `screen_m0.py` - M0所有图表
- `screen_grp.py` - GRP所有图表

### 2. 数据格式统一

**旧项目:**
- 不同数据源使用不同格式
- S类: `recovery_data_{type}.json` - 直接数组格式
- M1: `assignment_repayment_data.json` - 直接数组格式
- M0: 硬编码在代码中或使用 `m0_data.py`
- GRP: JSON格式，但需要特殊解析

**新项目:**
- 所有数据采用统一格式
```json
{
  "header": ["field1", "field2", ...],
  "rows": [[val1, val2, ...], ...],
  "rowCount": N
}
```

### 3. 数据文件命名规范

**旧项目 → 新项目:**
- `recovery_data_ALL.json` → `s_class_all.json`
- `recovery_data_NEW.json` → `s_class_new.json`
- `recovery_data_MTD.json` → `s_class_mtd.json`
- `assignment_repayment_data.json` → `m1_assignment_repayment.json`
- （M0数据从硬编码/m0_data.py） → `m0_data.json` + `m0_data_grouped.json`
- `grp_data.json` → `grp_data.json` (保持不变)

### 4. 图表命名规范

**S类图表:**
- 旧: `screenshots/recovery_rate_S1_ALL.png`
- 新: `screenshots/recovery_rate_S1_ALL.png` (保持不变)

**M1图表:**
- 旧: `C:/0_项目/周报自动化2/screenshots/assignment_repayment_overall.png`
- 新: `screenshots/assignment_repayment_overall.png`

**M0图表:**
- 旧: `C:/0_项目/周报自动化2/screenshots/m0_principal_overdue_rate_monthly.png`
- 新: `screenshots/m0_principal_overdue_rate_monthly.png`

**GRP图表:**
- 旧: `C:/0_项目/周报自动化2/screenshots/grp_API-M1.png`
- 新: `screenshots/grp_API-M1.png`

### 5. 路径处理改进

**旧项目:**
- 使用硬编码绝对路径
- 如: `'C:/0_项目/周报自动化2/screenshots/xxx.png'`

**新项目:**
- 使用相对路径 + Path对象
```python
from pathlib import Path
DATA_DIR = Path(__file__).parent.parent.parent / 'data'
OUTPUT_DIR = Path(__file__).parent.parent.parent / 'screenshots'
```

### 6. 代码结构改进

**统一的模块结构:**
```python
# 1. 导入库
import matplotlib.pyplot as plt
import ...

# 2. 设置字体和路径
matplotlib.rcParams['font.sans-serif'] = [...]
DATA_DIR = Path(...)
OUTPUT_DIR = Path(...)

# 3. 数据加载函数
def load_data():
    ...

# 4. 数据处理函数
def process_data(data):
    ...

# 5. 图表生成函数（每个函数生成一张或一类图）
def generate_chart_1(...):
    ...

def generate_chart_2(...):
    ...

# 6. 主函数
def main():
    print("=" * 60)
    print("开始生成XXX图表...")
    # 加载数据
    # 生成图表
    print("完成！")

# 7. 入口
if __name__ == '__main__':
    main()
```

### 7. S类图表增强

**新增功能:**
- S2和S3的单独图表（旧项目只有S1）
- 每个类型都生成ALL/NEW/MTD三种变体
- S类从9张图扩展到15张图

**旧项目输出（S类）:**
- S1_ALL.png, S1_NEW.png, S1_MTD.png (3张)
- S_combined_ALL.png, S_combined_NEW.png, S_combined_MTD.png (3张)
- S_table_ALL.png, S_table_NEW.png, S_table_MTD.png (3张)
- 共9张

**新项目输出（S类）:**
- S1_ALL/NEW/MTD.png (3张)
- S2_ALL/NEW/MTD.png (3张) ← 新增
- S3_ALL/NEW/MTD.png (3张) ← 新增
- S_combined_ALL/NEW/MTD.png (3张)
- S_table_ALL/NEW/MTD.png (3张)
- 共15张

### 8. M0图表增强

**旧项目:**
- 5张图表
- 月度和周度的逾期率/催回率

**新项目:**
- 8张图表
- 新增2张：按首逾标识（ind）分组的催回率图
- 新增1张：首逾用户占比图

### 9. GRP图表优化

**改进点:**
- 更好的标签重叠处理
- 智能的月份标识显示
- 改进的颜色方案
- 底部排序文字显示

### 10. 错误处理增强

**新项目增强:**
- 更详细的日志输出
- 数据加载失败时的友好提示
- 进度显示（[1/4] 生成XXX...）
- 成功/失败计数统计

## 兼容性说明

### 保持兼容的部分:
1. 图表文件名格式（便于下游流程使用）
2. 图表风格（颜色、标签、格式）
3. 核心计算逻辑（回款率计算方式）

### 不兼容的部分:
1. 数据文件格式（需要从数据库重新导出）
2. 数据文件路径（从根目录移到data/目录）
3. 代码导入方式（不能直接import，需要独立运行）

## 迁移检查清单

- [x] S类图表代码迁移完成
- [x] M1图表代码迁移完成
- [x] M0图表代码迁移完成
- [x] GRP图表代码迁移完成
- [x] 数据格式统一
- [x] 路径结构统一
- [x] 错误处理增强
- [x] 文档编写完成
- [x] 批处理脚本创建
- [ ] 实际运行测试（需要真实数据）
- [ ] 性能测试
- [ ] 图表质量验证

## 运行测试

```bash
# 进入screens目录
cd code/screens   # 在项目根目录下

# 测试单个脚本
python screen_s_class.py
python screen_m1.py
python screen_m0.py
python screen_grp.py

# 或使用批处理脚本
run_all.bat  # Windows
./run_all.sh  # Linux/Mac
```

## 预期输出

成功运行后，应在 `../../screenshots/` 目录生成共38张图表：
- S类: 15张
- M1: 3张
- M0: 8张
- GRP: 12张（取决于数据中的case_type数量）

## 已知问题和注意事项

1. **字体问题**: 如果系统没有SimHei/Microsoft YaHei/DengXian字体，可能显示方块或乱码
2. **数据依赖**: 必须先运行数据提取脚本生成JSON文件
3. **内存使用**: M0图表可能占用较多内存（因为数据量大）
4. **生成时间**: 全部图表生成约需要30-60秒

## 后续优化建议

1. 添加命令行参数支持（指定生成哪些图表）
2. 添加图表预览功能
3. 支持自定义颜色方案
4. 支持多种输出格式（PNG/PDF/SVG）
5. 添加图表对比功能（对比不同月份的图表）
6. 性能优化（并行生成图表）
