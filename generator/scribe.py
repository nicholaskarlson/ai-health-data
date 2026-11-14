"""The AI scribe (Milestone 5): clinics, clinicians, the seeded rollout draw, the
clinician-week panel, the wellbeing survey, the frame of AI-drafted notes, the
true errors in every note, the audit sample, the raters and their ratings.

Blocks 30 to 36 and 40 to 43, one stream each. Nothing here reads the inpatient
world or draws from its blocks, so this module cannot change an earlier file.

Order (DESIGN.md decision D11): the panel is generated first, and the frame then
holds exactly as many notes for a clinician-week as the panel's scribe_visits.

Where the scribe changes something, hidden/ keeps the paired answer for the same
clinician-week without it (decision D6): the visits come from one uniform draw
read at two means, and the documentation and after-hours minutes share their noise.

Data-path rules as in common.py: det_* helpers only, exact sums, no built-in
distributions. Every true value is rounded to the decimals it is written with
before it is used, so hidden/ reproduces data/ exactly.

Everything generated is fictional. hidden/ is simulator truth and is never evidence.
"""
import datetime as dt
import math

import numpy as np
import pandas as pd

import spec
from common import (categorical_from_uniform, det_categorical, det_exp, det_gamma, det_log,
                    det_mean, det_normal, det_plogis, det_poisson, poisson_from_uniform, rng,
                    solve_intercept, write_csv, write_json)

BUILT = True

C = spec.SCRIBE
STREAMS = ("clinics_clinicians", "rollout_draw", "clinician_traits", "adoption", "clinician_weeks",
           "survey", "notes_frame", "note_errors", "audit_sample", "rater_parameters", "ratings")

# ------------------------------------------------------------------ calendar
WEEK0 = dt.date.fromisoformat(spec.DATES["scribe_measure_start"])     # a Monday
NWEEKS = spec.SCRIBE_WEEKS
WEEK_ISO = [(WEEK0 + dt.timedelta(days=7 * w)).isoformat() for w in range(NWEEKS)]
WAVE_WEEK0 = np.array(C["wave_weeks"], dtype=np.int64) - 1            # go-live week, counted from 0
V24_WEEK0 = C["version_24_week"] - 1
HOLIDAY = np.array([C["holiday_weeks"].get(iso, 1.0) for iso in WEEK_ISO])
_CLOSED = {dt.date.fromisoformat(d).toordinal() for d in C["closed_dates"]}
# Open weekdays (Monday = 0 to Friday = 4) of each week, padded with -1.
OPEN_DAYS = np.full((NWEEKS, 5), -1, dtype=np.int64)
N_OPEN = np.zeros(NWEEKS, dtype=np.int64)
for _w in range(NWEEKS):
    _days = [d for d in range(5) if WEEK0.toordinal() + 7 * _w + d not in _CLOSED]
    OPEN_DAYS[_w, :len(_days)] = _days
    N_OPEN[_w] = len(_days)

CLINIC_IDS = [c[0] for c in C["clinics"]]
NCLINIC = len(CLINIC_IDS)
CLINIC_SPECIALTY = np.array([c[1] == "specialty" for c in C["clinics"]])
GROUP_OF = {s: g for g, members in spec.SPECIALTY_GROUPS.items() for s in members}
ROLE_CODES = list(C["roles"])
TYPE_CODES = list(spec.ADOPTION_TYPES)                 # adopter, partial, never
ADOPTER, PARTIAL, NEVER = 0, 1, 2
ERRORS = list(spec.ERROR_TYPES)                        # omission, hallucination, misattribution, wrong_value
SEV = list(spec.SEVERITIES)                            # none, minor, moderate, major


def _round(x, decimals):
    """Round half up to a fixed number of decimals, with exact operations only."""
    k = float(10 ** decimals)
    return np.floor(np.asarray(x, dtype=np.float64) * k + 0.5) / k


def _standardise(z):
    """Centre and scale draws to mean 0 and SD exactly 1 (population SD)."""
    centred = z - det_mean(z)
    return centred / math.sqrt(det_mean(centred * centred))


def _ids(prefix, width, numbers):
    return [f"{prefix}{int(v):0{width}d}" for v in numbers]


def _blank(values, keep):
    """Object array with None wherever `keep` is False."""
    out = np.array(values, dtype=object)
    out[~np.asarray(keep)] = None
    return out


def _count_true(matrix, columns):
    """Row counts of True among the first `columns[i]` entries of row i."""
    mask = np.arange(matrix.shape[1])[None, :] < columns[:, None]
    return (matrix & mask).sum(axis=1).astype(np.int64)


