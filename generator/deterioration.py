"""Deterioration on the ward: vital signs at the index time, the vendor's
deterioration index (VDI) in versions 2.0 and 3.0, alerts, the rapid-response
evaluation and its fading, both potential outcomes, the EHR outcome flag, and
what a deterioration does to the rest of the stay.

Blocks 15 (vitals_true), 16 (vitals_recorded), 18 (alert_response),
19 (deterioration) and 20 (ehr_outcome). Design: DESIGN.md sections 5.2 and 6.1.
The model is described in prose in WORLD_SPEC.md section 11; every number is in
spec.DETERIORATION.

Built in Milestone 3. `step` is called from `course` in inpatient.py, once for
each day's batch of stays and once for the reference cohort. Milestone 4 added
`write_products`: the chart review (block 26), the rapid-response log (block 27),
the laboratory change log (block 28), the change points and the monthly truth.
Those are drawn after the day loop and change nothing that came before.

Data-path rules (common.py): no np.exp, np.log or built-in distributions; no
np.sum or np.mean of floats; no BLAS. Only the det_* helpers and exact arithmetic.
"""
import datetime as dt
import math

import numpy as np
import pandas as pd

import spec
from common import (categorical_from_uniform, det_exp, det_gamma, det_log, det_mean, det_plogis,
                    write_csv, write_json)

BUILT = True

Q = spec.DETERIORATION
FACILITY_IDS = [f["facility_id"] for f in spec.FACILITIES]
NFAC = len(FACILITY_IDS)
DX = list(spec.DX_GROUPS)
PAYER_CODES = list(spec.PAYERS)
RACE_CODES = list(spec.RACE_ETHNICITY)
O2_CODES = list(spec.O2_SUPPORT)                 # none, low_flow, high_flow
ALERT_CODES = list(spec.ALERTNESS)               # alert, drowsy, confused, unresponsive
EVENT_TYPES = list(spec.EVENT_TYPES)             # icu_transfer, transfer_out, death
EV_ICU, EV_OUT, EV_DEATH = (EVENT_TYPES.index(c) for c in ("icu_transfer", "transfer_out", "death"))
DISP = list(spec.DISPOSITIONS)
DISP_DIED = DISP.index("died")
DISP_TRANSFER = DISP.index("transfer")
THRESHOLD = spec.VDI["threshold"]

_DAY0 = dt.date.fromisoformat(spec.DATES["burn_in_start"])


def _day(iso):
    return (dt.date.fromisoformat(iso) - _DAY0).days


FACILITY_START = np.array([_day(f["network_data_from"]) for f in spec.FACILITIES], dtype=np.int64)
SCORING_FROM = np.array([_day(f["vdi_scoring_from"]) for f in spec.FACILITIES], dtype=np.int64)
ALERTS_FROM = np.array([_day(f["vdi_alerts_from"]) for f in spec.FACILITIES], dtype=np.int64)
CENTRAL_LAB = np.array([f["central_lab"] == 1 for f in spec.FACILITIES])
ASSAY_DAY = _day(spec.DATES["lactate_assay_change"])
V3_DAY = _day(spec.DATES["vdi_v3"])
LABEL_DAYS = spec.VDI["outcome_window_hours"] // 24 + spec.VDI["label_delay_days"]
INDEX_HOURS = spec.VDI["index_hours_after_admission"]


def _dx_vec(table):
    return np.array([table.get(g, 0.0) for g in DX], dtype=np.float64)


def _fac_vec(table, default=0.0):
    return np.array([table.get(f, default) for f in FACILITY_IDS], dtype=np.float64)


def _round(x, decimals):
    """Round half up to a fixed number of decimals, with exact operations only."""
    k = float(10 ** decimals)
    return np.floor(x * k + 0.5) / k


_VT = Q["vitals_true"]
VITAL_DX = {k: _dx_vec(_VT[k].get("dx", {})) for k in _VT}
O2_DX = _dx_vec(Q["o2_support"]["dx"])
ALERT_DX = _dx_vec(Q["alertness"]["dx"])
_VR = Q["vitals_recorded"]
RR_DEFAULT_SHARE = _fac_vec(_VR["rr_default_share"], _VR["rr_default_share"]["elsewhere"])
BIASED_RACE = RACE_CODES.index(_VR["spo2_bias"]["group"])
_T = Q["truth"]
TRUTH_DX = _dx_vec(_T["dx"])
TRUTH_FAC = _fac_vec(_T["facility_shift"])
SOLVED_ON = np.array([f in _T["intercept_solved_on"] for f in FACILITY_IDS])
_EV = Q["event_type"]
EVENT_W = np.array([[_EV["by_facility"].get(f, _EV["elsewhere"])[c] for c in EVENT_TYPES]
                    for f in FACILITY_IDS], dtype=np.float64)
