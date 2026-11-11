# 航天飞机任务数据分析报告

**数据源**：NASA/TM–2011–216142 *Space Shuttle Missions Summary*（JSC，2011 年 9 月，300 页）
**数据范围**：1981-04-12（STS-1）至 2011-07-21（STS-135），共 **135 次轨道飞行**（另含 1 个取消任务 STS 51-E）

---

## 1. 数据集说明

| 文件 | 内容 | 规模 |
|---|---|---|
| `data/missions.csv` | 每任务一行：任务号、轨道器、发射/着陆时间（GMT）、任务时长、乘组、飞行主管、轨道参数、关键事件 MET、着陆场等 | 136 行 × 59 列 |
| `data/weights.csv` | 附录 A 重量表：轨道器/推进剂/载荷/ET/SRB 重量、累积重量、Mach 3 与着陆重量及纵向质心 | 135 行 × 30 列 |
| `data/weights-revised.xlsx` | 人工校对版重量数据（2 处源文档印刷错误修正 + 3 处人工校对值）：`weights`（lbs/in）+ `weights_mks`（kg/m）双表单 | 135 行 × 19 列 ×2 |
| `data/space_shuttle_missions.xlsx` | 以上数据 + Wikipedia 参考数据 + 统计汇总（4 个 sheet） | — |
| `data/reference/wiki_sts_list.csv` | 外部核对参考（Wikipedia 任务列表） | 135 行 |

### 1.1 `missions.csv` 表头说明（59 列）

时间基准：**GMT 即 UTC**；当地时为 KSC 所在**美国东部时**（EST/EDT，印刷日期为当地日期）；**MET（任务经过时间）零点 = T-0 = SRB 点火 = liftoff（起飞瞬间）**，SSME 主发动机于 T-6.6 s 先行点火（轨道器被固紧螺栓锁定，未离台），故所有 "SRB IGN"（SRB 点火时）口径的重量均为起飞时刻值。

