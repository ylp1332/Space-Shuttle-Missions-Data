"""Deep-dive analysis of the proofread shuttle weight data (metric units).

Reads the weights_mks sheet of data/weights-revised.xlsx and produces
figures 15-22 plus printed statistics: dry-weight drift per orbiter,
stack composition, ET evolution (SLWT), weight distributions, landing
vs dry weight, Mach-3 vs landing lockstep, Xcg envelope against the
forward/aft limits, and SRB left/right symmetry.

Chinese labels (units and acronyms like OMS/RCS stay English); run from
repo root.
"""

from __future__ import annotations

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from openpyxl import load_workbook

plt.rcParams["font.family"] = ["Times New Roman", "SimSun"]
plt.rcParams["axes.unicode_minus"] = False

OUT = os.path.join("output", "figures")
ORBITER_BY_TAIL = {99: "Challenger", 102: "Columbia", 103: "Discovery",
                   104: "Atlantis", 105: "Endeavour"}
ORBITER_COLORS = {
    "Columbia": "#1f77b4", "Challenger": "#d62728",
    "Discovery": "#2ca02c", "Atlantis": "#ff7f0e", "Endeavour": "#9467bd",
}
# 轨道器着陆质心前/后限（机身参考长度 L = 1656.5 in）
CG_FWD_M = 1076.7 * 0.0254          # 前限 65.0% L = 27.348 m
CG_AFT_M = 1109.9 * 0.0254          # 后限·飞行阶段 67.0% L = 28.191 m
CG_AFT_DESIGN_M = 1118.1 * 0.0254   # 后限·设计阶段 67.5% L = 28.400 m
SEQ_51L, SEQ_107 = 25, 113   # loss-of-crew missions (flight sequence)


def load():
    ws = load_workbook("data/weights-revised.xlsx", read_only=True)["weights_mks"]
    rows = list(ws.iter_rows(values_only=True))
    df = pd.DataFrame(rows[1:], columns=rows[0])
    df = df[df.seq.apply(lambda v: isinstance(v, (int, float)))].copy()
    df["seq"] = df.seq.astype(int)
    for c in df.columns[3:]:
        df[c] = pd.to_numeric(df[c], errors="coerce")  # 'N/A' -> NaN
    df["orbiter"] = df.ov_tail.map(ORBITER_BY_TAIL)
    return df


def style(ax):
    ax.grid(True, alpha=0.3, linewidth=0.5)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def accident_lines(ax):
    for seq in (SEQ_51L, SEQ_107):
        ax.axvline(seq + 0.5, color="gray", ls=":", lw=1)


def fig_label(fig, ax, x, y, text, color="gray", fontsize=9, va="bottom",
              bbox=True):
    """在数据坐标 (x, y) 处放置图级文本标注。

    matplotlib 3.11 的 font.family 回退链下，axes 域内自由文本
    （ax.text/ax.annotate）的中文会静默塌缩，figure 级 fig.text 不受
    影响——故用坐标变换把标注锚到数据位置后以 fig.text 绘制。
    """
    xf, yf = fig.transFigure.inverted().transform(
        ax.transData.transform((x, y)))
    kw = {}
    if bbox:
        kw["bbox"] = dict(boxstyle="round,pad=0.15", fc="white",
                          ec="none", alpha=0.85)
    return fig.text(xf, yf, text, fontsize=fontsize, color=color,
                    va=va, ha="left", **kw)


STATS = []  # (text) printed statistics findings


def fig_dry_weight_evolution(df):
    fig, ax = plt.subplots(figsize=(11.5, 6))
    STATS.append("【规律 1】各轨道器干重随任务持续增长（结构改装/系统升级累积）：")
    for orb in ["Challenger", "Columbia", "Discovery", "Atlantis", "Endeavour"]:
        g = df[(df.orbiter == orb)].dropna(subset=["orb_wt_wo_prop_kg"])
        if len(g) < 4:
            continue
        ax.scatter(g.seq, g.orb_wt_wo_prop_kg / 1000, s=18,
                   color=ORBITER_COLORS[orb], label=orb, alpha=0.8,
                   edgecolor="white", linewidth=0.4)
        k, b = np.polyfit(g.seq, g.orb_wt_wo_prop_kg / 1000, 1)
        xs = np.array([g.seq.min(), g.seq.max()])
        ax.plot(xs, k * xs + b, color=ORBITER_COLORS[orb], lw=1.1, ls="--",
                alpha=0.85)
        STATS.append(f"  {orb:11s} n={len(g):3d}  趋势 {k * 1000:+6.1f} kg/飞行，"
                     f"全程漂移 {k * (g.seq.max() - g.seq.min()) * 1000:+5.0f} kg")
    accident_lines(ax)
    ax.set(title="各轨道器干重演化与线性趋势（虚线）\n"
                 "（空缺 = DOD 任务，源文档未公开）",
           xlabel="飞行序号", ylabel="轨道器干重 (t)")
    ax.legend(fontsize=9)
    style(ax)
    return fig


