# 工作计划：NASA TM-2011-216142《Space Shuttle Missions Summary》数据分析

## 项目背景与目标

对 `refs/NASA_TM–2011–216142 Space Shuttle Missions Summary.pdf`（300 页，NASA JSC，2011 年 9 月）
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
| 附录 A 重量汇总 | PDF 第 273–281 页 | 135 次飞行的轨道器/OMS/RCS 推进剂、载荷、累积重量、性能余量、各阶段重量与纵向质心 | 中（规整表格，跨行续行需合并） |
| 附录 C 飞行主管日志 | PDF 第 291–294 页 | 飞行主管名单（辅助数据） | 低 |

**技术路线：** Python 3.13 + venv（`.venv/`），`pdfplumber`（词级坐标提取）→ `pandas`（清洗）→
`openpyxl`（Excel 输出）→ `matplotlib`（图表）→ `pytest`（单元测试）。

## 目录规划（随项目演进更新，当前实际结构）

```
data/           # 提取出的数据集与汇总工作簿
  missions.csv               # 主数据集：每任务一行（发射/着陆/时长/乘组/轨道/重量等）
  weights.csv                # 附录 A：每任务重量明细
  weights-revised.xlsx       # 人工校对版重量数据（英制/公制双表单）
  space_shuttle_missions.xlsx# 汇总 Excel 工作簿（4 sheet）
  reference/wiki_sts_list.csv# 外部核对参考（Wikipedia 任务列表）
scripts/        # 提取/校验/绘图/分析/工作簿脚本
tests/          # pytest 单元测试（25 项）
refs/           # NASA 源 PDF（40MB，已入库）+ 纵向质心包线等中文参考文档
docs/
  PLAN.md       # 本文件
output/
  figures/      # 28 张分析图表 PNG
  reports/      # 校验报告、分析报告、重量深入分析报告
```

> 附录 C 飞行主管日志（PDF 第 291–294 页）经勘察后未单独建库——主管名单已含于
> `missions.csv` 的 `flight_directors` / `fd_count` 列。

## 里程碑

### M0 — 工作计划（本文件）
- [x] 勘察 PDF 结构，确定数据源与提取策略
- [x] 编写 PLAN.md 并提交

### M1 — 任务摘要页数据提取 ✅（已完成）
- [x] 编写 `scripts/extract_missions.py`（12 列坐标切分 + 宽字距重连 + 正则字段提取）
- [x] 输出 `data/missions.csv`（136 行 × 59 列：135 次飞行 + 取消任务 51-E）
- [x] `tests/test_extract.py`：18 项断言（STS-1/135 参考值、轨道器计数、单调性等）
- 验收：135 行、序号无缺、25 项测试通过 → **已提交**

### M2 — 附录 A 重量表提取 ✅（已完成）
- [x] `scripts/extract_weights.py`：表格线提取 + 合并单元格拆分 + 锚定列映射
  （早期 SODB 页与后期 TDDP 页中部载荷列布局不同，改用全表一致的锚定列）
- [x] `data/weights.csv`（135 行 × 30 列）；`tests/test_weights.py` 7 项测试
- 验收：双源重量 0 差异 → **已提交**

### M3 — 数据核实 ✅（已完成）
- [x] `scripts/validate.py` 两级校验（内部 11 项 + 外部 4 项；M6/M9 增补校验项后现为内部 16 项）
- [x] 验证驱动修复：OCR 天数离群值、误读发射日期（STS-4/7）、乘组头格式、
  STS-107 计划着陆场置空、GMT/印刷日期仲裁
- [x] 结果：**0 错误、3 警告**（均为文档口径差异，已记录于报告）
- [x] 外部核对：发射日期 135/135、轨道器 135/135、时长 134/135、乘组 134/135
- [x] `output/reports/validation_report.md` → **已提交**

### M4 — 分析图表 ✅（已完成）
- [x] `scripts/plots.py` → `output/figures/` 10 张 PNG（150 dpi）
- [x] 图表经视觉审查修正（KSC 78 / EDW 54 / WSMR 1 与史实一致）
- 验收：全部生成、经视觉模型审查 → **已提交**

