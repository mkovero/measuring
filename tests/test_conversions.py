"""Unit tests for conversions.py — pure math, no I/O."""
import math
import pytest
from ac.conversions import (
    vrms_to_dbu, dbu_to_vrms, dbfs_to_vrms, fmt_vrms,
    set_dbu_ref, get_dbu_ref,
)


# Restore the default reference after tests that change it
@pytest.fixture(autouse=True)
def restore_dbu_ref():
    original = get_dbu_ref()
    yield
    set_dbu_ref(original)


def test_vrms_to_dbu_reference():
    # 0 dBu is defined as sqrt(0.001 * 600) = 0.77459667 Vrms
    set_dbu_ref(0.77459667)
    assert abs(vrms_to_dbu(0.77459667)) < 1e-6


def test_vrms_to_dbu_roundtrip():
    set_dbu_ref(0.77459667)
    for v in (0.001, 0.1, 0.5, 1.0, 5.0):
        assert abs(dbu_to_vrms(vrms_to_dbu(v)) - v) < v * 1e-9


def test_dbfs_to_vrms():
    # -20 dBFS with ref=1.0 Vrms should give 0.1 Vrms
    result = dbfs_to_vrms(-20.0, vrms_at_0dbfs=1.0)
    assert abs(result - 0.1) < 1e-9


def test_dbfs_to_vrms_unity():
    assert dbfs_to_vrms(0.0, vrms_at_0dbfs=0.5) == pytest.approx(0.5)


def test_fmt_vrms_millivolts():
    s = fmt_vrms(0.7746)
    assert "mVrms" in s
    assert "774" in s


def test_fmt_vrms_volts():
    s = fmt_vrms(1.5)
    assert "Vrms" in s
    assert "mVrms" not in s


# ---------------------------------------------------------------------------
# vrms_to_vpp / fmt_vpp
# ---------------------------------------------------------------------------

def test_vrms_to_vpp():
    from ac.conversions import vrms_to_vpp
    # Vpp = Vrms * 2 * sqrt(2)
    assert vrms_to_vpp(1.0) == pytest.approx(2 * math.sqrt(2), rel=1e-9)
    assert vrms_to_vpp(0.7746) == pytest.approx(0.7746 * 2 * math.sqrt(2), rel=1e-6)


def test_fmt_vpp():
    from ac.conversions import fmt_vpp
    s = fmt_vpp(0.1)
    assert "mVpp" in s
    s2 = fmt_vpp(1.5)
    assert "Vpp" in s2
    assert "mVpp" not in s2


# ---------------------------------------------------------------------------
# dBu standard values
# ---------------------------------------------------------------------------

def test_dbu_known_values():
    """Verify well-known dBu↔Vrms correspondences from audio engineering standards."""
    set_dbu_ref(0.77459667)
    # +4 dBu = 1.228 Vrms (pro audio reference level)
    assert dbu_to_vrms(4.0) == pytest.approx(1.228, abs=0.002)
    # -10 dBV = 0.3162 Vrms → in dBu (ref 0.7746) = ~-7.78 dBu
    # +20 dBu = 7.746 Vrms
    assert dbu_to_vrms(20.0) == pytest.approx(7.746, abs=0.002)
    # Reverse: 1.228 Vrms → +4 dBu
    assert vrms_to_dbu(1.228) == pytest.approx(4.0, abs=0.05)


def test_dbfs_to_vrms_chain():
    """Full chain: dBFS level + calibration ref → Vrms → dBu."""
    # Scenario: 0 dBFS = 4.4 Vrms (typical pro interface)
    vrms_at_0dbfs = 4.4
    # -20 dBFS → 0.44 Vrms
    result = dbfs_to_vrms(-20.0, vrms_at_0dbfs)
    assert result == pytest.approx(0.44, rel=1e-6)
    # That 0.44 Vrms in dBu (ref 0.7746):
    set_dbu_ref(0.77459667)
    dbu = vrms_to_dbu(result)
    # 20*log10(0.44/0.7746) ≈ -4.91 dBu
    assert dbu == pytest.approx(-4.91, abs=0.05)