# ------------------------------------------------------------------ clinics, clinicians, rollout
def build_clinics(S):
    """Clinic sizes, interpreter rates and the clinicians (block clinics_clinicians)."""
    r = S["clinics_clinicians"]
    weights = np.array([C["clinic_size_weight"][c[1]] for c in C["clinics"]])
    extra = C["clinicians"] - NCLINIC * C["clinic_min_clinicians"]
    size = C["clinic_min_clinicians"] + np.bincount(det_categorical(r, weights, extra), minlength=NCLINIC)
    il = C["interpreter_logit"]
    interpreter_rate = _round(det_plogis(il["mean"] + il["sd"] * det_normal(r, NCLINIC)), 4)
    n = int(size.sum())
    clinic = np.repeat(np.arange(NCLINIC), size)
    role = det_categorical(r, list(C["roles"].values()), n)
    fte = np.array([v for v, _ in C["fte"]])[det_categorical(r, [w for _, w in C["fte"]], n)]
    return {"n": n, "size": size, "interpreter_rate": interpreter_rate, "clinic": clinic,
            "role": role, "fte": fte, "specialty": CLINIC_SPECIALTY[clinic]}


def draw_rollout(S):
    """Wave of each clinic (block rollout_draw): each stratum is shuffled, then dealt
    to waves 1, 2, 3, 4, 1, 2 ... so every wave gets four primary care and two specialty clinics."""
    r = S["rollout_draw"]
    wave = np.zeros(NCLINIC, dtype=np.int64)
    for specialty in (False, True):
        members = np.flatnonzero(CLINIC_SPECIALTY == specialty)
        order = r.permutation(len(members))
        wave[members[order]] = np.arange(len(members)) % len(C["wave_weeks"]) + 1
    return wave


# ------------------------------------------------------------------ clinician traits and adoption
def build_traits(S, K):
    """What each clinician is like before the scribe (blocks clinician_traits and adoption)."""
    r = S["clinician_traits"]
    n = K["n"]
    b = C["baseline_doc"]
    centre = np.where(K["specialty"], b["specialty"], b["primary_care"])
    baseline = _round(centre * det_exp(b["log_sd"] * det_normal(r, n)), 2)
    zb = _standardise(det_log(baseline / centre))          # how heavy a documenter, in SD units
    e = C["effect_minutes"]
    effect = _round(np.clip(e["mean"] + e["sd"] * det_normal(r, n), e["low"], e["high"]), 2)
    a = C["after_hours"]
    w = a["weight_on_baseline_doc"]
    z_ah = w * zb + math.sqrt(1.0 - w * w) * det_normal(r, n)
    after_hours = _round(a["mean_at_full_time"] * K["fte"]
                         * det_exp(a["log_sd"] * z_ah - 0.5 * a["log_sd"] * a["log_sd"]), 1)
    sc = C["same_day_close"]
    close_logit = sc["logit_mean"] + sc["logit_sd"] * det_normal(r, n)
    wb = C["wellbeing"]
    ww = wb["weight_on_baseline_doc"]
    wellbeing0 = _round(ww * zb + math.sqrt(1.0 - ww * ww) * det_normal(r, n), 4)
    z_effect = det_normal(r, n)
    volume = det_exp(C["visit_volume"]["clinician_log_sd"] * det_normal(r, n))

    # Adoption: a latent propensity that rises with baseline documentation time
    # (planted selection, P23). Types are dealt by rank, so their shares are exact.
    r = S["adoption"]
    ad = C["adoption"]
    propensity = ad["weight_on_baseline_doc"] * zb + det_normal(r, n)
    order = np.argsort(propensity, kind="stable")
    kind = np.full(n, ADOPTER, dtype=np.int64)
    kind[order[:ad["never"]]] = NEVER
    kind[order[ad["never"]:ad["never"] + ad["partial"]]] = PARTIAL
    z_share = det_normal(r, n)
    sl = ad["steady_share_logit"]
    steady = np.where(kind == ADOPTER, det_plogis(sl["adopter"][0] + sl["adopter"][1] * z_share),
                      np.where(kind == PARTIAL, det_plogis(sl["partial"][0] + sl["partial"][1] * z_share), 0.0))
    steady = _round(steady, 4)

    eff = wb["effect"]
    params = np.array([eff[TYPE_CODES[k]] for k in kind])          # mean, SD, low, high per clinician
    wellbeing_effect = _round(np.clip(params[:, 0] + params[:, 1] * z_effect, params[:, 2], params[:, 3]), 4)
    return {"baseline": baseline, "zb": zb, "effect": effect, "after_hours": after_hours,
            "close_logit": close_logit, "wellbeing0": wellbeing0, "wellbeing_effect": wellbeing_effect,
            "volume": volume, "kind": kind, "steady": steady}


