"""The in-house readmission model, R30: development sample, univariable screen,
logistic fit by iteratively reweighted least squares with a pure-Python solver,
model card and production scores.

The fit draws no random numbers and changes no outcome: showing the score on
the discharge worklist has a true effect of zero (mechanism P17). Design:
DESIGN.md sections 6.2 and 9.3. Prose: WORLD_SPEC.md section 14. Every setting
is in spec.R30.

Built in Milestone 4. `write` is called after the day loop.

Data-path rules (common.py): no np.exp, np.log or built-in distributions; no
np.sum or np.mean of floats; no BLAS. Sums go through det_sum, and the normal
equations are solved by gauss_jordan_solve.
"""
import math

import numpy as np
import pandas as pd

import spec
from common import (det_log, det_plogis, det_sum, format_float, gauss_jordan_solve, write_csv,
                    write_json)

BUILT = True

R = spec.R30
DEV = R["development"]
CUT = R["cut"]
FACILITY_IDS = [f["facility_id"] for f in spec.FACILITIES]
DX = list(spec.DX_GROUPS)
PAYER_CODES = list(spec.PAYERS)
DISP = list(spec.DISPOSITIONS)

# The candidate predictors, in the order the team listed them. A term is one test
# in the screen; prior admissions is one term with two parameters.
TERMS = [name for name, _columns, _text in R["terms"]]
TERM_COLUMNS = {name: list(columns) for name, columns, _text in R["terms"]}
PARAMETERS = [c for name in TERMS for c in TERM_COLUMNS[name]]


# ------------------------------------------------------------------ predictors
def predictors(adm, rows, female, weekday0, month):
    """The team's predictors for the admissions in `rows`, as a dict of float arrays.

    Every one can be rebuilt from data/ (CHECKS.md S27 and S29). A laboratory
    value that was not measured counts as not low: production does the same.
    """
    g = {key: adm[key][rows] for key in ("age", "los", "prior", "comorbidity", "disposition", "payer",
                                         "rec_sodium", "rec_hemoglobin", "dx", "emergency", "discharge",
                                         "person")}
    disc = g["discharge"]
    weekday = (weekday0 + disc) % 7
    sodium_low = np.where(np.isnan(g["rec_sodium"]), False, g["rec_sodium"] < CUT["sodium"])
    hemoglobin_low = np.where(np.isnan(g["rec_hemoglobin"]), False, g["rec_hemoglobin"] < CUT["hemoglobin"])
    out = {
        "age_65_plus": g["age"] >= CUT["age"],
        "female": female[g["person"]],
        "los_over_5": g["los"] > CUT["los_days"],
        "prior_admits_1": g["prior"] == 1,
        "prior_admits_2_plus": g["prior"] >= 2,
        "comorbidity_count": g["comorbidity"],
        "disp_snf": g["disposition"] == DISP.index("snf"),
        "disp_home_health": g["disposition"] == DISP.index("home_health"),
        "medicaid": g["payer"] == PAYER_CODES.index("medicaid"),
        "sodium_low": sodium_low,
        "hemoglobin_low": hemoglobin_low,
        "dx_cancer": g["dx"] == DX.index("cancer"),
        "dx_heart_failure": g["dx"] == DX.index("heart_failure"),
        "dx_copd": g["dx"] == DX.index("copd"),
        "emergency": g["emergency"],
        "weekend_discharge": weekday >= 5,
        "winter_discharge": np.isin(month[disc], spec.WINTER_MONTHS),
    }
    return {name: np.asarray(values, dtype=np.float64) for name, values in out.items()}


