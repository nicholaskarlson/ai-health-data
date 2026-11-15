"""Chapter 2, the answer key. This is the only file in the lab that opens hidden/.

    python3 labs/ch02_a_hospital_where_the_truth_is_known/answer_key.py

For every admission the simulator stored whether the patient was truly readmitted
within 30 days, to any hospital, and whether that readmission was outside the
network, where the record cannot see it. Setting that beside the rule in lab.py
shows what the rule recovers, and what no rule applied to data/ can recover.

Nothing here is evidence. No real hospital has these files.
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import read  # noqa: E402
from lab import PAYERS, YEARS, admissions, readmission_2023, with_next_admission  # noqa: E402


def main():
    a = with_next_admission(admissions())
    _in_2023, index, readmitted, _planned, _returned = readmission_2023(a)
    truth = pd.concat([read(f"hidden/inpatient/admissions_truth_{year}.csv") for year in YEARS],
                      ignore_index=True).set_index("encounter_id").loc[a["encounter_id"]]
    eligible = (truth["readmit_eligible"] == "1").to_numpy()
    any_hospital = (truth["readmit_any_30d"] == "1").to_numpy()
    outside = (truth["readmit_outside"] == "1").to_numpy()
    n = int(np.sum(index))
    true_any = int(np.sum(index & any_hospital))
    true_outside = int(np.sum(index & any_hospital & outside))
    differ = int(np.sum(index & (readmitted != (any_hospital & ~outside))))

    print("Chapter 2, against the truth: 30-day readmission after 2023 discharges.")
    print(f"  discharges the rule counts: {n:,}; eligible in the truth: {int(np.sum(index & eligible)):,}; "
          f"eligible in the truth but not counted: {int(np.sum(eligible & ~index & (a['discharge_date'].str[:4] == '2023').to_numpy()))}")
    print(f"  readmitted to any hospital: {true_any:,} ({true_any / n:.4f}); "
          f"seen in the record: {int(np.sum(readmitted)):,} ({np.sum(readmitted) / n:.4f})")
    print(f"  readmitted outside the network, where the record cannot see it: {true_outside} "
          f"({true_outside / true_any:.4f} of true readmissions)")
    print(f"  the rule against the simulator's own network readmissions: {differ} of {n:,} discharges differ")
    print("  by payer, per 100 discharges: in the record, and in the truth")
    for payer in PAYERS:
        here = index & (a["payer"] == payer).to_numpy()
        seen = 100 * np.sum(readmitted & here) / np.sum(here)
        true = 100 * np.sum(any_hospital & here) / np.sum(here)
        print(f"    {payer:<11s}{seen:6.1f}{true:8.1f}")

    # Deaths after discharge are in hidden/ only: the record cannot tell a patient who
    # died at home from one who stayed well.
    people = read("hidden/inpatient/persons_truth.csv").set_index("person_id").loc[a["person_id"]]
    died = pd.to_datetime(people["death_date"], format="%Y-%m-%d", errors="coerce").to_numpy()
    discharged = pd.to_datetime(a["discharge_date"], format="%Y-%m-%d", errors="coerce").to_numpy()
    days = (died - discharged) / np.timedelta64(1, "D")
    away = (people["death_place"] == "outside").to_numpy() & (days >= 0) & (days <= 30)
    print(f"  died outside hospital within 30 days, with no readmission: "
          f"{int(np.sum(index & away & ~any_hospital))} of {n:,}")

    hand = read("labs/ch02_a_hospital_where_the_truth_is_known/by_hand.csv")
    rows = truth.loc[hand["encounter_id"]]
    fate = read("hidden/inpatient/persons_truth.csv").set_index("person_id").loc[hand["person_id"]]
    counted = hand["disposition"].isin(["home", "home_health", "snf"]).to_numpy()
    gone = counted & (hand["next_admit_date"] == "").to_numpy()
    print(f"The {int(np.sum(counted))} counted discharges in by_hand.csv: "
          f"{int(np.sum(counted & (rows['readmit_any_30d'] == '1').to_numpy()))} truly readmitted, "
          f"{int(np.sum(counted & (rows['readmit_outside'] == '1').to_numpy()))} of them outside the network. "
          f"Of the {int(np.sum(gone))} with no later admission, "
          f"{int(np.sum(gone & (fate['death_place'] == 'outside').to_numpy()))} died outside hospital: "
          + ", ".join(f"{e} on {d}" for e, d in zip(hand["encounter_id"][gone], fate["death_date"][gone]) if d) + ".")
    print(f"A first look at the truth: hidden/inpatient/admissions_truth_2023.csv has "
          f"{len(truth.columns) + 1} columns, among them {', '.join(truth.columns[2:7])}.")


if __name__ == "__main__":
    main()