# ------------------------------------------------------------------ the clinician-week panel
def build_panel(S, K, T, wave):
    """One row per clinician and week (block clinician_weeks), with the paired
    no-scribe values for hidden/."""
    r = S["clinician_weeks"]
    n, W = K["n"], NWEEKS
    N = n * W
    ci = np.repeat(np.arange(n), W)
    wk = np.tile(np.arange(W), n)
    go = WAVE_WEEK0[wave[K["clinic"][ci]] - 1]
    live = wk >= go
    k = np.where(live, wk - go, 0)                          # whole weeks since go-live
    P = C["panel"]

    ramp = np.array(list(C["adoption"]["ramp"]) + [1.0] * W)[k]
    share = np.where(live, _round(T["steady"][ci] * ramp, 4), 0.0)      # chance a visit uses the scribe
    learning = np.where(live, np.array(list(P["learning"]) + [1.0] * W)[k], 0.0)

    # Visits: one uniform per row, read at the mean without the scribe and at the mean with it.
    vv = C["visit_volume"]
    away = r.random(N) < vv["away_probability"]
    per_fte = np.where(K["specialty"], vv["per_fte_week"]["specialty"], vv["per_fte_week"]["primary_care"])
    lam0 = np.where(away, 0.0, (per_fte * K["fte"] * T["volume"])[ci] * HOLIDAY[wk])
    lam1 = np.where(away, 0.0, lam0 + P["visits_effect"] * share * learning)
    u = r.random(N)
    visits0 = poisson_from_uniform(u, lam0)
    visits = poisson_from_uniform(u, lam1)

    # Scribe visits and same-day closes: one uniform per visit.
    most = int(visits.max())
    scribe_visits = _count_true(r.random((N, most)) < share[:, None], visits)
    has = visits > 0
    safe = np.where(has, visits, 1)
    realised = scribe_visits / safe                         # 0 where there were no visits
    dose = realised * learning
    sc = C["same_day_close"]
    p_close = det_plogis(T["close_logit"][ci] + P["same_day_close_effect_logit"] * dose
                         + sc["week_logit_sd"] * det_normal(r, N))
    closed = _count_true(r.random((N, most)) < p_close[:, None], visits)

    # Documentation minutes per visit: the same noise with and without the scribe.
    noise = (P["week_shock_sd"] * det_normal(r, N)
             + P["visit_sd"] * det_normal(r, N) / np.sqrt(safe))
    saving = _round(T["effect"][ci] * learning, 2)          # minutes saved on each scribe visit
    doc0 = np.maximum(T["baseline"][ci] + P["trend_per_week"] * wk + noise, P["doc_floor"])
    doc = np.maximum(T["baseline"][ci] + P["trend_per_week"] * wk + noise - saving * realised,
                     P["doc_floor"])

    # After-hours minutes.
    a = C["after_hours"]
    volume = np.where(away, a["away_share"], HOLIDAY[wk])
    ah0 = T["after_hours"][ci] * volume * det_exp(a["week_log_sd"] * det_normal(r, N)
                                                  - 0.5 * a["week_log_sd"] * a["week_log_sd"])
    ah = ah0 * (1.0 + P["after_hours_effect"] * dose)

    return {"N": N, "ci": ci, "wk": wk, "live": live, "k": k, "share": share, "learning": learning,
            "visits0": visits0, "visits": visits, "scribe_visits": scribe_visits, "has": has,
            "realised": realised, "closed": closed, "saving": saving, "doc0": doc0, "doc": doc,
            "ah0": ah0, "ah": ah}