MISS = np.array([Q["ehr_flag"]["miss"][c] for c in EVENT_TYPES], dtype=np.float64)


# ------------------------------------------------------------------ the two formulas
def linear_predictor(coef, hr, rr, sbp, temp, spo2, o2, alertness, lactate, age, encounters):
    """The sum of terms that the true model and the vendor's formula share.

    Each vital sign enters as its distance beyond a limit (spec.DETERIORATION
    ["features"]), so a normal value adds nothing. `coef` is the truth's table
    or the vendor's; the vendor's is applied to recorded values.
    """
    f = Q["features"]
    o2_coef = np.array([0.0, coef["o2_low_flow"], coef["o2_high_flow"]])
    alert_coef = np.array([0.0, coef["drowsy"], coef["confused"], coef["unresponsive"]])
    return (coef["hr_per_10"] * np.maximum(0.0, hr - f["hr_above"]) / 10.0
            + coef["rr_per_2"] * np.maximum(0.0, rr - f["rr_above"]) / 2.0
            + coef["sbp_per_10"] * np.maximum(0.0, f["sbp_below"] - sbp) / 10.0
            + coef["temp_per_degree"] * (np.maximum(0.0, temp - f["temp_above"])
                                         + np.maximum(0.0, f["temp_below"] - temp))
            + coef["spo2_per_point"] * np.maximum(0.0, f["spo2_below"] - spo2)
            + o2_coef[o2] + alert_coef[alertness]
            + coef["lactate_per_mmol"] * np.maximum(0.0, np.minimum(lactate, f["lactate_cap"]) - f["lactate_above"])
            + coef["age_per_10"] * (age - 65.0) / 10.0
            + coef["encounters"] * np.minimum(encounters, f["encounters_cap"]))


def display_score(lp, version):
    """The 0 to 100 score the vendor shows for a risk logit: a fixed transform of the
    risk, one for each version (`version` is a key of spec.VDI["versions"])."""
    d = Q["vendor"]["display"][version]
    return np.floor(100.0 * det_plogis(d["shift"] + d["scale"] * lp) + 0.5).astype(np.int64)


def vendor_risk_table(version):
    """The vendor's score-to-risk table for one version: the display transform turned round.

    A score of 0 or 100 has no exact risk, so the table uses 0.5 and 99.5 there.
    """
    d = Q["vendor"]["display"][version]
    score = np.arange(spec.VDI["score_min"], spec.VDI["score_max"] + 1, dtype=np.float64)
    q = np.clip(score, 0.5, 99.5) / 100.0
    risk = det_plogis((det_log(q / (1.0 - q)) - d["shift"]) / d["scale"])
    return np.maximum(_round(risk, 4), 0.0001)


def assay_shift(ctx):
    """mmol/L that the central laboratory's new lactate assay adds (mechanism P4)."""
    if ctx.get("day") is None:                   # the reference cohort has no calendar
        return np.zeros(len(ctx["facility"]))
    after = ctx["day"] >= ASSAY_DAY
    return np.where(CENTRAL_LAB[ctx["facility"]] & after, Q["assay_shift_mmol"], 0.0)