| 列名 | 含义 | 备注 |
|---|---|---|
| `designation` | 任务代号（含 ISS 联合编号后缀，如 `STS-88/ISS-01A`） | — |
| `base` | 基础任务号（剥离 ISS 后缀，如 `STS-88`；跨表关联键） | — |
| `pdf_section` | 该任务在源 PDF 中的章节号（如 `2-1`） | — |
| `pdf_pages` | 该任务在源 PDF 中占据的页数 | — |
| `flight_seq` | 全计划飞行序号（1–135；取消任务为空） | — |
| `launch_pad` | 发射工位（39A / 39B） | — |
| `iss_flight` | ISS 联合飞行编号（如 `01A.1`；非 ISS 任务为空） | — |
| `cancelled` | 取消任务标志（1 = 取消；仅 STS 51-E） | — |
| `orbiter_id` | 轨道器编号（OV-099/102/103/104/105） | — |
| `orbiter` | 轨道器名称（Columbia / Challenger / Discovery / Atlantis / Endeavour） | — |
| `orbiter_flight_no` | 该轨道器的第几次飞行 | — |
| `crew_size` | 发射乘组人数（乘组交换任务取 UP 发射人数） | — |
| `crew_roles` | 乘组岗位缩写（CDR / PLT / MS / PS） | — |
| `crew_names` | 乘组成员名单（`岗位: 姓名` 以分号分隔） | — |
| `flight_directors` | 飞行主管名单（分号分隔） | — |
| `fd_count` | 飞行主管人数 | — |
| `launch_site` | 发射场（KSC） | — |
| `launch_date` | 发射日期（印刷日期，`YYYY-MM-DD`） | 当地日期，与 UTC 可差 ±1 天 |
| `launch_year` | 发射年份 | — |
| `launch_gmt_raw` | 发射 GMT 原始时间戳（`DDD:HH:MM:SS.SZ` 格式） | DDD 为年积日；GMT = UTC |
| `launch_dt_utc` | 发射时刻（UTC，由 GMT 时间戳解析） | 即 T-0（SRB 点火 / liftoff） |
| `launch_planned_local` | 计划发射当地时刻（文档 (P) 标注） | 美国东部时（EST/EDT） |
| `launch_actual_local` | 实际发射当地时刻（文档 (A) 标注） | 美国东部时（EST/EDT） |
| `window_hours` | 发射窗口时长（小时） | — |
| `meco_met` | 主发动机关机 MECO 时刻（MET，分:秒） | MET 自 T-0 起算 |
| `srb_sep_met` | SRB 分离时刻（MET） | MET 自 T-0 起算（约 T+2 min） |
| `et_sep_met` | 外贮箱分离时刻（MET） | MET 自 T-0 起算（约 T+8.5 min） |
| `oms1_met` | OMS-1 入轨点火时刻（MET） | MET 自 T-0 起算 |
| `oms2_met` | OMS-2 入轨点火时刻（MET） | MET 自 T-0 起算 |
| `maxq` | 最大动压 Max Q 数值 | 发生于上升段约 T+60 s |
| `landing_site` | 着陆场与跑道（EDW / KSC / WSMR 等） | — |
| `landing_date` | 着陆日期（`YYYY-MM-DD`） | 当地日期 |
| `touchdown_utc` | 主轮触地时刻（UTC） | 51-L / STS-107 无着陆数据 |
| `wheels_stop_utc` | 全停（wheels stop）时刻（UTC） | 51-L / STS-107 无着陆数据 |
| `duration_source` | 时长来源（`text` = 文档印刷值；`derived` = 由 GMT 差值推算） | 两者偏差 >15 min 时以 GMT 为准 |
| `duration` | 任务时长（`Xd HH:MM:SS`） | 自 T-0 至主轮触地 |
| `duration_hours` | 任务时长（小时） | 同上 |
| `xrange_nm` | 再入横向航程 XRANGE（nm） | — |
| `mlgtd_ft` | 主起落架滑跑距离 MLGTD（ft） | — |
| `mach3_weight_lbs` | Mach 3 EOM 重量（lbs，任务页 SSME 栏） | 再入减速至马赫 3 时刻 |
| `mach3_xcg` | Mach 3 纵向质心 Xcg（in） | 同上时刻 |
| `landing_weight_lbs` | 着陆重量（lbs） | 全停时刻 |
| `landing_xcg` | 着陆纵向质心 Xcg（in） | 全停时刻 |
| `engine_sns` | 三台主发动机序号（`位置=SN`，分号分隔） | — |
| `et_no` | 外贮箱编号（ET-n） | — |
| `et_impact_lat` | 外贮箱溅落点纬度（°，N/S） | ET 分离后溅落 |
| `et_impact_long` | 外贮箱溅落点经度（°，E/W） | — |
| `inclination_deg` | 轨道倾角（°） | — |
| `insertion_alt_nm` | 入轨高度（nm） | — |
| `hahp_raw` | 远/近地点（HA/HP）栏原始文本 | — |
| `cargo_lbs` | 载荷重量 CARGO（lbs） | — |
| `deployed_lbs` | 已部署载荷 DEPLOYED（lbs） | — |
| `nondeployed_lbs` | 未部署载荷 NON-DEPLOYED（lbs） | — |
| `cargo_total_lbs` | 载荷合计 CARGO TOTAL（lbs） | — |
| `workdays_opf` | 周转停场天数——OPF（天） | — |
| `workdays_vab` | 周转停场天数——VAB（天） | — |
| `workdays_pad` | 周转停场天数——发射台（天） | — |
| `night_launch` | 文档标注夜间发射标志（1 / 0） | — |
| `eva_count_hint` | 由 HIGHLIGHTS 栏推断的出舱活动（EVA）次数 | — |

### 1.2 `weights.csv` 表头说明（30 列，附录 A 原始提取）

时刻口径：**"SRB 点火时"（AT SRB IGN）= T-0 = liftoff（起飞瞬间）**——航天飞机起飞即定义为 SRB 点火，SSME 于 T-6.6 s 先行点火但仍被固紧螺栓锁定，故本表所有 "AT SRB IGN" 重量均为起飞时刻值（与 1.1 表 `launch_dt_utc` 同一时刻）。

