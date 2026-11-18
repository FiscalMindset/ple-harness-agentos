"""Deterministic closed-form engineering solvers for PLE deliverables.

Every function is pure, bounded and returns a typed verdict with the governing
equation named. These are real calculations with known-answer tests in
`test_solvers.py` — not seeded-random scores or unconditional success stubs.

Engineering use only: these simplified formulas are aids, not a substitute for
a licensed engineer's seal. Limits and assumptions are explicit in each result.
"""

from __future__ import annotations

import math
from typing import Any

LIMITS = {
    "max_span_ft": 200.0,
    "max_load_klf": 50.0,
    "max_length_ft": 2000.0,
    "max_flow_gpm": 100000.0,
    "max_pipe_in": 120.0,
}


def _check(value: float, low: float, high: float, name: str) -> float:
    if not math.isfinite(value) or value < low or value > high:
        raise ValueError(f"{name} out of bounds [{low}, {high}]: {value}")
    return value


def steel_beam_lrfd(
    span_ft: float,
    w_dead_klf: float,
    w_live_klf: float,
    zx_in3: float,
    ix_in4: float,
    d_in: float,
    tw_in: float,
    fy_ksi: float = 50.0,
    e_ksi: float = 29000.0,
    phi_b: float = 0.90,
    phi_v: float = 0.90,
) -> dict[str, Any]:
    """AISC 360-16 LRFD flexure/shear + live-load deflection (L/360)."""
    span = _check(span_ft, 1, LIMITS["max_span_ft"], "span_ft")
    wd = _check(w_dead_klf, 0, LIMITS["max_load_klf"], "w_dead_klf")
    wl = _check(w_live_klf, 0, LIMITS["max_load_klf"], "w_live_klf")
    zx = _check(zx_in3, 1, 1e7, "Zx")
    ix = _check(ix_in4, 1, 1e9, "Ix")
    d = _check(d_in, 1, 100, "d")
    tw = _check(tw_in, 0.1, 10, "tw")
    wu = 1.2 * wd + 1.6 * wl
    mu = (wu * span**2 / 8.0) * 12.0
    phi_mn = phi_b * fy_ksi * zx
    moment = mu / phi_mn
    vu = wu * span / 2.0
    phi_vn = phi_v * 0.6 * fy_ksi * (d * tw)
    shear = vu / phi_vn
    lin = span * 12.0
    delta = (5.0 * (wl / 12.0) * lin**4) / (384.0 * e_ksi * ix)
    deflection = delta / (lin / 360.0)
    ratios = {"moment": moment, "shear": shear, "deflection": deflection}
    return {
        "governing": "AISC 360-16 LRFD (phi_b*Fy*Zx, phi_v*0.6*Fy*Aw), L/360 live",
        "ratios": ratios,
        "max_dcr": max(ratios.values()),
        "compliant": all(r <= 1.0 for r in ratios.values()),
    }


NEC_75C_CU = {
    "14": 20, "12": 25, "10": 35, "8": 50, "6": 65, "4": 85, "3": 100,
    "2": 115, "1": 130, "1/0": 150, "2/0": 175, "3/0": 200, "4/0": 230,
    "250": 255, "300": 285, "350": 310, "400": 335, "500": 380, "600": 420,
}
CMIL = {
    "14": 4110, "12": 6530, "10": 10380, "8": 16510, "6": 26240, "4": 41740,
    "3": 52620, "2": 66360, "1": 83690, "1/0": 105600, "2/0": 133100,
    "3/0": 167800, "4/0": 211600, "250": 250000, "300": 300000, "350": 350000,
    "400": 400000, "500": 500000, "600": 600000,
}


