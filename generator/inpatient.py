"""The coupled inpatient simulation: network, persons, admissions with the 2021
burn-in, laboratory values, status at 12 hours, death, disposition, length of
stay and readmission truth.

Blocks 1, 2, 3, 10 to 14, 17 and 21 to 25; deterioration.py adds 15, 16 and 18 to 20. Design: DESIGN.md sections 5.2 and 6.
The model is described in prose in WORLD_SPEC.md; every coefficient is in
spec.INPATIENT.

Built in Milestone 2. Milestone 3 added vital signs, the vendor's score, alerts
and deterioration to the same day loop (deterioration.py, called from `course`),
and the inpatient files changed then: DESIGN.md section 15 lists how.

How it runs
  1. Network: hospital effects (block network).
  2. The append-only test hook (block dummy), which must change nothing.
  3. The catchment pool (blocks persons and comorbidity).
  4. A reference cohort (block calibration). The intercepts are solved on it by
     bisection, in order, and stored in hidden/calibrated_intercepts.json.
  5. The day loop, 2021-01-01 to 2026-06-30. Each step draws from its own block.
     A stay's whole course is drawn on its admission day; returns are scheduled
     as future admissions.
  6. Writers: every table exactly as spec.FILES declares it.

Data-path rules (common.py): no np.exp, np.log or built-in distributions; no
np.sum or np.mean of floats; no BLAS. Only the det_* helpers and exact arithmetic.
"""
import datetime as dt
import math

import numpy as np
import pandas as pd

import deterioration
import readmission
import spec
from common import (categorical_from_uniform, det_categorical, det_exp, det_log, det_mean,
                    det_normal, det_plogis, det_poisson, draw_dummy_block, rng,
                    solve_intercept, write_csv, write_json)

BUILT = True

P = spec.INPATIENT
FACILITY_IDS = [f["facility_id"] for f in spec.FACILITIES]
NFAC = len(FACILITY_IDS)
DX = list(spec.DX_GROUPS)
PAYER_CODES = list(spec.PAYERS)                  # medicare, medicaid, commercial, self_pay
RACE_CODES = list(spec.RACE_ETHNICITY)
DISP = list(spec.DISPOSITIONS)                   # home, home_health, snf, hospice, ama, transfer, died
DISP_DIED = DISP.index("died")
ELIGIBLE_DISP = [DISP.index(c) for c in spec.READMIT_ELIGIBLE_DISPOSITIONS]

SRC_NEW, SRC_READMIT, SRC_PLANNED = 0, 1, 2
NEVER = 10 ** 9                                  # "blocked until" value for a person who has died
PLACE_NONE, PLACE_NETWORK, PLACE_OUTSIDE = 0, 1, 2
PLACE_CODES = {PLACE_NETWORK: "network_hospital", PLACE_OUTSIDE: "outside"}

# ------------------------------------------------------------------ calendar
DAY0 = dt.date.fromisoformat(spec.DATES["burn_in_start"])
DAY_END = dt.date.fromisoformat(spec.DATES["data_end"])
NDAYS = (DAY_END - DAY0).days + 1                # 2,007 simulated days


def day_index(iso):
    return (dt.date.fromisoformat(iso) - DAY0).days


PUBLISHED_FROM = day_index(spec.DATES["published_start"])
_DATES = [DAY0 + dt.timedelta(days=i) for i in range(NDAYS)]
ISO = [d.isoformat() for d in _DATES]
YEAR = np.array([d.year for d in _DATES], dtype=np.int64)
MONTH = np.array([d.month for d in _DATES], dtype=np.int64)
WEEKDAY0 = DAY0.weekday()                        # Monday is 0
FAC_START = np.array([day_index(f["network_data_from"]) for f in spec.FACILITIES], dtype=np.int64)
MIN_AGE_DAYS = (P["min_age"] * 1461 + 3) // 4    # smallest day count with age >= min_age


def age_on(day, birth_day):
    """Whole years of age on a day index. Integer arithmetic on a 365.25-day year."""
    return ((day - birth_day) * 4) // 1461


# ------------------------------------------------------------------ tables from the spec
def _dx_vec(table, default=0.0):
    return np.array([table.get(g, default) for g in DX], dtype=np.float64)


def _fac_vec(table, default=0.0):
    return np.array([table.get(f, default) for f in FACILITY_IDS], dtype=np.float64)


def _mean_one(factors, weights):
    total = sum(f * w for f, w in zip(factors, weights))
    return [f * sum(weights) / total for f in factors]


