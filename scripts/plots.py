"""Generate analysis figures from the extracted shuttle mission data.

Reads data/missions.csv + data/weights.csv, writes PNGs to
output/figures/.  All charts are English-labelled; run from repo root.
"""

from __future__ import annotations

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

OUT = os.path.join("output", "figures")

ORBITER_COLORS = {
    "Columbia": "#1f77b4", "Challenger": "#d62728",
    "Discovery": "#2ca02c", "Atlantis": "#ff7f0e", "Endeavour": "#9467bd",
}
ACCIDENTS = [("1986-01-28", "Challenger\n(STS-51-L)"),
             ("2003-02-01", "Columbia\n(STS-107)")]


def load():
    m = pd.read_csv("data/missions.csv", dtype={"base": str})
    flown = m[m.cancelled == 0].copy()
    flown["flight_seq"] = flown.flight_seq.astype(int)
    flown["launch_dt"] = pd.to_datetime(flown.launch_dt_utc)
    flown["duration_h"] = flown.duration_hours
    w = pd.read_csv("data/weights.csv", dtype={"base": str})
    j = flown.merge(w, on="base", how="left")
    return flown, j


def style(ax):
    ax.grid(True, alpha=0.3, linewidth=0.5)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def fig_launches_per_year(f):
    fig, ax = plt.subplots(figsize=(10, 5))
    per = f.groupby(f.launch_dt.dt.year).size().reindex(range(1981, 2012), fill_value=0)
    colors = ["#d62728" if y in (1986, 2003) else "#4c72b0" for y in per.index]
    ax.bar(per.index, per.values, color=colors, edgecolor="white")
    for y, label in ACCIDENTS:
        ax.axvline(pd.Timestamp(y).year + 0.5, color="gray", ls="--", lw=1)
    ax.annotate("Challenger accident", xy=(1986.7, 9), fontsize=8, color="gray")
    ax.annotate("Columbia accident", xy=(2003.7, 5), fontsize=8, color="gray")
    ax.set(title="Space Shuttle launches per year (1981-2011)",
           xlabel="Year", ylabel="Launches")
    ax.set_xticks(range(1981, 2012, 2))
    style(ax)
    return fig


def fig_orbiter_flights(f):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    order = ["Columbia", "Challenger", "Discovery", "Atlantis", "Endeavour"]
    counts = f.orbiter.value_counts().reindex(order)
    axes[0].bar(order, counts.values,
                color=[ORBITER_COLORS[o] for o in order], edgecolor="white")
    for i, v in enumerate(counts.values):
        axes[0].text(i, v + 0.5, str(v), ha="center", fontsize=10)
    axes[0].set(title="Flights per orbiter", ylabel="Flights")
    style(axes[0])
    data = [f[f.orbiter == o].duration_h.dropna() / 24 for o in order]
    bp = axes[1].boxplot(data, tick_labels=order, patch_artist=True,
                         showfliers=True,
                         flierprops=dict(marker=".", markersize=3))
    for patch, o in zip(bp["boxes"], order):
        patch.set_facecolor(ORBITER_COLORS[o])
        patch.set_alpha(0.7)
    axes[1].set(title="Mission duration by orbiter", ylabel="Duration (days)")
    axes[1].tick_params(axis="x", rotation=20)
    style(axes[1])
    fig.tight_layout()
    return fig


def fig_duration_evolution(f):
    fig, ax = plt.subplots(figsize=(11, 5.5))
    for orb, g in f.groupby("orbiter"):
        ax.scatter(g.flight_seq, g.duration_h / 24, s=22,
                   color=ORBITER_COLORS[orb], label=orb, alpha=0.85,
                   edgecolor="white", linewidth=0.4)
    x = f.flight_seq.values
    y = (f.duration_h / 24).values
    z = np.polyfit(x, y, 2)
    xs = np.linspace(1, 135, 300)
    ax.plot(xs, np.polyval(z, xs), color="black", lw=1.5, ls="--",
            label="quadratic trend")
    for d, label in ACCIDENTS:
        seq = f[f.launch_date <= d].flight_seq.max()
        ax.axvline(seq + 0.5, color="gray", ls=":", lw=1)
    ax.annotate("gap after Challenger", xy=(28, 16.5), fontsize=8, color="gray")
    ax.annotate("gap after Columbia", xy=(114, 16.5), fontsize=8, color="gray")
    ax.set(title="Mission duration across the program (135 flights)",
           xlabel="Flight sequence", ylabel="Duration (days)")
    ax.legend(loc="lower right", ncol=3, fontsize=8)
    style(ax)
    return fig


