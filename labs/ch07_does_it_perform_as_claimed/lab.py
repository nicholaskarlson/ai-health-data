"""Chapter 7. Does it perform as claimed?

    python3 labs/ch07_does_it_perform_as_claimed/lab.py [OUTFILE]

The vendor's model card claims a C-statistic of 0.84. This lab measures the
score on Tonmick's own patients during the six months when it ran silently:
scored, but shown to nobody.

Reads data/ only. The same numbers come from lab.R, and the two must agree.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common import Results, c_statistic, c_statistic_se, logistic, logit, num, read  # noqa: E402

SILENT_FROM, SILENT_TO = "2023-07-01", "2023-12-31"
BANDS = [0.0, 0.01, 0.02, 0.05, 0.10, 0.20, 1.0]      # the vendor's predicted risk, in bands


def silent_cohort():
    """Index encounters at the five hospitals that ran the score silently, in the
    silent window, with a recorded outcome. Returns the score, the vendor's
    predicted risk and the recorded outcome."""
    ix = read("data/deterioration/index_encounters.csv")
    day = ix["index_datetime"].str[:10]
    keep = ((day >= SILENT_FROM) & (day <= SILENT_TO) & (ix["facility_id"] != "F06")
            & (ix["vdi_shown"] == "0") & (ix["ehr_outcome_48h"] != "")).to_numpy()
    score = num(ix["vdi_score"])[keep]
    outcome = num(ix["ehr_outcome_48h"])[keep]
    table = read("data/deterioration/vendor_risk_table.csv")
    v2 = table[table["vdi_version"] == "2.0"]
    risk_of = dict(zip(num(v2["vdi_score"]).astype(int), num(v2["vendor_risk"])))
    risk = np.array([risk_of[int(s)] for s in score])
    return ix.loc[keep, "encounter_id"].to_numpy(), score, risk, outcome


def main(outfile):
    _ids, score, risk, outcome = silent_cohort()
    out = Results("ch07")
    events = float(np.sum(outcome))
    out.put("n.encounters", len(outcome))
    out.put("n.events", events)
    out.put("stat.event_rate", events / len(outcome))

    # Discrimination: can the score tell who will deteriorate?
    c = c_statistic(score, outcome)
    se = c_statistic_se(score, outcome)
    out.put("stat.c_statistic", c)
    out.put("stat.c_statistic_se", se)
    out.put("stat.c_statistic_low", c - 1.96 * se)
    out.put("stat.c_statistic_high", c + 1.96 * se)

    # Calibration: are the vendor's predicted risks the right size here?
    out.put("stat.mean_predicted_risk", np.mean(risk))
    oe = events / np.sum(risk)
    out.put("stat.observed_over_expected", oe)
    out.put("stat.observed_over_expected_low", oe * np.exp(-1.96 / np.sqrt(events)))
    out.put("stat.observed_over_expected_high", oe * np.exp(1.96 / np.sqrt(events)))
    lp = logit(risk)
    beta, beta_se = logistic(lp[:, None], outcome)
    out.put("fit.calibration_intercept", beta[0])
    out.put("fit.calibration_slope", beta[1])
    out.put("fit.calibration_slope_se", beta_se[1])
    large, large_se = logistic(None, outcome, offset=lp)
    out.put("fit.calibration_in_the_large", large[0])
    out.put("fit.calibration_in_the_large_se", large_se[0])

    # A calibration table: predicted against observed, in bands of predicted risk.
    for k in range(len(BANDS) - 1):
        band = (risk >= BANDS[k]) & (risk < BANDS[k + 1]) if k < len(BANDS) - 2 else (risk >= BANDS[k])
        out.put(f"n.band{k + 1}_encounters", int(np.sum(band)))
        out.put(f"n.band{k + 1}_events", int(np.sum(outcome[band])))
        out.put(f"stat.band{k + 1}_mean_predicted", np.mean(risk[band]))
        out.put(f"stat.band{k + 1}_observed", np.mean(outcome[band]))
    out.write(outfile)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "results/ch07_python.csv")
