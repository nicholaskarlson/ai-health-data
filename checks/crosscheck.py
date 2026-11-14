"""Python side of the Python and R cross-check.

    python3 checks/crosscheck.py ROOT OUTFILE

Reads the CSV files under ROOT/data and ROOT/hidden (and one JSON file, the R30
model card) and writes OUTFILE with two columns, `statistic` and `value`, to 12
significant digits. checks/crosscheck.R computes the same list in base R, and
checks/compare_crosscheck.py requires the two files to agree.

Names say how a value is compared:
    rows.*  n.*   counts; must be equal
    fit.*         fitted coefficients; may differ by 1e-6
    stat.*        everything else; must agree to a relative 1e-8

This script is not part of the data path and its output is not hashed, so it
uses NumPy and pandas freely. hidden/ is simulator truth and is never evidence.
"""
import csv
import json
import os
import sys

import numpy as np
import pandas as pd

OUT = []


def put(name, value):
    OUT.append((name, value))


def rd(root, path):
    """Every column as text; an empty field stays an empty string."""
    return pd.read_csv(os.path.join(root, path), dtype=str, keep_default_na=False)


def num(series):
    """Text to numbers; an empty field becomes NaN."""
    return pd.to_numeric(series.replace("", np.nan)).to_numpy(dtype=float)


def c_statistic(score, outcome):
    """Mann-Whitney C-statistic with average ranks for ties."""
    ranks = pd.Series(score).rank(method="average").to_numpy()
    n1 = float(np.sum(outcome == 1))
    n0 = float(np.sum(outcome == 0))
    return (np.sum(ranks[outcome == 1]) - n1 * (n1 + 1.0) / 2.0) / (n1 * n0)


def logistic(x, y):
    """Maximum-likelihood logistic regression by Newton's method. `x` holds the
    predictors as columns, without the intercept. Returns the intercept first."""
    design = np.column_stack([np.ones(len(y)), x])
    beta = np.zeros(design.shape[1])
    for _ in range(100):
        p = 1.0 / (1.0 + np.exp(-(design @ beta)))
        step = np.linalg.solve(design.T @ (design * (p * (1.0 - p))[:, None]), design.T @ (y - p))
        beta = beta + step
        if np.max(np.abs(step)) < 1e-13:
            break
    return beta


def kappa(a, b):
    """Cohen's kappa for two 0/1 vectors."""
    agree = np.mean(a == b)
    chance = np.mean(a) * np.mean(b) + (1.0 - np.mean(a)) * (1.0 - np.mean(b))
    return (agree - chance) / (1.0 - chance)


