# 航天飞机任务数据分析报告

**数据源**：NASA/TM–2011–216142 *Space Shuttle Missions Summary*（JSC，2011 年 9 月，300 页）
**数据范围**：1981-04-12（STS-1）至 2011-07-21（STS-135），共 **135 次轨道飞行**（另含 1 个取消任务 STS 51-E）

---

## 1. 数据集说明

| 文件 | 内容 | 规模 |
|---|---|---|
| `data/missions.csv` | 每任务一行：任务号、轨道器、发射/着陆时间（GMT）、任务时长、乘组、飞行主管、轨道参数、关键事件 MET、着陆场等 | 136 行 × 60 列 |
| `data/weights.csv` | 附录 A 重量表：轨道器/推进剂/载荷/ET/SRB 重量、累积重量、Mach 3 与着陆重量及纵向质心 | 135 行 × 30 列 |
| `data/weights-revised.xlsx` | 人工校对版重量数据（含 2 处源文档印刷错误修正）：`weights`（lbs/in）+ `weights_mks`（kg/m）双表单 | 135 行 × 19 列 ×2 |
| `data/space_shuttle_missions.xlsx` | 以上数据 + Wikipedia 参考数据 + 统计汇总（4 个 sheet） | — |
| `data/reference/wiki_sts_list.csv` | 外部核对参考（Wikipedia 任务列表） | 135 行 |

## 2. 数据质量结论（详见 `validation_report.md`）

**内部一致性**（0 错误）：
- 135 个飞行序号完整唯一；发射日期随序号单调递增；
- 全部任务时长与"着陆 GMT − 发射 GMT"差值吻合（<3 分钟）；
- 印刷日期与 GMT 时间戳一致（允许当地时区 ±1 天）；
- 任务页与附录 A 双源重量数据完全一致（Mach 3 / 着陆重量可比行 0 差异）；
- 各轨道器飞行序号 1..n 连续。

**外部核对**（对照 Wikipedia 任务列表）：
- 发射日期 **135/135 一致**；轨道器 **135/135 一致**；
- 任务时长 **134/135 一致**（STS-60 为 Wikipedia 列表页自身错误：其标 7d06h，而 NASA 档案与本文档均为 8d07h）；
- 乘组人数 **134/135 一致**（STS-85 文档标注 (7) vs 列表 6）。

**文档自身的已知空白**（非提取错误）：7 个 DOD 任务（51-C、51-J、27、28、33、36、38）重量未公开；51-L/STS-107 无着陆数据；STS-3 的 wheels-stop 时间戳在原文存在格式异常（`89:16:06.09Z`）。

## 3. 项目级统计

| 指标 | 数值 |
|---|---|
| 总飞行次数 | 135 |
| 总在轨时间 | **1330.7 天**（本数据集按时长合计；NASA 官方口径 1322.3 天，差异源于统计截止点不同） |
| 平均任务时长 | 9.86 天 |
| 最长任务 | STS-80，17 天 15:53（Columbia，1996） |
| 最短任务 | STS-51-L，1 分 14 秒（Challenger 事故，1986） |
| 轨道器飞行次数 | Discovery 39、Atlantis 33、Columbia 28、Endeavour 25、Challenger 10 |
| 发射工位 | 全部自 KSC 39A/39B |
| 着陆分布 | KSC 78、Edwards 54、White Sands 1 |
| 乘组规模 | 2 人（早期测试）→ 7 人（常态）→ 4 人（STS-135 救援约束） |
| 发射人次合计 | 818 |
| 文档标注的夜间发射 | 21 次 |

## 4. 图表与主要发现

图表位于 `output/figures/`（150 dpi PNG）：

1. **`01_launches_per_year.png` — 年发射次数**
   1985 年达到峰值 9 次；Challenger（1986）与 Columbia（2003）事故后分别停飞 32 个月与 30 个月（1987、2004 全年零发射）；恢复期后年发射率再未回到 1985 年水平，2000 年代稳定在 4-5 次/年。

