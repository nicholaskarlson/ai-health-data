"""Chapter 7, the answer key. This script opens hidden/.

    python3 labs/ch07_does_it_perform_as_claimed/answer_key.py

hidden/ is what the simulator did. It is never evidence: no real hospital has
it. It is used here for one thing, to show how far the estimates in lab.py are
from the truth, and why.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import c_statistic, logistic, logit, num, read  # noqa: E402
from lab import silent_cohort  # noqa: E402


def main():
    ids, score, risk, flagged = silent_cohort()
    truth = read("hidden/deterioration/index_truth.csv").set_index("encounter_id").loc[ids]
    happened = num(truth["y_true"])          # did the patient truly deteriorate?
    true_risk = num(truth["p0"])             # the simulator's own risk, with no response to an alert
    slope = logistic(logit(risk)[:, None], flagged)[0][1]
    true_slope = logistic(logit(risk)[:, None], happened)[0][1]
    rows = [
        ("Events", f"{int(flagged.sum())} recorded", f"{int(happened.sum())} true"),
        ("C-statistic of the score", f"{c_statistic(score, flagged):.4f}", f"{c_statistic(score, happened):.4f}"),
        ("Calibration slope", f"{slope:.3f}", f"{true_slope:.3f}"),
        ("Observed over expected", f"{flagged.sum() / risk.sum():.3f}", f"{happened.sum() / risk.sum():.3f}"),
        ("C-statistic of the true risk (the ceiling)", f"{c_statistic(true_risk, flagged):.4f}",
         f"{c_statistic(true_risk, happened):.4f}"),
        ("Expected events under the true risk", "", f"{true_risk.sum():.1f}"),
    ]
    print(f"Chapter 7 answer key: {len(ids):,} silent-mode encounters\n")
    print(f"{'':46s}{'against the record':>20s}{'against the truth':>20s}")
    for label, recorded, true in rows:
        print(f"{label:46s}{recorded:>20s}{true:>20s}")
    both = int(((flagged == 1) & (happened == 1)).sum())
    print(f"\nThe record and the truth agree on {both} events. The record misses "
          f"{int(happened.sum()) - both} true events and adds {int(flagged.sum()) - both} that did not happen.")
    print("The vendor claims 0.84. No score could do better here than the true risk does.")
    print("CHECKS.md rows T16, T17 and T18 print the same values.")


if __name__ == "__main__":
    main()
