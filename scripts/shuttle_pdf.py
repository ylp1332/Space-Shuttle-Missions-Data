"""Shared layout utilities for NASA TM-2011-216142 mission summary PDF.

The mission summary pages are landscape pages with a 12-column table.
Text is recovered per-column by bucketing pdfplumber words on their
x-center, then reassembling lines by y position.

Later pages typeset parts of the text with wide character spacing
(each glyph separated by real space chars).  A regex pass re-joins
single-character word runs (e.g. "S T S - 1 3 5" -> "STS-135").
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import pdfplumber

PDF_NAME = "NASA_TM–2011–216142 Space Shuttle Missions Summary.pdf"

# 12-column x-boundaries (points), measured from the tall table rules on
# the STS-1 page; the layout is constant across all mission pages.
COLUMNS = [
    ("FLT_NO", 0, 59),
    ("ORBITER", 59, 105),
    ("CREW", 105, 191),
    ("LAUNCH", 191, 269.5),
    ("LANDING", 269.5, 335),
    ("SSME", 335, 391),
    ("SRB_ET", 391, 420),
    ("INC", 420, 449),
    ("HAHP", 449, 501),
    ("PAYLOAD_WT", 501, 530),
    ("PAYLOADS", 530, 593),
    ("HIGHLIGHTS", 593, 792),
]

HEADER_BAND = 45  # words above this y are page header / column titles

# pdfplumber's extract_words is expensive on this 300-page file; all
# layout code goes through this per-page cache.
_WORDS_CACHE: dict = {}


def page_words(page):
    key = page.page_number
    if key not in _WORDS_CACHE:
        _WORDS_CACHE[key] = page.extract_words()
    return _WORDS_CACHE[key]

# Header pattern like "Page 2-1-STS-1" with irregular spacing.
HEADER_RE = re.compile(r"Page\s*(2-\d+)\s*-\s*(STS[-\s]?[A-Za-z0-9.\-/]*)")

# Re-join character-spaced runs: single char + space + single char,
# plus hyphen-mediated splits ("STS - 135" on late pages).
_SPLIT1 = re.compile(r"(?:(?<=\w)|(?<=\d)) (?=\w )")
_SPLIT2 = re.compile(r"(?<=[\w/.]) (?=[\w/.](?![\w/.]))")
_SPLIT3 = re.compile(r"(?<=\w) (?=-)")
_SPLIT4 = re.compile(r"(?<=-) (?=\w)")


def rejoin(line: str) -> str:
    """Merge single-character word runs produced by wide tracking."""
    prev = None
    while prev != line:
        prev = line
        line = (_SPLIT4.sub("", _SPLIT3.sub("", _SPLIT2.sub("", _SPLIT1.sub("", line)))))
    return line


@dataclass
class MissionPages:
    """All PDF pages belonging to one mission summary."""

    designation: str          # e.g. "STS-1", "STS 41-B" as printed
    section: str              # e.g. "2-1"
    pages: list = field(default_factory=list)  # pdfplumber page objects

    @property
    def first(self):
        return self.pages[0]

    @property
    def data_page(self):
        """First page that actually carries the data table.

        A few missions open with a full-page photo whose header repeats
        the mission designation; the table starts on a later page.
        """
        base = base_designation(self.designation)
        for page in self.pages:
            d = _body_designation(page)
            if d is not None and base_designation(d) == base:
                return page
        return self.pages[0]


def base_designation(desig: str) -> str:
    """Normalize a printed designation to its core mission number.

    'STS-88/2A' -> '88', 'STS 41-C' -> '41-C', 'STS-117/13A4' -> '117'.
    """
    m = re.match(r"STS[- ]?(\d+(?:-[A-Z])?(?:\.\d+)?)", desig.strip())
    return m.group(1) if m else desig.strip()


_BODY_DESIG_RE = re.compile(r"^STS[- ]?\w{1,6}(?:[-./][\w.]+)?$")
# Split-line forms on late pages: "STS-" / "135/ ULF7" in separate buckets.
_BODY_DESIG_JOIN_RE = re.compile(
    r"STS\s*[- ]\s*(\d{1,3}(?:\.\d+)?(?:[- ][A-Z])?)(?!\d)")


def _body_designation(page) -> str | None:
    """Read the mission designation from the FLT_NO column body text."""
    try:
        lines = column_lines(page)["FLT_NO"]
    except Exception:
        return None
    for line in lines[:8]:
        s = line.strip()
        if _BODY_DESIG_RE.match(s) and s.upper() not in ("STS-", "STS"):
            return s
    # Wide tracking splits both words and numbers ("13 1/ 19A"): squeeze
    # digit gaps before joining the split designation lines.
    joined = re.sub(r"(?<=\d) (?=\d)", "", " ".join(lines[:6]))
    m = _BODY_DESIG_JOIN_RE.search(joined)
    if m:
        return f"STS-{m.group(1)}"
    return None


def iter_mission_pages(pdf) -> list:
    """Group PDF pages into missions.

    Every page of a mission repeats the header, so consecutive headers
    with the same base designation are merged into one mission.  A few
    pages have a missing header; their designation is recovered from the
    FLT_NO column body so they are not silently glued to the previous
    mission.  Scanning stops at Appendix A.

    Note: the book also contains one cancelled mission (STS 51-E); it
    appears here as its own group and is flagged later during field
    extraction.
    """
    missions: list[MissionPages] = []
    current: MissionPages | None = None
    for page in pdf.pages:
        words = page_words(page)
        tops = [w for w in words if w["top"] < 40]
        header = " ".join(w["text"] for w in tops)
        if "APPENDIX" in header.upper():
            break
        m = HEADER_RE.search(header)
        # Pages before the first real mission page (cover, TOC) have no
        # header; their FLT_NO band may contain TOC text like "STS-1 2-1".
        # Only trust body designations once a mission is underway.
        if m:
            designation = m.group(2).strip()
        elif current is not None:
            designation = _body_designation(page)
        else:
            designation = None
        if designation is not None:
            base = base_designation(designation)
            if current is not None and base == base_designation(current.designation):
                current.pages.append(page)
                continue
            section = m.group(1) if m else (current.section if current else "?")
            current = MissionPages(designation=designation, section=section,
                                   pages=[page])
            missions.append(current)
            continue
        if current is not None:
            current.pages.append(page)
    return missions


def column_lines(page) -> dict:
    """Return {column_name: [line, ...]} for one mission page."""
    words = page_words(page)
    buckets = {name: [] for name, _, _ in COLUMNS}
    for w in words:
        if w["top"] < HEADER_BAND:
            continue
        cx = (w["x0"] + w["x1"]) / 2
        for name, x0, x1 in COLUMNS:
            if x0 <= cx < x1:
                buckets[name].append(w)
                break
    out = {}
    for name, ws in buckets.items():
        ws.sort(key=lambda w: (w["top"], w["x0"]))
        rows: dict[int, list] = {}
        for w in ws:
            rows.setdefault(round(w["top"] / 2.6), []).append(w["text"])
        out[name] = [rejoin(" ".join(v)) for v in rows.values()]
    return out


def column_text(page, name: str) -> str:
    return "\n".join(column_lines(page)[name])


def full_page_text(page) -> str:
    """All words below the header band reassembled into reading lines.

    Used as a fallback when a photo occludes part of the table and the
    column bucketing loses text (STS-4/7/8/9 layout).
    """
    words = [w for w in page_words(page) if w["top"] >= HEADER_BAND]
    words.sort(key=lambda w: (w["top"], w["x0"]))
    rows: dict[int, list] = {}
    for w in words:
        rows.setdefault(round(w["top"] / 2.6), []).append(w["text"])
    return "\n".join(rejoin(" ".join(v)) for v in rows.values())