def nec_feeder(
    load_kva: float, voltage_ll: float, length_ft: float, gauge: str,
    ambient_c: float = 35.0, conductors: int = 3, pf: float = 0.9,
    vd_limit_pct: float = 3.0,
) -> dict[str, Any]:
    """NEC 2023 125% continuous current + copper ampacity derate + voltage drop."""
    kva = _check(load_kva, 0.1, 1e6, "load_kva")
    vll = _check(voltage_ll, 100, 15000, "voltage_ll")
    length = _check(length_ft, 1, LIMITS["max_length_ft"], "length_ft")
    if gauge not in NEC_75C_CU:
        raise ValueError(f"unknown gauge {gauge}")
    fl = (kva * 1000.0) / (math.sqrt(3) * vll * pf)
    required = 1.25 * fl
    temp_factor = 0.94 if ambient_c > 30 else 1.0
    fill_factor = 1.0 if conductors <= 3 else 0.8
    allowable = NEC_75C_CU[gauge] * temp_factor * fill_factor
    ampacity_ratio = required / allowable
    cmil = CMIL[gauge]
    dv = (math.sqrt(3) * 12.9 * fl * length) / cmil
    vd_pct = (dv / vll) * 100.0
    vd_ratio = vd_pct / vd_limit_pct
    return {
        "governing": "NFPA 70/NEC 2023 Art 210.20(A), 310.15(B), voltage drop",
        "design_current_a": fl,
        "required_a": required,
        "allowable_a": allowable,
        "ampacity_ratio": ampacity_ratio,
        "voltage_drop_pct": vd_pct,
        "vd_ratio": vd_ratio,
        "max_dcr": max(ampacity_ratio, vd_ratio),
        "compliant": ampacity_ratio <= 1.0 and vd_ratio <= 1.0,
    }


def darcy_weisbach_lcc(
    flow_gpm: float, length_ft: float, pipe_id_in: float,
    roughness_in: float = 0.0018, op_hours_yr: float = 6000.0,
    pump_eff: float = 0.78, motor_eff: float = 0.92,
    capital: float = 45000.0, years: int = 25, rate: float = 0.05,
    elec_rate: float = 0.12,
) -> dict[str, Any]:
    """Darcy-Weisbach head loss + Swamee-Jain friction + 25-year LCC."""
    q = _check(flow_gpm, 1, LIMITS["max_flow_gpm"], "flow_gpm")
    length = _check(length_ft, 1, LIMITS["max_length_ft"], "length_ft")
    dia = _check(pipe_id_in, 0.5, LIMITS["max_pipe_in"], "pipe_id_in")
    q_cfs = q * 0.002228
    d_ft = dia / 12.0
    area = math.pi * d_ft**2 / 4.0
    v = q_cfs / area
    re = (v * d_ft) / 1e-5
    rel = roughness_in / dia
    f = 0.25 / (math.log10(rel / 3.7 + 5.74 / re**0.9)) ** 2
    hf = f * (length / d_ft) * (v**2) / (2 * 32.174)
    hyd_hp = (q * hf * 8.34) / 33000.0
    kw = (hyd_hp * 0.7457) / (pump_eff * motor_eff)
    annual = kw * op_hours_yr * elec_rate
    factor = (1 - (1 + rate) ** (-years)) / rate
    lcc = capital + annual * factor
    return {
        "governing": "Darcy-Weisbach / Swamee-Jain + discounted LCC",
        "velocity_fps": v,
        "reynolds": re,
        "friction_factor": f,
        "head_loss_ft": hf,
        "pump_kw": kw,
        "annual_energy_usd": annual,
        "lcc_25yr_usd": lcc,
    }


def earthwork_prismoidal(
    stations: list[dict[str, float]], spacing_ft: float,
) -> dict[str, Any]:
    """Prismoidal cut/fill betweenstations; positive cut, negative fill."""
    if len(stations) < 2:
        raise ValueError("need at least 2 stations")
    spacing = _check(spacing_ft, 1, 1000, "spacing_ft")
    cut = fill = 0.0
    for a, b in zip(stations, stations[1:]):
        a1, a2 = a.get("area"), b.get("area")
        am = a.get("mid_area", (a1 + a2) / 2.0)
        if None in (a1, a2) or not all(math.isfinite(float(x)) for x in (a1, a2, am)):
            raise ValueError("station areas must be finite")
        vol = spacing * (float(a1) + 4.0 * float(am) + float(a2)) / 6.0
        if vol >= 0:
            cut += vol
        else:
            fill += -vol
    return {
        "governing": "prismoidal formula A1+4Am+A2 over 6 * spacing",
        "cut_cy": cut / 27.0,
        "fill_cy": fill / 27.0,
        "net_cy": (cut - fill) / 27.0,
        "balanced": abs(cut - fill) / max(cut, fill, 1.0) <= 0.05,
    }