def main(root, outfile):
    # ---- row counts of every CSV in the dictionary
    dictionary = rd(root, "DICTIONARY.csv")
    files = list(dict.fromkeys(dictionary["file"]))
    for path in files:
        put("rows." + path, len(rd(root, path)))

    # ---- inpatient
    adm = pd.concat([rd(root, f"data/inpatient/admissions_{y}.csv") for y in range(2022, 2027)], ignore_index=True)
    persons = rd(root, "data/inpatient/persons.csv")
    put("stat.inpatient.mean_age", np.mean(num(adm["age"])))
    put("stat.inpatient.share_emergency", np.mean(adm["admission_type"] == "emergency"))
    los = num(adm["los_days"])
    put("stat.inpatient.mean_los_days", np.mean(los[~np.isnan(los)]))
    put("stat.inpatient.share_died", np.mean(adm["died_in_hospital"] == "1"))
    put("stat.inpatient.share_lactate_drawn", np.mean(adm["lactate"] != ""))
    put("stat.persons.share_female", np.mean(persons["sex"] == "f"))

    # ---- the readmission model R30
    dev = rd(root, "data/readmission/r30_development_sample.csv")
    with open(os.path.join(root, "data/readmission/r30_model_card.json"), encoding="utf-8") as fh:
        card = json.load(fh)["coefficients"]
    y = num(dev["readmit_30d_observed"])
    put("n.r30.development_rows", len(dev))
    put("n.r30.development_events", int(np.sum(y == 1)))
    columns = {name: num(dev[name]) for name in dev.columns if name not in ("encounter_id", "prior_admits_cat")}
    columns["prior_admits_1"] = (dev["prior_admits_cat"] == "1").to_numpy(dtype=float)
    columns["prior_admits_2_plus"] = (dev["prior_admits_cat"] == "2").to_numpy(dtype=float)
    terms = sorted(name for name in card if name != "intercept")
    beta = logistic(np.column_stack([columns[name] for name in terms]), y)
    put("fit.r30.coef.intercept", beta[0])
    put("stat.r30.card.intercept", card["intercept"])
    lp = np.full(len(dev), card["intercept"])
    for j, name in enumerate(terms):
        put("fit.r30.coef." + name, beta[j + 1])
        put("stat.r30.card." + name, card[name])
        lp = lp + card[name] * columns[name]
    # Rank on the linear predictor in whole millionths, so that ties do not depend on the last bit.
    put("stat.r30.apparent_c", c_statistic(np.rint(lp * 1e6), y))
    put("stat.r30.mean_production_score", np.mean(num(rd(root, "data/readmission/r30_scores.csv")["r30_risk"])))

    # ---- the vendor's score in silent mode
    ix = rd(root, "data/deterioration/index_encounters.csv")
    day = ix["index_datetime"].str[:10]
    silent = ((day >= "2023-07-01") & (day <= "2023-12-31") & (ix["facility_id"] != "F06")
              & (ix["ehr_outcome_48h"] != "")).to_numpy()
    score = num(ix["vdi_score"])[silent]
    outcome = num(ix["ehr_outcome_48h"])[silent]
    table = rd(root, "data/deterioration/vendor_risk_table.csv")
    v2 = table[table["vdi_version"] == "2.0"]
    risk_of = dict(zip(num(v2["vdi_score"]).astype(int), num(v2["vendor_risk"])))
    risk = np.array([risk_of[int(s)] for s in score])
    put("n.vdi.silent_rows", int(np.sum(silent)))
    put("n.vdi.silent_events", int(np.sum(outcome == 1)))
    put("stat.vdi.silent_c", c_statistic(score, outcome))
    put("stat.vdi.silent_alert_rate", np.mean(score >= 60))
    put("stat.vdi.silent_observed_over_expected", np.sum(outcome) / np.sum(risk))
    fit = logistic(np.log(risk / (1.0 - risk))[:, None], outcome)
    put("fit.vdi.calibration_intercept", fit[0])
    put("fit.vdi.calibration_slope", fit[1])
    review = rd(root, "data/deterioration/chart_review.csv")
    weight = 1.0 / num(review["incl_prob"])
    put("stat.chart_review.weighted_event_rate", np.sum(weight * num(review["reviewer_outcome"])) / np.sum(weight))
    rrt = rd(root, "data/deterioration/rrt_log.csv")
    put("stat.rrt.mean_nurse_minutes", np.mean(num(rrt["nurse_minutes"])))
    put("stat.rrt.mean_physician_minutes", np.mean(num(rrt["physician_minutes"])))
    truth = rd(root, "hidden/deterioration/index_truth.csv")
    put("stat.hidden.risk_ratio_of_response", np.sum(num(truth["y1"])) / np.sum(num(truth["y0"])))

    # ---- the scribe
    frame = rd(root, "data/scribe/ai_notes_frame.csv")
    errors = rd(root, "hidden/scribe/note_errors_truth.csv")
    put("stat.scribe.share_interpreter", np.mean(frame["interpreter_used"] == "1"))
    put("stat.scribe.mean_visit_minutes", np.mean(num(frame["visit_minutes"])))
    position = pd.Series(np.arange(len(errors)), index=errors["note_id"])
    has_omission = (num(errors["n_omission"]) > 0)[position.reindex(frame["note_id"]).to_numpy()]
    v23 = (frame["scribe_version"] == "2.3").to_numpy()
    put("stat.hidden.omission_rate_v23", np.mean(has_omission[v23]))
    sample = rd(root, "data/scribe/audit_sample.csv")
    ratings = rd(root, "data/scribe/audit_ratings.csv")
    one = ratings[ratings["rating_round"] == "1"].set_index("note_id").reindex(sample["note_id"])
    two = ratings[ratings["rating_round"] == "2"].set_index("note_id").reindex(sample["note_id"])
    three = ratings[ratings["rating_round"] == "3"].set_index("note_id")
    put("n.scribe.adjudicated_notes", len(three))
    put("stat.scribe.kappa_hallucination", kappa(num(one["hallucination"]), num(two["hallucination"])))
    put("stat.scribe.kappa_omission", kappa(num(one["omission"]), num(two["omission"])))
    final = num(one["omission"])
    senior = three["omission"].reindex(sample["note_id"])
    replaced = senior.notna().to_numpy()
    final[replaced] = num(senior[replaced])
    weight = num(sample["stratum_size"]) / num(sample["stratum_sampled"])
    put("stat.scribe.weighted_omission_rate", np.sum(weight * final) / np.sum(weight))
    put("stat.scribe.unweighted_omission_rate", np.mean(final))
    panel = rd(root, "data/scribe/clinician_weeks.csv")
    weekly = rd(root, "hidden/economics/clinician_weeks_truth.csv")
    visits, scribe_visits = num(panel["visits"]), num(panel["scribe_visits"])
    put("n.scribe.panel_visits", int(np.sum(visits)))
    put("n.scribe.panel_scribe_visits", int(np.sum(scribe_visits)))
    doc = num(panel["doc_minutes_per_visit"])
    put("stat.scribe.mean_doc_minutes_per_visit", np.mean(doc[~np.isnan(doc)]))
    since = num(panel["weeks_since_go_live"])
    steady = ~np.isnan(since) & (since >= 7)
    put("stat.hidden.saving_per_scribe_visit_steady",
        np.sum(num(weekly["saving_per_scribe_visit"])[steady] * scribe_visits[steady]) / np.sum(scribe_visits[steady]))
    survey = rd(root, "data/scribe/wellbeing_survey.csv")
    put("stat.scribe.survey_response_rate", np.mean(survey["responded"] == "1"))
    put("stat.economics.mean_loaded_hourly_cost",
        np.mean(num(rd(root, "data/economics/wage_rates.csv")["loaded_hourly_cost"])))

    os.makedirs(os.path.dirname(os.path.abspath(outfile)), exist_ok=True)
    with open(outfile, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(["statistic", "value"])
        for name, value in OUT:
            text = str(int(value)) if name.startswith(("rows.", "n.")) else f"{float(value):.12g}"
            writer.writerow([name, text])
    print(f"crosscheck.py: wrote {len(OUT)} statistics to {outfile}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2]))
