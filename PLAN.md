# 工作计划：NASA TM-2011-216142《Space Shuttle Missions Summary》数据分析

## 项目背景与目标

对根目录下 `NASA_TM–2011–216142 Space Shuttle Missions Summary.pdf`（300 页，NASA JSC，2011 年 9 月）
开展数据分析。该文档记录了美国航天飞机全部 **135 次飞行任务**（STS-1 至 STS-135，1981–2011）的
"as-flown"（实际飞行）运行数据。

**目标：**
1. 从 PDF 中提取结构化数据，保存为 CSV 与 Excel 文件；
2. 核实数据正确性（内部一致性校验 + 与公开权威数据交叉核对）；
3. 绘制多维分析图表；
4. 输出分析报告。

## 数据源勘察结论（已完成）

| 数据源 | 位置 | 内容 | 提取难度 |
|---|---|---|---|
| 任务摘要页 | PDF 第 19–272 页，`Page 2-N-STS-X` 页眉 | 每任务 1–2 页 12 列表格：任务号、轨道器、乘组、发射/着陆数据、SSME/SRB/ET、轨道参数、载荷、任务要点 | **高**（多栏排版+照片导致纯文本行交错，需按词坐标切列） |
| 附录 A 重量汇总 | PDF 第 273–281 页 | 135 次飞行的轨道器/OMS/RCS 推进剂、载荷、累积重量、性能余量、各阶段重量与 X 重心 | 中（规整表格，跨行续行需合并） |
| 附录 C 飞行主管日志 | PDF 第 291–294 页 | 飞行主管名单（辅助数据） | 低 |

**技术路线：** Python 3.14 + venv（`.venv/`），`pdfplumber`（词级坐标提取）→ `pandas`（清洗）→
`openpyxl`（Excel 输出）→ `matplotlib`（图表）→ `pytest`（单元测试）。

## 目录规划

```
data/           # 提取出的 CSV 数据
  missions.csv        # 主数据集：每任务一行（发射/着陆/时长/乘组/轨道/重量等）
  weights.csv         # 附录 A：每任务重量明细
  flight_directors.csv# 附录 C：飞行主管
  space_shuttle_missions.xlsx   # 汇总 Excel 工作簿（多 sheet）
scripts/        # 提取/校验/绘图脚本
tests/          # pytest 单元测试
output/
  figures/      # 分析图表 PNG
  reports/      # 校验报告、分析报告
PLAN.md         # 本文件
```

## 里程碑

### M0 — 工作计划（本文件）
- [x] 勘察 PDF 结构，确定数据源与提取策略
- [x] 编写 PLAN.md 并提交

### M1 — 任务摘要页数据提取
- [ ] 编写 `scripts/extract_missions.py`：
  - 按 `Page 2-N-STS-X` 页眉定位 135 个任务的页面；
  - 用 pdfplumber 词级 x 坐标把 12 列版面切分为独立列文本；
  - 正则提取关键字段：
    - 任务号（官方 STS 编号 + 原始编号 + 序号）、轨道器（OV-101/099/102/103/104/105）
    - 发射日期、计划/实际发射时间（EST + GMT）、发射工位（39A/39B-序号）
    - 着陆场/跑道、着陆时间（GMT）、任务时长（Elapsed Time）
    - 乘组规模（按 CDR/PLT/MS 计数）与飞行主管数量
    - 轨道倾角、入射轨道 HA/HP（NM）、轨道器方向
    - 关键事件 MET：MECO、SRB SEP、ET SEP、OMS-1/2
    - 着陆重量、EOM 重量、X CG 等
  - 输出 `data/missions.csv`
- [ ] 编写 `tests/test_extract_missions.py`：对 STS-1/STS-2/STS-135 等已知真值断言
  （如 STS-1：1981-04-12 发射、EDW 着陆、时长 54:20:53、乘组 2 人）
- [ ] 验收：135 行、无缺任务、测试通过 → **提交 M1**

### M2 — 附录 A 重量表提取
- [ ] 编写 `scripts/extract_weights.py`：表格线定位 + 跨页/跨行续行合并，
  输出 `data/weights.csv`（数值型列统一为 lbs）
- [ ] 测试：对 STS-1/STS-135 已知值断言；135 行完整性
- [ ] 验收：测试通过 → **提交 M2**

### M3 — 数据核实
- [ ] `scripts/validate.py`，两级校验：
  - **内部一致性**：
    - 任务数 = 135，任务号连续无缺失；
    - 发射日期单调递增；发射日期 ≤ 着陆日期；
    - 任务时长 ≈ 着陆 GMT − 发射 GMT（容差 ±2 分钟，跨日校验）；
    - 任务页重量字段 vs 附录 A 对应列一致；
    - 乘组人数、轨道器飞行次数累加与各轨道器总数（OV-102:28, OV-099:10, OV-103:39, OV-104:33, OV-105:25）一致。
  - **外部交叉核对**：与 Wikipedia《List of Space Shuttle missions》及 NASA 公开数据核对
    发射日期、任务时长、轨道器、着陆场、乘组人数（允许时区/取整差异）。
- [ ] 输出 `output/reports/validation_report.md`（含差异清单与处置说明）
- [ ] 验收：校验通过或差异均有解释 → **提交 M3**

### M4 — 分析图表
- [ ] `scripts/plots.py` 输出 PNG 至 `output/figures/`：
  1. 每年发射次数柱状图（1981–2011）
  2. 各轨道器飞行次数与任务时长分布
  3. 任务时长随任务序号演变（含 Challenger/ Columbia 事故停飞窗口标注）
  4. 乘组规模演变
  5. 轨道倾角分布（28.45°/39°/51.6°/57° 聚类）
  6. 入射轨道高度（HA/HP）散点
  7. 着陆场统计（KSC/EDW/其他）及随时间占比
  8. 发射时刻昼夜分布
  9. 重量演变：着陆重量/EOM 重量/累积载荷（附录 A）
  10. 相邻任务发射间隔与年飞行率
- [ ] 验收：图全部生成、可读、无空图 → **提交 M4**

### M5 — 汇总报告
- [ ] 汇总 Excel 工作簿 `data/space_shuttle_missions.xlsx`（missions/weights/directors/校验差异 sheet）
- [ ] 编写 `output/reports/ANALYSIS.md` 分析报告（关键发现 + 图表引用）
- [ ] 更新 PLAN.md 勾选状态 → **提交 M5**

## 约定

- 所有脚本在 `.venv` 下运行；输出统一 UTF-8；
- 提取脚本幂等：重跑覆盖输出，不修改 PDF 原文件；
- 代码修改后必须运行 `pytest`，测试不过不算完成；
- Git 提交：Conventional Commits 英文消息，每个里程碑一次提交。
