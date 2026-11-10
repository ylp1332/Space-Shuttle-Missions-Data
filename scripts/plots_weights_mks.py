"""Analysis figures for the proofread metric-unit weight data.

Reads the weights_mks sheet of data/weights-revised.xlsx (kg / m columns,
renamed from the Appendix A lbs / in data) and writes PNGs to
output/figures/.  English labels; run from repo root.

DOD flights (weights unpublished in the source document) and the two
loss-of-crew missions appear as gaps in the series, which is faithful to
the source.
"""

from __future__ import annotations

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from openpyxl import load_workbook

# 中文宋体、西文与数字 Times New Roman（font.family 列表 = 逐字形回退链；
# 3.11 中 font.sans-serif 列表不会回退，须用 font.family）
plt.rcParams["font.family"] = ["Times New Roman", "SimSun"]
plt.rcParams["axes.unicode_minus"] = False

OUT = os.path.join("output", "figures")
WB = "data/weights-revised.xlsx"
SHEET = "weights_mks"

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
L_REF_IN = 1656.5                   # 机身参考长度（in）
L_REF_M = L_REF_IN * 0.0254         # 42.075 m


def load():
    ws = load_workbook(WB, read_only=True)[SHEET]
    rows = list(ws.iter_rows(values_only=True))
    df = pd.DataFrame(rows[1:], columns=rows[0])
    df = df[df.seq.apply(lambda v: isinstance(v, (int, float)))].copy()
    df["seq"] = df.seq.astype(int)
    df["orbiter"] = df.ov_tail.map(ORBITER_BY_TAIL)
    return df


def accident_lines(df):
    """Vertical markers at the two loss-of-crew missions, by flight seq."""
    seq_51l = df.loc[df.flight.astype(str).str.contains("51-L"), "seq"]
    seq_107 = df.loc[df.flight.astype(str).str.contains("107"), "seq"]
    lines = []
    for seq, label in [(seq_51l.iloc[0] if len(seq_51l) else 25, "Challenger (STS 51-L)"),
                       (seq_107.iloc[0] if len(seq_107) else 113, "Columbia (STS-107)")]:
        lines.append((seq, label))
    return lines


def style(ax):
    ax.grid(True, alpha=0.3, linewidth=0.5)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def scatter_by_orbiter(ax, d, y, **kw):
    for orb, g in d.groupby("orbiter"):
        ax.scatter(g.seq, g[y], s=20, color=ORBITER_COLORS[orb], label=orb,
                   alpha=0.85, edgecolor="white", linewidth=0.4, **kw)


def fig_liftoff_stack_weight(df):
    fig, ax = plt.subplots(figsize=(11, 5.5))
    d = df[df.shuttle_wt_srb_ign_kg.apply(lambda v: isinstance(v, (int, float)))].copy()
    d["liftoff_t"] = d.shuttle_wt_srb_ign_kg / 1000.0
    scatter_by_orbiter(ax, d, "liftoff_t")
    for seq, label in accident_lines(df):
        ax.axvline(seq + 0.5, color="gray", ls="--", lw=1)
    fig_label(fig, ax, 27, d.liftoff_t.min(), "挑战者号事故")
    fig_label(fig, ax, 95, d.liftoff_t.min(), "哥伦比亚号事故", bbox=False)
    ax.set(title="历次飞行全系统起飞总重（公制单位）",
           xlabel="飞行序号", ylabel="起飞总重 (t)")
    ax.legend(fontsize=9)
    style(ax)
    return fig


def fig_payload_to_orbit(df):
    fig, ax = plt.subplots(figsize=(11, 5.5))
    m = df.apply(lambda r: isinstance(r.orb_plus_pyld_srb_ign_kg, (int, float))
                 and isinstance(r.orb_wt_srb_ign_kg, (int, float)), axis=1)
    d = df[m].copy()
    d["payload_t"] = (d.orb_plus_pyld_srb_ign_kg - d.orb_wt_srb_ign_kg) / 1000.0
    dropped = d[d.payload_t <= 0]
    if len(dropped):
        print(f"note: excluded non-positive payload rows: {dropped.flight.tolist()}")
        note = ("已排除（载荷 <= 0，源文档印刷错误）: "
                + ", ".join(dropped.flight))
        fig.text(0.99, 0.005, note, ha="right", va="bottom", fontsize=7.5,
                 color="gray")
    d = d[d.payload_t > 0]
    scatter_by_orbiter(ax, d, "payload_t")
    for seq, _ in accident_lines(df):
        ax.axvline(seq + 0.5, color="gray", ls="--", lw=1)
    ax.set(title="历次飞行 SRB 点火时载荷\n"
                 "（空缺 = DOD 任务，源文档未公开重量）",
           xlabel="飞行序号", ylabel="载荷 (t)")
    ax.legend(fontsize=9)
    style(ax)
    return fig


