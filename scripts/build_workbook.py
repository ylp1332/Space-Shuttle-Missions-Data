"""Build the consolidated Excel workbook from the extracted CSVs.

Sheets: Missions (135 flights + STS 51-E), Weights (Appendix A),
Reference (Wikipedia cross-check), Summary (program statistics).
"""

from __future__ import annotations

import os

import pandas as pd


def main():
    m = pd.read_csv("data/missions.csv", dtype={"base": str})
    w = pd.read_csv("data/weights.csv", dtype={"base": str})
    ref = pd.read_csv("data/reference/wiki_sts_list.csv")

    flown = m[m.cancelled == 0].copy()
    flown["flight_seq"] = flown.flight_seq.astype(int)

    # summary statistics sheet
    rows = [
        ("Total flights (1981-2011)", 135),
        ("Flights per orbiter: Discovery", int((flown.orbiter == "Discovery").sum())),
        ("Flights per orbiter: Columbia", int((flown.orbiter == "Columbia").sum())),
        ("Flights per orbiter: Atlantis", int((flown.orbiter == "Atlantis").sum())),
        ("Flights per orbiter: Endeavour", int((flown.orbiter == "Endeavour").sum())),
        ("Flights per orbiter: Challenger", int((flown.orbiter == "Challenger").sum())),
        ("Total mission time (days)", round(flown.duration_hours.sum() / 24, 2)),
        ("Mean mission duration (days)", round(flown.duration_hours.mean() / 24, 2)),
        ("Longest mission (STS-80, days)", round(flown.duration_hours.max() / 24, 2)),
        ("Landings at Kennedy", 78),
        ("Landings at Edwards", 54),
        ("Landings at White Sands", 1),
        ("Crew members flown (launch counts, sum)", int(flown.crew_size.sum())),
        ("Night launches (documented)", int(flown.night_launch.sum())),
    ]
    summary = pd.DataFrame(rows, columns=["Metric", "Value"])

    with pd.ExcelWriter("data/space_shuttle_missions.xlsx", engine="openpyxl") as xw:
        m.to_excel(xw, sheet_name="Missions", index=False)
        w.to_excel(xw, sheet_name="Weights_AppendixA", index=False)
        ref.to_excel(xw, sheet_name="Reference_Wikipedia", index=False)
        summary.to_excel(xw, sheet_name="Summary", index=False)

    print("wrote data/space_shuttle_missions.xlsx")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
