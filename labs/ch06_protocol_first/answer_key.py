"""Chapter 6, the answer key. This is the only file in the lab that opens hidden/.

    python3 labs/ch06_protocol_first/answer_key.py

The protocol keeps out every encounter where the score was shown. The simulator
stored, for every encounter, what would have happened with no evaluation by the
rapid-response team (y0) and what did happen (y_true). Setting the two side by
side shows what showing the score does to the outcomes it is judged against.

Nothing here is evidence. No real hospital has these files.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common import c_statistic, num, read  # noqa: E402
from lab import FIRST_YEAR_TO, conditions  # noqa: E402


def line(label, ix, truth, keep):
    keep = keep & (ix["ehr_outcome_48h"] != "").to_numpy()
    score = num(ix["vdi_score"])[keep]
    record = num(ix["ehr_outcome_48h"])[keep]
    y0 = num(truth["y0"])[keep]
    y_true = num(truth["y_true"])[keep]
    alerted = (ix["alert_fired"] == "1").to_numpy()[keep]
    evaluated = (ix["rrt_evaluated"] == "1").to_numpy()[keep]
    print(label)
    print(f"  encounters {int(np.sum(keep)):,}; alerts fired {int(np.sum(alerted)):,}; "
          f"evaluated by the rapid-response team {int(np.sum(evaluated)):,}")
    print(f"  would have deteriorated with no evaluation: {int(np.sum(y0))}; did deteriorate: {int(np.sum(y_true))}; "
          f"events prevented: {int(np.sum(y0) - np.sum(y_true))}; recorded events: {int(np.sum(record))}")
    print(f"  among alerted patients: {int(np.sum(y0[alerted]))} would have deteriorated, "
          f"{int(np.sum(y_true[alerted]))} did")
    print(f"  the same outcome either way for {int(np.sum(y0 == y_true)):,} of {int(np.sum(keep)):,} encounters")
    print(f"  C-statistic of the score: {c_statistic(score, y0):.4f} against what would have happened, "
          f"{c_statistic(score, y_true):.4f} against what did, {c_statistic(score, record):.4f} against the record")


def main():
    ix = read("data/deterioration/index_encounters.csv")
    truth = read("hidden/deterioration/index_truth.csv").set_index("encounter_id").loc[ix["encounter_id"]]
    in_window, silent_hospital, not_shown, has_outcome = conditions(ix)
    cohort = in_window & silent_hospital & not_shown & has_outcome
    first_year = (ix["index_datetime"].str[:10] <= FIRST_YEAR_TO).to_numpy()
    print("Chapter 6, against the truth.")
    line("The protocol's cohort: silent mode, July to December 2023", ix, truth, cohort)
    line("Left out by the protocol: shown, from go-live to June 30, 2024", ix, truth, first_year & ~not_shown)
    line("Left out by the protocol: silent, but after the planned window", ix, truth, not_shown & ~in_window)


if __name__ == "__main__":
    main()