# ------------------------------------------------------------------ the fit
def fit_logistic(columns, y, iterations=None, standard_errors=False):
    """Logistic regression by iteratively reweighted least squares.

    `columns` is a list of float arrays (no intercept; one is added in front).
    The normal equations are built from elementwise products and exact sums and
    solved in pure Python, so the answer is the same on every machine. A fixed
    number of Newton steps is taken; the fit has converged long before the last.
    Returns (coefficients with the intercept first, deviance), and with
    `standard_errors` a third item: the usual standard errors, from the inverse
    of the information matrix at the last step.
    """
    iterations = R["irls_iterations"] if iterations is None else iterations
    y = np.asarray(y, dtype=np.float64)
    X = [np.ones(len(y))] + [np.asarray(c, dtype=np.float64) for c in columns]
    k = len(X)
    beta = [0.0] * k

    def linear(b):
        lp = b[0] * X[0]
        for j in range(1, k):
            lp = lp + b[j] * X[j]
        return lp

    for _ in range(iterations):
        p = det_plogis(linear(beta))
        w = p * (1.0 - p)
        resid = y - p
        a = [[0.0] * k for _ in range(k)]
        for i in range(k):
            wx = w * X[i]
            for j in range(i, k):
                a[i][j] = a[j][i] = det_sum(wx * X[j])
        step = gauss_jordan_solve(a, [det_sum(resid * X[i]) for i in range(k)])
        beta = [b + s for b, s in zip(beta, step)]
    dev = deviance(det_plogis(linear(beta)), y)
    if not standard_errors:
        return beta, dev
    se = [math.sqrt(gauss_jordan_solve(a, [1.0 if j == i else 0.0 for j in range(k)])[i]) for i in range(k)]
    return beta, dev, se


def deviance(p, y):
    """-2 log likelihood of 0/1 outcomes y under probabilities p."""
    return -2.0 * det_sum(np.where(y > 0.5, det_log(p), det_log(1.0 - p)))


def c_statistic(score, outcome):
    """Rank-based C-statistic with average ranks for ties. Rank sums are exact."""
    outcome = np.asarray(outcome, dtype=bool)
    ranks = pd.Series(np.asarray(score, dtype=np.float64)).rank(method="average").to_numpy()
    n1 = int(outcome.sum())
    n0 = len(outcome) - n1
    return (det_sum(ranks[outcome]) - n1 * (n1 + 1) / 2.0) / (n1 * n0)


def screen_and_fit(x, y):
    """The team's procedure (mechanism P15): one likelihood-ratio test for each
    candidate term, keep those with p < 0.20, then one multivariable fit.

    p < 0.20 is tested as LR statistic > the chi-square critical value, so no
    p-value function is needed in the data path. Returns the trace.
    """
    y = np.asarray(y, dtype=np.float64)
    n, events = len(y), int(y.sum())
    rate = events / n
    null = deviance(np.full(n, rate), y)
    screen, kept = [], []
    for name in TERMS:
        cols = TERM_COLUMNS[name]
        _beta, dev = fit_logistic([x[c] for c in cols], y)
        lr = null - dev
        critical = R["screen_critical"][len(cols)]
        keep = lr > critical
        screen.append({"term": name, "parameters": cols, "df": len(cols), "lr_statistic": lr,
                       "critical_value": critical, "kept": bool(keep)})
        if keep:
            kept += cols
    beta, dev = fit_logistic([x[c] for c in kept], y)
    rounded = [float(format_float(b, R["coef_decimals"])) for b in beta]
    lp = np.full(n, rounded[0])
    for c, b in zip(kept, rounded[1:]):
        lp = lp + b * x[c]
    return {"n": n, "events": events, "null_deviance": null, "screen": screen, "kept": kept,
            "unrounded": dict(zip(["intercept"] + kept, beta)),
            "coefficients": dict(zip(["intercept"] + kept, rounded)),
            "deviance": dev, "apparent_c": c_statistic(lp, y > 0.5)}


def risk(coefficients, x, n):
    """R30 risk from the rounded coefficients on the model card."""
    lp = np.full(n, coefficients["intercept"])
    for name, b in coefficients.items():
        if name != "intercept":
            lp = lp + b * x[name]
    return det_plogis(lp)