# ------------------------------------------------------------------ one batch of stays
def step(ctx, D, s, lactate_true, lactate_rec, lactate_rec_plain, icu, comfort,
         died_base, survivor_disposition, los_base, effects, intercept):
    """Vital signs, score, alert, response and deterioration for a batch of stays.

    The stay's course without any deterioration has already been drawn
    (`died_base`, `survivor_disposition`, `los_base`). This step decides who is
    on a ward at 12 hours, who deteriorates, and then changes the course of
    those who do. Returns the final death, disposition and length of stay with
    everything the index files need.
    """
    n = len(s)
    fac = ctx["facility"]
    dx = ctx["dx"]
    age = ctx["age"].astype(np.float64)
    age_c15 = (age - 64.0) / 15.0
    calendar = ctx.get("day") is not None
    eligible = (~icu) & (~comfort) & (los_base >= 0.5)

    # --- acute instability at 12 hours: tied to admission severity, skewed to the right
    a = Q["acute"]
    z = D["z_vital"]
    acute = a["severity_corr"] * s + math.sqrt(1.0 - a["severity_corr"] * a["severity_corr"]) * z[0]
    h = det_exp(a["log_sd"] * acute) - 1.0

    # --- true vital signs
    def true_vital(name, zrow):
        t = _VT[name]
        v = (t["mean"] + t["instability"] * h + t.get("age_per_15", 0.0) * age_c15
             + VITAL_DX[name][dx] + t["sd"] * zrow)
        return np.clip(v, t["min"], t["max"])

    hr = true_vital("hr", z[1])
    rr = true_vital("rr", z[2])
    sbp = true_vital("sbp", z[3])
    temp = true_vital("temp_c", z[4])
    c = Q["o2_support"]
    need = c["instability"] * h + O2_DX[dx] + z[6]
    o2 = (need >= c["low_flow_at"]).astype(np.int64) + (need >= c["high_flow_at"])
    # Saturation falls further as the need for oxygen grows: the low tail of SpO2.
    t = _VT["spo2"]
    spo2 = np.clip(true_vital("spo2", z[5]) - t["per_unit_of_need"] * np.maximum(0.0, need - t["need_above"]),
                   t["min"], t["max"])
    c = Q["alertness"]
    dull = c["instability"] * h + c["age_per_15"] * age_c15 + ALERT_DX[dx] + z[7]
    alertness = ((dull >= c["drowsy_at"]).astype(np.int64) + (dull >= c["confused_at"])
                 + (dull >= c["unresponsive_at"]))

    # --- recorded vital signs: measurement error, the charted default, the oximeter bias
    zr = D["z_vital_rec"]
    hr_rec = np.clip(_round(hr + _VR["hr_sd"] * zr[0], 0), _VT["hr"]["min"], _VT["hr"]["max"])
    rr_defaulted = D["u_vital_rec"] < RR_DEFAULT_SHARE[fac]
    rr_rec = np.where(rr_defaulted, float(_VR["rr_default"]),
                      np.clip(_round(rr + _VR["rr_sd"] * zr[1], 0), _VT["rr"]["min"], _VT["rr"]["max"]))
    sbp_rec = np.clip(_round(sbp + _VR["sbp_sd"] * zr[2], 0), _VT["sbp"]["min"], _VT["sbp"]["max"])
    temp_rec = np.clip(_round(temp + _VR["temp_sd"] * zr[3], 1), _VT["temp_c"]["min"], _VT["temp_c"]["max"])
    b = _VR["spo2_bias"]
    spo2_bias = np.where(ctx["race"] == BIASED_RACE,
                         np.where(spo2 < b["below"], b["size_below"], b["size"]), 0.0)
    spo2_rec = np.clip(_round(spo2 + spo2_bias + _VR["spo2_sd"] * zr[4], 0),
                       _VT["spo2"]["min"], _VT["spo2"]["max"])

    # --- true risk with no rapid-response evaluation
    enc_true = ctx["enc_network"] + ctx["enc_outside"]
    lp = (linear_predictor(_T, hr, rr, sbp, temp, spo2, o2, alertness, lactate_true, age, enc_true)
          + _T["comorbidity"] * (ctx["comorbidity"] - 2.5) + TRUTH_DX[dx] + _T["severity"] * s
          + _T["instability"] * h + _T["winter"] * ctx["winter"] + _T["unmeasured_sd"] * D["z_det"]
          + effects["deterioration"][fac] + TRUTH_FAC[fac])
    lp = intercept("deterioration", lp, eligible & SOLVED_ON[fac]) + lp
    p0 = det_plogis(lp)
    p1 = Q["response"]["risk_ratio"] * p0
    u = D["u_det"]
    y0 = eligible & (u[0] < p0)                  # common random numbers (decision D5):
    y1 = eligible & (u[0] < p1)                  # every y1 event is also a y0 event

    # --- the vendor's score, from recorded values only
    V = Q["vendor"]

    def vendor_lp(lactate):
        seen = np.where(np.isnan(lactate), V["lactate_imputed"], lactate)
        lp2 = V["v2"]["intercept"] + linear_predictor(V["v2"], hr_rec, rr_rec, sbp_rec, temp_rec, spo2_rec,
                                                      o2, alertness, seen, age, ctx["enc_network"])
        return lp2, V["v3"]["intercept"] + V["v3"]["slope"] * lp2

    if calendar:
        index_day = ctx["day"] + (ctx["hour"] + INDEX_HOURS) // 24
        v3 = index_day >= V3_DAY
        shown = index_day >= ALERTS_FROM[fac]
        months = (index_day - ALERTS_FROM[fac]) * 12.0 / 365.25
    else:                                        # the reference cohort: version 2.0, silent
        index_day = np.zeros(n, dtype=np.int64)
        v3 = np.zeros(n, dtype=bool)
        shown = np.zeros(n, dtype=bool)
        months = np.zeros(n)
    lp2, lp3 = vendor_lp(lactate_rec)
    lp2_plain, lp3_plain = vendor_lp(lactate_rec_plain)
    old, new = spec.VDI["versions"]
    score = np.where(v3, display_score(lp3, new), display_score(lp2, old))
    score_plain = np.where(v3, display_score(lp3_plain, new), display_score(lp2_plain, old))

    # --- alert, response (fading with months since go-live), realised outcome
    r = Q["response"]
    response_prob = np.maximum(r["floor"], r["start"] - r["fall_per_month"] * np.maximum(months, 0.0))
    alert = eligible & shown & (score >= THRESHOLD)
    rrt = alert & (D["u_alert"] < response_prob)
    y = np.where(rrt, y1, y0)

    # --- what the event is, and what it does to the rest of the stay
    etype = categorical_from_uniform(u[1], EVENT_W[fac])
    is_icu = y & (etype == EV_ICU)
    is_out = y & (etype == EV_OUT)
    is_death = y & (etype == EV_DEATH)
    c = Q["course"]
    died = np.where(is_death, True,
                    np.where(is_out, False, died_base | (is_icu & (u[2] < c["death_after_icu_transfer"]))))
    disposition = np.where(died, DISP_DIED, np.where(is_out, DISP_TRANSFER, survivor_disposition))
    w = c["window_los"]
    in_window = _round(w["min"] + (w["max"] - w["min"]) * u[3], 1)
    late = eligible & (~y) & died & (los_base <= w["max"])   # no death inside the window without an event
    los = np.where(is_death | is_out, in_window,
                   np.where(is_icu, _round(los_base * c["icu_transfer_los_factor"] + c["icu_transfer_los_add"], 1),
                            np.where(late, _round(los_base + w["max"], 1), los_base)))

    # --- the EHR outcome flag (mechanism P9)
    ue = D["u_ehr"]
    missed = y & (ue[0] < MISS[etype])
    false_positive = eligible & (~y) & (ue[1] < Q["ehr_flag"]["false_positive"])
    ehr_flag = (y & ~missed) | false_positive

    return {"died": died, "disposition": disposition, "los": los,
            "idx_eligible": eligible, "idx_day": index_day,
            "hr_true": hr, "rr_true": rr, "sbp_true": sbp, "temp_true": temp, "spo2_true": spo2,
            "o2": o2, "alertness": alertness,
            "hr_rec": hr_rec, "rr_rec": rr_rec, "sbp_rec": sbp_rec, "temp_rec": temp_rec,
            "spo2_rec": spo2_rec, "spo2_bias": spo2_bias, "rr_defaulted": rr_defaulted,
            "det_lp": lp, "p0": p0, "p1": p1, "y0": y0, "y1": y1, "y": y, "etype": etype,
            "vdi_score": score, "vdi_score_plain": score_plain, "vdi_v3": v3, "vdi_shown": shown,
            "alert": alert, "rrt": rrt, "response_prob": response_prob,
            "ehr_flag": ehr_flag, "ehr_missed": missed, "ehr_false_positive": false_positive}