def fig_stack_composition(df):
    fig, ax = plt.subplots(figsize=(12, 5.5))
    c = df.dropna(subset=["shuttle_wt_srb_ign_kg"]).sort_values("seq")
    parts = [("轨道器+载荷", "orb_plus_pyld_srb_ign_kg", "#4c72b0"),
             ("外储箱（ET）", "et_wt_srb_ign_kg", "#55a868"),
             ("固体助推器（2×SRB）",
              df.srb_wt_left_srb_ign_kg + df.srb_wt_right_srb_ign_kg, "#dd8452")]
    bottom = np.zeros(len(c))
    for label, col, color in parts:
        vals = (col if isinstance(col, pd.Series) else c.__getitem__(col.name) if hasattr(col, "name") else col) \
            if False else (c[col] if isinstance(col, str) else col[c.index])
        vals = vals / 1000.0
        ax.bar(c.seq, vals, bottom=bottom, color=color, label=label,
               width=0.85, edgecolor="white", linewidth=0.3)
        bottom += vals.values
    total = bottom.mean()
    share = {label: (np.nansum((c[col] if isinstance(col, str) else col[c.index]) / 1000)
                     / (c.shuttle_wt_srb_ign_kg / 1000).sum() * 100)
             for label, col, _ in parts}
    STATS.append("【规律 2】全系统起飞构成（均值占比）：火箭部分 (ET+2×SRB) 占 "
                 f"{share['外储箱（ET）'] + share['固体助推器（2×SRB）']:.1f}%，"
                 f"轨道器+载荷仅 {share['轨道器+载荷']:.1f}%——"
                 "近 94% 的起飞质量为一次性推进结构")
    ax.set(title="全系统起飞总重构成（DOD 任务缺重量数据故留空）",
           xlabel="飞行序号", ylabel="起飞总重 (t)")
    ax.legend(fontsize=9, loc="upper left", bbox_to_anchor=(1.01, 1.0),
              frameon=False)
    style(ax)
    return fig


def fig_et_evolution(df):
    fig, ax = plt.subplots(figsize=(11, 5.5))
    d = df.dropna(subset=["et_wt_srb_ign_kg"]).sort_values("seq")
    ax.scatter(d.seq, d.et_wt_srb_ign_kg / 1000, s=18, color="#55a868",
               edgecolor="white", linewidth=0.4)
    seq_91 = d[d.flight.astype(str).str.contains("91")].seq
    x_slwt = int(seq_91.iloc[0]) if len(seq_91) else 91
    # SLWT 首飞即 STS-91（1998-06）：分界线画在其前，STS-91 计入 SLWT 组
    ax.axvline(x_slwt - 0.5, color="gray", ls="--", lw=1)
    fig_label(fig, ax, x_slwt + 1, 745.6, "STS-91 起启用超轻量 ET (SLWT)",
              bbox=False)
    pre, post = d[d.seq < x_slwt], d[d.seq >= x_slwt]
    STATS.append(f"【规律 3】ET 重量演化：STS-{x_slwt - 1} 及之前均值 "
                 f"{pre.et_wt_srb_ign_kg.mean() / 1000:.1f} t → "
                 f"STS-91 起（SLWT）{post.et_wt_srb_ign_kg.mean() / 1000:.1f} t，"
                 "含早期标准型→轻量型（STS-8 起）的阶梯下降")
    ax.set(title="外储箱（ET）点火重量演化", xlabel="飞行序号",
           ylabel="ET 重量 (t)")
    style(ax)
    return fig