# ------------------------------------------------------------------ samples
def development_rows(adm, day_index):
    """The development sample (mechanism P14): the university hospital's medicine
    discharges in the window, alive to home, home health or skilled nursing, with
    every test of the admission panel on file, and each patient's first such
    discharge only."""
    disc = adm["discharge"]
    rows = ((adm["facility"] == FACILITY_IDS.index(DEV["facility"])) & ~adm["surgery"] & adm["eligible"]
            & (disc >= day_index(DEV["from"])) & (disc <= day_index(DEV["to"]))
            & (adm["day"] >= day_index(spec.DATES["published_start"])))     # admitted inside the extract
    for test in DEV["panel"]:
        rows &= ~np.isnan(adm["rec_" + test])
    if DEV["first_discharge_per_person"]:
        idx = np.nonzero(rows)[0]
        order = idx[np.lexsort((adm["enc"][idx], disc[idx]))]      # by discharge day, then encounter
        _persons, first = np.unique(adm["person"][order], return_index=True)
        rows = np.zeros(len(disc), dtype=bool)
        rows[order[first]] = True
    return rows


def _ids(prefix, width, numbers):
    return [f"{prefix}{int(v):0{width}d}" for v in numbers]


# ------------------------------------------------------------------ writer
def write(outdir, adm, pool, K, effects, iso, ndays, day_index, weekday0, month):
    """Write the R30 files. Nothing here feeds back into the simulation."""
    female = pool["female"]
    observed = adm["readmit"] & ~adm["outside"]      # what the network's record shows (CHECKS.md S09)
    disc = adm["discharge"]

    # --- development sample, screen and fit
    dev = development_rows(adm, day_index)
    x = predictors(adm, dev, female, weekday0, month)
    y = observed[dev].astype(np.float64)
    trace = screen_and_fit(x, y)
    prior = adm["prior"][dev]
    sample = pd.DataFrame({
        "encounter_id": _ids("E", 8, adm["enc"][dev]),
        "readmit_30d_observed": y.astype(np.int64),
        "age_65_plus": x["age_65_plus"].astype(np.int64),
        "female": x["female"].astype(np.int64),
        "los_over_5": x["los_over_5"].astype(np.int64),
        "prior_admits_cat": np.minimum(prior, 2),
        "comorbidity_count": x["comorbidity_count"].astype(np.int64),
        "disp_snf": x["disp_snf"].astype(np.int64),
        "disp_home_health": x["disp_home_health"].astype(np.int64),
        "medicaid": x["medicaid"].astype(np.int64),
        "sodium_low": x["sodium_low"].astype(np.int64),
        "hemoglobin_low": x["hemoglobin_low"].astype(np.int64),
        "dx_cancer": x["dx_cancer"].astype(np.int64),
        "dx_heart_failure": x["dx_heart_failure"].astype(np.int64),
        "dx_copd": x["dx_copd"].astype(np.int64),
        "emergency": x["emergency"].astype(np.int64),
        "weekend_discharge": x["weekend_discharge"].astype(np.int64),
        "winter_discharge": x["winter_discharge"].astype(np.int64),
    })
    write_csv(sample, outdir, "data/readmission/r30_development_sample.csv")

    # --- production scores: every eligible discharge from the scoring start, every hospital
    scored = adm["eligible"] & (disc >= day_index(spec.DATES["r30_scores_start"])) & (disc < ndays)
    xs = predictors(adm, scored, female, weekday0, month)
    r30 = risk(trace["coefficients"], xs, int(scored.sum()))
    scores = pd.DataFrame({
        "encounter_id": _ids("E", 8, adm["enc"][scored]),
        "score_date": np.array(iso, dtype=object)[disc[scored]],
        "r30_risk": r30,
    })
    write_csv(scores, outdir, "data/readmission/r30_scores.csv")

    # --- the model card, as the team wrote it
    reported_c = float(format_float(trace["apparent_c"], R["reported_c_decimals"]))
    dropped = [s["term"] for s in trace["screen"] if not s["kept"]]
    card = dict(spec.R30_MODEL_CARD)
    card.update({
        "development_sample": {"discharges": trace["n"], "readmissions": trace["events"]},
        "candidate_terms": {name: text for name, _columns, text in R["terms"]},
        "terms_dropped_by_the_screen": dropped,
        "coefficients": trace["coefficients"],
        "reported_performance": {"c_statistic": reported_c,
                                 "basis": "Calculated on the development sample"},
    })
    write_json(card, outdir, "data/readmission/r30_model_card.json")

    # --- hidden: the fit trace
    write_json({
        "world": spec.WORLD,
        "note": ("How the team's procedure ran on the development sample. A term is kept when its "
                 "likelihood-ratio statistic is above the chi-square critical value for p = 0.20. "
                 "Simulator truth: never evidence."),
        "n": trace["n"], "events": trace["events"], "null_deviance": trace["null_deviance"],
        "screen": trace["screen"], "kept_parameters": trace["kept"],
        "newton_steps": R["irls_iterations"],
        "coefficients_unrounded": trace["unrounded"],
        "coefficients_on_the_card": trace["coefficients"],
        "deviance": trace["deviance"], "apparent_c": trace["apparent_c"],
    }, outdir, "hidden/readmission/r30_fit_trace.json")

    # --- hidden: what is true
    ref = R["reference_fit"]
    ref_rows = (adm["eligible"] & (disc >= day_index(ref["from"])) & (disc <= day_index(ref["to"]))
                & np.isin(adm["facility"], [FACILITY_IDS.index(f) for f in ref["facilities"]]))
    xr = predictors(adm, ref_rows, female, weekday0, month)
    truth_fit = {}
    for label, outcome in (("true_outcome_any_hospital", adm["readmit"]), ("observed_outcome_network", observed)):
        beta, _dev, se = fit_logistic([xr[c] for c in PARAMETERS], outcome[ref_rows].astype(np.float64),
                                      iterations=ref["irls_iterations"], standard_errors=True)
        truth_fit[label] = {"coefficients": dict(zip(["intercept"] + PARAMETERS, beta)),
                            "standard_errors": dict(zip(["intercept"] + PARAMETERS, se))}
    r30_ref = risk(trace["coefficients"], xr, int(ref_rows.sum()))
    r30_dev = risk(trace["coefficients"], x, trace["n"])
    prob = adm["readmit_prob"]
    truth = {
        "world": spec.WORLD,
        "note": ("Simulator truth: never evidence. The true model is not of R30's form: it uses "
                 "continuous age, stay and laboratory values, a hospital effect and two things no "
                 "record holds, severity and frailty. It has no term for sex, day of the week or "
                 "season, so the true effect of weekend_discharge and winter_discharge is zero. "
                 "A fit of R30's form can still give either a small coefficient, because who leaves "
                 "at a weekend or in winter differs in ways the form does not hold: that is "
                 "confounding, not an effect."),
        "true_model": {"logit_terms": spec.INPATIENT["readmission"], "solved_intercept": K["readmission"],
                       "hospital_effects_logit": dict(zip(FACILITY_IDS, [float(v) for v in effects["readmission"]]))},
        "noise_predictors": {"weekend_discharge": 0.0, "winter_discharge": 0.0},
        "worklist_effect_on_readmission": 0.0,
        "reference_fit": {
            "what": ("All 17 parameters of R30's form, with no screen, fitted to every eligible "
                     f"discharge from {ref['from']} to {ref['to']} at {', '.join(ref['facilities'])}, once on "
                     "the true outcome and once on the observed one. These are what the form gives "
                     "with about sixteen times the development sample."),
            "discharges": int(ref_rows.sum()),
            "fits": truth_fit,
        },
        "c_statistics": {
            "development_sample": {
                "r30_observed_outcome": trace["apparent_c"],
                "r30_true_outcome": c_statistic(r30_dev, adm["readmit"][dev]),
                "true_probability_true_outcome": c_statistic(prob[dev], adm["readmit"][dev]),
            },
            "reference_discharges": {
                "r30_observed_outcome": c_statistic(r30_ref, observed[ref_rows]),
                "r30_true_outcome": c_statistic(r30_ref, adm["readmit"][ref_rows]),
                "true_probability_true_outcome": c_statistic(prob[ref_rows], adm["readmit"][ref_rows]),
                "true_probability_observed_outcome": c_statistic(prob[ref_rows], observed[ref_rows]),
            },
        },
    }
    write_json(truth, outdir, "hidden/readmission/r30_truth.json")
    return {"r30_development_discharges": trace["n"], "r30_scores": int(scored.sum())}