2. **`02_orbiter_flights.png` — 轨道器对比**
   Discovery 以 39 次成为"机队主力"；Columbia（28 次，最长任务纪录保持者）与 Challenger（10 次）因事故提前退役；Endeavour（1991 年接替 Challenger）25 次全部成功。

3. **`03_duration_evolution.png` — 任务时长演变**
   从早期测试飞行的 2-8 天增长到 ISS 时代的 12-16 天，二次趋势明显；两次事故后的停飞窗口清晰可见；STS-80（17.7 天）为全计划最长。

4. **`04_crew_evolution.png` — 乘组规模演变**
   STS-1~4 双人（弹射座椅限制）→ STS-5 起 4-5 人 → Spacelab/ISS 时代稳定 7 人（最大 8 人：STS 61-A）；计划末尾 STS-135 因救援能力约束降为 4 人。

5. **`05_inclination.png` — 轨道倾角**
   明显聚类：28.45°（KSC 正东发射，52 次）、51.6°（ISS 轨道，44 次）、57°（DOD 极轨任务，19 次）、39°/38°（Hubble 等）。1998 年后 ISS 任务主导 51.6°。

6. **`06_landing_sites.png` — 着陆场**
   早期以 Edwards 为主（湖床安全余度大），1990 年代起 KSC 占比持续上升（避免轨道器跨国转运成本），最终 KSC 78 : Edwards 54 : White Sands 1（STS-3 唯一一次）。

7. **`07_launch_hours.png` — 发射时刻（UTC）**
   发射窗口呈双峰分布（约 08-11 与 15-19 UTC），对应 KSC 白天窗口与轨道交会/照明约束；文档标注的 21 次夜间发射与 UTC 01-11 时的绿色条带吻合。

8. **`08_weight_evolution.png` — 重量演变（附录 A）**
   起飞总重稳定在 4.46-4.53M lbs；轨道器干重从 STS-1 的 ~172k lbs 持续增长到 ~186k lbs（结构改进 + 系统加装）；着陆重量随任务类型在 194-226k lbs 波动。

9. **`09_et_impact_map.png` — 外贮箱溅落点**
   溅落点集中在太平洋（约 280-310°E 航迹）与印度洋（DOD 大倾角任务偏南），与发射方位角 39-57° 的地面航迹一致。

10. **`10_flight_rate.png` — 发射间隔**
    常态周转 30-90 天；两次事故后出现 2.5 年级空白；1997 年实现最短 52 天连续周转（STS-83→94 复飞）。

### 重量数据深入分析（第 11–28 号图）

基于人工校对版 `data/weights-revised.xlsx`（公制单位）的扩展分析，共 18 张图
（中文标注）：起飞总重与构成、载荷、推进剂加注、着陆重量与着陆载荷、轨道器干重演化、
ET 减重阶梯、Mach 3/着陆纵向质心（含前/后限包线）、SRB 左右对称性等。
8 条统计规律、纵向质心限值定义（前限 1076.7 in / 飞行后限 1109.9 in / 设计后限 1118.1 in）
及两处源文档印刷错误修正（STS-125 列对调、STS-5 首位数字误排）详见
**[`WEIGHTS_ANALYSIS.md`](WEIGHTS_ANALYSIS.md)**。

## 5. 方法备注

- 提取方法：pdfplumber 词级坐标按 12 列版面切分 + 宽字距文本重连 + 逐字段正则；附录 A 使用表格线提取并对跨行合并单元格拆分；
- 时长仲裁：印刷时长与"GMT 差值"互验，超 15 分钟偏差时以 GMT 为准（纠正了 STS-69/72 等窗口误匹配）；
- 复现流程：`scripts/extract_missions.py` → `scripts/extract_weights.py` → `scripts/validate.py` → `scripts/plots.py` → `scripts/build_workbook.py`；重量深入分析：`scripts/plots_weights_mks.py` + `scripts/analyze_weights.py`（读取 `weights-revised.xlsx`，输出图 11–28 与统计规律）；测试 `pytest tests/`（25 项全部通过）。