def fig_propellant_loading(df):
    fig, ax = plt.subplots(figsize=(12, 5.5))
    cols = [("oms_prop_kg", "OMS 推进剂", "#4c72b0"),
            ("rcs_prop_fwd_kg", "RCS 推进剂（前舱）", "#dd8452"),
            ("rcs_prop_aft_kg", "RCS 推进剂（后舱）", "#55a868")]
    num = df.apply(lambda r: all(isinstance(r[c], (int, float)) for c, _, _ in cols), axis=1)
    d = df[num].sort_values("seq")
    bottom = [0.0] * len(d)
    for col, label, color in cols:
        vals = d[col].tolist()
        ax.bar(d.seq, vals, bottom=bottom, color=color, label=label,
               edgecolor="white", linewidth=0.3, width=0.85)
        bottom = [b + v for b, v in zip(bottom, vals)]
    for seq, _ in accident_lines(df):
        ax.axvline(seq + 0.5, color="gray", ls=":", lw=1)
    ax.set(title="SRB 点火时轨道器推进剂加注\n"
                 "（空缺 = DOD 任务，源文档未公开）",
           xlabel="飞行序号", ylabel="推进剂加注量 (kg)")
    ax.legend(fontsize=9, loc="upper left", bbox_to_anchor=(1.01, 1.0),
              frameon=False)
    style(ax)
    return fig


def _draw_xcg_panel(ax, d, ycol, df, ylabel, subtitle, fwd, aft, aft_design,
                    ylim, labels):
    """Shared rendering for the Xcg figures (limits + annotations).

    fwd/aft/aft_design/ylim are given in the panel's own y-units
    (metres or % of reference length); labels = (forward, aft-flight,
    aft-design) annotation texts.
    """
    scatter_by_orbiter(ax, d, ycol)
    for seq, _ in accident_lines(df):
        ax.axvline(seq + 0.5, color="gray", ls=":", lw=1)
    ax.axhline(fwd, color="#c44e52", ls="--", lw=1.2)
    ax.axhline(aft, color="#c44e52", ls="--", lw=1.2)
    ax.axhline(aft_design, color="#c44e52", ls="-.", lw=1.2)
    pad = (ylim[1] - ylim[0]) * 0.012
    ax.set_ylim(*ylim)   # fix axis limits BEFORE converting to figure coords
    fig = ax.figure
    for y, text in ((fwd, labels[0]), (aft, labels[1]),
                    (aft_design, labels[2])):
        fig_label(fig, ax, 2, y + pad, text, color="#c44e52")
    ax.set(title=subtitle, xlabel="飞行序号", ylabel=ylabel)
    ax.legend(fontsize=9)
    style(ax)


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


M_LIM = (CG_FWD_M, CG_AFT_M, CG_AFT_DESIGN_M, (27.25, 28.62))
PCT_LIM = (CG_FWD_M / L_REF_M * 100, CG_AFT_M / L_REF_M * 100,
           CG_AFT_DESIGN_M / L_REF_M * 100, (64.8, 68.05))
M_LABELS = ("纵向质心前限 65.0% L（1076.7 in）",
            "纵向质心后限·飞行阶段 1109.9 in（67.0% L）",
            "纵向质心后限·设计阶段 1118.1 in（67.5% L）")
PCT_LABELS = ("纵向质心前限 65.0% L（1076.7 in）",
              "纵向质心后限·飞行阶段 1109.9 in（67.0% L）",
              "纵向质心后限·设计阶段 1118.1 in（67.5% L）")


def fig_landing_xcg(df):
    fig, ax = plt.subplots(figsize=(11, 5.5))
    m = df.landing_xcg_m.apply(lambda v: isinstance(v, (int, float)))
    _draw_xcg_panel(ax, df[m], "landing_xcg_m", df, "着陆纵向质心 (m)",
                    "历次飞行着陆纵向质心（含前/后限）\n"
                    "STS-107 无着陆数据（再入失事）",
                    *M_LIM, M_LABELS)
    return fig


def fig_mach3_xcg(df):
    fig, ax = plt.subplots(figsize=(11, 5.5))
    m = df.mach3_eom_xcg_m.apply(lambda v: isinstance(v, (int, float)))
    _draw_xcg_panel(ax, df[m], "mach3_eom_xcg_m", df, "Mach 3 EOM 纵向质心 (m)",
                    "历次飞行 Mach 3 EOM 纵向质心位置（含前/后限）\n"
                    "STS-107 与 DOD 任务无数据",
                    *M_LIM, M_LABELS)
    return fig


def fig_landing_xcg_percent(df):
    """与图 14 对应的相对纵向质心位置版：Xcg / L_ref，百分比表示。

    限位线按 in 值精确换算：前限 1076.7/1656.5 = 65.00%；
    后限·飞行阶段 1109.9/1656.5 = 67.00%；后限·设计阶段 1118.1 in = 67.50%。
    """
    fig, ax = plt.subplots(figsize=(11, 5.5))
    m = df.landing_xcg_m.apply(lambda v: isinstance(v, (int, float)))
    d = df[m].copy()
    d["xcg_pct"] = d.landing_xcg_m / L_REF_M * 100.0
    _draw_xcg_panel(ax, d, "xcg_pct", df, "着陆纵向质心 (% L)",
                    "历次飞行着陆相对纵向质心位置（% 机身参考长度 L）\n"
                    "L = 1656.5 in；STS-107 无着陆数据（再入失事）",
                    *PCT_LIM, PCT_LABELS)
    return fig


