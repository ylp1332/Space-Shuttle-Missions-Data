# 航天飞机任务数据分析（Space Shuttle Missions Data）

从 NASA 技术报告 **NASA/TM–2011–216142《Space Shuttle Missions Summary》**（JSC，2011 年 9 月，300 页）
中提取并校验美国航天飞机全部 **135 次飞行任务**（STS-1 至 STS-135，1981–2011）的
"as-flown"（实际飞行）运行数据，输出结构化数据集、分析图表与报告。

## 数据集一览

| 文件 | 内容 | 规模 |
|---|---|---|
| `data/missions.csv` | 每任务一行：任务号、轨道器、发射/着陆时间（GMT）、任务时长、乘组、飞行主管、轨道参数、关键事件 MET、着陆场等 | 136 行 × 59 列 |
| `data/weights.csv` | 附录 A 重量表：轨道器/推进剂/载荷/ET/SRB 重量、累积重量、Mach 3 与着陆重量及纵向质心 | 135 行 × 30 列 |
| `data/weights-revised.xlsx` | 人工校对版重量数据（含 2 处源文档印刷错误修正）：`weights`（lbs/in）+ `weights_mks`（kg/m）双表单 | 135 行 × 19 列 ×2 |
| `data/space_shuttle_missions.xlsx` | 汇总工作簿（4 sheet：Missions / Weights_AppendixA / Reference_Wikipedia / Summary） | — |
| `data/reference/wiki_sts_list.csv` | 外部核对参考（Wikipedia 任务列表，已入库） | 135 行 |

## 项目结构

```
data/           # 提取出的数据集与汇总工作簿
  reference/          # 外部核对参考数据
docs/           # 项目文档（PLAN.md 工作计划）
refs/           # NASA 源 PDF（40MB）+ 纵向质心包线等中文参考文档（均已入库）
scripts/        # 提取/校验/绘图/分析/工作簿脚本
tests/          # pytest 单元测试（25 项）
output/
  figures/      # 28 张分析图表 PNG（150 dpi；11–28 号为中文标注）
  reports/      # 校验报告、分析报告、重量深入分析报告
```

## 环境搭建

要求 Python 3.13。

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # Windows
# source .venv/bin/activate && pip install -r requirements.txt   # Linux/macOS
```

> 源 PDF 已随仓库入库（`refs/`，约 40MB），源自 NASA NTRS（ntrs.nasa.gov）
> 检索 "NASA TM-2011-216142"。提取类脚本依赖此文件；校验、绘图与工作簿
> 脚本只读取已入库的 CSV，无需 PDF。

## 复现流程

按顺序在项目根目录运行：

```bash
# 1. 提取任务摘要页（PDF 第 19-272 页，12 列坐标切分）
python scripts/extract_missions.py            # → data/missions.csv

# 2. 提取附录 A 重量表（PDF 第 274-282 页）
python scripts/extract_weights.py             # → data/weights.csv

# 3. 数据校验（内部一致性 11 项 + 外部核对 4 项）
python scripts/validate.py                    # → output/reports/validation_report.md

# 4. 分析图表（英文标注，图 01-10）
python scripts/plots.py                       # → output/figures/01-10_*.png

# 5. 汇总 Excel 工作簿
python scripts/build_workbook.py              # → data/space_shuttle_missions.xlsx

# 6. 重量深入分析（中文标注，图 11-28；读取 weights-revised.xlsx）
python scripts/plots_weights_mks.py           # → 图 11-14、23-28
python scripts/analyze_weights.py             # → 图 15-22 + 统计规律（stdout）
```

提取脚本幂等：重跑覆盖输出，不修改 PDF 原文件。

## 测试

```bash
python -m pytest
```

25 项测试覆盖：正则与切列逻辑单元测试、STS-1/135 参考值、135 次飞行完整性、
发射日期单调性、轨道器计数与史实一致、双源重量交叉核对等。

## 数据质量

- **内部一致性**：0 错误（序号完整唯一、时长与 GMT 差值吻合、双源重量 0 差异等；
  3 项警告均为源文档口径差异，详见报告）
- **外部核对**：发射日期 135/135、轨道器 135/135、时长 134/135、乘组 134/135
  与 Wikipedia 任务列表一致（差异项均为文档口径问题，详见报告）
- **源文档勘误**（经提取脚本勘误层应用于 `missions.csv` / `weights.csv` 与汇总工作簿，
  并同步于 `weights-revised.xlsx`）：STS-125 两列重量对调、STS-5 Mach 3 纵向质心
  首位数字误排、STS-125/127 右 SRB 补值、51-C 着陆纵向质心校正与 Mach 3 纵向质心
  置空（人工核对裁定）、STS-40/STS-46 任务页纵向质心数字误排
- 详见 [`output/reports/validation_report.md`](output/reports/validation_report.md)、
  [`output/reports/ANALYSIS.md`](output/reports/ANALYSIS.md) 与
  [`output/reports/WEIGHTS_ANALYSIS.md`](output/reports/WEIGHTS_ANALYSIS.md)

## 出处

- 数据源：NASA/TM–2011–216142, *Space Shuttle Missions Summary*, NASA Johnson
  Space Center, 2011（美国政府公有领域文档）
- 提取代码：本仓库 `scripts/`
