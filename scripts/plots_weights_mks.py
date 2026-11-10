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

OUT = os.path.join("output", "figures")
WB = "data/weights-revised.xlsx"
SHEET = "weights_mks"

ORBITER_BY_TAIL = {99: "Challenger", 102: "Columbia", 103: "Discovery",
                   104: "Atlantis", 105: "Endeavour"}
ORBITER_COLORS = {
    "Columbia": "#1f77b4", "Challenger": "#d62728",
    "Discovery": "#2ca02c", "Atlantis": "#ff7f0e", "Endeavour": "#9467bd",
}


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
    ax.annotate("Challenger accident", xy=(27, d.liftoff_t.min()),
                fontsize=8, color="gray")
    ax.annotate("Columbia accident", xy=(115, d.liftoff_t.min()),
                fontsize=8, color="gray")
    ax.set(title="Shuttle stack liftoff weight by flight (metric)",
           xlabel="Flight sequence", ylabel="Liftoff weight (t)")
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
        note = ("excluded (payload <= 0, source printing error): "
                + ", ".join(dropped.flight))
        fig.text(0.99, 0.005, note, ha="right", va="bottom", fontsize=7.5,
                 color="gray")
    d = d[d.payload_t > 0]
    scatter_by_orbiter(ax, d, "payload_t")
    for seq, _ in accident_lines(df):
        ax.axvline(seq + 0.5, color="gray", ls="--", lw=1)
    ax.set(title="Payload mass at SRB ignition by flight\n"
                 "(gaps = DOD flights, weights unpublished in source)",
           xlabel="Flight sequence", ylabel="Payload (t)")
    ax.legend(fontsize=9)
    style(ax)
    return fig


def fig_propellant_loading(df):
    fig, ax = plt.subplots(figsize=(12, 5.5))
    cols = [("oms_prop_kg", "OMS propellant", "#4c72b0"),
            ("rcs_prop_fwd_kg", "RCS propellant (fwd)", "#dd8452"),
            ("rcs_prop_aft_kg", "RCS propellant (aft)", "#55a868")]
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
    ax.set(title="Orbiter propellant loading at SRB ignition "
                 "(gaps = DOD flights, unpublished in source)",
           xlabel="Flight sequence", ylabel="Propellant loaded (kg)")
    ax.legend(fontsize=9, loc="upper left", bbox_to_anchor=(1.01, 1.0),
              frameon=False)
    style(ax)
    return fig


def fig_landing_xcg(df):
    fig, ax = plt.subplots(figsize=(11, 5.5))
    m = df.landing_xcg_m.apply(lambda v: isinstance(v, (int, float)))
    d = df[m]
    scatter_by_orbiter(ax, d, "landing_xcg_m")
    for seq, _ in accident_lines(df):
        ax.axvline(seq + 0.5, color="gray", ls=":", lw=1)
    ax.set(title="Landing center of gravity (X c.g.) by flight\n"
                 "STS-107 landing data absent (loss on re-entry)",
           xlabel="Flight sequence", ylabel="Landing X c.g. (m)")
    ax.legend(fontsize=9)
    style(ax)
    return fig


FIGURES = [
    ("11_liftoff_stack_weight", fig_liftoff_stack_weight),
    ("12_payload_to_orbit", fig_payload_to_orbit),
    ("13_propellant_loading", fig_propellant_loading),
    ("14_landing_xcg", fig_landing_xcg),
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