def fig_mach3_xcg_percent(df):
    """与图 24 对应的相对纵向质心位置版：Mach 3 EOM Xcg / L_ref（%）。"""
    fig, ax = plt.subplots(figsize=(11, 5.5))
    m = df.mach3_eom_xcg_m.apply(lambda v: isinstance(v, (int, float)))
    d = df[m].copy()
    d["xcg_pct"] = d.mach3_eom_xcg_m / L_REF_M * 100.0
    _draw_xcg_panel(ax, d, "xcg_pct", df, "Mach 3 EOM 纵向质心 (% L)",
                    "历次飞行 Mach 3 EOM 相对纵向质心位置（% 机身参考长度 L）\n"
                    "L = 1656.5 in；STS-107 与 DOD 任务无数据",
                    *PCT_LIM, PCT_LABELS)
    return fig


def fig_landing_weight(df):
    fig, ax = plt.subplots(figsize=(11, 5.5))
    m = df.landing_wt_kg.apply(lambda v: isinstance(v, (int, float)))
    d = df[m].copy()
    d["landing_t"] = d.landing_wt_kg / 1000.0
    scatter_by_orbiter(ax, d, "landing_t")
    for seq, _ in accident_lines(df):
        ax.axvline(seq + 0.5, color="gray", ls=":", lw=1)
    ax.set(title="历次飞行着陆重量\n"
                 "STS-107 无着陆数据（再入失事）；DOD 任务无重量数据",
           xlabel="飞行序号", ylabel="着陆重量 (t)")
    ax.legend(fontsize=9)
    style(ax)
    return fig


def fig_landing_payload(df):
    """着陆载荷 = 着陆重量 - 轨道器干重（返回载荷 + 剩余推进剂 + 消耗品残余）。"""
    fig, ax = plt.subplots(figsize=(11, 5.5))
    m = df.apply(lambda r: isinstance(r.landing_wt_kg, (int, float))
                 and isinstance(r.orb_wt_wo_prop_kg, (int, float)), axis=1)
    d = df[m].copy()
    d["return_t"] = (d.landing_wt_kg - d.orb_wt_wo_prop_kg) / 1000.0
    scatter_by_orbiter(ax, d, "return_t")
    mean_t = d.return_t.mean()
    ax.axhline(mean_t, color="gray", ls="--", lw=1.1)
    fig_label(fig, ax, 2, mean_t + 0.35,
              f"着陆载荷均值 {mean_t:.1f} t\n（区间 {d.return_t.min():.1f}"
              f"–{d.return_t.max():.1f} t）", fontsize=9)
    for seq, _ in accident_lines(df):
        ax.axvline(seq + 0.5, color="gray", ls=":", lw=1)
    ax.set(title="历次飞行着陆载荷（着陆重量 − 轨道器干重）\n"
                 "= 返回载荷 + 剩余推进剂 + 消耗品残余",
           xlabel="飞行序号", ylabel="着陆载荷 (t)")
    ax.legend(fontsize=9)
    style(ax)
    return fig


def fig_orbiter_dry_weight(df):
    """轨道器干重散点图（样式与图 27 着陆载荷对应：均值线 + 注记）。"""
    fig, ax = plt.subplots(figsize=(11, 5.5))
    m = df.orb_wt_wo_prop_kg.apply(lambda v: isinstance(v, (int, float)))
    d = df[m].copy()
    d["dry_t"] = d.orb_wt_wo_prop_kg / 1000.0
    scatter_by_orbiter(ax, d, "dry_t")
    mean_t = d.dry_t.mean()
    ax.axhline(mean_t, color="gray", ls="--", lw=1.1)
    fig_label(fig, ax, 2, mean_t + 0.35,
              f"轨道器干重均值 {mean_t:.1f} t\n（区间 {d.dry_t.min():.1f}"
              f"–{d.dry_t.max():.1f} t）", fontsize=9)
    for seq, _ in accident_lines(df):
        ax.axvline(seq + 0.5, color="gray", ls=":", lw=1)
    ax.set(title="历次飞行轨道器干重\n"
                 "（空缺 = DOD 任务，源文档未公开重量）",
           xlabel="飞行序号", ylabel="轨道器干重 (t)")
    ax.legend(fontsize=9)
    style(ax)
    return fig


FIGURES = [
    ("11_liftoff_stack_weight", fig_liftoff_stack_weight),
    ("12_payload_to_orbit", fig_payload_to_orbit),
    ("13_propellant_loading", fig_propellant_loading),
    ("14_landing_xcg", fig_landing_xcg),
    ("23_landing_xcg_percent", fig_landing_xcg_percent),
    ("24_mach3_xcg", fig_mach3_xcg),
    ("25_mach3_xcg_percent", fig_mach3_xcg_percent),
    ("26_landing_weight", fig_landing_weight),
    ("27_landing_payload", fig_landing_payload),
    ("28_orbiter_dry_weight", fig_orbiter_dry_weight),
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
    print(f"\n{len(FIGURES)} figures written to {OUT}")


if __name__ == "__main__":
    main()