STEP_KEYS = ("idx_eligible", "idx_day", "hr_true", "rr_true", "sbp_true", "temp_true", "spo2_true",
             "o2", "alertness", "hr_rec", "rr_rec", "sbp_rec", "temp_rec", "spo2_rec", "spo2_bias",
             "rr_defaulted", "det_lp", "p0", "p1", "y0", "y1", "y", "etype", "vdi_score",
             "vdi_score_plain", "vdi_v3", "vdi_shown", "alert", "rrt", "response_prob",
             "ehr_flag", "ehr_missed", "ehr_false_positive")


# ------------------------------------------------------------------ writers
def _ids(prefix, width, numbers):
    return [f"{prefix}{int(v):0{width}d}" for v in numbers]


def _blank(values, keep):
    out = np.array(values, dtype=object)
    out[~np.asarray(keep)] = None
    return out


def index_rows(adm, ndays):
    """Which admissions are index encounters in the files: on a ward at 12 hours,
    with the index time on or after the hospital's first scoring day and on or
    before the last day of data."""
    return (adm["idx_eligible"] & (adm["idx_day"] >= SCORING_FROM[adm["facility"]])
            & (adm["idx_day"] < ndays))


def write(outdir, adm, iso, ndays):
    """Write the Milestone 3 files. `adm` holds one array per column for every admission."""
    rows = index_rows(adm, ndays)
    g = {key: value[rows] for key, value in adm.items()}
    n = int(rows.sum())
    iso = np.array(iso, dtype=object)
    enc_id = np.array(_ids("E", 8, g["enc"]), dtype=object)
    hour = (g["hour"] + INDEX_HOURS) % 24
    label_day = g["idx_day"] + LABEL_DAYS
    labelled = label_day < ndays                 # the label arrived before the data end (decision D10)

    public = pd.DataFrame({
        "encounter_id": enc_id,
        "facility_id": np.array(FACILITY_IDS, dtype=object)[g["facility"]],
        "index_datetime": [f"{iso[d]}T{h:02d}:00" for d, h in zip(g["idx_day"].tolist(), hour.tolist())],
        "hr": g["hr_rec"],
        "rr": g["rr_rec"],
        "sbp": g["sbp_rec"],
        "temp_c": g["temp_rec"],
        "spo2": g["spo2_rec"],
        "o2_support": np.array(O2_CODES, dtype=object)[g["o2"]],
        "alertness": np.array(ALERT_CODES, dtype=object)[g["alertness"]],
        "lactate_at_index": g["rec_lactate"],
        "network_encounters_12m": g["enc_network"],
        "vdi_score": g["vdi_score"],
        "vdi_version": np.where(g["vdi_v3"], spec.VDI["versions"][1], spec.VDI["versions"][0]),
        "vdi_shown": g["vdi_shown"].astype(np.int64),
        "alert_fired": g["alert"].astype(np.int64),
        "rrt_evaluated": g["rrt"].astype(np.int64),
        "ehr_outcome_48h": _blank(g["ehr_flag"].astype(np.int64), labelled),
        "outcome_available_date": _blank(iso[np.minimum(label_day, ndays - 1)], labelled),
    })
    write_csv(public, outdir, "data/deterioration/index_encounters.csv")

    error = np.where(g["ehr_missed"], "missed", np.where(g["ehr_false_positive"], "false_positive", "none"))
    truth = pd.DataFrame({
        "encounter_id": enc_id,
        "hr_true": g["hr_true"],
        "rr_true": g["rr_true"],
        "sbp_true": g["sbp_true"],
        "temp_c_true": g["temp_true"],
        "spo2_true": g["spo2_true"],
        "lactate_true": g["lactate_true"],
        "spo2_bias": g["spo2_bias"],
        "rr_defaulted": g["rr_defaulted"].astype(np.int64),
        "outside_encounters_12m": g["enc_outside"],
        "deterioration_lp": g["det_lp"],
        "p0": g["p0"],
        "p1": g["p1"],
        "y0": g["y0"].astype(np.int64),
        "y1": g["y1"].astype(np.int64),
        "event_type": _blank(np.array(EVENT_TYPES, dtype=object)[g["etype"]], g["y0"]),
        "response_prob": np.where(g["alert"], g["response_prob"], np.nan),
        "y_true": g["y"].astype(np.int64),
        "ehr_flag_error": error,
        "vdi_score_no_assay_shift": g["vdi_score_plain"],
    })
    write_csv(truth, outdir, "hidden/deterioration/index_truth.csv")

    scores = np.arange(spec.VDI["score_min"], spec.VDI["score_max"] + 1)
    table = pd.DataFrame({
        "vdi_version": np.repeat(np.array(spec.VDI["versions"], dtype=object), len(scores)),
        "vdi_score": np.tile(scores, len(spec.VDI["versions"])),
        "vendor_risk": np.concatenate([vendor_risk_table(v) for v in spec.VDI["versions"]]),
    })
    write_csv(table, outdir, "data/deterioration/vendor_risk_table.csv")

    write_json(spec.VENDOR_MODEL_CARD, outdir, "data/deterioration/vendor_model_card.json")
    formula = {
        "world": spec.WORLD,
        "note": ("The vendor's formula, which a customer never sees. Simulator truth: never evidence. "
                 "The score is a fixed transform of the vendor's risk, one for each version. "
                 "Version 3.0 changes the intercept and slope of the risk logit and the transform."),
        "features": Q["features"],
        "v2": Q["vendor"]["v2"],
        "v3": Q["vendor"]["v3"],
        "display": Q["vendor"]["display"],
        "lactate_imputed_when_missing": Q["vendor"]["lactate_imputed"],
        "threshold": THRESHOLD,
        "true_model": {key: _T[key] for key in sorted(_T)},
        "response": Q["response"],
        "ehr_flag": Q["ehr_flag"],
    }
    write_json(formula, outdir, "hidden/deterioration/vdi_formula.json")
    return {"index_encounters": n}