def fig_crew_evolution(f):
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.scatter(f.flight_seq, f.crew_size, s=25, c="#4c72b0",
               edgecolor="white", linewidth=0.4)
    roll = f.sort_values("flight_seq").crew_size.rolling(9, center=True).mean()
    ax.plot(f.sort_values("flight_seq").flight_seq, roll, color="#c44e52", lw=2,
            label="9-flight rolling mean")
    ax.set(title="Crew size evolution", xlabel="Flight sequence",
           ylabel="Crew members")
    ax.set_yticks(range(2, 9))
    ax.legend()
    style(ax)
    return fig


def fig_inclination(f):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    inc = f.inclination_deg.dropna()
    axes[0].hist(inc, bins=np.arange(28, 63, 1.0), color="#4c72b0",
                 edgecolor="white")
    axes[0].set(title="Orbit inclination distribution",
                xlabel="Inclination (deg)", ylabel="Flights")
    style(axes[0])
    for orb, g in f.groupby("orbiter"):
        axes[1].scatter(g.flight_seq, g.inclination_deg, s=20,
                        color=ORBITER_COLORS[orb], label=orb, alpha=0.8,
                        edgecolor="white", linewidth=0.4)
    axes[1].axhline(51.6, color="gray", ls=":", lw=1)
    axes[1].annotate("ISS 51.6 deg", xy=(5, 52.6), fontsize=8, color="gray")
    axes[1].axhline(28.45, color="gray", ls=":", lw=1)
    axes[1].annotate("KSC due-east 28.45 deg", xy=(5, 29.2), fontsize=8, color="gray")
    axes[1].set(title="Inclination over the program", xlabel="Flight sequence",
                ylabel="Inclination (deg)")
    axes[1].legend(fontsize=8, loc="center right")
    style(axes[1])
    fig.tight_layout()
    return fig


def fig_landing_sites(f):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    site = f.landing_site.dropna().str.extract(r"^(EDW|KSC|WSMR|NOR|WSSH|DFR)",
                                               expand=False)
    counts = site.value_counts()
    colors = {"KSC": "#4c72b0", "EDW": "#dd8452", "WSMR": "#937860"}
    axes[0].bar(counts.index, counts.values,
                color=[colors.get(s, "gray") for s in counts.index],
                edgecolor="white")
    for i, v in enumerate(counts.values):
        axes[0].text(i, v + 0.8, str(v), ha="center", fontsize=10)
    axes[0].set(title="Landing site totals (133 landed missions)",
                ylabel="Landings")
    style(axes[0])
    g = f.dropna(subset=["landing_date"]).copy()
    g["site"] = g.landing_site.str.extract(r"^(EDW|KSC|WSMR|NOR|WSSH|DFR)",
                                           expand=False)
    g["year"] = pd.to_datetime(g.landing_date).dt.year
    piv = (g.groupby(["year", "site"]).size().unstack(fill_value=0))
    piv = piv.div(piv.sum(axis=1), axis=0)
    bottom = np.zeros(len(piv))
    for s in piv.columns:
        axes[1].bar(piv.index, piv[s], bottom=bottom, label=s,
                    color=colors.get(s, "gray"), edgecolor="white", width=0.8)
        bottom += piv[s].values
    axes[1].set(title="KSC vs Edwards landings over time", xlabel="Year",
                ylabel="Share of landings", ylim=(0, 1))
    axes[1].legend(fontsize=8, loc="lower right")
    style(axes[1])
    fig.tight_layout()
    return fig


def fig_launch_hours(f):
    fig, ax = plt.subplots(figsize=(10, 5))
    hours = f.launch_dt.dt.hour + f.launch_dt.dt.minute / 60
    n, bins, patches = ax.hist(hours, bins=24, range=(0, 24),
                               color="#4c72b0", edgecolor="white")
    for p, h in zip(patches, range(24)):
        # night at KSC (EST/EDT ~ UTC-5): 01-11 UTC
        if h in range(1, 11):
            p.set_facecolor("#55a868")
    ax.set(title="Liftoff time of day (UTC, green = night at Kennedy)",
           xlabel="Hour of day (UTC)", ylabel="Launches",
           xticks=range(0, 25, 2))
    style(ax)
    return fig