# ------------------------------------------------------------------ the survey
def build_survey(S, K, T, wave):
    """The Tonmick Clinician Pulse (block survey): rows, latent wellbeing, response, items."""
    r = S["survey"]
    n = K["n"]
    sv = C["survey"]
    sd = C["wellbeing"]["wave_drift_sd"]
    clinician_wave = wave[K["clinic"]]
    post = _round(T["wellbeing0"] + sd * det_normal(r, n) + T["wellbeing_effect"], 4)
    final = _round(T["wellbeing0"] + sd * det_normal(r, n) + T["wellbeing_effect"], 4)
    has_post = clinician_wave < len(C["wave_weeks"])        # wave 4: the final survey serves
    who, code, month, latent = [], [], [], []
    for i in range(n):
        who.append(i); code.append("baseline"); month.append(spec.SURVEY_MONTHS["baseline"])
        latent.append(T["wellbeing0"][i])
        if has_post[i]:
            who.append(i); code.append("post_wave")
            month.append(sv["post_wave_months"][int(clinician_wave[i]) - 1]); latent.append(post[i])
        who.append(i); code.append("final"); month.append(spec.SURVEY_MONTHS["final"])
        latent.append(final[i])
    latent = np.array(latent)
    rows = len(latent)
    slope = sv["response_slope"]
    intercept = round(solve_intercept(lambda a: det_plogis(a + slope * latent), sv["response_target"]), 6)
    responded = r.random(rows) < det_plogis(intercept + slope * latent)
    noise = det_normal(r, rows * len(sv["items"])).reshape(rows, len(sv["items"]))
    items = []
    for j, (loading, shift, _wording) in enumerate(sv["items"]):
        x = sv["item_centre"] + shift + sv["item_scale"] * (
            loading * latent + math.sqrt(1.0 - loading * loading) * noise[:, j])
        items.append(np.clip(np.floor(x + 0.5), 1, 5).astype(np.int64))
    return {"who": np.array(who), "code": code, "month": month, "responded": responded, "items": items,
            "post": post, "final": final, "has_post": has_post, "intercept": intercept}


# ------------------------------------------------------------------ the notes frame
def build_notes(S, K, Pn):
    """One note for every scribe visit in the panel (block notes_frame)."""
    r = S["notes_frame"]
    N = C["notes"]
    row = np.repeat(np.arange(Pn["N"]), Pn["scribe_visits"])
    M = len(row)
    first = np.cumsum(Pn["scribe_visits"]) - Pn["scribe_visits"]
    seq = np.arange(M) - first[row]
    clinician = Pn["ci"][row]
    week = Pn["wk"][row]
    clinic = K["clinic"][clinician]
    specialty = CLINIC_SPECIALTY[clinic]

    pick = np.floor(r.random(M) * N_OPEN[week]).astype(np.int64)
    day = WEEK0.toordinal() + 7 * week + OPEN_DAYS[week, np.minimum(pick, N_OPEN[week] - 1)]

    u = r.random(M)
    visit_type = np.where(specialty, categorical_from_uniform(u, N["visit_type"]["specialty"]),
                          categorical_from_uniform(u, N["visit_type"]["primary_care"]))
    interpreter = r.random(M) < K["interpreter_rate"][clinic]
    vm = N["visit_minutes"]
    mean = np.array([vm[t] for t in spec.VISIT_TYPES])[visit_type] * np.where(interpreter, vm["interpreter_factor"], 1.0)
    minutes = np.clip(np.floor(mean * det_exp(vm["log_sd"] * det_normal(r, M) - 0.5 * vm["log_sd"] * vm["log_sd"]) + 0.5),
                      vm["low"], vm["high"])
    speakers = np.minimum(2 + det_categorical(r, N["speakers"], M) + interpreter, 6)
    words = np.maximum(np.floor(minutes * N["words_per_minute"] * det_exp(N["words_log_sd"] * det_normal(r, M))),
                       N["words_low"]).astype(np.int64)
    shape = N["edit"]["gamma_shape"]
    edit_noise = det_gamma(r, shape, M) / shape

    # Note IDs run in order of date, then clinician, then the visit's place in the week.
    order = np.lexsort((seq, clinician, day))
    out = {"M": M, "clinician": clinician, "week": week, "clinic": clinic, "day": day,
           "visit_type": visit_type, "interpreter": interpreter, "minutes": minutes,
           "speakers": speakers, "words": words, "edit_noise": edit_noise}
    out = {key: (value[order] if key != "M" else value) for key, value in out.items()}
    out["v24"] = out["week"] >= V24_WEEK0
    return out