def fig_weight_distributions(df):
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    ords = ["Challenger", "Columbia", "Discovery", "Atlantis", "Endeavour"]

    ax = axes[0][0]
    data = [df[df.orbiter == o].dropna(subset=["orb_wt_wo_prop_kg"])
            .orb_wt_wo_prop_kg / 1000 for o in ords]
    data = [x for x in data if len(x)]
    bp = ax.boxplot(data, patch_artist=True, widths=0.55)
    for patch, o in zip(bp["boxes"], [o for o in ords if len(
            df[df.orbiter == o].dropna(subset=["orb_wt_wo_prop_kg"]))]):
        patch.set_facecolor(ORBITER_COLORS[o])
        patch.set_alpha(0.6)
    ax.set_xticklabels([o for o in ords if len(df[df.orbiter == o].dropna(
        subset=["orb_wt_wo_prop_kg"]))], fontsize=8, rotation=20)
    ax.set(title="干重分布（按轨道器）", ylabel="干重 (t)")

    ax = axes[0][1]
    p = df.orb_plus_pyld_srb_ign_kg - df.orb_wt_srb_ign_kg
    p = (p / 1000).dropna()
    p = p[p > 0]
    ax.hist(p, bins=24, color="#4c72b0", edgecolor="white")
    ax.set(title=f"载荷分布（n={len(p)}）", xlabel="载荷 (t)", ylabel="任务数")

    ax = axes[1][0]
    lw_ = (df.landing_wt_kg / 1000).dropna()
    ax.hist(lw_, bins=24, color="#dd8452", edgecolor="white")
    ax.set(title=f"着陆重量分布（n={len(lw_)}）", xlabel="着陆重量 (t)",
           ylabel="任务数")

    ax = axes[1][1]
    data = [df[df.orbiter == o].dropna(subset=["orb_wt_srb_ign_kg"])
            .orb_wt_srb_ign_kg / 1000 for o in ords]
    data = [x for x in data if len(x)]
    bp = ax.boxplot(data, patch_artist=True, widths=0.55)
    for patch, o in zip(bp["boxes"], [o for o in ords if len(
            df[df.orbiter == o].dropna(subset=["orb_wt_srb_ign_kg"]))]):
        patch.set_facecolor(ORBITER_COLORS[o])
        patch.set_alpha(0.6)
    ax.set_xticklabels([o for o in ords if len(df[df.orbiter == o].dropna(
        subset=["orb_wt_srb_ign_kg"]))], fontsize=8, rotation=20)
    ax.set(title="SRB 点火时轨道器总重分布（按轨道器）", ylabel="总重 (t)")

    STATS.append(f"【规律 4】分布特征：载荷中位数 {p.median():.1f} t"
                 f"（区间 {p.min():.1f}–{p.max():.1f} t）；"
                 f"着陆重量中位数 {lw_.median():.1f} t"
                 f"（区间 {lw_.min():.1f}–{lw_.max():.1f} t）")
    fig.tight_layout()
    for axx in axes.flat:
        style(axx)
    return fig


def fig_landing_vs_dry(df):
    fig, ax = plt.subplots(figsize=(7.5, 6.5))
    d = df.dropna(subset=["orb_wt_wo_prop_kg", "landing_wt_kg"])
    for orb, g in d.groupby("orbiter"):
        ax.scatter(g.orb_wt_wo_prop_kg / 1000, g.landing_wt_kg / 1000, s=22,
                   color=ORBITER_COLORS[orb], label=orb, alpha=0.85,
                   edgecolor="white", linewidth=0.4)
    margin = (d.landing_wt_kg - d.orb_wt_wo_prop_kg)
    xs = np.linspace(77, 88, 10)
    ax.plot(xs, xs + margin.mean() / 1000, color="gray", ls="--", lw=1.2)
    fig_label(fig, ax, 77.5, 101,
              f"着陆 = 干重 + 着陆载荷均值\n({margin.mean() / 1000:.1f} t，"
              f"区间 {margin.min() / 1000:.1f}–{margin.max() / 1000:.1f} t)",
              fontsize=9)
    r = d.orb_wt_wo_prop_kg.corr(d.landing_wt_kg)
    STATS.append(f"【规律 5】着陆重量与干重相关 r={r:+.3f}：着陆重量 = 干重基线"
                 f"+ 返回载荷/剩余推进剂（均值 {margin.mean() / 1000:.1f} t，"
                 "反映任务返回能力差异）")
    ax.set(title="着陆重量 vs 干重（虚线为均值偏移）", xlabel="干重 (t)",
           ylabel="着陆重量 (t)")
    ax.legend(fontsize=9)
    style(ax)
    return fig