| 列名 | 含义 | 备注 |
|---|---|---|
| `flight` | 附录 A 原始任务标签 | — |
| `ov_tail` | 轨道器尾号（099 / 102 / 103 / 104 / 105） | — |
| `orb_wt_wo_prop_lbs` | 轨道器不含推进剂干重（lbs） | 地面称重值，与发射时刻无涉 |
| `non_prop_cons_srb_ign_lbs` | SRB 点火时非推进剂消耗品重量（lbs） | T-0 时刻 |
| `oms_prop_lbs` | OMS 推进剂加注量（lbs） | 加注量，与发射时刻无涉 |
| `rcs_prop_fwd_lbs` | 前舱 RCS 推进剂量（lbs） | 同上 |
| `rcs_prop_aft_lbs` | 后舱 RCS 推进剂量（lbs） | 同上 |
| `orb_wt_srb_ign_lbs` | SRB 点火时轨道器重量（lbs） | T-0（含全部推进剂） |
| `pyld_pri_dply_lbs` | 主部署载荷（合并单元格首值，lbs） | — |
| `raw_c9` | 中部载荷块原始列（早期 SODB 页与后期 TDDP 页版面不同，语义不统一，仅保留原文；合并单元格以 `\|` 连接两值） | — |
| `raw_c10` | 同上，载荷块原始列 | — |
| `raw_c11` | 同上，载荷块原始列 | — |
| `raw_c12` | 同上，载荷块原始列 | — |
| `pyld_flight_total_lbs` | 飞行总载荷（lbs） | — |
| `raw_c14` | 同 `raw_c9`，载荷块原始列 | — |
| `raw_c15` | 同 `raw_c9`，载荷块原始列 | — |
| `orb_plus_pyld_srb_ign_lbs` | SRB 点火时轨道器 + 载荷重量（lbs） | T-0 时刻 |
| `orb_wt_orbit_insert_lbs` | 入轨时轨道器重量（lbs） | OMS 入轨完成后（约 MET 45 min 内） |
| `orb_wt_orbit_insert_accum_lbs` | 入轨重量累积值（lbs） | — |
| `et_wt_srb_ign_lbs` | SRB 点火时外贮箱重量（lbs） | T-0 时刻（含推进剂） |
| `srb_wt_left_srb_ign_lbs` | 左 SRB 点火重量（lbs；左右为合并单元格拆分） | T-0 时刻 |
| `srb_wt_right_srb_ign_lbs` | 右 SRB 点火重量（lbs） | T-0 时刻 |
| `shuttle_wt_srb_ign_lbs` | 全系统起飞总重（轨道器 + ET + 双 SRB，lbs） | T-0（GLOW）；与组件之和的残差为源文档分代记账口径，见 §2 与 `WEIGHTS_ANALYSIS.md` §2(d) |
| `perf_marg_tddp_lbs` | 性能余量 TDDP 值（lbs；与 RECON 为合并单元格拆分） | — |
| `perf_marg_recon_lbs` | 性能余量 RECON 值（lbs） | — |
| `mach3_eom_wt_lbs` | Mach 3 EOM 重量（lbs） | 再入减速至马赫 3 时刻（EOM = 使命终点弹道段） |
| `mach3_eom_xcg_in` | Mach 3 纵向质心 Xcg（in） | 同上时刻 |
| `landing_wt_lbs` | 着陆重量（lbs） | 全停时刻 |
| `landing_xcg_in` | 着陆纵向质心 Xcg（in） | 全停时刻 |
| `base` | 由附录 A 标签归一化的基础任务号（用于与 `missions.csv` 的 `base` 关联） | — |

### 1.3 `weights-revised.xlsx` 表头说明（2 表单 × 19 列）

人工校对版：`weights` 表单为英制（lbs / in），`weights_mks` 表单为公制（kg / m），列结构相同；相对 `weights.csv` 删去 `raw_*`、`perf_marg_*` 与累积列，新增 `seq`，并已修正 2 处源文档印刷错误（详见 `WEIGHTS_ANALYSIS.md`）。时刻口径同 1.2：**"SRB IGN" = T-0 = liftoff**；Mach 3 EOM 为再入至马赫 3 时刻；landing 为着陆全停时刻。