# ------------------------------------------------------------------ true errors
def build_errors(S, F):
    """True errors in every note (block note_errors). Intercepts are solved on the
    version 2.3 notes, so that the expected rate there equals the target."""
    r = S["note_errors"]
    E = C["errors"]
    M = F["M"]
    clinic_effect = _round(E["clinic_logit_sd"] * _standardise(det_normal(r, NCLINIC)), 6)
    base = clinic_effect[F["clinic"]]
    lor = {name: float(det_log(np.array([value]))[0]) for name, value in E["odds_ratio"].items()}
    drivers = {
        "omission": (lor["omission_interpreter"] * F["interpreter"]
                     + lor["omission_long_visit"] * (F["minutes"] > E["long_visit_minutes"])),
        "hallucination": lor["hallucination_v24"] * F["v24"],
        "misattribution": lor["misattribution_three_speakers"] * (F["speakers"] >= E["many_speakers"]),
        "wrong_value": np.zeros(M),
    }
    v23 = ~F["v24"]
    intercept, count = {}, {}
    for name in ERRORS:
        x = base + drivers[name]
        intercept[name] = round(solve_intercept(lambda a, x=x: det_plogis(a + x[v23]),
                                                E["target_v23"][name]), E["intercept_decimals"])
        has = r.random(M) < det_plogis(intercept[name] + x)
        count[name] = has * (1 + det_poisson(r, E["extra_count_mean"], M))
    total = count["omission"] + count["hallucination"] + count["misattribution"] + count["wrong_value"]

    # Worst severity. Each error is major with chance q and moderate or worse with a
    # fixed chance; q is solved so that the target share of version 2.3 notes has a major error.
    def p_major(a, n):
        return 1.0 - det_exp(n * det_log(1.0 - det_plogis(np.array([a])))[0])
    major_logit = round(solve_intercept(lambda a: p_major(a, total[v23]), E["major_target_v23"]),
                        E["intercept_decimals"])
    pm = p_major(major_logit, total)
    pmod = 1.0 - det_exp(total * float(det_log(np.array([1.0 - E["moderate_per_error"]]))[0]))
    us = r.random(M)
    severity = np.where(total == 0, 0, np.where(us < pm, 3, np.where(us < pmod, 2, 1)))
    return {"clinic_effect": clinic_effect, "intercept": intercept, "major_logit": major_logit,
            "count": count, "total": total, "severity": severity, "log_odds_ratio": lor}


# ------------------------------------------------------------------ the audit
def stratum_codes(F, K):
    """Sampling stratum of every note: specialty group, interpreter, version."""
    groups = list(spec.SPECIALTY_GROUPS)
    group_of_clinic = np.array([groups.index(GROUP_OF[c[2]]) for c in C["clinics"]])
    return group_of_clinic[F["clinic"]], F["interpreter"].astype(np.int64), F["v24"].astype(np.int64)


def draw_audit(S, F, K):
    """The committee's stratified sample of notes (block audit_sample)."""
    r = S["audit_sample"]
    groups = list(spec.SPECIALTY_GROUPS)
    g, i, v = stratum_codes(F, K)
    picked, code, size, sampled = [], [], [], []
    for (group, interp, version), want in C["audit"]["allocation"].items():
        members = np.flatnonzero((g == groups.index(group)) & (i == interp)
                                 & (v == spec.SCRIBE_VERSIONS.index(version)))
        take = members[r.permutation(len(members))[:want]]
        picked.append(take)
        code += [spec.audit_stratum_code(group, interp, version)] * len(take)
        size += [len(members)] * len(take)
        sampled += [len(take)] * len(take)
    picked = np.concatenate(picked)
    order = np.argsort(picked, kind="stable")
    return {"note": picked[order], "stratum": np.array(code, dtype=object)[order],
            "size": np.array(size)[order], "sampled": np.array(sampled)[order]}


def draw_raters(S):
    """True accuracy of the eight raters and the senior reviewer (block rater_parameters)."""
    r = S["rater_parameters"]
    A = C["audit"]
    raters = spec.AUDIT["raters"]
    lenient = int(r.integers(0, raters))
    u = r.random((raters, len(ERRORS)))
    lo, hi = A["rater_sensitivity"]
    sens = lo + (hi - lo) * u
    llo, lhi = A["lenient_sensitivity"]
    sens[lenient] = llo + (lhi - llo) * u[lenient]
    flo, fhi = A["rater_false_positive"]
    fpr = flo + (fhi - flo) * r.random(raters)
    slo, shi = A["senior_sensitivity"]
    senior = slo + (shi - slo) * r.random(len(ERRORS))
    sflo, sfhi = A["senior_false_positive"]
    senior_fpr = sflo + (sfhi - sflo) * r.random(1)
    return {"sens": _round(np.vstack([sens, senior[None, :]]), 4),
            "fpr": _round(np.concatenate([fpr, senior_fpr]), 4), "lenient": lenient}