_MONTH_DAYS = [31, 28.25, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
MONTH_F = _mean_one(P["month_factor"], _MONTH_DAYS)
WEEKDAY_F = _mean_one(P["weekday_factor"], [1.0] * 7)
NEW_RATE = np.array([f["admissions_per_year"] / 365.25 * P["new_arrival_share"]
                     for f in spec.FACILITIES], dtype=np.float64)

ELECTIVE_WEEKDAY = _fac_vec(P["elective_share_weekday"])
DX_EM_U65 = _dx_vec(P["dx_emergency_under_65"])
DX_EM_65 = _dx_vec(P["dx_emergency_65_plus"])
DX_ELECTIVE = _dx_vec(P["dx_elective"])
DX_WINTER = _dx_vec(P["dx_winter_multiplier"], 1.0)
SURG_EM = _dx_vec(P["surgery_share_emergency"])
SURG_EM_FAC = _fac_vec(P["surgery_emergency_multiplier"], 1.0)
SURG_EL = _dx_vec(P["surgery_share_elective"])
HOUR_EM = np.array(P["hour_emergency"], dtype=np.float64)
HOUR_EL = np.array(P["hour_elective"], dtype=np.float64)
_PB = P["payer_by_age"]
PAYER_CUM = np.array([np.cumsum([_PB["under_65"][c] for c in PAYER_CODES]),
                      np.cumsum([_PB["65_plus"][c] for c in PAYER_CODES])])

SEV_DX = _dx_vec(P["severity"]["dx"])
_LT = P["labs_true"]
LOG_MEDIAN = {k: float(det_log(_LT[k]["median"])) for k in ("creatinine", "wbc", "lactate")}
LAB_DX = {k: _dx_vec(_LT[k]["dx"]) for k in _LT}
_LR = P["labs_recorded"]
LACTATE_DX = _dx_vec(_LR["lactate_drawn"]["dx"])
LACTATE_FAC = _fac_vec(_LR["lactate_drawn"]["facility"])
ICU_DX = _dx_vec(P["icu"]["dx"])
ICU_FAC = _fac_vec(P["icu"]["facility"])
COMFORT_DX = _dx_vec(P["comfort_care"]["dx"])
_DP = P["disposition"]
SNF_DX = _dx_vec(_DP["snf"]["dx"])
HOSPICE_DX = _dx_vec(_DP["hospice"]["dx"])
AMA_PAYER = np.array([_DP["ama"]["payer"].get(c, 0.0) for c in PAYER_CODES])
TRANSFER_FAC = _fac_vec(_DP["transfer"]["facility"])
LOS_DX = _dx_vec(P["los"]["dx"])
LOS_DISP = np.array([P["los"]["disposition"].get(c, 0.0) for c in DISP])
_SHORT = P["los"]["short_stay"]
SHORT_DISP = np.array([_SHORT["share"] if c in _SHORT["dispositions"] else 0.0 for c in DISP])
_RM = P["readmission"]
READMIT_DX = _dx_vec(_RM["dx"])
READMIT_DISP = np.array([_RM["disposition"].get(c, 0.0) for c in DISP])
READMIT_PAYER = np.array([_RM["payer"].get(c, 0.0) for c in PAYER_CODES])
GAP_W = np.array([1.0 / (g + _RM["gap_weight_offset"]) for g in range(1, 31)])
OUTSIDE_PAYER = np.array([P["outside_readmission"]["payer"].get(c, 0.0) for c in PAYER_CODES])
PLANNED_DX = _dx_vec(P["planned_return"]["dx"], P["planned_return"]["default"])
_DA = P["death_after_discharge"]
DAD_DISP = np.array([_DA["intercept"].get(c, 0.0) for c in DISP])
DAD_MEAN_GAP = np.array([_DA["mean_gap_days"]["hospice" if c == "hospice" else "other"]
                         for c in DISP])
WINTER_MONTHS = set(spec.WINTER_MONTHS)

# Where a readmission goes when it is not to the same hospital: by home area,
# before and after F06 joined. Row = area index * 2 + (1 if F06 is in the network).
_VOLUME = np.array([f["admissions_per_year"] for f in spec.FACILITIES], dtype=np.float64)
ALT_FACILITY = np.array([
    [_VOLUME[j] * P["catchment_mix"][FACILITY_IDS[j]][area] * (1.0 if (after or j != NFAC - 1) else 0.0)
     for j in range(NFAC)]
    for area in spec.AREAS for after in (0, 1)])
F06_START = int(FAC_START[NFAC - 1])


def _round(x, decimals):
    """Round half up to a fixed number of decimals, with exact operations only."""
    k = float(10 ** decimals)
    return np.floor(x * k + 0.5) / k


# ------------------------------------------------------------------ network and pool
def _standardise(z):
    """Centre and scale a few draws to mean 0 and SD exactly 1 (population SD)."""
    centred = z - det_mean(z)
    return centred / math.sqrt(det_mean(centred * centred))


def build_network(S):
    """Hospital effects (block network): six draws each, centred and scaled to the design SD."""
    z = det_normal(S["network"], 2 * NFAC)
    sd = P["facility_effect_sd"]
    return {"readmission": sd["readmission"] * _standardise(z[:NFAC]),
            "deterioration": sd["deterioration"] * _standardise(z[NFAC:])}


def build_pool(S):
    """The catchment pool of adults (blocks persons and comorbidity)."""
    r = S["persons"]
    n = P["pool_size"]
    pa = P["pool_age"]
    ages = np.arange(pa["min"], pa["max"] + 1, dtype=np.float64)
    density = np.where(ages <= pa["knee"], 1.0, (pa["top"] - ages) / (pa["top"] - pa["knee"]))
    age_ref = ages[det_categorical(r, density, n)] + r.random(n)
    birth_day = day_index(P["age_reference_date"]) - np.floor(age_ref * 365.25).astype(np.int64)
    female = r.random(n) < spec.FEMALE_SHARE
    race = det_categorical(r, list(spec.RACE_ETHNICITY.values()), n)
    interpreter = r.random(n) < np.array([P["interpreter_by_race"][c] for c in RACE_CODES])[race]
    area = det_categorical(r, [P["area_share"][a] for a in spec.AREAS], n)
    frailty = det_normal(r, n)
    oc = P["outside_care"]
    outside_logit = (oc["intercept"] + np.array([oc[a] for a in spec.AREAS])[area]
                     + oc["sd"] * det_normal(r, n))
    u_payer = r.random(n)

    cm = P["comorbidity"]
    lam = det_exp(cm["log_mean"] + cm["age_per_year"] * (age_ref - 64.0) + cm["frailty"] * frailty)
    comorbidity = np.minimum(det_poisson(S["comorbidity"], np.minimum(lam, 400.0)),
                             spec.COMORBIDITY_MAX)

    # Admission weights by hospital, as running totals for inverse-CDF selection.
    ar = P["admission_rate"]
    base = ar["age_per_year"] * (age_ref - 50.0) + ar["frailty"] * frailty
    cum, total = [], []
    rate = np.zeros(n)                           # expected new admissions a year, for the reference cohort
    f06_weight = P["reference"]["f06_weight"]
    for j, fid in enumerate(FACILITY_IDS):
        mix = np.array([P["catchment_mix"][fid][a] / P["area_share"][a] for a in spec.AREAS])
        w = det_exp(base + P["facility_age_tilt"][fid] * (age_ref - 64.0) / 15.0) * mix[area]
        c = np.cumsum(w)
        cum.append(c)
        total.append(float(c[-1]))
        share = f06_weight if j == NFAC - 1 else 1.0
        rate += NEW_RATE[j] * 365.25 * share * w / c[-1]

    # Other encounters in the last 12 months (Milestone 3, mechanism P5): one fixed
    # pair of counts per person, drawn last so that everything above is unchanged.
    # The network's record holds the first count; the second happened elsewhere.
    en = spec.DETERIORATION["encounters"]
    older = (age_ref >= 65.0).astype(np.int64)
    payer_ref = np.minimum((u_payer[:, None] >= PAYER_CUM[older]).sum(axis=1), len(PAYER_CODES) - 1)
    payer_term = np.array([en["outside_payer"].get(c, 0.0) for c in PAYER_CODES])[payer_ref]
    mean_enc = det_exp(en["log_mean"] + en["frailty"] * frailty + en["age_per_15"] * (age_ref - 64.0) / 15.0)
    share_out = det_plogis(outside_logit + payer_term)
    enc_net = det_poisson(r, np.minimum(mean_enc * (1.0 - share_out), 400.0))
    enc_out = det_poisson(r, np.minimum(mean_enc * share_out, 400.0))
    return {"n": n, "age_ref": age_ref, "birth_day": birth_day, "female": female, "race": race,
            "interpreter": interpreter, "area": area, "frailty": frailty,
            "outside_logit": outside_logit, "u_payer": u_payer, "comorbidity": comorbidity,
            "cum": cum, "total": total, "rate": rate, "enc_net": enc_net, "enc_out": enc_out}


def select_persons(pool, facility, u):
    """Pool index for each uniform, by the hospital's admission weights."""
    idx = np.searchsorted(pool["cum"][facility], u * pool["total"][facility], side="right")
    return np.minimum(idx, pool["n"] - 1)


# ------------------------------------------------------------------ one batch of stays
def attributes(pool, person, facility, source, age, weekday, winter, index_dx, u):
    """Admission attributes for a batch. `u` is five rows of uniforms."""
    weekend = weekday >= 5
    p_elective = ELECTIVE_WEEKDAY[facility] * np.where(weekend, P["elective_weekend_multiplier"], 1.0)
    elective = np.where(source == SRC_NEW, u[0] < p_elective, source == SRC_PLANNED)
    older = age >= 65
    w = np.where(older[:, None], DX_EM_65[None, :], DX_EM_U65[None, :])
    w = w * np.where(np.asarray(winter)[:, None], DX_WINTER[None, :], 1.0)
    dx = np.where(elective, categorical_from_uniform(u[1], DX_ELECTIVE),
                  categorical_from_uniform(u[1], w))
    same = (source == SRC_READMIT) & (u[2] < P["readmission_same_dx"])
    dx = np.where((source == SRC_PLANNED) | same, index_dx, dx)
    surgery = u[3] < np.where(elective, SURG_EL[dx], SURG_EM[dx] * SURG_EM_FAC[facility])
    hour = np.where(elective, categorical_from_uniform(u[4], HOUR_EL),
                    categorical_from_uniform(u[4], HOUR_EM))
    cum = PAYER_CUM[older.astype(np.int64)]
    payer = np.minimum((pool["u_payer"][person][:, None] >= cum).sum(axis=1), len(PAYER_CODES) - 1)
    return {"person": person, "facility": facility, "source": source, "age": age,
            "female": pool["female"][person], "frailty": pool["frailty"][person],
            "area": pool["area"][person], "outside_logit": pool["outside_logit"][person],
            "race": pool["race"][person],
            "emergency": ~elective, "dx": dx, "surgery": surgery, "hour": hour, "payer": payer,
            "winter": np.asarray(winter, dtype=bool)}


def draw_course(gen, n):
    """Every random array one batch of n stays needs, in a fixed order.

    `gen(block)` returns the block's Generator. In the day loop each step has
    its own stream; for the reference cohort every step uses block calibration.
    """
    out = {}
    out["z_severity"] = det_normal(gen("admission_attributes"), n)
    out["z_lab"] = det_normal(gen("labs_true"), 5 * n).reshape(5, n)
    out["u_measured"] = gen("labs_recorded").random((3, n))
    out["z_recorded"] = det_normal(gen("labs_recorded"), 5 * n).reshape(5, n)
    out["u_status"] = gen("index_eligibility").random((2, n))
    out["u_death"] = gen("inpatient_death").random((3, n))
    out["u_disposition"] = gen("los_disposition").random(n)
    out["z_los"] = det_normal(gen("los_disposition"), n)
    out["u_short"] = gen("los_disposition").random((2, n))
    out["u_readmit"] = gen("readmission").random((4, n))
    out["u_outside"] = gen("outside_care").random(n)
    out["u_planned"] = gen("planned_readmission").random((2, n))
    # Milestone 3, added after everything above so that the earlier draws keep their order.
    out["z_vital"] = det_normal(gen("vitals_true"), 8 * n).reshape(8, n)
    out["z_vital_rec"] = det_normal(gen("vitals_recorded"), 5 * n).reshape(5, n)
    out["u_vital_rec"] = gen("vitals_recorded").random(n)
    out["z_det"] = det_normal(gen("deterioration"), n)
    out["u_det"] = gen("deterioration").random((4, n))
    out["u_alert"] = gen("alert_response").random(n)
    out["u_ehr"] = gen("ehr_outcome").random((2, n))
    return out


def course(ctx, D, K, effects, targets=None):
    """The clinical course of a batch of stays, from context `ctx` and draws `D`.

    `K` holds the solved intercepts. When `targets` is given (the reference
    cohort), any intercept not yet in `K` is solved here, in order, so that the
    batch mean equals the target.
    """
    def intercept(name, lp, mask=None):
        if name not in K:
            if targets is None:
                raise KeyError(f"intercept {name} has not been solved")
            x = lp if mask is None else lp[mask]
            K[name] = solve_intercept(lambda a: det_plogis(a + x), targets[name])
            K["reference_mean"][name] = det_mean(det_plogis(K[name] + x))
        return K[name]

    age_c = ctx["age"] - 64.0
    frailty = ctx["frailty"]
    dx = ctx["dx"]
    fac = ctx["facility"]
    payer = ctx["payer"]
    emergency = ctx["emergency"].astype(np.float64)
    surgery = ctx["surgery"].astype(np.float64)
    female = ctx["female"].astype(np.float64)
    comorbidity = ctx["comorbidity"].astype(np.float64)

    # --- unmeasured severity, standardised on the reference cohort
    sv = P["severity"]
    raw = (sv["frailty"] * frailty + sv["age_per_15"] * age_c / 15.0
           + sv["comorbidity_per_2"] * (comorbidity - 2.5) / 2.0 + SEV_DX[dx]
           + sv["emergency"] * emergency + sv["readmission"] * (ctx["source"] == SRC_READMIT)
           + sv["winter"] * ctx["winter"] + sv["noise_sd"] * D["z_severity"])
    if "severity_center" not in K:
        if targets is None:
            raise KeyError("severity has not been standardised")
        K["severity_center"] = det_mean(raw)
        dev = raw - K["severity_center"]
        K["severity_scale"] = math.sqrt(det_mean(dev * dev))
    s = (raw - K["severity_center"]) / K["severity_scale"]

    # --- true laboratory values
    z = D["z_lab"]
    t = _LT["sodium"]
    sodium = np.clip(t["mean"] + t["severity"] * s + LAB_DX["sodium"][dx] + t["sd"] * z[0],
                     t["min"], t["max"])
    t = _LT["creatinine"]
    creatinine = np.clip(det_exp(LOG_MEDIAN["creatinine"] + t["severity"] * s
                                 + t["age_per_15"] * age_c / 15.0 + t["female"] * female
                                 + LAB_DX["creatinine"][dx] + t["log_sd"] * z[1]),
                         t["min"], t["max"])
    t = _LT["hemoglobin"]
    hemoglobin = np.clip(t["mean"] + t["severity"] * s + t["age_per_15"] * age_c / 15.0
                         + t["female"] * female + LAB_DX["hemoglobin"][dx] + t["sd"] * z[2],
                         t["min"], t["max"])
    t = _LT["wbc"]
    wbc = np.clip(det_exp(LOG_MEDIAN["wbc"] + t["severity"] * s + LAB_DX["wbc"][dx]
                          + t["log_sd"] * z[3]), t["min"], t["max"])
    t = _LT["lactate"]
    lactate = np.clip(det_exp(LOG_MEDIAN["lactate"] + t["severity"] * s + LAB_DX["lactate"][dx]
                              + t["log_sd"] * z[4]), t["min"], t["max"])

    # --- recorded laboratory values
    u = D["u_measured"]
    zr = D["z_recorded"]
    nz = _LR["noise"]
    is_emergency = ctx["emergency"]
    chem = u[0] < np.where(is_emergency, _LR["chemistry_measured"]["emergency"],
                           _LR["chemistry_measured"]["elective"])
    count = u[1] < np.where(is_emergency, _LR["blood_count_measured"]["emergency"],
                            _LR["blood_count_measured"]["elective"])
    ld = _LR["lactate_drawn"]
    lp = (ld["severity"] * s + ld["emergency"] * emergency + ld["surgery"] * surgery
          + LACTATE_FAC[fac] + LACTATE_DX[dx])
    lactate_drawn = u[2] < det_plogis(intercept("lactate_drawn", lp) + lp)
    nan = np.nan
    creatinine_rec = np.maximum(0.1, _round(creatinine * (1.0 + nz["creatinine_cv"] * zr[1]), 2))
    wbc_rec = np.maximum(0.1, _round(wbc * (1.0 + nz["wbc_cv"] * zr[3]), 1))
    # The central laboratory's assay change (mechanism P4) adds a shift from March 2024.
    # The unshifted value is kept for the paired counterfactual score.
    lactate_measured = lactate * (1.0 + nz["lactate_cv"] * zr[4])
    lactate_plain = np.where(lactate_drawn, np.maximum(_LR["lactate_min"], _round(lactate_measured, 1)), nan)
    lactate_rec = np.maximum(_LR["lactate_min"], _round(lactate_measured + deterioration.assay_shift(ctx), 1))
    rec = {
        "sodium": np.where(chem, _round(sodium + nz["sodium_sd"] * zr[0], 0), nan),
        "creatinine": np.where(chem, creatinine_rec, nan),
        "hemoglobin": np.where(count, _round(hemoglobin + nz["hemoglobin_sd"] * zr[2], 1), nan),
        "wbc": np.where(count, wbc_rec, nan),
        "lactate": np.where(lactate_drawn, lactate_rec, nan),
    }

    # --- status at 12 hours
    c = P["icu"]
    lp = (c["severity"] * s + c["emergency_surgery"] * emergency * surgery + ICU_FAC[fac] + ICU_DX[dx])
    icu = D["u_status"][0] < det_plogis(intercept("icu", lp) + lp)
    c = P["comfort_care"]
    lp = c["severity"] * s + c["age_per_year"] * age_c + c["frailty"] * frailty + COMFORT_DX[dx]
    comfort = D["u_status"][1] < det_plogis(intercept("comfort_care", lp) + lp)

    # --- death in hospital, before any deterioration on the ward is counted
    c = P["death"]
    lp = c["severity"] * s + c["age_per_year"] * age_c + c["icu"] * icu + c["comfort_care"] * comfort
    died = D["u_death"][0] < det_plogis(intercept("death", lp) + lp)

    # --- disposition among survivors: multinomial logit against home
    n = len(s)
    w = np.ones((n, DISP_DIED))                  # home, home_health, snf, hospice, ama, transfer
    c = _DP["home_health"]
    w[:, 1] = det_exp(c["intercept"] + c["age_per_year"] * age_c + c["severity"] * s
                      + c["comorbidity"] * (comorbidity - 2.5))
    c = _DP["snf"]
    w[:, 2] = det_exp(c["intercept"] + c["age_per_year"] * age_c + c["severity"] * s
                      + c["frailty"] * frailty + SNF_DX[dx])
    c = _DP["hospice"]
    w[:, 3] = det_exp(c["intercept"] + c["age_per_year"] * age_c + c["severity"] * s
                      + c["comfort_care"] * comfort + HOSPICE_DX[dx])
    c = _DP["ama"]
    w[:, 4] = det_exp(c["intercept"] + c["age_per_year"] * age_c + c["elective"] * (1.0 - emergency)
                      + AMA_PAYER[payer])
    c = _DP["transfer"]
    w[:, 5] = det_exp(TRANSFER_FAC[fac] + c["severity"] * s + c["icu"] * icu)
    survivor_disposition = categorical_from_uniform(D["u_disposition"], w)
    disposition = np.where(died, DISP_DIED, survivor_disposition)

    # --- length of stay
    c = P["los"]
    log_los = (c["mu"] + c["severity"] * s + c["icu"] * icu
               + c["elective_surgery"] * (1.0 - emergency) * surgery + LOS_DX[dx]
               + LOS_DISP[disposition] + c["sd"] * D["z_los"])
    los = np.maximum(0.1, _round(det_exp(log_los), 1))
    short = D["u_short"][0] < SHORT_DISP[disposition]
    los = np.where(short, _round(_SHORT["min"] + (_SHORT["max"] - _SHORT["min"]) * D["u_short"][1], 1), los)

    # --- the ward at 12 hours: vital signs, the vendor's score, alert, response and
    # deterioration (Milestone 3). A deterioration changes death, disposition and stay.
    det = deterioration.step(ctx, D, s, lactate, rec["lactate"], lactate_plain, icu, comfort,
                             died, survivor_disposition, los, effects, intercept)
    died, disposition, los = det["died"], det["disposition"], det["los"]

    # --- true 30-day unplanned readmission to any hospital
    eligible = np.isin(disposition, ELIGIBLE_DISP)
    c = _RM
    lp = (c["age_per_year"] * age_c + c["comorbidity"] * comorbidity
          + c["prior_admits"] * np.minimum(ctx["prior"], c["prior_admits_cap"])
          + c["log_los"] * det_log(los) + c["emergency"] * emergency + c["severity"] * s
          + c["frailty"] * frailty
          + c["hemoglobin_below_12_per_g"] * np.maximum(0.0, 12.0 - hemoglobin)
          + c["sodium_below_138_per_mmol"] * np.maximum(0.0, 138.0 - sodium)
          + READMIT_DISP[disposition] + READMIT_PAYER[payer] + READMIT_DX[dx]
          + effects["readmission"][fac])
    readmit_lp = intercept("readmission", lp, eligible) + lp
    readmit_prob = det_plogis(readmit_lp)
    ur = D["u_readmit"]
    readmit = eligible & (ur[0] < readmit_prob)
    gap = 1 + categorical_from_uniform(ur[1], GAP_W)
    outside = readmit & (D["u_outside"] < det_plogis(ctx["outside_logit"] + OUTSIDE_PAYER[payer]))

    # --- planned return, among eligible discharges with no unplanned readmission
    pr = P["planned_return"]
    planned = eligible & ~readmit & (D["u_planned"][0] < PLANNED_DX[dx])
    span = pr["gap_max"] - pr["gap_min"] + 1
    planned_gap = pr["gap_min"] + np.minimum(np.floor(D["u_planned"][1] * span), span - 1).astype(np.int64)

    # --- death after discharge, outside hospital
    lp = DAD_DISP[disposition] + _DA["severity"] * s + _DA["age_per_year"] * age_c
    death_gap = 1 + np.floor(-DAD_MEAN_GAP[disposition] * det_log(1.0 - D["u_death"][2])).astype(np.int64)
    death_after = (~died) & (D["u_death"][1] < det_plogis(lp)) & (death_gap <= _DA["horizon_days"])

    out = {key: det[key] for key in deterioration.STEP_KEYS}
    out.update(
           {"severity": s, "sodium_true": sodium, "creatinine_true": creatinine,
            "hemoglobin_true": hemoglobin, "wbc_true": wbc, "lactate_true": lactate,
            "lactate_drawn": lactate_drawn, "recorded": rec, "icu": icu, "comfort": comfort,
            "died": died, "disposition": disposition, "los": los, "eligible": eligible,
            "readmit_lp": readmit_lp, "readmit_prob": readmit_prob, "readmit": readmit,
            "gap": gap, "outside": outside, "planned": planned, "planned_gap": planned_gap,
            "death_after": death_after, "death_gap": death_gap,
            "u_same_facility": ur[2], "u_other_facility": ur[3]})
    return out


# ------------------------------------------------------------------ calibration
def calibrate(pool, effects, S):
    """Solve the intercepts on a reference cohort (block calibration).

    The cohort is a set of admissions drawn the way the day loop draws them,
    but all at once and with no history: hospital by volume, month and weekday
    by their factors, person by the hospital's admission weights. Prior
    admissions come from each person's expected admission rate.
    """
    r = S["calibration"]
    R = P["reference"]
    n = R["size"]
    volume = _VOLUME.copy()
    volume[NFAC - 1] *= R["f06_weight"]
    facility = det_categorical(r, volume, n)
    month = 1 + det_categorical(r, [f * d for f, d in zip(MONTH_F, _MONTH_DAYS)], n)
    weekday = det_categorical(r, WEEKDAY_F, n)
    u = r.random(n)
    person = np.empty(n, dtype=np.int64)
    for j in range(NFAC):
        m = facility == j
        person[m] = select_persons(pool, j, u[m])
    mix = R["source_mix"]
    source = det_categorical(r, [mix["new"], mix["readmission"], mix["planned"]], n)
    age = np.maximum(P["min_age"], np.floor(pool["age_ref"][person])).astype(np.int64)
    prior = det_poisson(r, np.minimum(pool["rate"][person] * R["prior_admits_factor"], 50.0))
    prior = prior + (source != SRC_NEW)
    gained = r.random(n) < P["comorbidity"]["gain_per_admission"]
    comorbidity = np.minimum(pool["comorbidity"][person] + gained, spec.COMORBIDITY_MAX)
    index_dx = det_categorical(r, 0.5 * (DX_EM_U65 + DX_EM_65), n)
    winter = np.isin(month, list(WINTER_MONTHS))
    ctx = attributes(pool, person, facility, source, age, weekday, winter, index_dx, r.random((5, n)))
    ctx["comorbidity"] = comorbidity
    ctx["prior"] = prior
    ctx["day"] = None                            # no calendar: version 2.0, silent, no assay shift
    ctx["enc_network"] = prior + pool["enc_net"][person]
    ctx["enc_outside"] = pool["enc_out"][person]
    K = {"reference_mean": {}}
    course(ctx, draw_course(lambda block: r, n), K, effects, targets=R["targets"])
    return K


# ------------------------------------------------------------------ the day loop
def simulate(pool, K, effects, S):
    """Run the day loop and return one row per admission, as arrays."""
    npool = pool["n"]
    birth_day = pool["birth_day"]
    area = pool["area"]
    blocked = np.full(npool, -1, dtype=np.int64)     # not at risk of a new admission through this day
    comorbidity = pool["comorbidity"].copy()
    death_day = np.full(npool, -1, dtype=np.int64)
    death_place = np.zeros(npool, dtype=np.int64)
    history = {}                                     # person -> admission days, ascending
    outside_history = {}                             # person -> days of outside readmissions, ascending
    schedule = {}                                    # day -> list of (person, facility, source, index encounter, index dx)
    outside_rows = []
    cols = {}
    n_enc = 0
    gain = P["comorbidity"]["gain_per_admission"]
    block_days = P["block_after_discharge_days"]
    same_facility = _RM["same_facility"]
    arrivals = S["arrivals"]

    def gen(block):
        return S[block]

    for d in range(NDAYS):
        month = int(MONTH[d])
        weekday = (WEEKDAY0 + d) % 7
        winter = month in WINTER_MONTHS

        # 1. arrivals: new admissions per hospital, then who they are
        lam = NEW_RATE * (MONTH_F[month - 1] * WEEKDAY_F[weekday])
        lam = np.where(FAC_START <= d, lam, 0.0)
        counts = det_poisson(arrivals, lam)
        persons, facs, srcs, index_enc, index_dx = [], [], [], [], []
        for j in range(NFAC):
            need = int(counts[j])
            while need > 0:
                cand = select_persons(pool, j, arrivals.random(2 * need + 8))
                for p in cand.tolist():
                    if blocked[p] < d and d - birth_day[p] >= MIN_AGE_DAYS:
                        blocked[p] = d
                        persons.append(p)
                        facs.append(j)
                        srcs.append(SRC_NEW)
                        index_enc.append(0)
                        index_dx.append(0)
                        need -= 1
                        if need == 0:
                            break

        # 2. returns scheduled for today
        for p, j, src, enc, dxi in schedule.pop(d, ()):
            persons.append(p)
            facs.append(j)
            srcs.append(src)
            index_enc.append(enc)
            index_dx.append(dxi)

        n = len(persons)
        if n == 0:
            continue
        person = np.array(persons, dtype=np.int64)
        facility = np.array(facs, dtype=np.int64)
        source = np.array(srcs, dtype=np.int64)

        # 3. admission attributes, comorbidity, prior admissions from the network's own record
        age = age_on(d, birth_day[person])
        ctx = attributes(pool, person, facility, source, age, np.full(n, weekday),
                         np.full(n, winter), np.array(index_dx, dtype=np.int64),
                         S["admission_attributes"].random((5, n)))
        gained = S["comorbidity"].random(n) < gain
        comorbidity[person] = np.minimum(comorbidity[person] + gained, spec.COMORBIDITY_MAX)
        ctx["comorbidity"] = comorbidity[person]
        prior = np.zeros(n, dtype=np.int64)
        since = d - 365
        for i, p in enumerate(persons):
            h = history.get(p)
            if h is None:
                history[p] = [d]
            else:
                c = 0
                for x in reversed(h):
                    if x < since:
                        break
                    c += 1
                prior[i] = c
                h.append(d)
        ctx["prior"] = prior
        outside_recent = np.zeros(n, dtype=np.int64)
        for i, p in enumerate(persons):
            h = outside_history.get(p)
            if h is not None:
                outside_recent[i] = sum(1 for x in h if since <= x <= d)
        ctx["day"] = np.full(n, d, dtype=np.int64)
        # The network's record of a Sallowfield patient's other encounters starts when
        # the hospital joined, so it fills in over the first 12 months (mechanism P11).
        other = pool["enc_net"][person]
        on_record = np.where(facility == NFAC - 1,
                             np.floor(other * min(1.0, (d - F06_START) / 365.0)).astype(np.int64), other)
        ctx["enc_network"] = prior + on_record
        ctx["enc_outside"] = outside_recent + pool["enc_out"][person] + (other - on_record)

        # 4 to 10. the whole course of each stay
        out = course(ctx, draw_course(gen, n), K, effects)

        los10 = np.floor(out["los"] * 10.0 + 0.5).astype(np.int64)
        discharge = d + (ctx["hour"] * 10 + los10 * 24) // 240
        gap = out["gap"]
        return_day = discharge + gap
        after_f06 = (return_day >= F06_START).astype(np.int64)
        other = categorical_from_uniform(out["u_other_facility"], ALT_FACILITY[area[person] * 2 + after_f06])
        return_facility = np.where(out["u_same_facility"] < same_facility, facility, other)
        planned_day = discharge + out["planned_gap"]
        planned_weekday = (WEEKDAY0 + planned_day) % 7
        planned_day = planned_day + np.where(planned_weekday == 5, 2, np.where(planned_weekday == 6, 1, 0))

        enc = n_enc + 1 + np.arange(n, dtype=np.int64)
        n_enc += n
        died = out["died"].tolist()
        readmit = out["readmit"].tolist()
        outside = out["outside"].tolist()
        planned = out["planned"].tolist()
        death_after = out["death_after"].tolist()
        death_gap = out["death_gap"].tolist()
        disc = discharge.tolist()
        gaps = gap.tolist()
        dxs = ctx["dx"].tolist()
        for i in range(n):
            p = persons[i]
            dd = disc[i]
            if died[i]:
                blocked[p] = NEVER
                death_day[p] = dd
                death_place[p] = PLACE_NETWORK
                continue
            dies = death_after[i]
            when = dd + death_gap[i]
            if readmit[i]:
                g = gaps[i]
                if outside[i]:
                    blocked[p] = dd + g + block_days
                    outside_rows.append((int(enc[i]), p, dd + g, g))
                    outside_history.setdefault(p, []).append(dd + g)
                    when = max(when, dd + g + 1)
                else:
                    day2 = dd + g
                    blocked[p] = day2
                    dies = False                 # fate is drawn again at the readmission
                    if day2 < NDAYS:
                        schedule.setdefault(day2, []).append(
                            (p, int(return_facility[i]), SRC_READMIT, int(enc[i]), dxs[i]))
            elif planned[i]:
                day2 = int(planned_day[i])
                blocked[p] = day2
                dies = False
                if day2 < NDAYS:
                    schedule.setdefault(day2, []).append((p, facs[i], SRC_PLANNED, int(enc[i]), dxs[i]))
            else:
                blocked[p] = dd + block_days
            if dies:
                blocked[p] = NEVER
                death_day[p] = when
                death_place[p] = PLACE_OUTSIDE

        row = {"enc": enc, "person": person, "facility": facility, "day": np.full(n, d, dtype=np.int64),
               "hour": ctx["hour"], "discharge": discharge, "age": age, "payer": ctx["payer"],
               "emergency": ctx["emergency"], "surgery": ctx["surgery"], "dx": ctx["dx"],
               "comorbidity": ctx["comorbidity"], "prior": prior, "source": source,
               "index_enc": np.array(index_enc, dtype=np.int64),
               "enc_network": ctx["enc_network"], "enc_outside": ctx["enc_outside"]}
        for key in ("severity", "sodium_true", "creatinine_true", "hemoglobin_true", "wbc_true",
                    "lactate_true", "lactate_drawn", "icu", "comfort", "died", "disposition", "los",
                    "eligible", "readmit_lp", "readmit_prob", "readmit", "gap", "outside", "planned"
                    ) + deterioration.STEP_KEYS:
            row[key] = out[key]
        for key, value in out["recorded"].items():
            row["rec_" + key] = value
        for key, value in row.items():
            cols.setdefault(key, []).append(value)

    adm = {key: np.concatenate(parts) for key, parts in cols.items()}
    return adm, outside_rows, death_day, death_place


# ------------------------------------------------------------------ writers
def _ids(prefix, width, numbers):
    return [f"{prefix}{int(v):0{width}d}" for v in numbers]


def _codes(codes, idx):
    return np.array(codes, dtype=object)[idx]


def _blank(values, keep):
    """Object array with None wherever `keep` is False."""
    out = np.array(values, dtype=object)
    out[~np.asarray(keep)] = None
    return out


def write_network(outdir, effects):
    fac = pd.DataFrame([{k: f[k] for k in ("facility_id", "facility_name", "facility_type", "area",
                                           "beds", "network_data_from", "vdi_scoring_from",
                                           "vdi_alerts_from", "central_lab")}
                        for f in spec.FACILITIES])
    write_csv(fac, outdir, "data/network/facilities.csv")
    timeline = pd.DataFrame([{"event_date": spec.DATES[key], "event_code": code, "scope": scope,
                              "description": text}
                             for key, code, scope, text in spec.TIMELINE_EVENTS])
    write_csv(timeline, outdir, "data/network/timeline.csv")
    truth = pd.DataFrame({"facility_id": FACILITY_IDS,
                          "readmit_effect_logit": effects["readmission"],
                          "deterioration_effect_logit": effects["deterioration"]})
    write_csv(truth, outdir, "hidden/inpatient/facility_truth.csv")


def write_inpatient(outdir, pool, adm, outside_rows, death_day, death_place):
    n = len(adm["enc"])
    day = adm["day"]
    year = YEAR[day]
    closed = adm["discharge"] < NDAYS            # discharged on or before the last day of data
    in_hospital_12h = adm["los"] >= 0.5
    enc_id = np.array(_ids("E", 8, adm["enc"]), dtype=object)
    person_id = np.array(_ids("P", 7, adm["person"] + 1), dtype=object)
    iso = np.array(ISO, dtype=object)
    discharge_iso = _blank(iso[np.minimum(adm["discharge"], NDAYS - 1)], closed)

    public = pd.DataFrame({
        "encounter_id": enc_id,
        "person_id": person_id,
        "facility_id": _codes(FACILITY_IDS, adm["facility"]),
        "admit_datetime": [f"{ISO[d]}T{h:02d}:00" for d, h in zip(day.tolist(), adm["hour"].tolist())],
        "discharge_date": discharge_iso,
        "los_days": np.where(closed, adm["los"], np.nan),
        "age": adm["age"],
        "payer": _codes(PAYER_CODES, adm["payer"]),
        "admission_type": np.where(adm["emergency"], "emergency", "elective"),
        "service": np.where(adm["surgery"], "surgery", "medicine"),
        "dx_group": _codes(DX, adm["dx"]),
        "comorbidity_count": adm["comorbidity"],
        "prior_admits_12m": adm["prior"],
        "planned_admission": (adm["source"] == SRC_PLANNED).astype(np.int64),
        "sodium": adm["rec_sodium"],
        "creatinine": adm["rec_creatinine"],
        "hemoglobin": adm["rec_hemoglobin"],
        "wbc": adm["rec_wbc"],
        "lactate": adm["rec_lactate"],
        "icu_at_12h": (adm["icu"] & in_hospital_12h).astype(np.int64),
        "comfort_care_12h": (adm["comfort"] & in_hospital_12h).astype(np.int64),
        "disposition": _blank(_codes(DISP, adm["disposition"]), closed),
        "died_in_hospital": (adm["died"] & closed).astype(np.int64),
    })

    # The readmission's encounter, looked up from the returning admission.
    link = np.zeros(int(adm["enc"].max()) + 1, dtype=np.int64)
    back = adm["source"] == SRC_READMIT
    link[adm["index_enc"][back]] = adm["enc"][back]
    linked = link[adm["enc"]]
    eligible = adm["eligible"]
    readmit = adm["readmit"]
    truth = pd.DataFrame({
        "encounter_id": enc_id,
        "person_id": person_id,
        "in_published_data": (day >= PUBLISHED_FROM).astype(np.int64),
        "severity_latent": adm["severity"],
        "sodium_true": adm["sodium_true"],
        "creatinine_true": adm["creatinine_true"],
        "hemoglobin_true": adm["hemoglobin_true"],
        "wbc_true": adm["wbc_true"],
        "lactate_true": adm["lactate_true"],
        "lactate_drawn": adm["lactate_drawn"].astype(np.int64),
        "readmit_eligible": eligible.astype(np.int64),
        "readmit_lp": np.where(eligible, adm["readmit_lp"], np.nan),
        "readmit_prob": np.where(eligible, adm["readmit_prob"], np.nan),
        "readmit_any_30d": readmit.astype(np.int64),
        "readmit_outside": adm["outside"].astype(np.int64),
        "readmit_gap_days": np.where(readmit, adm["gap"], np.nan),
        "planned_return": adm["planned"].astype(np.int64),
        "readmit_encounter_id": _blank(_ids("E", 8, linked), linked > 0),
    })

    for y in spec.SIMULATED_YEARS:
        rows = year == y
        write_csv(truth[rows], outdir, f"hidden/inpatient/admissions_truth_{y}.csv")
        if y in spec.PUBLISHED_YEARS:
            write_csv(public[rows], outdir, f"data/inpatient/admissions_{y}.csv")
        else:
            write_csv(public[rows], outdir, f"hidden/inpatient/burnin_admissions_{y}.csv")

    # Persons: everyone admitted at least once; the public file keeps those with
    # at least one published admission.
    ever = np.zeros(pool["n"], dtype=bool)
    ever[adm["person"]] = True
    published = np.zeros(pool["n"], dtype=bool)
    published[adm["person"][day >= PUBLISHED_FROM]] = True
    idx = np.nonzero(ever)[0]
    pub = np.nonzero(published)[0]
    birth = (np.datetime64(DAY0.isoformat(), "D") + pool["birth_day"]).astype("datetime64[Y]").astype(np.int64) + 1970
    persons = pd.DataFrame({
        "person_id": _ids("P", 7, pub + 1),
        "sex": np.where(pool["female"][pub], "f", "m"),
        "birth_year": birth[pub],
        "race_ethnicity": _codes(RACE_CODES, pool["race"][pub]),
        "interpreter_needed": pool["interpreter"][pub].astype(np.int64),
        "home_area": _codes(list(spec.AREAS), pool["area"][pub]),
    })
    write_csv(persons, outdir, "data/inpatient/persons.csv")
    died = (death_day[idx] >= 0) & (death_day[idx] < NDAYS)
    persons_truth = pd.DataFrame({
        "person_id": _ids("P", 7, idx + 1),
        "in_published_data": published[idx].astype(np.int64),
        "frailty": pool["frailty"][idx],
        "outside_care_propensity": det_plogis(pool["outside_logit"][idx]),
        "death_date": _blank(iso[np.clip(death_day[idx], 0, NDAYS - 1)], died),
        "death_place": _blank([PLACE_CODES.get(int(v)) for v in death_place[idx]], died),
    })
    write_csv(persons_truth, outdir, "hidden/inpatient/persons_truth.csv")

    rows = [r for r in outside_rows if r[2] < NDAYS]
    outside = pd.DataFrame({
        "index_encounter_id": _ids("E", 8, [r[0] for r in rows]),
        "person_id": _ids("P", 7, [r[1] + 1 for r in rows]),
        "outside_admit_date": [ISO[r[2]] for r in rows],
        "gap_days": [r[3] for r in rows],
    })
    write_csv(outside, outdir, "hidden/inpatient/outside_readmissions.csv")
    return {"admissions": n, "published_admissions": int((day >= PUBLISHED_FROM).sum()),
            "persons": int(len(pub)), "outside_readmissions": len(rows)}


def write_intercepts(outdir, K):
    R = P["reference"]
    names = list(R["targets"])
    obj = {
        "world": spec.WORLD,
        "note": ("Intercepts solved by bisection on a reference cohort drawn from block 3 "
                 "(calibration), so that the cohort mean equals the target. The day loop's "
                 "population differs a little from the cohort; CHECKS.md tests the realised "
                 "values. Simulator truth: never evidence."),
        "reference_cohort_size": R["size"],
        "severity": {"center": K["severity_center"], "scale": K["severity_scale"]},
        "intercepts": {name: {"target": R["targets"][name], "intercept": K[name],
                              "reference_mean": K["reference_mean"][name]} for name in names},
    }
    write_json(obj, outdir, "hidden/calibrated_intercepts.json")


# ------------------------------------------------------------------ entry point
STREAMS = ("network", "persons", "calibration", "arrivals", "admission_attributes", "comorbidity",
           "labs_true", "labs_recorded", "vitals_true", "vitals_recorded", "index_eligibility",
           "alert_response", "deterioration", "ehr_outcome", "los_disposition",
           "inpatient_death", "readmission", "outside_care", "planned_readmission",
           "chart_review", "rrt_log", "lab_change_log")


def generate(outdir):
    """Generate the inpatient core under `outdir` and return a short summary."""
    S = {block: rng(block) for block in STREAMS}
    effects = build_network(S)
    draw_dummy_block()                           # append-only test hook; must change nothing
    pool = build_pool(S)
    K = calibrate(pool, effects, S)
    adm, outside_rows, death_day, death_place = simulate(pool, K, effects, S)
    write_network(outdir, effects)
    summary = write_inpatient(outdir, pool, adm, outside_rows, death_day, death_place)
    summary.update(deterioration.write(outdir, adm, ISO, NDAYS))
    # Milestone 4: products drawn after the day loop, from their own blocks. They read
    # the simulation and change nothing in it.
    summary.update(deterioration.write_products(outdir, adm, S, ISO, NDAYS))
    summary.update(readmission.write(outdir, adm, pool, K, effects, ISO, NDAYS, day_index, WEEKDAY0, MONTH))
    write_intercepts(outdir, K)
    return summary
