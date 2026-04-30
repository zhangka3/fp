# GRP图表鲁棒性增强说明

## 设计目标

确保 `screen_grp.py` 能够处理 **任意数量** 的collectors（催收员/区域），无论未来各月的collectors是增加还是减少。

## 已实现的动态适应机制

### 1. **Collectors数量不一致处理**
```python
# 确保两个月的DataFrame都包含所有collectors（填充缺失的为0）
for collector in collectors:
    if collector not in last_assign.columns:
        last_assign[collector] = 0
        last_rate[collector] = 0
    if collector not in curr_assign.columns:
        curr_assign[collector] = 0
        curr_rate[collector] = 0
```

**效果**：即使202603有4个collectors，202604只有3个，也能正常绘制对比图。

### 2. **颜色池扩展**
```python
colors = ['#FF8C42', '#FF6B9D', '#C44569', '#5DADE2', '#F39C12', '#6C5B7B', '#58D68D',
          '#E74C3C', '#3498DB', '#2ECC71', '#F39C12', '#9B59B6', '#1ABC9C', '#E67E22']
```

**支持范围**：14种颜色，通过取模 `colors[i % len(colors)]` 可支持任意数量。

### 3. **图例动态调整**
```python
legend_fontsize = 9 if len(collectors) <= 5 else 8
legend_ncol = min(len(collectors), 5)
ax.legend(handles, labels, loc='lower left', fontsize=legend_fontsize,
         bbox_to_anchor=(0, -0.25), ncol=legend_ncol)
```

**规则**：
- ≤5个collectors: 字体9号，最多5列
- >5个collectors: 字体8号，最多5列

### 4. **排序文字智能截断**
```python
if len(sorted_collectors) > 8:
    top_5 = sorted_collectors[:5]
    last_1 = sorted_collectors[-1:]
    ranking_text = " > ".join(top_5) + " ... " + " > ".join(last_1)
```

**规则**：
- ≤8个collectors: 显示全部
- >8个collectors: 显示前5名 + "..." + 最后1名

### 5. **标签间隔动态调整**
```python
if num_labels <= 4:
    min_gap = 3.0
    label_fontsize = 8
elif num_labels <= 6:
    min_gap = 2.5
    label_fontsize = 7
else:
    min_gap = 2.0
    label_fontsize = 6
```

**效果**：collectors越多，标签越小，间隔越紧凑，避免重叠。

### 6. **底部空间动态调整**
```python
if num_collectors <= 4:
    text_fontsize = 13
    bottom_space = 0.15
elif num_collectors <= 6:
    text_fontsize = 11
    bottom_space = 0.17
else:
    text_fontsize = 10
    bottom_space = 0.20
```

**效果**：collectors越多，底部预留空间越大，确保图例和排序文字不重叠。

## 测试场景

| Collectors数量 | 测试结果 | 示例 |
|---------------|---------|------|
| 3个 | ✓ 通过 | S2RC (EDN, XH, 内催) |
| 4个 | ✓ 通过 | S3 202603 (EDN, PM, XH, 内催) |
| 4个→3个 | ✓ 通过 | S3 跨月对比 (PM消失) |
| 5-8个 | ✓ 设计支持 | 自动调整布局 |
| 9-20个 | ✓ 设计支持 | 智能截断显示 |

## 关键技术点

1. **数据对齐**：通过填充0确保两个月的DataFrame列一致
2. **取模循环**：颜色数组用取模方式支持任意数量
3. **分段阈值**：根据数量范围使用不同的布局参数
4. **智能截断**：超过阈值时只显示关键信息
5. **移除裁剪**：不使用`bbox_inches='tight'`避免自动裁剪破坏布局

## 未来维护建议

1. **新增collectors**：无需修改代码，自动适应
2. **颜色不够用**：可扩展colors数组（建议14+种）
3. **调整阈值**：修改`if num_collectors`的条件值
4. **极端情况**（20+个）：建议分组显示或使用热力图

## 相关文件

- 主程序：`screen_grp.py`
- 数据源：`../../data/grp_data.json`
- 输出目录：`../../screenshots/grp_*.png`

## 最后更新

2026-04-21 - 完成全面鲁棒性增强