def fig_weight_evolution(j):
    fig, ax = plt.subplots(figsize=(11, 5.5))
    d = j.dropna(subset=["shuttle_wt_srb_ign_lbs"]).sort_values("flight_seq")
    ax.scatter(d.flight_seq, d.shuttle_wt_srb_ign_lbs / 1e6, s=20,
               color="#4c72b0", label="Liftoff (Shuttle stack)", alpha=0.85,
               edgecolor="white", linewidth=0.4)
    d2 = j.dropna(subset=["landing_wt_lbs"]).sort_values("flight_seq")
    ax.scatter(d2.flight_seq, d2.landing_wt_lbs / 1e3, s=18, color="#dd8452",
               label="Orbiter at landing", alpha=0.85, edgecolor="white",
               linewidth=0.4)
    d3 = j.dropna(subset=["orb_wt_wo_prop_lbs"]).sort_values("flight_seq")
    ax.scatter(d3.flight_seq, d3.orb_wt_wo_prop_lbs / 1e3, s=18,
               color="#c44e52", label="Orbiter dry + residuals", alpha=0.85,
               edgecolor="white", linewidth=0.4)
    ax.set(title="Weight evolution across the program (Appendix A)",
           xlabel="Flight sequence", ylabel="Weight (klbs / Mlbs)")
    ax.legend(fontsize=9)
    style(ax)
    return fig


def fig_et_impact(j):
    fig, ax = plt.subplots(figsize=(10, 5))
    d = j.dropna(subset=["et_impact_lat", "et_impact_long"])
    lat_raw = d.et_impact_lat.astype(str)
    lon_raw = d.et_impact_long.astype(str)
    lat = lat_raw.str.extract(r"^([\d.]+)", expand=False).astype(float) \
        * np.where(lat_raw.str.contains("S"), -1, 1)
    lon = lon_raw.str.extract(r"^([\d.]+)", expand=False).astype(float) \
        * np.where(lon_raw.str.contains("W"), -1, 1)
    ok = lat.notna() & lon.notna()
    d, lat, lon = d[ok], lat[ok], lon[ok]
    sc = ax.scatter(lon, lat, c=d.flight_seq, cmap="viridis", s=30,
                    edgecolor="white", linewidth=0.4)
    ax.set(title="External Tank impact points (%d flights with data)" % len(d),
           xlabel="Longitude (deg)", ylabel="Latitude (deg)")
    ax.axhline(0, color="gray", lw=0.6, ls=":")
    plt.colorbar(sc, ax=ax, label="Flight sequence")
    style(ax)
    return fig


def fig_flight_rate(f):
    fig, ax = plt.subplots(figsize=(11, 5))
    s = f.sort_values("launch_dt")
    gaps = s.launch_dt.diff().dt.total_seconds() / 86400
    ax.bar(s.flight_seq, gaps.clip(upper=200), color="#4c72b0",
           edgecolor="white", width=0.8)
    ax.set(title="Days between consecutive launches (clipped at 200)",
           xlabel="Flight sequence", ylabel="Gap (days)")
    ax2 = ax.twinx()
    per = s.groupby(s.launch_dt.dt.year).size()
    ax2.plot(per.index, per.values, color="#c44e52", marker="o", ms=4, lw=1.5)
    ax2.set_ylabel("Launches per year", color="#c44e52")
    ax2.tick_params(axis="y", colors="#c44e52")
    ax2.spines["top"].set_visible(False)
    for d, label in ACCIDENTS:
        seq = f[f.launch_date <= d].flight_seq.max()
        ax.axvline(seq + 0.5, color="gray", ls=":", lw=1)
    style(ax)
    return fig


def main():
    os.makedirs(OUT, exist_ok=True)
    flown, j = load()
    figs = {
        "01_launches_per_year": fig_launches_per_year(flown),
        "02_orbiter_flights": fig_orbiter_flights(flown),
        "03_duration_evolution": fig_duration_evolution(flown),
        "04_crew_evolution": fig_crew_evolution(flown),
        "05_inclination": fig_inclination(flown),
        "06_landing_sites": fig_landing_sites(flown),
        "07_launch_hours": fig_launch_hours(flown),
        "08_weight_evolution": fig_weight_evolution(j),
        "09_et_impact": fig_et_impact(j),
        "10_flight_rate": fig_flight_rate(flown),
    }
    for name, fig in figs.items():
        path = os.path.join(OUT, f"{name}.png")
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print("wrote", path)
    print(f"\n{len(figs)} figures written to {OUT}")


if __name__ == "__main__":
    main()
