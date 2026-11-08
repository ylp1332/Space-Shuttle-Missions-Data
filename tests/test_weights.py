"""Tests for the Appendix A weight table extraction."""

import os
import sys

import pandas as pd
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from extract_weights import normalize_flight  # noqa: E402


@pytest.fixture(scope="session")
def weights():
    path = os.path.join(ROOT, "data", "weights.csv")
    if not os.path.exists(path):
        import subprocess
        subprocess.run([sys.executable, "-I",
                        os.path.join(ROOT, "scripts", "extract_weights.py")],
                       cwd=ROOT, check=True)
    return pd.read_csv(path)


@pytest.fixture(scope="session")
def joined(weights):
    missions = pd.read_csv(os.path.join(ROOT, "data", "missions.csv"))
    flown = missions[missions.cancelled == 0][["base", "flight_seq", "designation"]]
    return flown.merge(weights, on="base", how="inner")


def test_normalize_flight():
    assert normalize_flight("STS 41-B\n(STS-11)") == "STS-11"
    assert normalize_flight("SYS-90") == "STS-90"
    assert normalize_flight("STS-135") == "STS-135"


def test_135_rows_no_dupes(weights):
    assert len(weights) == 135
    assert weights.base.duplicated().sum() == 0


def test_sts1_reference_values(weights):
    r = weights[weights.base == "1"].iloc[0]
    assert r.ov_tail == 102
    assert r.orb_wt_srb_ign_lbs == 208437
    assert r.shuttle_wt_srb_ign_lbs == 4459280
    assert r.mach3_eom_wt_lbs == 195943
    assert r.mach3_eom_xcg_in == 1096.7
    assert r.landing_wt_lbs == 195473
    assert r.landing_xcg_in == 1098.1


def test_sts135_reference_values(weights):
    r = weights[weights.base == "135"].iloc[0]
    assert r.ov_tail == 104
    # STS-135 liftoff weight ~4.5M lbs
    assert 4.40e6 < r.shuttle_wt_srb_ign_lbs < 4.60e6
    assert r.landing_wt_lbs > 200000


def test_joins_all_flown_missions(joined):
    assert len(joined) == 135
    assert joined.flight_seq.notna().all()


def test_cross_check_mach3_weight_vs_mission_pages(joined):
    """Mach-3 EOM weight appears both on the mission page (SSME column)
    and in Appendix A; the two extractions must agree."""
    m = pd.read_csv(os.path.join(ROOT, "data", "missions.csv"))
    m = m[m.cancelled == 0][["base", "mach3_weight_lbs"]].copy()
    m["mach3_page"] = pd.to_numeric(m.mach3_weight_lbs.astype(str)
                                    .str.replace(",", ""), errors="coerce")
    j = joined.merge(m[["base", "mach3_page"]], on="base")
    both = j.dropna(subset=["mach3_page", "mach3_eom_wt_lbs"])
    agree = (both.mach3_page == both.mach3_eom_wt_lbs).sum()
    # require agreement on the bulk of comparable rows (layout noise on
    # a few pages is expected and lands in the validation report)
    assert agree >= 0.9 * len(both), f"only {agree}/{len(both)} agree"


def test_weight_sums_consistent(weights):
    """shuttle total at SRB ign ~= orbiter+payload + ET + 2 SRBs."""
    w = weights.copy()
    for c in ("orb_wt_srb_ign_lbs", "et_wt_srb_ign_lbs",
              "srb_wt_left_srb_ign_lbs", "srb_wt_right_srb_ign_lbs",
              "shuttle_wt_srb_ign_lbs"):
        w[c] = pd.to_numeric(w[c], errors="coerce")
    est = (w.orb_wt_srb_ign_lbs + w.pyld_flight_total_lbs
           + w.et_wt_srb_ign_lbs + w.srb_wt_left_srb_ign_lbs
           + w.srb_wt_right_srb_ign_lbs)
    diff = (est - w.shuttle_wt_srb_ign_lbs).abs()
    ok = (diff < 5000) | w.shuttle_wt_srb_ign_lbs.isna()
    assert ok.mean() > 0.95, f"sum check failed on {(~ok).sum()} rows"