# ------------------------------------------------------------------ Milestone 4 products
SILENT_FROM = _day(spec.DATES["vdi_silent_start"])
SILENT_TO = _day(spec.DATES["vdi_silent_end"])
F06 = NFAC - 1


def silent_rows(g):
    """Index encounters in the planned silent-mode window, at the five hospitals that had one."""
    return (g["idx_day"] >= SILENT_FROM) & (g["idx_day"] <= SILENT_TO) & (g["facility"] != F06)


def decile_cuts(scores):
    """The nine cut points between ten strata: the score at position ceil(k n / 10)
    in sorted order, k = 1 to 9. A score above a cut point is in a higher stratum."""
    v = np.sort(np.asarray(scores))
    return [int(v[(k * len(v) + 9) // 10 - 1]) for k in range(1, 10)]


def stratum_of(scores, cuts):
    return 1 + (np.asarray(scores)[:, None] > np.array(cuts)[None, :]).sum(axis=1)


def _vendor_risk(g):
    old, new = spec.VDI["versions"]
    return np.where(g["vdi_v3"], vendor_risk_table(new)[g["vdi_score"]], vendor_risk_table(old)[g["vdi_score"]])


def write_products(outdir, adm, S, iso, ndays):
    """Write the Milestone 4 files of this module. `S` holds the block streams."""
    rows = index_rows(adm, ndays)
    g = {key: value[rows] for key, value in adm.items()}
    iso = np.array(iso, dtype=object)
    enc_id = np.array(_ids("E", 8, g["enc"]), dtype=object)
    hour = (g["hour"] + INDEX_HOURS) % 24

    # --- chart review: a stratified sample of silent-mode encounters (block chart_review)
    c = spec.CHART_REVIEW
    r = S["chart_review"]
    sil = np.nonzero(silent_rows(g))[0]                       # in encounter order
    cuts = decile_cuts(g["vdi_score"][sil])
    stratum = stratum_of(g["vdi_score"][sil], cuts)
    picked, sizes = [], {}
    for k, take in enumerate(c["allocation"], 1):
        members = sil[stratum == k]
        sizes[k] = len(members)
        picked.append(members[np.sort(r.permutation(len(members))[:take])])
    picked = np.concatenate(picked)
    picked_stratum = stratum_of(g["vdi_score"][picked], cuts)
    u = r.random(len(picked))
    truth = g["y"][picked]
    reviewed = np.where(truth, u < c["reviewer_sensitivity"], u >= c["reviewer_specificity"])
    allocation = np.array(c["allocation"])[picked_stratum - 1]
    size = np.array([sizes[int(k)] for k in picked_stratum])
    review = pd.DataFrame({
        "encounter_id": enc_id[picked],
        "stratum": picked_stratum,
        "stratum_size": size,
        "stratum_sampled": allocation,
        "incl_prob": allocation / size,
        "reviewer_outcome": reviewed.astype(np.int64),
    })
    write_csv(review, outdir, "data/deterioration/chart_review.csv")

    # --- rapid-response log: one row for each evaluation (block rrt_log)
    q = spec.RRT_LOG
    r = S["rrt_log"]
    ev = np.nonzero(g["rrt"])[0]
    ev = ev[np.lexsort((g["enc"][ev], hour[ev], g["idx_day"][ev]))]      # by time, then encounter
    n = len(ev)
    delay = categorical_from_uniform(r.random(n), q["delay_hours"])
    nurse = q["nurse"]["added"] + det_gamma(r, q["nurse"]["shape"], n) * (q["nurse"]["mean"] / q["nurse"]["shape"])
    physician = (q["physician"]["added"]
                 + det_gamma(r, q["physician"]["shape"], n) * (q["physician"]["mean"] / q["physician"]["shape"]))
    stamp = g["idx_day"][ev] * 24 + hour[ev] + delay
    stamp = np.minimum(stamp, ndays * 24 - 1)                 # nothing is recorded after the data end
    order = np.lexsort((g["enc"][ev], stamp))                 # IDs run in the order the evaluations began
    stamp = stamp[order]
    log = pd.DataFrame({
        "rrt_id": _ids("RR", 6, np.arange(1, n + 1)),
        "encounter_id": enc_id[ev][order],
        "rrt_datetime": [f"{iso[d]}T{h:02d}:00" for d, h in zip((stamp // 24).tolist(), (stamp % 24).tolist())],
        "nurse_minutes": _round(nurse, 0)[order],
        "physician_minutes": _round(physician, 0)[order],
    })
    write_csv(log, outdir, "data/deterioration/rrt_log.csv")

    # --- the laboratory change log (block lab_change_log)
    L = spec.LAB_LOG
    r = S["lab_change_log"]
    sites = list(spec.LAB_SITES)
    site_day = np.array([max(int(FACILITY_START[FACILITY_IDS.index(f)]) for f in spec.LAB_SITES[site])
                         for site in sites])
    weight = np.array([L["site_weight"][site] for site in sites])
    first = _day(L["from"])
    days = first + r.integers(0, ndays - first, size=L["routine_entries"])
    site = categorical_from_uniform(r.random(L["routine_entries"]),
                                    np.where(days[:, None] >= site_day[None, :], weight[None, :], 0.0))
    template = r.integers(0, len(L["templates"]), size=L["routine_entries"])
    entries = [(int(d), int(k), 1, L["templates"][int(t)]) for d, k, t in zip(days, site, template)]
    entries += [(_day(date), sites.index(where), 0, (area, kind, text)) for date, where, area, kind, text in L["fixed"]]
    entries.sort(key=lambda e: (e[0], e[1], e[2], e[3]))
    lab = pd.DataFrame({
        "log_id": _ids("L", 4, np.arange(1, len(entries) + 1)),
        "effective_date": [iso[e[0]] for e in entries],
        "lab_site": [sites[e[1]] for e in entries],
        "facilities": [";".join(spec.LAB_SITES[sites[e[1]]]) for e in entries],
        "test_area": [e[3][0] for e in entries],
        "change_type": [e[3][1] for e in entries],
        "description": [e[3][2] for e in entries],
    })
    write_csv(lab, outdir, "data/network/lab_change_log.csv")

    # --- hidden: every planted change, dated
    write_csv(change_points(iso, ndays), outdir, "hidden/deterioration/change_points.csv")

    # --- hidden: monthly truth by hospital group
    vr = _vendor_risk(g)
    treated = np.where(g["rrt"], g["p1"], g["p0"])
    month = np.array([text[:7] for text in iso], dtype=object)[g["idx_day"]]
    at_threshold = g["vdi_score"] >= THRESHOLD
    groups = [(name, np.isin(g["facility"], [FACILITY_IDS.index(f) for f in members]))
              for name, members in spec.FACILITY_GROUPS.items()] + [("all", np.ones(len(month), dtype=bool))]
    out = []
    for m in sorted(set(month.tolist())):
        in_month = month == m
        for name, member in groups:
            cell = in_month & member
            count = int(cell.sum())
            if count == 0:
                continue
            fired = cell & g["alert"]
            expected = det_mean(vr[cell])
            as_treated = det_mean(treated[cell])
            out.append({"month": m, "facility_group": name, "index_encounters": count,
                        "true_rate_no_response": det_mean(g["p0"][cell]),
                        "true_rate_as_treated": as_treated,
                        "vendor_expected_rate": expected,
                        "true_oe": as_treated / expected,
                        "alert_rate": int(at_threshold[cell].sum()) / count,
                        "response_rate": (int((fired & g["rrt"]).sum()) / int(fired.sum())) if fired.any() else None})
    write_csv(pd.DataFrame(out), outdir, "hidden/deterioration/monthly_truth.csv")
    return {"chart_review": len(picked), "rrt_evaluations": n, "lab_log_entries": len(entries)}


def change_points(iso, ndays):
    """The planted changes with their dates (hidden/deterioration/change_points.csv)."""
    r = Q["response"]
    v = Q["vendor"]
    old, new = spec.VDI["versions"]
    steps = int(math.ceil((r["start"] - r["floor"]) / r["fall_per_month"] * 365.25 / 12.0 - 1e-9))
    five = ";".join(FACILITY_IDS[:F06])
    rows = [
        (_day(spec.DATES["r30_worklist_start"]), five, "r30_worklist_shown", 0.0, "log odds of readmission",
         "The R30 score is shown on the discharge-planning worklist. Its true effect on readmission is zero."),
        (SILENT_FROM, five, "silent_scoring_start", 0.0, "none",
         "VDI version 2.0 is scored and stored. Nobody sees it, so it changes nothing."),
        (_day(spec.DATES["lactate_assay_change"]), ";".join(f for f, lab in zip(FACILITY_IDS, CENTRAL_LAB) if lab),
         "lactate_assay_shift", Q["assay_shift_mmol"], "mmol/L added to recorded lactate",
         "The central laboratory's new method reads high. True lactate and true risk do not move; scores and alerts rise."),
        (int(FACILITY_START[F06]), FACILITY_IDS[F06], "acquisition", _T["facility_shift"][FACILITY_IDS[F06]],
         "logit of true risk, beside the drawn hospital effect",
         "Sallowfield's admissions enter the data: older patients, more events, and a record of other encounters that starts on this day."),
        (V3_DAY, ";".join(FACILITY_IDS), "vdi_version_3", v["v3"]["slope"],
         "slope applied to the version 2.0 risk logit",
         f"Version 3.0: risk logit = {v['v3']['intercept']} + {v['v3']['slope']} x the version 2.0 logit, with a new "
         f"score transform (shift {v['display'][new]['shift']} in place of {v['display'][old]['shift']}). Fewer alerts at the same threshold."),
    ]
    live = {}
    for j, fid in enumerate(FACILITY_IDS):
        live.setdefault(int(ALERTS_FROM[j]), []).append(fid)
    for day, members in sorted(live.items()):
        scope = ";".join(members)
        silent = all(int(SCORING_FROM[FACILITY_IDS.index(f)]) < day for f in members)
        rows.append((day, scope, "alerts_live" if silent else "alerts_live_no_silent_period", r["risk_ratio"],
                     "risk ratio after an evaluation",
                     f"Alerts are shown at a score of {THRESHOLD} or more. An answered alert multiplies the true risk by {r['risk_ratio']}."
                     + ("" if silent else " Scoring and alerts start together: no silent period.")))
        rows.append((day, scope, "response_fade_start", -r["fall_per_month"], "probability an alert is answered, per month",
                     f"The chance that an alert is answered starts at {r['start']} and falls each month since go-live."))
        if day + steps < ndays:
            rows.append((day + steps, scope, "response_floor_reached", r["floor"], "probability an alert is answered",
                         f"The chance that an alert is answered reaches its floor of {r['floor']} and stays there."))
    rows.sort(key=lambda row: (row[0], row[2], row[1]))
    return pd.DataFrame({
        "change_id": _ids("CP", 2, np.arange(1, len(rows) + 1)),
        "change_date": [iso[row[0]] for row in rows],
        "facilities": [row[1] for row in rows],
        "mechanism": [row[2] for row in rows],
        "size": [row[3] for row in rows],
        "unit": [row[4] for row in rows],
        "description": [row[5] for row in rows],
    })
