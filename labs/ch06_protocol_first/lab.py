"""Chapter 6. Protocol first.

    python3 labs/ch06_protocol_first/lab.py [OUTFILE]

Before anyone looks at a result: which encounters will the score be judged on?
This lab applies the protocol's four conditions one at a time and counts what
each leaves, by hospital and by month. Then it describes three other cohorts a
team might have chosen, to show what the choice changes.

Reads data/ only. The same numbers come from lab.R, and the two must agree.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common import Results, c_statistic, c_statistic_se, num, read  # noqa: E402

SILENT_FROM, SILENT_TO = "2023-07-01", "2023-12-31"     # the planned window, from data/network/timeline.csv
NEVER_SILENT = "F06"                                    # joined in 2024; scoring and alerts began together
FIRST_YEAR_TO = "2024-06-30"
ALERT_AT = 60
HOSPITALS = ["F01", "F02", "F03", "F04", "F05"]
SMALL_HOSPITALS = ["F04", "F05"]
MONTHS = ["2023-07", "2023-08", "2023-09", "2023-10", "2023-11", "2023-12"]


def conditions(ix):
    """The protocol's four conditions, each as one true-or-false value per encounter."""
    day = ix["index_datetime"].str[:10]
    in_window = ((day >= SILENT_FROM) & (day <= SILENT_TO)).to_numpy()
    silent_hospital = (ix["facility_id"] != NEVER_SILENT).to_numpy()
    not_shown = (ix["vdi_shown"] == "0").to_numpy()
    has_outcome = (ix["ehr_outcome_48h"] != "").to_numpy()
    return in_window, silent_hospital, not_shown, has_outcome


def describe(out, name, ix, keep):
    """Size, events and C-statistic of one candidate cohort, among encounters with a recorded outcome."""
    keep = keep & (ix["ehr_outcome_48h"] != "").to_numpy()
    score = num(ix["vdi_score"])[keep]
    outcome = num(ix["ehr_outcome_48h"])[keep]
    c = c_statistic(score, outcome)
    se = c_statistic_se(score, outcome)
    out.put(f"n.{name}_encounters", len(outcome))
    out.put(f"n.{name}_events", np.sum(outcome))
    out.put(f"stat.{name}_c_statistic", c)
    out.put(f"stat.{name}_c_statistic_low", c - 1.96 * se)
    out.put(f"stat.{name}_c_statistic_high", c + 1.96 * se)


def main(outfile):
    ix = read("data/deterioration/index_encounters.csv")
    in_window, silent_hospital, not_shown, has_outcome = conditions(ix)
    out = Results("ch06")

    # The flow: apply the conditions in the protocol's order and count what is left.
    step1 = in_window
    step2 = step1 & silent_hospital
    step3 = step2 & not_shown
    cohort = step3 & has_outcome
    out.put("n.index_encounters", len(ix))
    out.put("n.in_window", np.sum(step1))
    out.put("n.at_silent_hospitals", np.sum(step2))
    out.put("n.not_shown", np.sum(step3))
    out.put("n.cohort", np.sum(cohort))

    # What each condition would remove if it were the only one.
    out.put("n.outside_window", np.sum(~in_window))
    out.put("n.at_never_silent_hospital", np.sum(~silent_hospital))
    out.put("n.shown", np.sum(~not_shown))
    out.put("n.no_outcome_yet", np.sum(~has_outcome))

    # The cohort by hospital and by month.
    event = (ix["ehr_outcome_48h"] == "1").to_numpy()
    out.put("n.cohort_events", np.sum(cohort & event))
    for hospital in HOSPITALS:
        here = cohort & (ix["facility_id"] == hospital).to_numpy()
        out.put(f"n.{hospital.lower()}_encounters", np.sum(here))
        out.put(f"n.{hospital.lower()}_events", np.sum(here & event))
    for month in MONTHS:
        here = cohort & (ix["index_datetime"].str[:7] == month).to_numpy()
        out.put(f"n.m{month.replace('-', '_')}_encounters", np.sum(here))
        out.put(f"n.m{month.replace('-', '_')}_events", np.sum(here & event))

    # Nothing was shown, so no alert fired. How many would have, at the vendor's threshold?
    out.put("n.cohort_alerts_fired", np.sum(cohort & (ix["alert_fired"] == "1").to_numpy()))
    out.put("n.cohort_at_or_above_threshold", np.sum(cohort & (num(ix["vdi_score"]) >= ALERT_AT)))

    # The protocol's cohort, and three cohorts a team might have chosen instead.
    day = ix["index_datetime"].str[:10]
    first_year = (day <= FIRST_YEAR_TO).to_numpy()
    small = ix["facility_id"].isin(SMALL_HOSPITALS).to_numpy()
    describe(out, "protocol", ix, cohort)
    describe(out, "silent_as_run", ix, not_shown)                     # every encounter that was never shown
    describe(out, "silent_after_window", ix, not_shown & ~in_window)  # silent, but after the planned window
    describe(out, "first_year", ix, first_year)                       # the first twelve months, shown or not
    out.put("n.first_year_shown", np.sum(first_year & ~not_shown))
    out.put("n.protocol_small_hospitals", np.sum(cohort & small))
    out.put("n.silent_after_window_small_hospitals", np.sum(not_shown & ~in_window & small))
    out.write(outfile)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "results/ch06_python.csv")
