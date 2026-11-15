"""Chapter 2. A hospital where the truth is known.

    python3 labs/ch02_a_hospital_where_the_truth_is_known/lab.py [OUTFILE]

Before any method is tried on Tonmick Health: what kind of hospital is it? This
lab computes the headline figures an analyst would check first in any new
extract (who is admitted, how they pay, how long they stay, how many die), and
derives 30-day readmission from the admission files, with the rule written down.
The chapter sets these figures beside published ones.

Reads data/ only. The same numbers come from lab.R, and the two must agree.
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common import Results, num, read  # noqa: E402

YEARS = [2022, 2023, 2024, 2025, 2026]
PAYERS = ["medicare", "medicaid", "commercial", "self_pay"]
ELIGIBLE = ["home", "home_health", "snf"]          # alive, to home, home health or skilled nursing
NOT_ELIGIBLE_ALIVE = ["hospice", "ama", "transfer"]
WINTER = [12, 1, 2]


def admissions():
    """The five admission files stacked: every published admission, one row each."""
    return pd.concat([read(f"data/inpatient/admissions_{year}.csv") for year in YEARS],
                     ignore_index=True)


def lower_value(values, share):
    """The value at position ceil(share * n) in sorted order, with no interpolation."""
    ordered = np.sort(values)
    return ordered[int(np.ceil(share * len(ordered))) - 1]


def with_next_admission(adm):
    """Each admission with the same person's next admission, if there is one."""
    a = adm.sort_values(["person_id", "admit_datetime"], kind="mergesort").reset_index(drop=True)
    same = (a["person_id"].shift(-1) == a["person_id"]).to_numpy()
    a["next_admit_date"] = np.where(same, a["admit_datetime"].shift(-1).str[:10], "")
    a["next_planned"] = np.where(same, a["planned_admission"].shift(-1), "")
    return a


def readmission_2023(a):
    """The rule, for discharges in 2023. A discharge counts if the patient left alive
    to home, home health or skilled nursing. It has a readmission if the same person's
    next admission starts 1 to 30 days after the discharge date and was not planned."""
    discharged = pd.to_datetime(a["discharge_date"], format="%Y-%m-%d", errors="coerce")
    next_admit = pd.to_datetime(a["next_admit_date"], format="%Y-%m-%d", errors="coerce")
    gap = (next_admit - discharged).dt.days.to_numpy()
    in_2023 = (a["discharge_date"].str[:4] == "2023").to_numpy()
    eligible = a["disposition"].isin(ELIGIBLE).to_numpy()
    returned = (gap >= 1) & (gap <= 30)
    index = in_2023 & eligible
    readmitted = index & returned & (a["next_planned"] == "0").to_numpy()
    planned = index & returned & (a["next_planned"] == "1").to_numpy()
    return in_2023, index, readmitted, planned, returned


def main(outfile):
    out = Results("ch02")
    adm = admissions()
    persons = read("data/inpatient/persons.csv")
    n = len(adm)
    out.put("n.hospitals", len(read("data/network/facilities.csv")))
    out.put("n.persons", len(persons))
    out.put("n.admissions", n)

    # Who is admitted, and how they pay.
    age = num(adm["age"])
    out.put("stat.age_lower_quartile", lower_value(age, 0.25))
    out.put("stat.age_median", np.median(age))
    out.put("stat.age_upper_quartile", lower_value(age, 0.75))
    sex = persons.set_index("person_id")["sex"].reindex(adm["person_id"]).to_numpy()
    out.put("stat.female_share", np.sum(sex == "f") / n)
    for payer in PAYERS:
        out.put(f"stat.{payer}_share", np.sum(adm["payer"] == payer) / n)
    f06 = (adm["facility_id"] == "F06").to_numpy()
    out.put("stat.f06_medicare_share", np.sum(f06 & (adm["payer"] == "medicare").to_numpy()) / np.sum(f06))
    out.put("stat.emergency_share", np.sum(adm["admission_type"] == "emergency") / n)

    # Winter: admissions a day in December to February against the year's average,
    # at the five hospitals that were in the network for whole years 2022 to 2025.
    year = adm["admit_datetime"].str[:4].astype(int).to_numpy()
    month = adm["admit_datetime"].str[5:7].astype(int).to_numpy()
    whole = (adm["facility_id"] != "F06").to_numpy() & (year >= 2022) & (year <= 2025)
    days = pd.date_range("2022-01-01", "2025-12-31")
    winter_days = np.sum(days.month.isin(WINTER))
    in_winter = np.sum(whole & np.isin(month, WINTER))
    out.put("stat.winter_ratio", (in_winter / winter_days) / (np.sum(whole) / len(days)))

    # How long they stay, and how many die.
    los = num(adm["los_days"])
    out.put("n.open_stays", np.sum(adm["discharge_date"] == ""))
    out.put("stat.los_median", np.median(los[~np.isnan(los)]))
    out.put("stat.los_mean", np.mean(los[~np.isnan(los)]))
    deaths = np.sum(adm["died_in_hospital"] == "1")
    out.put("n.deaths_in_hospital", deaths)
    out.put("stat.death_share", deaths / n)

    # A missing value that is not missing at random: lactate is drawn more often in the sicker.
    drawn = (adm["lactate"] != "").to_numpy()
    icu = (adm["icu_at_12h"] == "1").to_numpy()
    out.put("stat.lactate_drawn_share", np.mean(drawn))
    out.put("stat.lactate_drawn_icu", np.mean(drawn[icu]))
    out.put("stat.lactate_drawn_not_icu", np.mean(drawn[~icu]))

    # Readmission within 30 days, derived from the admission files: 2023 discharges.
    a = with_next_admission(adm)
    in_2023, index, readmitted, planned, returned = readmission_2023(a)
    out.put("n.discharges_2023", np.sum(in_2023))
    out.put("n.index_2023", np.sum(index))
    out.put("n.readmissions_2023", np.sum(readmitted))
    out.put("n.planned_returns_2023", np.sum(planned))
    out.put("stat.readmission_2023", np.sum(readmitted) / np.sum(index))
    for payer in PAYERS:
        here = index & (a["payer"] == payer).to_numpy()
        out.put(f"n.index_2023_{payer}", np.sum(here))
        out.put(f"n.readmissions_2023_{payer}", np.sum(readmitted & here))
        out.put(f"stat.readmission_2023_{payer}", np.sum(readmitted & here) / np.sum(here))

    # Live discharges the rule leaves out, and how many of them came back within 30 days.
    left_out = in_2023 & a["disposition"].isin(NOT_ELIGIBLE_ALIVE).to_numpy()
    out.put("n.not_eligible_alive_2023", np.sum(left_out))
    out.put("n.not_eligible_returned_2023", np.sum(left_out & returned))
    out.write(outfile)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "results/ch02_python.csv")
