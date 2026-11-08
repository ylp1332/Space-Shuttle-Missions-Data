# Experimental: verify column-splitting by word x-coordinates on mission pages
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import pdfplumber
import re

PDF = "NASA_TM–2011–216142 Space Shuttle Missions Summary.pdf"

# 12-column boundaries measured from STS-1 page tall-rect edges
DEFAULT_COLS = [
    ("FLT_NO", 0, 59),
    ("ORBITER", 59, 105),
    ("CREW", 105, 191),
    ("LAUNCH", 191, 269.5),
    ("LANDING", 269.5, 335),
    ("THROTTLE", 335, 391),
    ("SRB_ET", 391, 420),
    ("INC", 420, 449),
    ("HAHP", 449, 501),
    ("PAYLOAD_WT", 501, 530),
    ("PAYLOADS", 530, 593),
    ("HIGHLIGHTS", 593, 792),
]

def page_columns(page):
    words = page.extract_words(use_text_flow=False, keep_blank_chars=False)
    cols = {name: [] for name, _, _ in DEFAULT_COLS}
    for w in words:
        cx = (w["x0"] + w["x1"]) / 2
        if w["top"] < 45:  # skip header band
            continue
        for name, x0, x1 in DEFAULT_COLS:
            if x0 <= cx < x1:
                cols[name].append(w)
                break
    out = {}
    for name, ws in cols.items():
        ws.sort(key=lambda w: (round(w["top"] / 2.5), w["x0"]))
        lines = {}
        for w in ws:
            key = round(w["top"] / 2.5)
            lines.setdefault(key, []).append(w["text"])
        out[name] = "\n".join(" ".join(v) for v in lines.values())
    return out

if __name__ == "__main__":
    pdf = pdfplumber.open(PDF)
    pageno = int(sys.argv[1]) if len(sys.argv) > 1 else 19
    page = pdf.pages[pageno - 1]
    cols = page_columns(page)
    for name, _, _ in DEFAULT_COLS:
        print(f"########## {name} ##########")
        print(cols[name][:2000])
        print()