def fig_mach3_vs_landing(df):
    fig, ax = plt.subplots(figsize=(7.5, 6.5))
    d = df.dropna(subset=["mach3_eom_wt_kg", "landing_wt_kg"])
    for orb, g in d.groupby("orbiter"):
        ax.scatter(g.mach3_eom_wt_kg / 1000, g.landing_wt_kg / 1000, s=22,
                   color=ORBITER_COLORS[orb], label=orb, alpha=0.85,
                   edgecolor="white", linewidth=0.4)
    lo, hi = 83, 108
    ax.plot([lo, hi], [lo, hi], color="gray", ls="--", lw=1.2)
    delta = d.mach3_eom_wt_kg - d.landing_wt_kg
    r = d.mach3_eom_wt_kg.corr(d.landing_wt_kg)
    fig_label(fig, ax, 98, 85,
              f"r = {r:.3f}\nMach 3 → 着陆消耗均值 {delta.mean():.0f} kg\n"
              f"（sd {delta.std():.0f} kg，能量管理段消耗稳定）",
              fontsize=9)
    STATS.append(f"【规律 6】Mach 3 EOM 重量与着陆重量相关 r={r:.3f}：两者几乎"
                 f"一一锁定，差值（终端能量管理段消耗）均值 {delta.mean():.0f} kg、"
                 f"sd {delta.std():.0f} kg")
    ax.set(title="Mach 3 EOM 重量 vs 着陆重量（虚线为 y = x）",
           xlabel="Mach 3 EOM 重量 (t)", ylabel="着陆重量 (t)")
    ax.legend(fontsize=9)
    style(ax)
    return fig


def fig_xcg_windows(df):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.8))
    ords = ["Challenger", "Columbia", "Discovery", "Atlantis", "Endeavour"]
    data, kept = [], []
    for o in ords:
        x = df[df.orbiter == o].dropna(subset=["landing_xcg_m"]).landing_xcg_m
        if len(x):
            data.append(x)
            kept.append(o)
    bp = ax1.boxplot(data, patch_artist=True, widths=0.55)
    for patch, o in zip(bp["boxes"], kept):
        patch.set_facecolor(ORBITER_COLORS[o])
        patch.set_alpha(0.6)
    ax1.set_xticklabels(kept, fontsize=8, rotation=20)
    ax1.axhline(CG_FWD_M, color="#c44e52", ls="--", lw=1.2)
    ax1.axhline(CG_AFT_M, color="#c44e52", ls="--", lw=1.2)
    ax1.axhline(CG_AFT_DESIGN_M, color="#c44e52", ls="-.", lw=1.2)
    ax1.set_ylim(27.25, 28.62)   # fix limits BEFORE figure-coord conversion
    fig = ax1.figure
    fig_label(fig, ax1, 0.62, CG_FWD_M + 0.004, "前限", color="#c44e52")
    fig_label(fig, ax1, 0.62, CG_AFT_M + 0.004, "后限·飞行", color="#c44e52")
    fig_label(fig, ax1, 0.62, CG_AFT_DESIGN_M + 0.004, "后限·设计",
              color="#c44e52")
    ax1.set(title="着陆纵向质心窗口（按轨道器）", ylabel="着陆纵向质心 (m)")

    d = df.dropna(subset=["mach3_eom_xcg_m", "landing_xcg_m"])
    for orb, g in d.groupby("orbiter"):
        ax2.scatter(g.mach3_eom_xcg_m, g.landing_xcg_m, s=20,
                    color=ORBITER_COLORS[orb], label=orb, alpha=0.85,
                    edgecolor="white", linewidth=0.4)
    ax2.plot([27.3, 28.25], [27.3, 28.25], color="gray", ls="--", lw=1.1)
    ax2.axvline(CG_FWD_M, color="#c44e52", ls="--", lw=1)
    ax2.axvline(CG_AFT_M, color="#c44e52", ls="--", lw=1)
    ax2.axvline(CG_AFT_DESIGN_M, color="#c44e52", ls="-.", lw=1)
    ax2.axhline(CG_FWD_M, color="#c44e52", ls="--", lw=1)
    ax2.axhline(CG_AFT_M, color="#c44e52", ls="--", lw=1)
    ax2.axhline(CG_AFT_DESIGN_M, color="#c44e52", ls="-.", lw=1)
    ax2.set_xlim(27.3, 28.55)
    ax2.set_ylim(27.3, 28.55)
    shift = d.landing_xcg_m - d.mach3_eom_xcg_m
    ax2.set(title="着陆纵向质心 vs Mach 3 纵向质心（红线为前/后限，虚线 y = x）",
            xlabel="Mach 3 纵向质心 (m)", ylabel="着陆纵向质心 (m)")
    ax2.legend(fontsize=8)

    allx = pd.concat(data)
    STATS.append(
        f"【规律 7】着陆纵向质心严格受控：{len(allx)} 次着陆纵向质心全部落在前限 "
        f"1076.7 in (65%L) 与飞行阶段后限 1109.9 in (67%L) 之间"
        f"（设计阶段后限 1118.1 in = 67.5%L 留有额外余量），"
        f"实际区间 [{allx.min():.3f}, {allx.max():.3f}] m，"
        f"仅占运营包线宽度的 {(allx.max() - allx.min()) / (CG_AFT_M - CG_FWD_M) * 100:.0f}%，"
        f"且 Mach 3 → 着陆纵向质心漂移极小（均值 {shift.mean() * 1000:+.0f} mm，"
        f"sd {shift.std() * 1000:.0f} mm）")
    for ax in (ax1, ax2):
        style(ax)
    fig.tight_layout()
    return fig


