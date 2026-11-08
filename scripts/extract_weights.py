"""Extract the Appendix A flight weight summary table from
NASA TM-2011-216142 into data/weights.csv (one row per mission).

The appendix spans PDF pages 274-282 ("A-2".."A-9").  Each mission is
one table row; merged cells carry two values (e.g. SRB left | right)
which are split into separate columns.

Column semantics were verified to be identical on all pages for
columns 0-8, 13 and 16-26 (checked against STS-1 on A-2 and
STS-114..135 on A-8/A-9).  The middle payload block (9-12, 14, 15)
changed layout between the early SODB pages and the late TDDP pages,
so those are kept as raw columns only.
"""

from __future__ import annotations

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import pdfplumber

import shuttle_pdf as sp

APPENDIX_PAGES = range(273, 282)  # 0-based PDF page numbers

COLS = {
    0: "flight",
    1: "ov_tail",
    2: "orb_wt_wo_prop_lbs",
    3: "non_prop_cons_srb_ign_lbs",
    4: "oms_prop_lbs",
    5: "rcs_prop_fwd_lbs",
    6: "rcs_prop_aft_lbs",
    7: "orb_wt_srb_ign_lbs",
    8: "pyld_pri_dply_lbs",        # first value of the merged cell
    9: "raw_c9",
    10: "raw_c10",
    11: "raw_c11",
    12: "raw_c12",
    13: "pyld_flight_total_lbs",
    14: "raw_c14",
    15: "raw_c15",
    16: "orb_plus_pyld_srb_ign_lbs",
    17: "orb_wt_orbit_insert_lbs",
    18: "orb_wt_orbit_insert_accum_lbs",
    19: "et_wt_srb_ign_lbs",
    20: "srb_wt_left_srb_ign_lbs",  # merged cell: left | right
    21: "shuttle_wt_srb_ign_lbs",
    22: "perf_marg_tddp_lbs",       # merged cell: TDDP | RECON
    23: "mach3_eom_wt_lbs",
    24: "mach3_eom_xcg_in",
    25: "landing_wt_lbs",
    26: "landing_xcg_in",
}


def clean_num(cell: str | None) -> str | None:
    if cell is None:
        return None
    s = cell.strip().replace(",", "")
    return s if s else None


def split_pair(cell: str | None):
    """Merged cell 'value\nsecond' -> (value, second)."""
    if cell is None:
        return None, None
    parts = [p for p in cell.replace(",", "").split("\n") if p.strip()]
    main = parts[0].strip() if parts else None
    second = parts[1].strip() if len(parts) > 1 else None
    return main or None, second or None


def normalize_flight(flight: str) -> str:
    """Normalize appendix flight labels.

    - 'STS 41-B\\n(STS-11)' carries the official number in parentheses;
      prefer it so the row joins missions.csv (which uses 'STS-11')
    - OCR errors like 'SYS-90' for 'STS-90'
    """
    flight = flight.replace("SYS-", "STS-").replace("SIS-", "STS-")
    m = re.search(r"\(STS[- ]([\w.]+)\)", flight)
    if m:
        return f"STS-{m.group(1)}"
    return flight.replace("\n", " ")


def extract(pdf) -> pd.DataFrame:
    rows = []
    for pageno in APPENDIX_PAGES:
        page = pdf.pages[pageno]
        tables = page.extract_tables()
        if not tables:
            continue
        table = tables[0]
        for r in table:
            flight = (r[0] or "").strip()
            if not re.match(r"^S[A-Z]S[- ]", flight):
                continue  # header / sequence / footnote rows
            if flight.startswith("*"):
                continue
            flight = normalize_flight(flight)
            rec = {}
            for idx, name in COLS.items():
                cell = r[idx] if idx < len(r) else None
                if idx == 0:
                    rec[name] = flight
                elif name == "srb_wt_left_srb_ign_lbs":
                    left, right = split_pair(cell)
                    rec["srb_wt_left_srb_ign_lbs"] = left
                    rec["srb_wt_right_srb_ign_lbs"] = right
                elif name == "shuttle_wt_srb_ign_lbs":
                    # last appendix page merges a duplicate value below
                    main, _ = split_pair(cell)
                    rec[name] = main
                elif name == "perf_marg_tddp_lbs":
                    main, recon = split_pair(cell)
                    rec[name] = main
                    rec["perf_marg_recon_lbs"] = recon
                elif name == "pyld_pri_dply_lbs":
                    main, _ = split_pair(cell)
                    rec[name] = main
                elif name.startswith("raw_"):
                    rec[name] = (cell or "").replace("\n", "|").strip() or None
                else:
                    rec[name] = clean_num(cell)
            rec["base"] = sp.base_designation(flight)
            rows.append(rec)
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", default=sp.PDF_NAME)
    ap.add_argument("--out", default="data/weights.csv")
    args = ap.parse_args()

    pdf = pdfplumber.open(args.pdf)
    df = extract(pdf)
    # numeric coercion; 'NOT AVAILABLE' perf margins stay as raw text
    for col in df.columns:
        if col in ("flight", "base") or col.startswith(("perf_marg", "raw_")):
            continue
        df[col] = pd.to_numeric(df[col], errors="coerce")
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    df.to_csv(args.out, index=False)
    print(f"wrote {args.out}: {len(df)} rows, {len(df.columns)} cols")

    print("rows:", len(df))
    dups = df[df.duplicated("base", keep=False)]
    if len(dups):
        print("duplicate flights:", dups[["flight", "base"]].to_string(index=False))
    missions = pd.read_csv("data/missions.csv")
    flown_bases = set(missions[missions.cancelled == 0].base.astype(str))
    missing = flown_bases - set(df.base.astype(str))
    print("flown missions missing from appendix:", sorted(missing))


if __name__ == "__main__":
    main()