def draw_ratings(S, sample, Er, R):
    """Two independent ratings of every sampled note and, where they differ in any
    field, the senior reviewer's rating (block ratings)."""
    r = S["ratings"]
    A = C["audit"]
    raters = spec.AUDIT["raters"]
    note = sample["note"]
    m = len(note)
    first = r.integers(0, raters, size=m)
    second = (first + 1 + r.integers(0, raters - 1, size=m)) % raters
    U = r.random((m, 3, len(ERRORS) + 1))
    truth = np.stack([Er["count"][name][note] > 0 for name in ERRORS], axis=1)
    worst = Er["severity"][note]
    who = [first, second, np.full(m, raters)]
    flags, sev = [], []
    for k in range(3):
        chance = np.where(truth, R["sens"][who[k]], R["fpr"][who[k]][:, None])
        f = U[:, k, :len(ERRORS)] < chance
        any_flag = f.any(axis=1)
        found = (f & truth).any(axis=1)
        us = U[:, k, len(ERRORS)]
        moved = np.where(us < A["severity_agree"], worst,
                         np.where(us < A["severity_agree"] + A["severity_lower"],
                                  np.maximum(worst - 1, 1), np.minimum(worst + 1, 3)))
        false_alarm = np.where(us < A["false_alarm_minor"], 1, 2)
        flags.append(f)
        sev.append(np.where(~any_flag, 0, np.where(found, moved, false_alarm)))
    differ = (flags[0] != flags[1]).any(axis=1) | (sev[0] != sev[1])
    return {"who": who, "flags": flags, "severity": sev, "differ": differ}