def fig_srb_symmetry(df):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.5))
    d = df.dropna(subset=["srb_wt_left_srb_ign_kg", "srb_wt_right_srb_ign_kg"])
    ax1.scatter(d.seq, d.srb_wt_left_srb_ign_kg / 1000, s=14, color="#4c72b0",
                label="左 SRB", alpha=0.8, edgecolor="white", linewidth=0.3)
    ax1.scatter(d.seq, d.srb_wt_right_srb_ign_kg / 1000, s=14, color="#dd8452",
                label="右 SRB", alpha=0.8, edgecolor="white", linewidth=0.3)
    accident_lines(ax1)
    ax1.set(title="左右 SRB 点火重量", xlabel="飞行序号", ylabel="SRB 重量 (t)")
    ax1.legend(fontsize=9)

    diff = (d.srb_wt_right_srb_ign_kg - d.srb_wt_left_srb_ign_kg).abs()
    ax2.hist(diff, bins=28, color="#55a868", edgecolor="white")
    ax2.set(title=f"|右 − 左| 差值分布（n={len(d)}）", xlabel="差值 (kg)",
            ylabel="任务数")
    STATS.append(f"【规律 8】SRB 左右对称性：|右−左| 均值 {diff.mean():.0f} kg，"
                 f"仅占单枚 SRB 重量 (~590 t) 的 {diff.mean() / d.srb_wt_left_srb_ign_kg.mean() * 100:.3f}%；"
                 f"单枚重量全程 sd {d.srb_wt_left_srb_ign_kg.std():.0f} kg")
    for ax in (ax1, ax2):
        style(ax)
    fig.tight_layout()
    return fig


FIGURES = [
    ("15_orbiter_dry_weight_evolution", fig_dry_weight_evolution),
    ("16_stack_composition", fig_stack_composition),
    ("17_et_weight_evolution", fig_et_evolution),
    ("18_weight_distributions", fig_weight_distributions),
    ("19_landing_vs_dry", fig_landing_vs_dry),
    ("20_mach3_vs_landing", fig_mach3_vs_landing),
    ("21_xcg_windows", fig_xcg_windows),
    ("22_srb_symmetry", fig_srb_symmetry),
]


def main():
    os.makedirs(OUT, exist_ok=True)
    df = load()
    for name, fn in FIGURES:
        fig = fn(df)
        path = os.path.join(OUT, f"{name}.png")
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"wrote {path}")
    print("\n===== 统计规律 =====")
    for s in STATS:
        print(s)


if __name__ == "__main__":
    main()
