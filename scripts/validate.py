"""Validation of the extracted shuttle mission data.

Two levels:
1. internal consistency (dates vs GMT stamps, duration vs GMT deltas,
   cross-source weights mission page vs Appendix A, orbiter flight
   numbering, sum identities)
2. external cross-check against a reference dataset
   (data/reference/wiki_sts_list.csv) - launch dates, durations,
   orbiters, crew sizes.

Run from the repository root.  Writes output/reports/validation_report.md;
exits nonzero on any severity-1 failure.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd


def load():
    m = pd.read_csv("data/missions.csv", dtype={"base": str})
    w = pd.read_csv("data/weights.csv", dtype={"base": str})
    flown = m[m.cancelled == 0].copy()
    flown["flight_seq"] = flown.flight_seq.astype(int)
    j = flown.merge(w, on="base", how="left", suffixes=("", "_w"))
    return m, w, j


CHECKS: list[dict] = []


def check(name: str, severity: int, detail: str, issues):
    n = len(issues) if issues is not None else 0
    CHECKS.append({"check": name, "severity": severity, "issues": n})
    tag = "FAIL" if (severity == 1 and n) else ("WARN" if n else " ok ")
    print(f"[{tag}] {name}: {n} issue(s)  {detail}")


def internal_checks(m, j):
    report = ["## 1. Internal consistency", ""]

    seqs = set(m[m.cancelled == 0].flight_seq.dropna().astype(int))
    check("flight sequence 1..135 complete", 1, "all 135 flown sequences present",
          [] if seqs == set(range(1, 136)) else ["missing"])

    s = j.sort_values("flight_seq")
    bad = s[s.launch_date < s.launch_date.shift()]
    check("launch dates monotonic by sequence", 1, "",
          bad[["designation", "launch_date"]] if len(bad) else [])

    # printed dates are local (EST/EDT), GMT stamps are UTC: a +-1 day
    # offset is a time-zone artefact, not an error
    j["gmt_date"] = pd.to_datetime(j.launch_dt_utc).dt.date.astype(str)
    d_off = (pd.to_datetime(j.gmt_date) - pd.to_datetime(j.launch_date)).abs().dt.days
    mism = j[(d_off > 1) | (d_off.isna() & j.launch_dt_utc.notna())]
    check("GMT liftoff date within +-1 day of printed launch date", 1, "",
          mism[["designation", "launch_date", "gmt_date"]] if len(mism) else [])

    j["ws_date"] = pd.to_datetime(j.wheels_stop_utc).dt.date.astype(str)
    d_off = (pd.to_datetime(j.ws_date) - pd.to_datetime(j.landing_date)).abs().dt.days
    mism = j[j.landing_date.notna() & j.ws_date.notna() & (d_off > 1)]
    check("landing date within +-1 day of wheels-stop GMT date", 2,
          "time-zone day shifts allowed",
          mism[["designation", "landing_date", "ws_date"]] if len(mism) else [])

    j["derived_h"] = ((pd.to_datetime(j.touchdown_utc)
                       - pd.to_datetime(j.launch_dt_utc)).dt.total_seconds() / 3600)
    cmp_ = j[j.derived_h.notna() & j.duration_hours.notna()].copy()
    cmp_["diff_min"] = (cmp_.duration_hours - cmp_.derived_h).abs() * 60
    big = cmp_[cmp_.diff_min > 3]
    check("duration matches GMT delta (<3 min)", 1, "",
          big[["designation", "duration", "diff_min"]] if len(big) else [])

    gaps = []
    for orb, g in j.groupby("orbiter"):
        nums = sorted(g.orbiter_flight_no.dropna().astype(int))
        if nums and nums != list(range(1, len(nums) + 1)):
            gaps.append(f"{orb}: {nums}")
    check("orbiter flight numbering continuous", 2, str(gaps),
          gaps if gaps else [])

    for page_col, w_col, label in (
            ("mach3_weight_lbs", "mach3_eom_wt_lbs", "Mach-3 EOM weight"),
            ("landing_weight_lbs", "landing_wt_lbs", "landing weight")):
        x = j.copy()
        x["page"] = pd.to_numeric(x[page_col].astype(str).str.replace(",", ""),
                                  errors="coerce")
        x["app"] = pd.to_numeric(x[w_col], errors="coerce")
        both = x.dropna(subset=["page", "app"])
        diff = both[(both.page - both.app).abs() > 1]
        check(f"cross-source: {label} (page vs Appendix A)", 2,
              f"{len(both)} comparable rows, {len(diff)} differ",
              diff[["designation", "page", "app"]] if len(diff) else [])

    x = j.dropna(subset=["shuttle_wt_srb_ign_lbs"])
    est = (x.orb_wt_srb_ign_lbs + x.pyld_flight_total_lbs
           + x.et_wt_srb_ign_lbs + x.srb_wt_left_srb_ign_lbs
           + x.srb_wt_right_srb_ign_lbs)
    bad = x[((est - x.shuttle_wt_srb_ign_lbs).abs() > 5000)]
    check("liftoff weight = orbiter+payload+ET+2xSRB (<5000 lbs)", 2, "",
          bad[["designation"]] if len(bad) else [])

    bad = j[(j.inclination_deg < 28) | (j.inclination_deg > 62.5)]
    check("inclination range 28-62.5 deg", 1, "",
          bad[["designation", "inclination_deg"]] if len(bad) else [])
    bad = j[(j.duration_hours <= 0) | (j.duration_hours > 440)]
    check("duration range 0-440 h", 1, "",
          bad[["designation", "duration_hours"]] if len(bad) else [])
    return report


def external_checks(j):
    report = ["## 2. External cross-check", ""]
    if not os.path.exists("data/reference/wiki_sts_list.csv"):
        report.append("Reference dataset missing, external checks skipped")
        print("[WARN] reference dataset missing - external checks skipped")
        return report
    ref = pd.read_csv("data/reference/wiki_sts_list.csv")
    ref["seq"] = pd.to_numeric(ref.seq, errors="coerce").astype("Int64")
    rr = j.merge(ref, left_on="flight_seq", right_on="seq", how="inner")
    report.append(f"Reference: Wikipedia List of Space Shuttle missions, "
                  f"{len(ref)} rows, joined {len(rr)}")

    rd = pd.to_datetime(rr.ref_launch_date)
    md = pd.to_datetime(rr.launch_date)
    mism = rr[(rd - md).abs() != pd.Timedelta(0)]
    check("external: launch dates match Wikipedia", 1, f"{len(rr)} rows",
          mism[["designation", "launch_date", "ref_launch_date"]] if len(mism) else [])

    cmp_ = rr.dropna(subset=["ref_duration_h", "duration_hours"]).copy()
    cmp_["diff_h"] = (cmp_.duration_hours - cmp_.ref_duration_h).abs()
    mism = cmp_[cmp_.diff_h > 1.05]  # wiki durations rounded to whole hours
    check("external: durations match Wikipedia (<1.05 h)", 2,
          f"{len(cmp_)} comparable rows",
          mism[["designation", "duration_hours", "ref_duration_h"]] if len(mism) else [])

    mism = rr[rr.ref_orbiter.astype(str).str.strip()
              != rr.orbiter.astype(str).str.strip()]
    check("external: orbiters match Wikipedia", 1, "",
          mism[["designation", "orbiter", "ref_orbiter"]] if len(mism) else [])

    cmp_ = rr.dropna(subset=["ref_crew"])
    mism = cmp_[cmp_.ref_crew.astype(int) != cmp_.crew_size.astype(int)]
    check("external: crew sizes match Wikipedia", 2, "",
          mism[["designation", "crew_size", "ref_crew"]] if len(mism) else [])
    return report


def main():
    m, w, j = load()
    report = ["# 数据验证报告 (Data Validation Report)", "",
              "Data source: NASA TM-2011-216142 extraction results",
              f"- missions.csv: {len(m)} rows (135 flights + cancelled STS 51-E)",
              f"- weights.csv: {len(w)} rows (Appendix A; 7 DOD missions have no "
              "published weights in the source document)",
              ""]

    report += internal_checks(m, j)
    report += external_checks(j)

    report += ["", "## 3. Summary", "",
               "| Check | Severity | Issues |", "|---|---|---|"]
    for c in CHECKS:
        report.append(f"| {c['check']} | "
                      f"{'error' if c['severity'] == 1 else 'warning'} "
                      f"| {c['issues']} |")

    fails = sum(1 for c in CHECKS if c["severity"] == 1 and c["issues"])
    warns = sum(1 for c in CHECKS if c["severity"] == 2 and c["issues"])
    report += ["", f"**Result: {fails} errors, {warns} warnings**", "",
               "Known gaps inherent to the source document (not extraction "
               "errors):",
               "- 7 DOD missions (STS 51-C, 51-J, 27, 28, 33, 36, 38) have no "
               "published weight data",
               "- STS 51-L and STS-107 have no landing data (accidents)",
               "- STS 51-E is a cancelled mission (crew info only)",
               "",
               "Documented disagreements between TM-2011-216142 and the "
               "Wikipedia reference list:",
               "- STS-60 duration: document 8d07h (GMT-consistent, matches "
               "NASA mission archive) vs list page 7d06h - document kept",
               "- STS-85 crew: document header '(7)' vs list '6' - document "
               "kept",
               "- liftoff weight sum differs on STS-1, STS-30, STS-32 by "
               "9-30k lbs (independent bookkeeping columns in the source)"]

    out_dir = Path("output") / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "validation_report.md").write_text("\n".join(report),
                                                  encoding="utf-8")
    print("\nwrote output/reports/validation_report.md "
          f"({fails} errors, {warns} warnings)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