### M5 — 汇总报告 ✅（已完成）
- [x] `scripts/build_workbook.py` → `data/space_shuttle_missions.xlsx`（4 sheet）
- [x] `output/reports/ANALYSIS.md` 分析报告
- [x] 更新 PLAN.md → **已提交**

### M6 — 人工校对数据入库与公制表单 ✅（已完成）
- [x] `data/weights-revised.xlsx`：人工校对版入库（表单更名 `weights_mks`）
- [x] 新增 `weights_metric`→`weights_mks` 公制表单（lbs→kg ×0.45359237、in→m ×0.0254），
  逐格验证 2057 个换算值零误差
- [x] 发现并修正源文档印刷错误 ×2：STS-125 两列对调（payload 22828 lbs ≈ 10.36 t）、
  STS-5 Mach 3 Xcg 2094.8→1094.8 in；`validate.py` 新增对应校验项与 known-gap 记录
- [x] 勘误层并入提取管道：`extract_weights.py` ERRATA 表（5 项 7 格，含修正前值断言）
  同步全部修订至 `weights.csv` 与汇总工作簿；任务页勘误 ×2（STS-40/STS-46 纵向质心
  数字误排）经 `extract_missions.py` ERRATA 同步至 `missions.csv`；
  校验口径 0 errors / 3 warnings
- [x] `refs/` 补充纵向质心包线等中文参考文档 ×2 → **已提交**

### M7 — 重量深入分析 ✅（已完成）
- [x] `scripts/plots_weights_mks.py`：图 11–14、23–28（起飞总重/载荷/推进剂/纵向质心/着陆系列）
- [x] `scripts/analyze_weights.py`：图 15–22 + 8 条统计规律输出
- [x] 纵向质心限位线：前限 1076.7 in（65%L）、飞行阶段后限 1109.9 in（67%L）、
  设计阶段后限 1118.1 in（67.5%L），L = 1656.5 in
- [x] 图表经视觉模型多轮验收（碰撞/塌缩问题修复）→ **已提交**

### M8 — 图表规范化与重量分析报告 ✅（已完成）
- [x] 全部 28 张图：中文宋体 + 西文/数字 Times New Roman（font.family 回退链）；
  术语统一（纵向质心 Xcg/起飞总重/载荷/着陆载荷）
- [x] 规避 matplotlib 3.11.2 小字号自由文本中文静默塌缩缺陷（`fig_label` + 字号≥9）
- [x] `output/reports/WEIGHTS_ANALYSIS.md` 重量深入分析报告；ANALYSIS.md/PLAN.md/README.md 同步更新
- [x] requirements.txt 与环境核对一致 → **已提交**

### M9 — 数据集表头文档化与起飞重量口径审计 ✅（已完成）
- [x] `ANALYSIS.md` §1：各数据文件（missions.csv / weights.csv / weights-revised.xlsx /
  space_shuttle_missions.xlsx / wiki_sts_list.csv）表头逐列说明（含备注列：
  时间基准 GMT=UTC、当地时、MET 零点=T-0、SRB IGN=liftoff、Mach 3 EOM、全停等）
- [x] 起飞重量"组件之和 vs 总量"审计：逐格对照 PDF 附录 A，提取值与印刷值一致；
  残差为源文档分代记账口径（62/128 行精确为零；早期 SODB 页偏正、后期 TDDP 页
  恒定偏负），记录于 `WEIGHTS_ANALYSIS.md` §2(d)，数据保留原值
- [x] `validate.py` 和式校验修正：改用附录 A 原生 `orb_plus_pyld_srb_ign` 列
  （原拼接口径在 STS-30 产生 −30,230 lbs 假警报）；报告 Summary 同步更新
- [x] `WEIGHTS_ANALYSIS.md` 新增 §1 数据集说明（双表单表头，编号新增，§1–§5 顺延
  为 §2–§6，交叉引用同步）；README/PLAN 过时说明修正 → **本次提交**

## 约定

- 所有脚本在 `.venv` 下运行；输出统一 UTF-8；
- 提取脚本幂等：重跑覆盖输出，不修改 PDF 原文件；
- 代码修改后必须运行 `pytest`，测试不过不算完成；
- Git 提交：Conventional Commits 英文消息，每个里程碑一次提交。
