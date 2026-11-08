"""Extract one structured row per Space Shuttle mission from the
mission summary pages of NASA TM-2011-216142.

Usage:
    python scripts/extract_missions.py [--pdf PATH] [--out data/missions.csv]

Produces data/missions.csv with one row per mission (including the one
cancelled mission STS 51-E kept for completeness, flagged cancelled=1).

Layout quirks handled here:
- wide-tracking text where digits/colons/slashes are split by spaces
  ("302 : 19 : 19 : 33 : 98Z") -> normalized before matching
- multi-word labels whose word order is scrambled in the recovered
  column text ("FLT DURATION" may appear as "DURATION: FLT")
- GMT liftoff stamps with an optional 5th centisecond field
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


def normalize(text: str) -> str:
    """Squeeze wide-tracking gaps around digits, colons and slashes."""
    t = re.sub(r"(?<=\d) (?=\d)", "", text)          # 1 33 -> 133
    t = re.sub(r"(?<=\d)\s?:\s?(?=\d)", ":", t)      # 19 : 33 -> 19:33
    t = re.sub(r"(?<=\d)\s?/\s?(?=\d)", "/", t)      # 10/ 29/ 98 -> 10/29/98
    t = re.sub(r"(?<=\.) (?=\d)", "", t)             # 46. 95 -> 46.95
    t = re.sub(r"\(\s+", "(", t)                     # ( P ) -> (P )
    t = re.sub(r"\s+\)", " )", t)
    return t


def first(pattern: str, text: str, flags: int = 0, default=None):
    m = re.search(pattern, text, flags)
    if not m:
        return default
    return m.group(1) if m.groups() else m.group(0)


ORBITER_NAMES = {"OV-102": "Columbia", "OV-099": "Challenger",
                 "OV-103": "Discovery", "OV-104": "Atlantis",
                 "OV-105": "Endeavour"}

# GMT stamp: DDD:HH:MM:SS[.f][,CS]Z with optional fractional/5th field;
# groups 1-4 are day, hh, mm, ss (extras ignored).
GMT_RE = r"(\d{1,3}):(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(?::\d{1,3})?\s?Z"
DATE_RE = r"(\d{1,2})/(\d{1,2})/(\d{2,4})(?!\d)"
TIME4_RE = re.compile(r"(\d+):(\d{2}):(\d{2}):(\d{2})(?! ?[.\dZ])")


def _valid_duration(m: re.Match) -> bool:
    d, h, mi, s = (int(x) for x in m.groups())
    # longest shuttle mission was 17.4 days; GMT day-of-year stamps are
    # 3 digits and end with Z, both rejected here
    return d <= 20 and h <= 23 and mi <= 59 and s <= 59


def find_duration(*col_texts: str):
    """Find the mission duration near any 'DURATION' keyword.

    The label words may be scrambled by column reassembly, so instead of
    an exact label match, search a window after each DURATION keyword
    for the first plausible dd:hh:mm:ss stamp.  GMT stamps (trailing Z)
    and S/T spacecraft-time stamps are excluded.
    """
    for text in col_texts:
        for kw in re.finditer(r"DURATION", text):
            window = text[kw.end():kw.end() + 80]
            for m in TIME4_RE.finditer(window):
                if "S/T" in window[:m.start()]:
                    continue
                if _valid_duration(m):
                    return m
    return None


def parse_gmt(year: int, match: re.Match):
    """GMT day-of-year timestamp -> pandas Timestamp (UTC)."""
    doy, hh, mm, ss = (int(match.group(1)), int(match.group(2)),
                       int(match.group(3)), int(match.group(4)))
    base = pd.Timestamp(year=year, month=1, day=1) + pd.Timedelta(days=doy - 1)
    return base + pd.Timedelta(hours=hh, minutes=mm, seconds=ss)


def year2(yy: int) -> int:
    return 1900 + yy if yy > 50 else 2000 + yy


def find_date(text: str):
    """First plausible M/D/YY date in text (rejects photo-caption noise)."""
    for m in re.finditer(DATE_RE, text):
        mm_, dd_, yy = (int(x) for x in m.groups())
        yy = yy if yy > 1000 else year2(yy)
        if 1980 <= yy <= 2012 and 1 <= mm_ <= 12 and 1 <= dd_ <= 31:
            return f"{yy:04d}-{mm_:02d}-{dd_:02d}", yy
    return None, None


def extract_mission(m: sp.MissionPages) -> dict:
    page = m.data_page
    lines = sp.column_lines(page)
    txt = {k: normalize("\n".join(v)) for k, v in lines.items()}
    highlights = normalize("\n".join(
        "\n".join(sp.column_lines(p)["HIGHLIGHTS"]) for p in m.pages))

    rec = {}
    rec["designation"] = m.designation
    rec["base"] = sp.base_designation(m.designation)
    rec["pdf_section"] = m.section
    rec["pdf_pages"] = len(m.pages)

    # ---- FLT_NO -------------------------------------------------------
    flt = txt["FLT_NO"]
    seq = first(r"F\s?LT\s?#?\s?(\d+)", flt) or first(r"KSC\s?-?\s?(\d+)", flt)
    rec["flight_seq"] = int(seq) if seq else None
    rec["launch_pad"] = first(r"PAD\s?(39[AB])", flt) or first(r"(39[AB])", flt)
    iss = re.search(r"/\s?([0-9][A-Z](?:\.[0-9a-z]+)?)", m.designation)
    rec["iss_flight"] = iss.group(1) if iss else None
    rec["cancelled"] = 0 if rec["flight_seq"] else 1

    # ---- ORBITER ------------------------------------------------------
    orb = txt["ORBITER"]
    ovm = re.search(r"[O0]V\s?-\s?0?(\d{2,3})", orb)
    ov = ovm.group(1).zfill(3) if ovm else None
    rec["orbiter_id"] = f"OV-{ov}" if ov else None
    rec["orbiter"] = ORBITER_NAMES.get(rec["orbiter_id"], None)
    rec["orbiter_flight_no"] = first(r"Flight\s?(\d+)", orb)

    # ---- CREW ---------------------------------------------------------
    crew_lines = [normalize(x) for x in lines["CREW"]]
    crew_text = "\n".join(crew_lines)
    roles, names = [], []
    pending_role = None
    for ln in crew_lines:
        s = ln.strip()
        rm = re.match(r"^(CDR|PLT|MS\d?|PS)\b[:\s]*(.*)$", s)
        if rm:
            role = rm.group(1).upper()
            if role not in roles:
                roles.append(role)
            pending_role = role
            rest = rm.group(2).strip()
            if re.match(r"^[A-Z][a-z]", rest):
                names.append(f"{role}: {rest}")
            continue
        if pending_role and re.match(r"^[A-Z][a-z]+\s+[A-Z]", s) and not re.match(r"^P\d", s):
            names.append(f"{pending_role}: {s}")
            pending_role = None
    rec["crew_size"] = len(roles) or None
    # The CREW column header carries the authoritative size.  Formats:
    # '(6)', '(6 )', '(10) 7 UP, 8 DOWN' (crew swap), '(6+1 UP/6+1 DN)',
    # '(7 up, 6 down)'.  The launched (UP) count is the crew size and
    # takes precedence over the parenthesized total.
    crew_hdr = " ".join(crew_lines[:5])
    m_up = re.search(r"(\d+)\s*\+?\s*(\d*)\s*UP\b", crew_hdr, re.I)
    if m_up:
        extra = int(m_up.group(2)) if m_up.group(2) else 0
        rec["crew_size"] = int(m_up.group(1)) + extra
    else:
        msz = re.search(r"^\(\s*(\d)\s*\)$", crew_hdr.split("\n")[1].strip()) \
            if len(crew_hdr.split("\n")) > 1 else None
        if not msz:
            msz = re.search(r"\(\s*(\d)\s*\)", crew_hdr)
        if msz:
            rec["crew_size"] = int(msz.group(1))
    rec["crew_roles"] = " ".join(roles)
    rec["crew_names"] = "; ".join(names)
    if "FLIGHT DIRECTORS" in crew_text:
        fd_block = crew_text.split("FLIGHT DIRECTORS")[-1]
        fd_names = re.findall(
            r"(?:^|\n)[A-Z/\s]{2,7}-\s?([A-Z]\.\s?[A-Z]\.\s?[A-Za-z-]+)", fd_block)
    else:
        fd_names = []
    rec["flight_directors"] = "; ".join(fd_names)
    rec["fd_count"] = len(fd_names) or None

    # ---- LAUNCH -------------------------------------------------------
    lau = txt["LAUNCH"]
    rec["launch_site"] = first(r"(KSC|VFS|WTR)\s?(39[AB])?", lau)
    date, year = find_date(lau)
    rec["launch_date"] = date
    rec["launch_year"] = year
    gmt = re.search(GMT_RE, lau)
    rec["launch_gmt_raw"] = gmt.group(0) if gmt else None
    if rec["launch_year"] is None and gmt:
        # photo-occluded pages (STS-8): recover the date by matching a
        # full-page date whose day-of-year equals the GMT stamp's
        doy = int(gmt.group(1))
        full = normalize(sp.full_page_text(page))
        for dm in re.finditer(DATE_RE, full):
            mm_, dd_ = int(dm.group(1)), int(dm.group(2))
            yy = int(dm.group(3))
            yy = yy if yy > 1000 else year2(yy)
            if not (1980 <= yy <= 2012 and 1 <= mm_ <= 12 and 1 <= dd_ <= 31):
                continue
            ts = pd.Timestamp(year=yy, month=mm_, day=dd_)
            if (ts.day_of_year == doy):
                rec["launch_date"] = f"{yy:04d}-{mm_:02d}-{dd_:02d}"
                rec["launch_year"] = yy
                break
    rec["launch_dt_utc"] = parse_gmt(rec["launch_year"], gmt) if gmt and rec["launch_year"] else None
    # if the printed date is off by more than a day from the GMT stamp
    # it was mis-extracted (e.g. STS-4 picked up the landing date);
    # local-vs-UTC day shifts of +-1 day are legitimate and kept
    if rec["launch_dt_utc"] is not None and rec["launch_date"] is not None:
        delta = abs((rec["launch_dt_utc"].normalize()
                     - pd.Timestamp(rec["launch_date"])).days)
        if delta > 1:
            rec["launch_date"] = str(rec["launch_dt_utc"].date())
            rec["launch_year"] = rec["launch_dt_utc"].year
    rec["launch_planned_local"] = first(r"([\d:]+\s?[AP]M\s?[A-Z]{2,3})\(\s?P\s?\)", lau)
    rec["launch_actual_local"] = first(r"([\d:]+\s?[AP]M\s?[A-Z]{2,3})\(\s?A\s?\)", lau)
    rec["window_hours"] = first(r"WINDOW[^:\n]*:?\s?([\d.]+)\s?HOURS", lau, re.I)
    rec["meco_met"] = first(r"MECO[:\s]*(\d+:\d{2}(?:\.\d)?)", lau)
    rec["srb_sep_met"] = first(r"SRB\s?STG[:\s]*(\d+:\d{2}(?:\.\d)?)", lau) \
        or first(r"SRB\s?SEP[:\s]*(\d+:\d{2}(?:\.\d)?)", lau)
    rec["et_sep_met"] = first(r"ET\s?SEP[:\s]*(\d+:\d{2}(?:\.\d)?)", lau)
    rec["oms1_met"] = first(r"OMS-1[:\s]*(\d+:\d{2}(?:\.\d)?)", lau)
    rec["oms2_met"] = first(r"OMS-2[:\s]*(\d+:\d{2}(?:\.\d)?)", lau)
    mq = first(r"MAX\s?Q\s?(?:NAV)?\s?=?\s?(\d{3})", lau)
    rec["maxq"] = mq

    # ---- LANDING ------------------------------------------------------
    lan = txt["LANDING"]
    rec["landing_site"] = first(r"(EDW|KSC|NOR|WSMR|WSSH|DFR|LKA|TGT)\s?\d{1,2}\b", lan) \
        or first(r"(EDW|KSC|NOR|WSMR|WSSH|DFR)\b", lan)
    ldates = re.findall(DATE_RE, lan)
    landing_date = None
    if ldates:
        landing_date, _ = find_date(lan)
    rec["landing_date"] = landing_date

    gmts = [g for g in re.finditer(GMT_RE, lan)
            if 1 <= int(g.group(1)) <= 366]
    # OCR digit errors create outlier days (775 for 175, 12 for 212):
    # keep only the majority day among the stamp cluster
    if gmts:
        from collections import Counter
        days = Counter(int(g.group(1)) for g in gmts)
        maj = days.most_common(1)[0][0]
        gmts = [g for g in gmts if int(g.group(1)) == maj]
    def after_label(*labels):
        for lab in labels:
            lm = re.search(lab, lan)
            if lm:
                for g in gmts:
                    if g.start() >= lm.end() - 2:
                        return g
        return None
    td_g = after_label(r"MLGTD", r"TD\s?NORM", r"NLGTD", r"TOUCHDOWN")
    ws_g = after_label(r"WHEELS\s?STOP", r"STOP:?\s?WHEELS")
    if td_g is None and gmts:               # fallback: earliest = touchdown
        td_g = gmts[0]
    if ws_g is None and gmts:               # fallback: latest = wheels stop
        ws_g = gmts[-1]
    rec["touchdown_utc"] = parse_gmt(rec["launch_year"], td_g) if td_g and rec["launch_year"] else None
    rec["wheels_stop_utc"] = parse_gmt(rec["launch_year"], ws_g) if ws_g and rec["launch_year"] else None
    if rec["landing_site"] is None and rec["touchdown_utc"] is not None:
        # photo-occluded pages: search the whole page for a runway stamp
        full = normalize(sp.full_page_text(page))
        m2 = re.search(r"(EDW|KSC|NOR|WSMR)\s?(\d{1,2})\b", full)
        if m2:
            rec["landing_site"] = m2.group(0)
    # landing date fallback: derive from the wheels-stop stamp
    if rec["wheels_stop_utc"] is not None:
        ws_date = str(rec["wheels_stop_utc"].date())
        if rec["landing_date"] is None:
            rec["landing_date"] = ws_date
        else:
            delta = abs((pd.Timestamp(rec["landing_date"])
                         - rec["wheels_stop_utc"].normalize()).days)
            if delta > 1:  # mis-extracted; trust the GMT stamp
                rec["landing_date"] = ws_date
    dur = find_duration(
        *(txt[c] for c in ("LANDING", "SSME", "SRB_ET", "INC", "HAHP",
                           "PAYLOAD_WT", "PAYLOADS", "HIGHLIGHTS")))
    if dur is None:
        # continuation pages may carry the LANDING table tail
        for p in m.pages[1:]:
            dur = find_duration(*(
                normalize("\n".join(sp.column_lines(p)[c]))
                for c in ("LANDING", "HIGHLIGHTS", "SSME")))
            if dur:
                break
    rec["duration_source"] = "text"
    # GMT-derived duration is the cross-check: touchdown - liftoff
    derived_secs = None
    if rec["touchdown_utc"] is not None and rec["launch_dt_utc"] is not None:
        secs = (rec["touchdown_utc"] - rec["launch_dt_utc"]).total_seconds()
        if 0 < secs < 18 * 86400:
            derived_secs = secs
    if dur is not None and derived_secs is not None:
        d, h, mi, s = (int(x) for x in dur.groups())
        text_secs = d * 86400 + h * 3600 + mi * 60 + s
        # mismatch: the window grabbed an event MET (e.g. Spartan release
        # on STS-69); trust the GMT stamps instead
        if abs(text_secs - derived_secs) > 15 * 60:
            dur = None
    if dur is None and derived_secs is not None:
        d, rem = divmod(int(derived_secs), 86400)
        h, rem = divmod(rem, 3600)
        mi, s = divmod(rem, 60)

        class _Dur:  # minimal match-like carrier
            def groups(self):
                return (str(d), str(h), str(mi), str(s))
        dur = _Dur()
        rec["duration_source"] = "derived"
    if dur:
        d, h, mi, s = (int(x) for x in dur.groups())
        rec["duration"] = f"{d}d {h:02d}:{mi:02d}:{s:02d}"
        rec["duration_hours"] = round(d * 24 + h + mi / 60 + s / 3600, 3)
    else:
        rec["duration"] = rec["duration_hours"] = None
    rec["xrange_nm"] = first(r"XRANGE:?\s?([\d.]+)\s?NM", lan)
    rec["mlgtd_ft"] = first(r"MLGTD:\s?([\d,]+)\s?FT", lan)

    # ---- SSME ---------------------------------------------------------
    ssme = txt["SSME"]
    m3 = re.search(r"M\s?3\s?EOM\s?WEIGHT:?\s?([\d,]+)", ssme)
    rec["mach3_weight_lbs"] = m3.group(1) if m3 else None
    rec["mach3_xcg"] = first(r"X\s?CG:?\s?([\d.]+)", ssme[m3.end():] if m3 else ssme)
    lw = re.search(r"LANDING\s?WEIGHT:?\s?([\d,]+)", ssme)
    rec["landing_weight_lbs"] = lw.group(1) if lw else None
    rec["landing_xcg"] = first(r"X\s?CG:?\s?([\d.]+)", ssme[lw.end():] if lw else ssme)
    rec["engine_sns"] = "; ".join(
        f"{a}={b}" for a, b in re.findall(r"(\d)\s?=\s?(\d{4})", ssme))

    # ---- SRB / ET -----------------------------------------------------
    srb = txt["SRB_ET"]
    rec["et_no"] = first(r"ET-(\d+)", srb)
    rec["et_impact_lat"] = first(r"LAT:?\s?([\d.]+)\s?°\s?([NS])", srb)
    rec["et_impact_long"] = first(r"LONG:?\s?([\d.]+)\s?°\s?([EW])", srb)

    # ---- inclination / orbit ------------------------------------------
    inc = txt["INC"]
    i = re.search(r"(\d{2}(?:\s?\.\s?\d+)?)\s?°?\s?[^\d(]{0,4}\(\s?(\d+)\s?\)", inc)
    inc_fallback = first(r"(\d{2}\s?\.\s?\d+)", inc)
    rec["inclination_deg"] = (
        float(i.group(1).replace(" ", "")) if i
        else (float(inc_fallback.replace(" ", "")) if inc_fallback else None))
    rec["insertion_alt_nm"] = first(r"ALTITUDE:?\s?([\d.]+)\s?NM", txt["HAHP"])
    rec["hahp_raw"] = " ".join(lines["HAHP"][:12])

    # ---- payloads -----------------------------------------------------
    pay = txt["PAYLOADS"] + "\n" + txt["PAYLOAD_WT"]
    rec["cargo_lbs"] = first(r"CARGO:?\s?([\d,]+)", pay)
    rec["deployed_lbs"] = first(r"DEPLOYED:?\s?([\d,]+)", pay)
    rec["nondeployed_lbs"] = first(r"NON-?\s?DEPLOYED:?\s?([\d,]+)", pay)
    rec["cargo_total_lbs"] = first(r"CARGO\s?TOTAL:?\s?([\d,]+)", pay)

    # ---- highlights-derived -------------------------------------------
    wd = re.search(r"OPF\s?(\d+),?\s?VAB\s?(\d+),?\s?PAD\s?=?\s?(\d+)", highlights)
    if wd:
        rec["workdays_opf"], rec["workdays_vab"], rec["workdays_pad"] = (int(x) for x in wd.groups())
    else:
        rec["workdays_opf"] = rec["workdays_vab"] = rec["workdays_pad"] = None
    rec["night_launch"] = 1 if re.search(r"NIGHT\s+LAUNCH", highlights, re.I) else 0
    eva_count = len(set(re.findall(r"EVA\s?#?\s?(\d)", highlights)))
    rec["eva_count_hint"] = eva_count or None

    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", default=sp.PDF_NAME)
    ap.add_argument("--out", default="data/missions.csv")
    args = ap.parse_args()

    pdf = pdfplumber.open(args.pdf)
    missions = sp.iter_mission_pages(pdf)
    print(f"missions grouped: {len(missions)}")
    rows = [extract_mission(m) for m in missions]
    df = pd.DataFrame(rows)

    # orbiter flight numbering: fill gaps by order within each orbiter
    # (a few pages print the number in a form the regex misses)
    flown = df.cancelled == 0
    ordered = df[flown].sort_values("flight_seq").copy()
    ordered["orbiter_flight_no"] = ordered.groupby("orbiter").cumcount() + 1
    df["orbiter_flight_no"] = df["orbiter_flight_no"].astype("object")
    df.loc[ordered.index, "orbiter_flight_no"] = ordered["orbiter_flight_no"]

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    df.to_csv(args.out, index=False)
    print(f"wrote {args.out}: {len(df)} rows, {len(df.columns)} cols")

    flown = df[df.cancelled == 0]
    print("flown missions:", len(flown))
    missing = [n for n in range(1, 136)
               if n not in set(flown.flight_seq.dropna().astype(int))]
    print("missing flight_seq (1..135):", missing)

    key = ["launch_date", "launch_dt_utc", "landing_date", "duration_hours",
           "crew_size", "orbiter", "inclination_deg", "landing_site",
           "cargo_total_lbs"]
    print("\nnull counts among key fields (of 135 flown):")
    print(flown[key].isna().sum().to_string())


if __name__ == "__main__":
    main()