# ------------------------------------------------------------------ writers
def write(outdir, K, wave, T, Pn, Sv, F, Er, sample, R, ratings):
    clinic_id = np.array(CLINIC_IDS, dtype=object)
    clinician_id = np.array(_ids("K", 3, np.arange(K["n"]) + 1), dtype=object)
    specialty = np.array([c[2] for c in C["clinics"]], dtype=object)
    go_live = np.array([spec.DATES[key] for key in spec.SCRIBE_WAVE_KEYS], dtype=object)

    write_csv(pd.DataFrame({
        "clinic_id": clinic_id, "clinic_type": [c[1] for c in C["clinics"]], "specialty": specialty,
        "area": [c[3] for c in C["clinics"]], "n_clinicians": K["size"]}), outdir, "data/scribe/clinics.csv")
    write_csv(pd.DataFrame({
        "clinician_id": clinician_id, "clinic_id": clinic_id[K["clinic"]],
        "role": np.array(ROLE_CODES, dtype=object)[K["role"]], "specialty": specialty[K["clinic"]],
        "fte": K["fte"]}), outdir, "data/scribe/clinicians.csv")
    write_csv(pd.DataFrame({
        "clinic_id": clinic_id, "stratum": [c[1] for c in C["clinics"]], "wave": wave,
        "go_live_date": go_live[wave - 1]}), outdir, "data/scribe/rollout.csv")

    week_iso = np.array(WEEK_ISO, dtype=object)
    ci, wk, has = Pn["ci"], Pn["wk"], Pn["has"]
    write_csv(pd.DataFrame({
        "clinician_id": clinician_id[ci], "clinic_id": clinic_id[K["clinic"][ci]],
        "week_start": week_iso[wk], "week_index": wk + 1, "clinic_live": Pn["live"].astype(np.int64),
        "weeks_since_go_live": _blank(Pn["k"], Pn["live"]),
        "holiday_week": (HOLIDAY[wk] < 1.0).astype(np.int64),
        "visits": Pn["visits"], "scribe_visits": Pn["scribe_visits"],
        "scribe_share": _blank(Pn["realised"], has),
        "doc_minutes_per_visit": _blank(Pn["doc"], has),
        "after_hours_minutes": Pn["ah"],
        "same_day_close_share": _blank(Pn["closed"] / np.where(has, Pn["visits"], 1), has),
    }), outdir, "data/scribe/clinician_weeks.csv")
    write_csv(pd.DataFrame({
        "clinician_id": clinician_id[ci], "week_start": week_iso[wk],
        "expected_scribe_share": Pn["share"], "learning": Pn["learning"],
        "saving_per_scribe_visit": Pn["saving"], "visits_no_scribe": Pn["visits0"],
        "doc_minutes_no_scribe": _blank(Pn["doc0"], has), "after_hours_no_scribe": Pn["ah0"],
    }), outdir, "hidden/economics/clinician_weeks_truth.csv")
    write_csv(pd.DataFrame({
        "clinician_id": clinician_id, "baseline_doc_minutes": T["baseline"],
        "adoption_type": np.array(TYPE_CODES, dtype=object)[T["kind"]],
        "individual_effect_minutes": T["effect"], "steady_share": T["steady"],
        "after_hours_baseline": T["after_hours"], "latent_wellbeing_baseline": T["wellbeing0"],
        "wellbeing_effect": T["wellbeing_effect"],
        "latent_wellbeing_post_wave": _blank(Sv["post"], Sv["has_post"]),
        "latent_wellbeing_final": Sv["final"],
    }), outdir, "hidden/economics/clinician_truth.csv")

    survey = {"clinician_id": clinician_id[Sv["who"]], "survey_wave": Sv["code"],
              "survey_month": Sv["month"], "responded": Sv["responded"].astype(np.int64)}
    for j, values in enumerate(Sv["items"]):
        survey[f"item{j + 1}"] = _blank(values, Sv["responded"])
    write_csv(pd.DataFrame(survey), outdir, "data/scribe/wellbeing_survey.csv")

    note_id = np.array(_ids("N", 7, np.arange(F["M"]) + 1), dtype=object)
    dates = {int(d): dt.date.fromordinal(int(d)).isoformat() for d in np.unique(F["day"])}
    edit = C["notes"]["edit"]
    edit_minutes = (edit["base"] + edit["per_error"] * Er["total"]
                    + edit["per_visit_minute"] * F["minutes"]) * F["edit_noise"]
    write_csv(pd.DataFrame({
        "note_id": note_id, "visit_date": [dates[int(d)] for d in F["day"]],
        "week_start": week_iso[F["week"]], "clinic_id": clinic_id[F["clinic"]],
        "clinician_id": clinician_id[F["clinician"]], "specialty": specialty[F["clinic"]],
        "visit_type": np.array(spec.VISIT_TYPES, dtype=object)[F["visit_type"]],
        "visit_minutes": F["minutes"], "interpreter_used": F["interpreter"].astype(np.int64),
        "n_speakers": F["speakers"],
        "scribe_version": np.array(spec.SCRIBE_VERSIONS, dtype=object)[F["v24"].astype(np.int64)],
        "note_words": F["words"], "edit_minutes": edit_minutes,
    }), outdir, "data/scribe/ai_notes_frame.csv")
    write_csv(pd.DataFrame({
        "note_id": note_id, "n_omission": Er["count"]["omission"],
        "n_hallucination": Er["count"]["hallucination"],
        "n_misattribution": Er["count"]["misattribution"], "n_wrong_value": Er["count"]["wrong_value"],
        "worst_severity": np.array(SEV, dtype=object)[Er["severity"]],
    }), outdir, "hidden/scribe/note_errors_truth.csv")
    write_csv(pd.DataFrame({
        "clinic_id": clinic_id, "error_effect_logit": Er["clinic_effect"],
        "interpreter_rate": K["interpreter_rate"]}), outdir, "hidden/scribe/clinic_effects.csv")

    write_csv(pd.DataFrame({
        "note_id": note_id[sample["note"]], "stratum": sample["stratum"],
        "stratum_size": sample["size"], "stratum_sampled": sample["sampled"],
        "incl_prob": sample["sampled"] / sample["size"]}), outdir, "data/scribe/audit_sample.csv")
    rater_id = np.array(_ids("R", 2, np.arange(spec.AUDIT["raters"] + 1) + 1), dtype=object)
    frames = []
    for k in range(3):
        keep = np.ones(len(sample["note"]), dtype=bool) if k < 2 else ratings["differ"]
        block = {"note_id": note_id[sample["note"]][keep], "rating_round": k + 1,
                 "rater_id": rater_id[ratings["who"][k]][keep]}
        for j, name in enumerate(ERRORS):
            block[name] = ratings["flags"][k][keep, j].astype(np.int64)
        block["severity"] = np.array(SEV, dtype=object)[ratings["severity"][k][keep]]
        frames.append(pd.DataFrame(block))
    write_csv(pd.concat(frames, ignore_index=True), outdir, "data/scribe/audit_ratings.csv")
    write_csv(pd.DataFrame({
        "rater_id": rater_id, "rater_role": ["rater"] * spec.AUDIT["raters"] + ["senior"],
        "sens_omission": R["sens"][:, 0], "sens_hallucination": R["sens"][:, 1],
        "sens_misattribution": R["sens"][:, 2], "sens_wrong_value": R["sens"][:, 3],
        "false_positive_rate": R["fpr"]}), outdir, "hidden/scribe/rater_parameters.csv")

    E = C["errors"]
    write_json({
        "world": spec.WORLD,
        "note": ("The true model behind hidden/scribe/note_errors_truth.csv. For each kind of error, "
                 "the chance that a note has at least one is plogis(intercept + the clinic's "
                 "error_effect_logit + the log odds ratios that apply). Intercepts were solved by "
                 "bisection on the version 2.3 notes. Simulator truth: never evidence."),
        "intercepts": Er["intercept"],
        "solved_for_version_2_3_rate": E["target_v23"],
        "log_odds_ratios": {name: round(value, 6) for name, value in Er["log_odds_ratio"].items()},
        "odds_ratios": E["odds_ratio"],
        "long_visit_is_more_than_minutes": E["long_visit_minutes"],
        "many_speakers_is_at_least": E["many_speakers"],
        "clinic_effect_logit_sd": E["clinic_logit_sd"],
        "errors_in_a_note_that_has_one": f"1 + Poisson({E['extra_count_mean']})",
        "severity": {
            "major_per_error_logit": Er["major_logit"],
            "major_per_error": round(float(det_plogis(np.array([Er["major_logit"]]))[0]), 6),
            "moderate_or_worse_per_error": E["moderate_per_error"],
            "solved_for_version_2_3_share_with_a_major_error": E["major_target_v23"],
            "rule": "worst severity over the note's errors, from one uniform draw per note",
        },
        "edit_minutes": {"formula": "(base + per_error * errors + per_visit_minute * visit_minutes) * noise",
                         **C["notes"]["edit"], "noise": "gamma with the given shape, mean 1"},
        "lenient_rater": str(rater_id[R["lenient"]]),
        "rater_rules": {"flag": "sensitivity if the note truly has that kind of error, else the false-positive rate",
                        "severity_agree": C["audit"]["severity_agree"],
                        "severity_one_lower": C["audit"]["severity_lower"],
                        "false_alarm_minor": C["audit"]["false_alarm_minor"]},
    }, outdir, "hidden/scribe/error_model_truth.json")

    P, ad = C["panel"], C["adoption"]
    write_json({
        "world": spec.WORLD,
        "note": ("True effects of the scribe in the clinician-week panel. Each clinician's own values "
                 "are in clinician_truth.csv, and the paired no-scribe values for every "
                 "clinician-week are in clinician_weeks_truth.csv. Simulator truth: never evidence."),
        "documentation_minutes": {
            "saving_per_scribe_visit_mean": C["effect_minutes"]["mean"],
            "saving_per_scribe_visit_sd": C["effect_minutes"]["sd"],
            "learning_by_live_week": list(P["learning"]), "full_effect_from_live_week": P["steady_from_live_week"],
            "trend_per_week": P["trend_per_week"],
            "rule": "minutes per visit fall by the clinician's saving times the learning share times the share of visits that used the scribe",
        },
        "after_hours_minutes": {"relative_effect_at_full_use": P["after_hours_effect"],
                                "rule": "multiplied by 1 + effect * learning * share of visits that used the scribe"},
        "visits": {"added_per_week_at_full_use": P["visits_effect"],
                   "rule": "Poisson mean rises by effect * learning * expected scribe share; one uniform draw read at both means"},
        "same_day_close": {"logit_effect_at_full_use": P["same_day_close_effect_logit"]},
        "adoption": {"selection": "types dealt by rank of weight * standardised log baseline documentation time + standard normal noise",
                     "weight_on_baseline_doc": ad["weight_on_baseline_doc"],
                     "never": ad["never"], "partial": ad["partial"],
                     "ramp_by_live_week": list(ad["ramp"])},
        "wellbeing": {"effect_mean_by_type": {k: v[0] for k, v in C["wellbeing"]["effect"].items()},
                      "weight_on_baseline_doc": C["wellbeing"]["weight_on_baseline_doc"],
                      "wave_drift_sd": C["wellbeing"]["wave_drift_sd"]},
        "survey_response": {"intercept": Sv["intercept"], "slope_on_latent_wellbeing": C["survey"]["response_slope"],
                            "solved_for_mean_response": C["survey"]["response_target"]},
        "holiday_weeks": C["holiday_weeks"],
    }, outdir, "hidden/economics/effects_truth.json")


# ------------------------------------------------------------------ entry point
def generate(outdir):
    """Generate every scribe file under `outdir` and return a short summary."""
    S = {block: rng(block) for block in STREAMS}
    K = build_clinics(S)
    wave = draw_rollout(S)
    T = build_traits(S, K)
    Pn = build_panel(S, K, T, wave)
    Sv = build_survey(S, K, T, wave)
    F = build_notes(S, K, Pn)
    Er = build_errors(S, F)
    sample = draw_audit(S, F, K)
    R = draw_raters(S)
    ratings = draw_ratings(S, sample, Er, R)
    write(outdir, K, wave, T, Pn, Sv, F, Er, sample, R, ratings)
    return {"clinicians": K["n"], "clinician_weeks": Pn["N"], "notes": F["M"],
            "audit_notes": len(sample["note"]), "adjudicated": int(ratings["differ"].sum())}