| 列名（英制后缀 / 公制后缀） | 含义 | 备注 |
|---|---|---|
| `seq` | 飞行序号（1–135，与 `missions.csv` 的 `flight_seq` 对应） | — |
| `flight` | 任务号 | — |
| `ov_tail` | 轨道器尾号 | — |
| `orb_wt_wo_prop_lbs` / `_kg` | 轨道器不含推进剂干重 | 地面称重值 |
| `non_prop_cons_srb_ign_lbs` / `_kg` | SRB 点火时非推进剂消耗品重量 | T-0 时刻 |
| `oms_prop_lbs` / `_kg` | OMS 推进剂加注量 | 加注量 |
| `rcs_prop_fwd_lbs` / `_kg` | 前舱 RCS 推进剂量 | 加注量 |
| `rcs_prop_aft_lbs` / `_kg` | 后舱 RCS 推进剂量 | 加注量 |
| `orb_wt_srb_ign_lbs` / `_kg` | SRB 点火时轨道器重量 | T-0（含全部推进剂） |
| `orb_plus_pyld_srb_ign_lbs` / `_kg` | SRB 点火时轨道器 + 载荷重量 | T-0 时刻 |
| `orb_wt_orbit_insert_lbs` / `_kg` | 入轨时轨道器重量 | OMS 入轨完成后 |
| `et_wt_srb_ign_lbs` / `_kg` | SRB 点火时外贮箱重量 | T-0（含推进剂） |
| `srb_wt_left_srb_ign_lbs` / `_kg` | 左 SRB 点火重量 | T-0 时刻 |
| `srb_wt_right_srb_ign_lbs` / `_kg` | 右 SRB 点火重量 | T-0 时刻 |
| `shuttle_wt_srb_ign_lbs` / `_kg` | 全系统起飞总重 | T-0（GLOW）；组件之和残差说明同 1.2 |
| `mach3_eom_wt_lbs` / `_kg` | Mach 3 EOM 重量 | 再入至马赫 3 时刻 |
| `mach3_eom_xcg_in` / `_m` | Mach 3 纵向质心 Xcg | 同上时刻 |
| `landing_wt_lbs` / `_kg` | 着陆重量 | 全停时刻 |
| `landing_xcg_in` / `_m` | 着陆纵向质心 Xcg | 全停时刻 |

### 1.4 `space_shuttle_missions.xlsx` 表头说明（4 表单）

| 表单 | 表头 | 备注 |
|---|---|---|
| `Missions` | 与 `missions.csv` 完全相同的 59 列（见 1.1） | 时刻基准说明同 1.1 |
| `Weights_AppendixA` | 与 `weights.csv` 完全相同的 30 列（见 1.2） | 时刻基准说明同 1.2 |
| `Reference_Wikipedia` | 与 `reference/wiki_sts_list.csv` 相同的 6 列（见 1.5） | — |
| `Summary` | `Metric`（统计指标名）+ `Value`（数值）两列汇总表 | 无时间基准列 |

### 1.5 `reference/wiki_sts_list.csv` 表头说明（6 列）

Wikipedia 任务列表外部核对值，列名统一加 `ref_` 前缀以区别于提取值。

| 列名 | 含义 | 备注 |
|---|---|---|
| `seq` | 序号（1–135） | 对应 `flight_seq` |
| `ref_mission` | 任务名 | — |
| `ref_launch_date` | 发射日期 | Wikipedia 列表页日期口径 |
| `ref_orbiter` | 轨道器名 | — |
| `ref_crew` | 乘组人数 | — |
| `ref_duration_h` | 任务时长（小时） | 整小时圆整值 |

## 2. 数据质量结论（详见 `validation_report.md`）

**内部一致性**（0 错误）：
- 135 个飞行序号完整唯一；发射日期随序号单调递增；
- 全部任务时长与"着陆 GMT − 发射 GMT"差值吻合（<3 分钟）；
- 印刷日期与 GMT 时间戳一致（允许当地时区 ±1 天）；
- 任务页与附录 A 双源重量数据完全一致（Mach 3 / 着陆重量可比行 0 差异）；
- 各轨道器飞行序号 1..n 连续；
- 起飞重量组件之和（轨道器+载荷、ET、双 SRB）与总量列在源文档中为独立记账：128 个可比行中 62 行精确相等，残差随附录版面分代（早期 SODB 页偏正、后期 TDDP 页偏负，最大 STS-1 +18,535 lbs）；经与 PDF 原文逐格核对，提取值与印刷值一致，属源文档自身口径而非提取错误，保留原值（详见 `WEIGHTS_ANALYSIS.md` §2(d)）。

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
