"""Design checks: the targets in spec.TARGETS that have been built, plus structural checks.

    python3 generator/checks.py ROOT [OUTFILE]

Reads ROOT/data and ROOT/hidden and writes CHECKS.md (default ROOT/CHECKS.md).
Exits 1 if any check fails.

CHECKS.md is hashed, so it must be the same on every machine. Nothing here
prints a time, a path or a machine detail. Counts are integers; sums of floats
go through det_sum (correctly rounded); no BLAS or LAPACK is used.

Basis words in the check text (DESIGN.md section 9.1):
  realised      computed from the generated files, as an analyst would
  expected      computed from hidden probabilities (small cells)
  construction  true by design; the check confirms it
"""
import datetime as dt
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np          # noqa: E402
import pandas as pd         # noqa: E402

import deterioration        # noqa: E402
import dictionary           # noqa: E402
import readmission          # noqa: E402
import spec                 # noqa: E402
from common import det_exp, det_log, det_mean, det_plogis, det_sum, format_float  # noqa: E402

DATA_END = dt.date.fromisoformat(spec.DATES["data_end"])
PATTERNS = {
    "int": r"-?\d+",
    "flag": r"[01]",
    "date": r"\d{4}-\d{2}-\d{2}",
    "datetime": r"\d{4}-\d{2}-\d{2}T\d{2}:00",
    "month": r"\d{4}-\d{2}",
}
VDI_BENCHMARKS = [
    # quantity, key into the computed values, published figure, source
    ("Vendor's score on local data: C-statistic in silent mode, against the vendor's claim", "vdi_c",
     "0.79 (95% CI 0.74 to 0.84) on local validation of a widely implemented proprietary deterioration index, 392 hospitalisations",
     "Singh et al., Ann Am Thorac Soc 2021"),
    ("Gap between the vendor's claimed C-statistic and the local one", "vdi_gap",
     "0.63 (95% CI 0.62 to 0.64) locally against 0.76 to 0.83 reported by the developer, for a widely implemented proprietary sepsis model",
     "Wong et al., JAMA Intern Med 2021"),
    ("Alerts at the threshold: share of encounters flagged, and share of events missed", "vdi_alerts",
     "alerts on 18% of hospitalisations while 67% of sepsis cases were not identified, same sepsis model",
     "Wong et al., JAMA Intern Med 2021"),
]
SCRIBE_BENCHMARKS = [
    ("AI-drafted notes with an omission, with a hallucination, and free of a major error", "scribe_errors",
     "356 of 7,545 notes reviewed: omissions in 18%, hallucinations in 11.5%; 94.7% free of significant errors",
     "Taylor et al., JMIR Med Inform 2026"),
    ("Documentation time saved by an ambient scribe", "scribe_time",
     "about 13.6 fewer minutes a day on notes, 79 clinicians, more than 25,600 notes",
     "Prospective study, JMIR Med Inform 2026;14:e84104"),
]
BENCHMARKS = [
    # quantity, key into the computed values, published figure, source
    ("True 30-day readmission, 2023 discharges", "t10",
     "13.9 per 100 index admissions, 2016 to 2020", "AHRQ HCUP Statistical Brief 304"),
    ("True 30-day readmission by payer, 2023: Medicare, Medicaid, self-pay, commercial", "by_payer",
     "17.0, 13.6, 11.9 and 8.5 per 100 in 2020", "AHRQ HCUP Statistical Brief 304"),
    ("In-hospital death share", "death",
     "2.1% of stays in December 2019, all causes", "AHRQ HCUP Statistical Brief 300"),
    ("Mean length of stay, days", "los_mean",
     "4.5 days for all stays in 2012; 4.8 (female) and 5.0 (male) outside maternal and neonatal stays",
     "AHRQ HCUP Statistical Brief 180"),
]


class Report:
    def __init__(self):
        self.sections = []
        self.failures = 0
        self.count = 0

    def section(self, title, note=""):
        self.sections.append({"title": title, "note": note, "rows": [], "header": None})

    def check(self, cid, text, value, target, ok):
        self.count += 1
        if not ok:
            self.failures += 1
        self.sections[-1]["rows"].append((f"{cid} {text}", value, target, "pass" if ok else "FAIL"))
        return ok

    def info(self, text, value, published, source):
        self.sections[-1]["header"] = ("Quantity", "Tonmick value", "Published figure", "Source")
        self.sections[-1]["rows"].append((text, value, published, source))

    def markdown(self):
        lines = [
            "# Checks", "",
            f"World `{spec.WORLD}`, version `{spec.VERSION}`, root seed `{spec.ROOT_SEED}`. "
            f"Milestones built: {', '.join(spec.BUILT_MILESTONES)}.", "",
            "Written by `generator/checks.py`. Do not edit by hand. Everything here is fictional, "
            "and values read from `hidden/` are simulator truth, never evidence.", "",
            "Each check names its basis: **realised** (computed from the generated files, as an "
            "analyst would), **expected** (computed from hidden probabilities) or **construction** "
            "(true by design). Target ranges were committed in `generator/spec.py` before the "
            "generator was written, except the rows marked T..b to T..e, whose ranges were added "
            "with the generator (see `spec.SECONDARY_TARGETS`). The parameters adjusted after seeing "
            "output are listed in `PROVENANCE.md` section 4.", "",
            f"**{self.count} checks, {self.failures} failed.**", "",
        ]
        for sec in self.sections:
            lines += [f"## {sec['title']}", ""]
            if sec["note"]:
                lines += [sec["note"], ""]
            head = sec["header"] or ("Check", "Value", "Target", "Result")
            lines.append("| " + " | ".join(head) + " |")
            lines.append("| " + " | ".join("---" for _ in head) + " |")
            for row in sec["rows"]:
                lines.append("| " + " | ".join(str(c).replace("|", "\\|") for c in row) + " |")
            lines.append("")
        return "\n".join(lines)


def fmt(x, decimals=4):
    return f"{x:.{decimals}f}"


def in_range(x, lo, hi):
    return (lo is None or x >= lo) and (hi is None or x <= hi)


def range_text(lo, hi, decimals=None):
    def one(v):
        if decimals is None:
            return f"{v:,}" if isinstance(v, int) else f"{v:g}"
        return f"{v:.{decimals}f}"
    if lo is None:
        return f"at most {one(hi)}"
    if hi is None:
        return f"at least {one(lo)}"
    return f"{one(lo)} to {one(hi)}"


def read(root, path):
    return pd.read_csv(os.path.join(root, path), dtype=str, keep_default_na=False)


def ordinal(series):
    """ISO dates (or datetimes) as day numbers; -1 where empty."""
    text = series.str[:10]
    uniq = {t: (dt.date.fromisoformat(t).toordinal() if t else -1) for t in text.unique()}
    return text.map(uniq).to_numpy(dtype=np.int64)


def quantile(values, q):
    """The value at position ceil(q * n) in sorted order: no interpolation, no float sums."""
    v = np.sort(np.asarray(values))
    k = int(np.ceil(q * len(v))) - 1
    return v[max(k, 0)]


def median(values):
    v = np.sort(np.asarray(values, dtype=np.float64))
    n = len(v)
    return float(v[n // 2]) if n % 2 else (float(v[n // 2 - 1]) + float(v[n // 2])) / 2.0


def c_statistic(score, outcome):
    """Rank-based C-statistic with average ranks for ties. Rank sums are exact
    (multiples of one half, far below 2**53), so the order of addition cannot matter."""
    score = np.asarray(score, dtype=np.float64)
    outcome = np.asarray(outcome, dtype=bool)
    ranks = pd.Series(score).rank(method="average").to_numpy()
    n1 = int(outcome.sum())
    n0 = len(outcome) - n1
    r1 = float(np.sum(ranks[outcome] * 2.0)) / 2.0
    return (r1 - n1 * (n1 + 1) / 2.0) / (n1 * n0)


def logistic_fit(x, y, offset=False):
    """Logistic regression of y on x by Newton's method, with exact sums.

    Returns (intercept, slope). With offset=True the slope is held at 1 and only
    the intercept is fitted (calibration-in-the-large). Uses det_plogis and
    det_sum, so the answer is the same on every machine.
    """
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    a, b = 0.0, 1.0
    for _ in range(40):
        p = det_plogis(a + b * x)
        w = p * (1.0 - p)
        g0, h00 = det_sum(y - p), det_sum(w)
        if offset:
            a += g0 / h00
            continue
        g1, h01, h11 = det_sum((y - p) * x), det_sum(w * x), det_sum(w * x * x)
        det = h00 * h11 - h01 * h01
        a += (h11 * g0 - h01 * g1) / det
        b += (h00 * g1 - h01 * g0) / det
    return a, b


def day_number(iso):
    return dt.date.fromisoformat(iso).toordinal()


# ------------------------------------------------------------------ Milestone 3: assemble
def index_frame(tables, adm, persons):
    """One row per index encounter: the public file, its truth, and the admission's columns."""
    ix = tables["data/deterioration/index_encounters.csv"]
    tr = tables["hidden/deterioration/index_truth.csv"]
    risk = tables["data/deterioration/vendor_risk_table.csv"]
    d = pd.DataFrame({"encounter_id": ix["encounter_id"], "facility_id": ix["facility_id"]})
    d["day"] = ordinal(ix["index_datetime"])
    d["hour"] = ix["index_datetime"].str[11:13].astype(np.int64)
    d["month"] = ix["index_datetime"].str[5:7].astype(np.int64)
    for name in ("hr", "rr", "sbp", "temp_c", "spo2"):
        d[name] = pd.to_numeric(ix[name]).to_numpy()
    d["lactate"] = pd.to_numeric(ix["lactate_at_index"]).to_numpy()
    d["lactate_text"] = ix["lactate_at_index"].to_numpy()
    for name in ("network_encounters_12m", "vdi_score", "vdi_shown", "alert_fired", "rrt_evaluated"):
        d[name] = ix[name].astype(np.int64).to_numpy()
    d["o2"] = ix["o2_support"].map({c: i for i, c in enumerate(spec.O2_SUPPORT)}).to_numpy()
    d["alertness"] = ix["alertness"].map({c: i for i, c in enumerate(spec.ALERTNESS)}).to_numpy()
    d["v3"] = (ix["vdi_version"] == spec.VDI["versions"][1]).to_numpy()
    d["labelled"] = (ix["ehr_outcome_48h"] != "").to_numpy()
    d["ehr"] = (ix["ehr_outcome_48h"] == "1").to_numpy()
    d["label_day"] = ordinal(ix["outcome_available_date"])
    table = {(v, int(sc)): float(r) for v, sc, r in zip(risk["vdi_version"], risk["vdi_score"], risk["vendor_risk"])}
    d["vendor_risk"] = [table[(v, sc)] for v, sc in zip(ix["vdi_version"], d["vdi_score"])]
    d["vendor_logit"] = det_log(d["vendor_risk"].to_numpy() / (1.0 - d["vendor_risk"].to_numpy()))
    same = len(tr) == len(ix) and (tr["encounter_id"].to_numpy() == ix["encounter_id"].to_numpy()).all()
    if same:
        for name in ("p0", "p1", "response_prob", "spo2_bias", "spo2_true", "rr_true"):
            d[name] = pd.to_numeric(tr[name]).to_numpy()
        for name in ("y0", "y1", "y_true", "rr_defaulted", "outside_encounters_12m", "vdi_score_no_assay_shift"):
            d[name] = tr[name].astype(np.int64).to_numpy()
        d["event_type"] = tr["event_type"].to_numpy()
        d["flag_error"] = tr["ehr_flag_error"].to_numpy()
        d["response_text"] = tr["response_prob"].to_numpy()
    a = adm.set_index("encounter_id")
    found = d["encounter_id"].isin(a.index).to_numpy()
    for name in ("person_id", "payer", "age", "prior_admits_12m", "icu_at_12h", "comfort_care_12h",
                 "admit_datetime", "admit_day", "disc_day", "los", "lactate", "disposition",
                 "died_in_hospital", "published", "facility_id"):
        d["adm_" + name] = a[name].reindex(d["encounter_id"]).to_numpy()
    d["race"] = persons.set_index("person_id")["race_ethnicity"].reindex(d["adm_person_id"]).to_numpy()
    return d, bool(same), bool(found.all())


FAC = {f["facility_id"]: f for f in spec.FACILITIES}


def check_deterioration_structure(rep, root, tables, adm, d, truth_ok, found_ok):
    """Structural checks S19 to S25 for the Milestone 3 files."""
    Q = spec.DETERIORATION
    end = DATA_END.toordinal()
    scoring = d["facility_id"].map({k: day_number(v["vdi_scoring_from"]) for k, v in FAC.items()}).to_numpy()
    alerts = d["facility_id"].map({k: day_number(v["vdi_alerts_from"]) for k, v in FAC.items()}).to_numpy()
    day = d["day"].to_numpy()

    # ---- S19: who is an index encounter, derived from data/ alone
    pub = adm[adm["published"]]
    hour = pub["admit_datetime"].str[11:13].astype(np.int64).to_numpy()
    idx_day = pub["admit_day"].to_numpy() + (hour + 12) // 24
    start = pub["facility_id"].map({k: day_number(v["vdi_scoring_from"]) for k, v in FAC.items()}).to_numpy()
    on_ward = ((pub["icu_at_12h"].to_numpy() == 0) & (pub["comfort_care_12h"].to_numpy() == 0)
               & ((pub["los_days"] == "").to_numpy() | (pub["los"].to_numpy() >= 0.5)))
    want = set(pub["encounter_id"].to_numpy()[on_ward & (idx_day >= start) & (idx_day <= end)])
    got = set(d["encounter_id"])
    time_ok = found_ok and (day == d["adm_admit_day"].to_numpy() + (d["hour"].to_numpy() < 12)).all() \
        and (d["hour"].to_numpy() == (pd.Series(d["adm_admit_datetime"]).str[11:13].astype(np.int64).to_numpy() + 12) % 24).all() \
        and (d["facility_id"].to_numpy() == d["adm_facility_id"]).all()
    rep.check("S19", "construction: the index encounters are exactly the published admissions on a ward at 12 hours (not in intensive care, not on comfort care, stay of at least half a day or still open) whose index time falls from the hospital's first scoring day to the data end; the index time is 12 hours after admission",
              f"{len(d):,} index encounters; {len(want - got)} missing, {len(got - want)} unexpected",
              "0 missing, 0 unexpected", d["encounter_id"].is_unique and want == got and bool(time_ok))

    # ---- S20: the outcome label and its date
    delay = spec.VDI["outcome_window_hours"] // 24 + spec.VDI["label_delay_days"]
    lab = d["labelled"].to_numpy()
    label_ok = ((d["label_day"].to_numpy()[lab] == day[lab] + delay).all() and (lab == (day + delay <= end)).all()
                and (lab == (d["label_day"].to_numpy() >= 0)).all())
    rep.check("S20", f"construction: the outcome label arrives {delay} days after the index date; label and date are empty exactly when that is after the data end",
              f"{int(lab.sum()):,} labelled, {int((~lab).sum()):,} not yet labelled", "consistent", bool(label_ok))

    # ---- S21: version, visibility, alert and response
    v3_day = day_number(spec.DATES["vdi_v3"])
    shown = d["vdi_shown"].to_numpy() == 1
    alert = d["alert_fired"].to_numpy() == 1
    rrt = d["rrt_evaluated"].to_numpy() == 1
    logic_ok = ((d["v3"].to_numpy() == (day >= v3_day)).all() and (shown == (day >= alerts)).all()
                and (alert == (shown & (d["vdi_score"].to_numpy() >= spec.VDI["threshold"]))).all()
                and (rrt <= alert).all())
    rep.check("S21", "construction: the version follows the date; the score is shown from the hospital's alert date; an alert fires exactly when the score is shown and at or above the threshold; an evaluation only follows an alert",
              f"{int(shown.sum()):,} shown, {int(alert.sum()):,} alerts, {int(rrt.sum()):,} evaluations",
              "consistent", bool(logic_ok))

    # ---- S22: inputs carried from the admission
    carried = (d["lactate_text"].to_numpy() == pd.Series(d["adm_lactate"]).to_numpy()).all() \
        and (d["network_encounters_12m"].to_numpy() >= d["adm_prior_admits_12m"].to_numpy()).all()
    rep.check("S22", "construction: lactate_at_index is the admission's recorded lactate, and network_encounters_12m is at least prior_admits_12m",
              f"{int((d['lactate_text'] != '').sum()):,} with a lactate on file", "consistent", bool(carried))
    if not truth_ok:
        rep.check("S23", "construction: index_truth.csv has one row for each index encounter, in the same order", "rows differ", "equal", False)
        return False

    # ---- S23: potential outcomes, realised outcome and the EHR flag
    r = Q["response"]
    y0, y1, y = (d[k].to_numpy() == 1 for k in ("y0", "y1", "y_true"))
    p0, p1 = d["p0"].to_numpy(), d["p1"].to_numpy()
    err = d["flag_error"].to_numpy()
    months = (day - alerts) * 12.0 / 365.25
    want_resp = np.maximum(r["floor"], r["start"] - r["fall_per_month"] * np.maximum(months, 0.0))
    resp = d["response_prob"].to_numpy()
    truth_rules = ((np.abs(p1 - r["risk_ratio"] * p0) <= 1.5e-6).all() and (y1 <= y0).all()
                   and (y == np.where(rrt, y1, y0)).all()
                   and ((d["event_type"].to_numpy() != "") == y0).all()
                   and ((d["response_text"].to_numpy() != "") == alert).all()
                   and (np.abs(resp[alert] - want_resp[alert]) <= 1.5e-6).all()
                   and ((err == "missed") <= y).all() and ((err == "false_positive") <= ~y).all()
                   and (d["ehr"].to_numpy()[lab] == (y & (err != "missed") | (err == "false_positive"))[lab]).all())
    rep.check("S23", "construction: p1 is 0.80 times p0; every y1 event is a y0 event; the realised outcome is y1 after an evaluation and y0 otherwise; the response probability follows the fading rule; the EHR flag is the truth except where ehr_flag_error says otherwise",
              f"{int(y0.sum()):,} events with no evaluation, {int(y1.sum()):,} with one, {int(y.sum()):,} realised; {int((err == 'missed').sum())} missed, {int((err == 'false_positive').sum())} false positives",
              "consistent", bool(truth_rules))

    # ---- S24: planted measurement mechanisms
    b = Q["vitals_recorded"]["spo2_bias"]
    black = d["race"].to_numpy() == b["group"]
    # spo2_true is printed to one decimal, so a value printed as exactly the limit may sit on either side.
    true_spo2 = d["spo2_true"].to_numpy()
    bias = d["spo2_bias"].to_numpy()
    want_bias = np.where(black, np.where(true_spo2 < b["below"], b["size_below"], b["size"]), 0.0)
    want_bias = np.where(black & (true_spo2 == b["below"]), bias, want_bias)
    bias_ok = (np.abs(bias - want_bias) < 1e-9).all() and np.isin(bias, (0.0, b["size"], b["size_below"])).all()
    central = d["facility_id"].map({k: v["central_lab"] == 1 for k, v in FAC.items()}).to_numpy()
    shifted = central & (d["adm_admit_day"].to_numpy() >= day_number(spec.DATES["lactate_assay_change"])) \
        & (d["lactate_text"].to_numpy() != "")
    same_score = d["vdi_score"].to_numpy() == d["vdi_score_no_assay_shift"].to_numpy()
    defaulted = d["rr_defaulted"].to_numpy() == 1
    planted_ok = (bool(bias_ok) and same_score[~shifted].all()
                  and (d["vdi_score"].to_numpy() >= d["vdi_score_no_assay_shift"].to_numpy()).all()
                  and (d["rr"].to_numpy()[defaulted] == Q["vitals_recorded"]["rr_default"]).all())
    rep.check("S24", "construction: the oximeter bias is in recorded SpO2 only for patients recorded as Black; the score differs from its no-shift twin only where the central laboratory's new assay measured a lactate; a defaulted respiratory rate is recorded as 18",
              f"{int(black.sum()):,} encounters with the bias ({int((bias == b['size_below']).sum())} at the larger size); {int((~same_score).sum()):,} scores moved by the assay; {int(defaulted.sum()):,} defaulted rates",
              "consistent", bool(planted_ok))

    # ---- S25: what a deterioration does to the stay
    w = Q["course"]["window_los"]
    closed = d["adm_disc_day"].to_numpy() >= 0
    los = d["adm_los"].to_numpy()
    died = d["adm_died_in_hospital"].to_numpy() == 1
    ev = d["event_type"].to_numpy()
    in_window = closed & (los <= w["max"])
    course_ok = ((died & in_window) <= y).all() \
        and (died & in_window)[y & (ev == "death") & closed].all() \
        and ((d["adm_disposition"] == "transfer").to_numpy() & in_window)[y & (ev == "transfer_out") & closed].all() \
        and (~died)[y & (ev == "transfer_out")].all()
    rep.check("S25", f"construction: nobody on a ward at 12 hours dies within {w['max']} days of admission without a true deterioration; an event of type death ends the stay in death inside that window, and one of type transfer_out ends it in a transfer",
              f"{int((died & in_window).sum()):,} deaths inside the window, all with a true event; {int((y & (ev == 'transfer_out')).sum()):,} transfers out",
              "consistent", bool(course_ok))

    # ---- S26: the vendor's files and the hidden formula
    risk = tables["data/deterioration/vendor_risk_table.csv"]
    scores = list(range(spec.VDI["score_min"], spec.VDI["score_max"] + 1))
    table_ok = len(risk) == len(scores) * len(spec.VDI["versions"])
    for version in spec.VDI["versions"]:
        part = risk[risk["vdi_version"] == version]
        values = pd.to_numeric(part["vendor_risk"]).to_numpy()
        table_ok = table_ok and part["vdi_score"].astype(int).tolist() == scores \
            and (np.diff(values) >= 0).all() and values.min() > 0 and values.max() < 1 \
            and (np.abs(values - deterioration.vendor_risk_table(version)) < 1e-12).all()
    with open(os.path.join(root, "hidden/deterioration/vdi_formula.json"), encoding="utf-8") as fh:
        formula = json.load(fh)
    with open(os.path.join(root, "data/deterioration/vendor_model_card.json"), encoding="utf-8") as fh:
        card = json.load(fh)
    seen = np.where(np.isnan(d["lactate"].to_numpy()), formula["lactate_imputed_when_missing"], d["lactate"].to_numpy())
    lp2 = formula["v2"]["intercept"] + deterioration.linear_predictor(
        formula["v2"], d["hr"].to_numpy(), d["rr"].to_numpy(), d["sbp"].to_numpy(), d["temp_c"].to_numpy(),
        d["spo2"].to_numpy(), d["o2"].to_numpy(), d["alertness"].to_numpy(), seen,
        d["adm_age"].astype(np.float64), d["network_encounters_12m"].to_numpy())
    lp3 = formula["v3"]["intercept"] + formula["v3"]["slope"] * lp2
    old, new = spec.VDI["versions"]
    rebuilt = np.where(d["v3"].to_numpy(), deterioration.display_score(lp3, new), deterioration.display_score(lp2, old))
    wrong = int((rebuilt != d["vdi_score"].to_numpy()).sum())
    card_ok = card["alert_threshold"] == spec.VDI["threshold"] \
        and card["claimed_performance"]["c_statistic"] == spec.VDI["vendor_claimed_c"] \
        and formula["features"] == {k: v for k, v in Q["features"].items()} and "formula" in card
    rep.check("S26", "construction: the vendor's risk table has every score for both versions and rises with the score; the model card states the threshold and the claimed C-statistic; the hidden formula, applied to the published inputs, reproduces every published score",
              f"{len(risk)} table rows; {wrong} of {len(d):,} scores differ from the formula",
              "0 differ", bool(table_ok) and bool(card_ok) and wrong == 0)
    return True


def check_deterioration_targets(rep, tables, adm, d, target, values):
    """Targets T14 to T32 that Milestone 3 builds."""
    Q = spec.DETERIORATION
    fac = d["facility_id"].to_numpy()
    day = d["day"].to_numpy()
    lab = d["labelled"].to_numpy()
    ehr = d["ehr"].to_numpy()
    score = d["vdi_score"].to_numpy()
    vr = d["vendor_risk"].to_numpy()
    vl = d["vendor_logit"].to_numpy()
    p0 = d["p0"].to_numpy()
    y = d["y_true"].to_numpy() == 1
    y0 = d["y0"].to_numpy() == 1
    y1 = d["y1"].to_numpy() == 1
    alert_rule = score >= spec.VDI["threshold"]
    f01_f05 = fac != "F06"
    f01_f03 = np.isin(fac, ("F01", "F02", "F03"))
    north = np.isin(fac, ("F04", "F05"))

    def between(first, last):
        return (day >= day_number(first)) & (day <= day_number(last))

    def rate(mask_num, mask_den):
        return float(mask_num.sum()) / int(mask_den.sum())

    # The chance that the EHR flag is raised when nobody responds: by hospital, from the planted
    # event mix and miss rates (basis "expected").
    miss = Q["ehr_flag"]["miss"]
    mix = Q["event_type"]
    miss_fac = {f: sum(mix["by_facility"].get(f, mix["elsewhere"])[c] * miss[c] for c in spec.EVENT_TYPES)
                for f in FAC}
    m = d["facility_id"].map(miss_fac).to_numpy()
    expected_flag = p0 * (1.0 - m) + (1.0 - p0) * Q["ehr_flag"]["false_positive"]

    rep.section("Deterioration and the vendor's index",
                "Silent mode means index encounters at F01 to F05 from 2023-07-01 to 2023-12-31, scored but not shown. "
                "The outcome is the EHR flag unless a row says otherwise. Vendor risk is read from "
                "`vendor_risk_table.csv`. O/E is observed events divided by the sum of vendor risks; on the "
                "expected basis the numerator is the sum of hidden probabilities that the flag is raised, and "
                "the realised value is shown beside it.")
    n = len(d)
    target("T14", n, f"{n:,}")
    pub = adm[adm["published"]]
    ward = ((pub["icu_at_12h"].to_numpy() == 0) & (pub["comfort_care_12h"].to_numpy() == 0)
            & ((pub["los_days"] == "").to_numpy() | (pub["los"].to_numpy() >= 0.5)))
    share = float(ward.sum()) / len(pub)
    target("T14b", share, fmt(share), 2)

    sil = between(spec.DATES["vdi_silent_start"], spec.DATES["vdi_silent_end"]) & f01_f05
    ns, es = int(sil.sum()), int(ehr[sil].sum())
    t15 = es / ns
    target("T15", t15, f"{t15:.4f} ({es} flagged of {ns:,}); true rate {rate(y & sil, sil):.4f}", 3)
    target("T15b", ns, f"{ns:,}")
    winter = np.isin(d["month"].to_numpy(), spec.WINTER_MONTHS)
    ratio = det_mean(p0[f01_f05 & winter]) / det_mean(p0[f01_f05 & ~winter])
    target("T15c", ratio, f"{ratio:.3f} (mean hidden risk with no evaluation, F01 to F05, all index encounters)", 2)

    c = c_statistic(score[sil], ehr[sil])
    target("T16", c, f"{c:.4f}; against the true outcome {c_statistic(score[sil], y[sil]):.4f}; the vendor claims {spec.VDI['vendor_claimed_c']:.2f}", 2)
    a, slope = logistic_fit(vl[sil], ehr[sil])
    target("T17", slope, f"{slope:.3f} (intercept {a:.3f})", 2)
    oe = es / det_sum(vr[sil])
    oe_expected = det_sum(expected_flag[sil]) / det_sum(vr[sil])
    target("T18", oe, f"{oe:.3f}; expected basis {oe_expected:.3f}", 2)
    payer = pd.Series(d["adm_payer"]).to_numpy()
    for cid, mask in (("T19", d["race"].to_numpy() == "black"), ("T20", north),
                      ("T21", np.isin(payer, ("medicaid", "self_pay")))):
        g = sil & mask
        value = det_sum(expected_flag[g]) / det_sum(vr[g])
        target(cid, value, f"{value:.3f}; realised {int(ehr[g].sum()) / det_sum(vr[g]):.3f} on {int(ehr[g].sum())} flagged of {int(g.sum()):,}", 2)
    flagged = sil & alert_rule
    t22 = rate(flagged, sil)
    target("T22", t22, f"{t22:.4f} ({int(flagged.sum()):,} at or above {spec.VDI['threshold']})", 2)
    t23 = rate(ehr & flagged, flagged)
    target("T23", t23, f"{t23:.3f}", 2)
    t24 = rate(ehr & flagged, ehr & sil)
    target("T24", t24, f"{t24:.3f}", 2)

    # ---- the assay change: the same patients with and without the shift (variance V4)
    plain = d["vdi_score_no_assay_shift"].to_numpy() >= spec.VDI["threshold"]
    april = between("2024-04-01", "2024-04-30") & f01_f03
    rise = rate(alert_rule & april, april) - rate(plain & april, april)
    feb = between("2024-02-01", "2024-02-29") & f01_f03
    target("T25", rise, f"{rise:.4f}: {rate(alert_rule & april, april):.4f} with the shift, {rate(plain & april, april):.4f} without, on the same {int(april.sum()):,} encounters; raw February {rate(alert_rule & feb, feb):.4f}, raw April {rate(alert_rule & april, april):.4f}", 2)
    extra = april & alert_rule & ~plain & (d["alert_fired"].to_numpy() == 1)
    saved = det_sum((d["response_prob"].to_numpy() * (p0 - d["p1"].to_numpy()))[extra]) / int(april.sum())
    y_without = np.where(plain, y, y0)
    target("T26", saved, f"{saved:.5f} lower, from {int(extra.sum())} extra alerts; realised {abs(rate(y & april, april) - rate(y_without & april, april)):.5f}; mean hidden risk with no evaluation: February {det_mean(p0[feb]):.4f}, April {det_mean(p0[april]):.4f}", 3)

    # ---- Sallowfield
    f06 = (fac == "F06") & lab
    t27 = rate(ehr & f06, f06)
    target("T27", t27, f"{t27:.4f} ({int(ehr[f06].sum())} flagged of {int(f06.sum()):,} labelled encounters)", 3)
    f06_v2 = f06 & ~d["v3"].to_numpy()
    t27b = int(ehr[f06_v2].sum()) / det_sum(vr[f06_v2])
    target("T27b", t27b, f"{t27b:.3f} ({int(ehr[f06_v2].sum())} flagged of {int(f06_v2.sum()):,})", 2)

    # ---- effect of the evaluation, flag accuracy, default rate
    rr = int(y1.sum()) / int(y0.sum())
    target("T28", rr, f"{rr:.4f} ({int(y1.sum()):,} events with an evaluation for everyone, {int(y0.sum()):,} with none)", 2)
    sens = rate(ehr & y & lab, y & lab)
    target("T29", sens, f"{sens:.4f} on {int((y & lab).sum()):,} true events", 2)
    ev = d["event_type"].to_numpy()
    g = y & north
    expected_sens = det_mean(np.array([1.0 - miss[t] for t in ev[g]]))
    target("T29b", expected_sens, f"{expected_sens:.3f} from the types of the {int(g.sum())} true events; realised {rate(ehr & g & lab, g & lab):.3f}", 2)
    fpr = rate(ehr & ~y & lab, ~y & lab)
    target("T29c", fpr, f"{fpr:.5f}", 3)
    eighteen = d["rr"].to_numpy() == Q["vitals_recorded"]["rr_default"]
    t30 = rate(eighteen & north, north)
    target("T30", t30, f"{t30:.3f} of recorded values are 18 at F04 and F05, {rate(eighteen & ~north, ~north):.3f} elsewhere; the hidden default flag: {rate((d['rr_defaulted'].to_numpy() == 1) & north, north):.3f} and {rate((d['rr_defaulted'].to_numpy() == 1) & ~north, ~north):.3f}", 2)

    # ---- response and its fading
    alert = d["alert_fired"].to_numpy() == 1
    rrt = d["rrt_evaluated"].to_numpy() == 1
    live_from = d["facility_id"].map({k: day_number(v["vdi_alerts_from"]) for k, v in FAC.items()}).to_numpy()
    early = alert & (day - live_from < 91)
    t31 = rate(rrt & early, early)
    target("T31", t31, f"{t31:.4f} of {int(early.sum())} alerts in each hospital's first 91 days live", 2)
    late = alert & f01_f03 & between("2025-10-01", "2025-12-31")
    t31b = rate(rrt & late, late)
    target("T31b", t31b, f"{t31b:.4f} of {int(late.sum())} alerts", 2)

    # ---- version 3.0
    v3 = d["v3"].to_numpy()
    t32 = rate(alert_rule & v3, v3)
    target("T32", t32, f"{t32:.4f} of {int(v3.sum()):,} encounters; version 2.0 in the twelve months before: {rate(alert_rule & ~v3 & between('2025-02-01', '2026-01-31'), ~v3 & between('2025-02-01', '2026-01-31')):.4f}", 2)
    g = v3 & lab
    _a, slope3 = logistic_fit(vl[g], ehr[g])
    target("T32b", slope3, f"{slope3:.3f} on {int(g.sum()):,} labelled encounters", 2)
    citl, _b = logistic_fit(vl[g], ehr[g], offset=True)
    target("T32c", citl, f"{citl:+.3f}; O/E {int(ehr[g].sum()) / det_sum(vr[g]):.3f}", 2)

    values.update({
        "vdi_c": f"{c:.2f} locally; the vendor claims {spec.VDI['vendor_claimed_c']:.2f}",
        "vdi_gap": f"{spec.VDI['vendor_claimed_c'] - c:.2f} lower locally",
        "vdi_alerts": f"{100 * t22:.1f}% flagged in silent mode; {100 * (1 - t24):.0f}% of events had a score below the threshold",
    })



# ------------------------------------------------------------------ Milestone 4: helpers
def simpson(values, width):
    """Simpson's rule on an odd number of equally spaced values, with an exact sum."""
    w = np.ones(len(values))
    w[1:-1:2] = 4.0
    w[2:-1:2] = 2.0
    return det_sum(w * values) * width / 3.0


def det_normal_cdf(z):
    """Standard normal CDF by Simpson's rule on det_exp: the same on every machine.
    (math.erf is not used here, because CHECKS.md is hashed.)"""
    t = np.linspace(0.0, abs(z), 2001)
    area = simpson(det_exp(-0.5 * t * t), abs(z) / 2000.0) / np.sqrt(2.0 * np.pi) if z != 0 else 0.0
    return 0.5 + area if z >= 0 else 0.5 - area


def det_normal_quantile(p):
    lo, hi = -8.0, 8.0
    for _ in range(60):
        mid = (lo + hi) / 2.0
        if det_normal_cdf(mid) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def r2_from_c(c, rate):
    """Cox-Snell R-squared a model with C-statistic `c` would have at outcome rate `rate`,
    when its linear predictor is normal with equal variance in events and non-events.
    That is the approximation Riley and colleagues give for turning a reported C into R-squared."""
    d = float(np.sqrt(2.0)) * det_normal_quantile(c)
    a = float(det_log(rate / (1.0 - rate))) - d * d / 2.0
    x = np.linspace(-9.0, 9.0 + d, 4001)
    width = (18.0 + d) / 4000.0
    p = det_plogis(a + d * x)
    root = float(np.sqrt(2.0 * np.pi))
    ll = (rate * simpson(det_exp(-0.5 * (x - d) * (x - d)) / root * det_log(p), width)
          + (1.0 - rate) * simpson(det_exp(-0.5 * x * x) / root * det_log(1.0 - p), width))
    ll0 = rate * float(det_log(rate)) + (1.0 - rate) * float(det_log(1.0 - rate))
    return 1.0 - float(det_exp(-2.0 * (ll - ll0)))


def max_r2(rate):
    ll0 = rate * float(det_log(rate)) + (1.0 - rate) * float(det_log(1.0 - rate))
    return 1.0 - float(det_exp(2.0 * ll0))


def riley_minimum(r2, rate, parameters):
    """Minimum development sample size for a binary outcome: the largest of the three
    criteria in Riley et al., BMJ 2020 (shrinkage, optimism in R-squared, overall risk)."""
    q = spec.R30["riley"]
    s1 = q["shrinkage"]
    n1 = parameters / ((s1 - 1.0) * float(det_log(1.0 - r2 / s1)))
    s2 = r2 / (r2 + q["r2_difference"] * max_r2(rate))
    n2 = parameters / ((s2 - 1.0) * float(det_log(1.0 - r2 / s2)))
    n3 = (1.96 / q["risk_margin"]) ** 2 * rate * (1.0 - rate)
    return int(np.ceil(max(n1, n2, n3)))


def r30_frame(adm, persons, observed):
    """The team's predictors rebuilt from data/ for every admission in `adm`
    (same row order), with the observed outcome an analyst derives."""
    cut = spec.R30["cut"]
    sodium = pd.to_numeric(adm["sodium"]).to_numpy()
    hemoglobin = pd.to_numeric(adm["hemoglobin"]).to_numpy()
    disc = adm["disc_day"].to_numpy()
    disc_month = pd.to_numeric(adm["discharge_date"].str[5:7]).to_numpy()
    prior = adm["prior_admits_12m"].to_numpy()
    disp = adm["disposition"].to_numpy()
    x = {
        "age_65_plus": adm["age"].to_numpy() >= cut["age"],
        "female": persons.set_index("person_id")["sex"].reindex(adm["person_id"]).to_numpy() == "f",
        "los_over_5": adm["los"].to_numpy() > cut["los_days"],
        "prior_admits_1": prior == 1,
        "prior_admits_2_plus": prior >= 2,
        "comorbidity_count": adm["comorbidity_count"].to_numpy(),
        "disp_snf": disp == "snf",
        "disp_home_health": disp == "home_health",
        "medicaid": adm["payer"].to_numpy() == "medicaid",
        "sodium_low": sodium < cut["sodium"],              # a missing value compares False
        "hemoglobin_low": hemoglobin < cut["hemoglobin"],
        "dx_cancer": adm["dx_group"].to_numpy() == "cancer",
        "dx_heart_failure": adm["dx_group"].to_numpy() == "heart_failure",
        "dx_copd": adm["dx_group"].to_numpy() == "copd",
        "emergency": adm["admission_type"].to_numpy() == "emergency",
        "weekend_discharge": (disc - 1) % 7 >= 5,          # ordinal 1 is a Monday
        "winter_discharge": np.isin(disc_month, spec.WINTER_MONTHS),
    }
    x = {name: np.asarray(values, dtype=np.float64) for name, values in x.items()}
    x["prior_admits_cat"] = np.minimum(prior, 2).astype(np.float64)
    x["readmit_30d_observed"] = observed.astype(np.float64)
    return x


def check_m4_structure(rep, root, tables, adm, persons, observed, index, x):
    """Structural checks S27 to S33 for the Milestone 4 files. Returns what the targets need."""
    R = spec.R30
    dev_spec = R["development"]
    enc = adm["encounter_id"].to_numpy()
    disc = adm["disc_day"].to_numpy()
    closed = disc >= 0
    eligible = adm["disposition"].isin(spec.READMIT_ELIGIBLE_DISPOSITIONS).to_numpy()
    published = adm["published"].to_numpy()

    # ---- S27: the development sample, rebuilt from data/
    sample = tables["data/readmission/r30_development_sample.csv"]
    rule = (published & eligible & closed & (adm["facility_id"].to_numpy() == dev_spec["facility"])
            & (adm["service"].to_numpy() == dev_spec["service"])
            & (disc >= day_number(dev_spec["from"])) & (disc <= day_number(dev_spec["to"])))
    for test in dev_spec["panel"]:
        rule &= (adm[test] != "").to_numpy()
    cand = pd.DataFrame({"i": np.nonzero(rule)[0], "person": adm["person_id"].to_numpy()[rule],
                         "disc": disc[rule], "enc": enc[rule]}).sort_values(["disc", "enc"], kind="mergesort")
    first = cand.drop_duplicates("person", keep="first")["i"].to_numpy()
    first = first[np.argsort(enc[first])]
    same_rows = len(first) == len(sample) and (enc[first] == sample["encounter_id"].to_numpy()).all()
    wrong_cells = -1
    if same_rows:
        wrong_cells = 0
        for name in [c[0] for c in spec.FILES["data/readmission/r30_development_sample.csv"]["columns"]][1:]:
            wrong_cells += int((sample[name].astype(np.float64).to_numpy() != x[name][first]).sum())
    rep.check("S27", "construction: the development sample is exactly what the model card describes, rebuilt from data/: the university hospital's medicine discharges in the first half of 2022, alive to home, home health or skilled nursing, with all five laboratory tests on file, each patient's first such discharge; every column, and the outcome, equals its definition",
              f"{len(sample):,} rows against {len(first):,} rebuilt ({int(rule.sum()):,} before keeping first discharges); {wrong_cells} cells differ",
              "same rows; 0 cells differ", bool(same_rows) and wrong_cells == 0)
    if not same_rows:
        return None

    # ---- S28: the model card and the fit trace against a refit of the published sample
    with open(os.path.join(root, "data/readmission/r30_model_card.json"), encoding="utf-8") as fh:
        card = json.load(fh)
    with open(os.path.join(root, "hidden/readmission/r30_fit_trace.json"), encoding="utf-8") as fh:
        trace = json.load(fh)
    with open(os.path.join(root, "hidden/readmission/r30_truth.json"), encoding="utf-8") as fh:
        truth = json.load(fh)
    xs = {name: sample[name].astype(np.float64).to_numpy() for name in sample.columns if name != "encounter_id"}
    xs["prior_admits_1"] = (xs["prior_admits_cat"] == 1).astype(np.float64)
    xs["prior_admits_2_plus"] = (xs["prior_admits_cat"] == 2).astype(np.float64)
    refit = readmission.screen_and_fit(xs, xs["readmit_30d_observed"])
    reported = float(format_float(refit["apparent_c"], R["reported_c_decimals"]))
    kept_terms = [s["term"] for s in refit["screen"] if s["kept"]]
    card_ok = (card["coefficients"] == refit["coefficients"]
               and card["reported_performance"]["c_statistic"] == reported
               and card["development_sample"] == {"discharges": refit["n"], "readmissions": refit["events"]}
               and card["terms_dropped_by_the_screen"] == [s["term"] for s in refit["screen"] if not s["kept"]]
               and trace["coefficients_on_the_card"] == refit["coefficients"]
               and [s["kept"] for s in trace["screen"]] == [s["kept"] for s in refit["screen"]]
               and max(abs(a["lr_statistic"] - b["lr_statistic"]) for a, b in zip(trace["screen"], refit["screen"])) < 1e-9
               and sum(len(c) for _n, c, _t in R["terms"]) == R["candidate_parameters"])
    rep.check("S28", "construction: refitting the published sample by the card's method (a likelihood-ratio screen at p < 0.20, then one logistic fit) gives the card's coefficients to six decimals and its reported C-statistic; the hidden fit trace agrees",
              f"{len(refit['kept'])} of {R['candidate_parameters']} candidate parameters kept ({len(kept_terms)} of {len(R['terms'])} terms); reported C {reported:.3f}",
              "card and trace equal the refit", bool(card_ok))

    # ---- S29: production scores, rebuilt from data/ and the card
    scores = tables["data/readmission/r30_scores.csv"]
    want = np.nonzero(published & eligible & closed & (disc >= day_number(spec.DATES["r30_scores_start"])))[0]
    want = want[np.argsort(enc[want])]
    rows_ok = len(want) == len(scores) and (enc[want] == scores["encounter_id"].to_numpy()).all()
    wrong = -1
    risk = np.full(len(adm), np.nan)
    if rows_ok:
        rebuilt = readmission.risk(card["coefficients"], {k: v[want] for k, v in x.items()}, len(want))
        text = np.array([format_float(float(v), 6) for v in rebuilt])
        wrong = int((text != scores["r30_risk"].to_numpy()).sum())
        wrong += int((scores["score_date"].to_numpy() != adm["discharge_date"].to_numpy()[want]).sum())
        risk[want] = pd.to_numeric(scores["r30_risk"]).to_numpy()
    rep.check("S29", "construction: r30_scores.csv holds every eligible discharge from 2023-01-01 at all six hospitals, dated on the discharge day, and each risk is reproduced from data/ and the model card",
              f"{len(scores):,} scores against {len(want):,} eligible discharges; {wrong} differ", "same rows; 0 differ",
              bool(rows_ok) and wrong == 0)

    # ---- S30: the chart review sample
    review = tables["data/deterioration/chart_review.csv"]
    c = spec.CHART_REVIEW
    d = index.set_index("encounter_id")
    sil = ((index["day"] >= day_number(spec.DATES["vdi_silent_start"])) & (index["day"] <= day_number(spec.DATES["vdi_silent_end"]))
           & (index["facility_id"] != "F06")).to_numpy()
    cuts = deterioration.decile_cuts(index["vdi_score"].to_numpy()[sil])
    strata_all = deterioration.stratum_of(index["vdi_score"].to_numpy()[sil], cuts)
    sizes = np.bincount(strata_all, minlength=11)[1:]
    in_silent = set(index["encounter_id"].to_numpy()[sil])
    rs = review["stratum"].astype(int).to_numpy()
    review_score = d["vdi_score"].reindex(review["encounter_id"]).to_numpy()
    review_ok = (review["encounter_id"].is_unique and set(review["encounter_id"]) <= in_silent
                 and (deterioration.stratum_of(review_score, cuts) == rs).all()
                 and np.bincount(rs, minlength=11)[1:].tolist() == list(c["allocation"])
                 and (review["stratum_size"].astype(int).to_numpy() == sizes[rs - 1]).all()
                 and (review["stratum_sampled"].astype(int).to_numpy() == np.array(c["allocation"])[rs - 1]).all()
                 and (review["incl_prob"].to_numpy() == np.array([format_float(a / b, 6) for a, b in zip(np.array(c["allocation"])[rs - 1], sizes[rs - 1])])).all())
    rep.check("S30", "construction: the chart review is a sample of silent-mode encounters in ten strata cut at the deciles of the score, with the planned number drawn from each and inclusion probability = sampled / stratum size",
              f"{len(review)} reviewed; cut points {cuts}; stratum sizes {sizes.tolist()}; sampled {list(c['allocation'])}",
              "consistent", bool(review_ok))

    # ---- S31: the rapid-response log
    log = tables["data/deterioration/rrt_log.csv"]
    evaluated = index.loc[index["rrt_evaluated"] == 1, "encounter_id"]
    stamp = ordinal(log["rrt_datetime"]) * 24 + log["rrt_datetime"].str[11:13].astype(np.int64).to_numpy()
    index_stamp = (d["day"] * 24 + d["hour"]).reindex(log["encounter_id"]).to_numpy()
    wait = stamp - index_stamp
    log_ok = (log["encounter_id"].is_unique and set(log["encounter_id"]) == set(evaluated)
              and (wait >= 0).all() and (wait <= len(spec.RRT_LOG["delay_hours"]) - 1).all()
              and (np.diff(stamp) >= 0).all() and (stamp <= DATA_END.toordinal() * 24 + 23).all()
              and (pd.to_numeric(log["nurse_minutes"]) >= spec.RRT_LOG["nurse"]["added"]).all()
              and (pd.to_numeric(log["physician_minutes"]) >= 0).all())
    rep.check("S31", "construction: rrt_log.csv has one row for each evaluation in index_encounters.csv, numbered in time order, beginning 0 to 3 hours after the index time",
              f"{len(log):,} rows for {len(evaluated):,} evaluations", "one each; times consistent", bool(log_ok))

    # ---- S32: the laboratory change log
    lab = tables["data/network/lab_change_log.csv"]
    L = spec.LAB_LOG
    lab_day = ordinal(lab["effective_date"])
    joined = {site: max(day_number(FAC[f]["network_data_from"]) for f in members) for site, members in spec.LAB_SITES.items()}
    lactate = lab[lab["description"].str.contains("actate")]
    lab_ok = (lab["log_id"].tolist() == [f"L{i:04d}" for i in range(1, len(lab) + 1)]
              and (np.diff(lab_day) >= 0).all() and lab_day.min() >= day_number(L["from"]) and lab_day.max() <= DATA_END.toordinal()
              and (lab["facilities"] == lab["lab_site"].map({k: ";".join(v) for k, v in spec.LAB_SITES.items()})).all()
              and (lab_day >= lab["lab_site"].map(joined).to_numpy()).all()
              and len(lab) == L["routine_entries"] + len(L["fixed"])
              and len(lactate) == 1 and lactate["effective_date"].iloc[0] == spec.DATES["lactate_assay_change"]
              and lactate["lab_site"].iloc[0] == "central")
    rep.check("S32", "construction: the laboratory change log is in date order, each entry names the hospitals its laboratory serves, no entry predates a hospital joining, and the lactate method change is one entry among the routine ones, on its date, saying nothing of its effect",
              f"{len(lab)} entries, {int((lab['change_type'] == 'method_change').sum())} of them method changes; lactate entry {lactate['log_id'].iloc[0] if len(lactate) == 1 else 'missing'}",
              "consistent; one lactate entry", bool(lab_ok))

    # ---- S33: change points and monthly truth
    cp = tables["hidden/deterioration/change_points.csv"]
    mt = tables["hidden/deterioration/monthly_truth.csv"]
    dates = {m: set(cp.loc[cp["mechanism"] == m, "change_date"]) for m in set(cp["mechanism"])}
    cp_ok = (dates.get("lactate_assay_shift") == {spec.DATES["lactate_assay_change"]}
             and dates.get("vdi_version_3") == {spec.DATES["vdi_v3"]}
             and dates.get("acquisition") == {spec.DATES["f06_acquired"]}
             and dates.get("alerts_live", set()) | dates.get("alerts_live_no_silent_period", set())
             == {f["vdi_alerts_from"] for f in spec.FACILITIES}
             and dates.get("alerts_live_no_silent_period") == {spec.DATES["vdi_live_f06"]}
             and cp["change_id"].tolist() == [f"CP{i:02d}" for i in range(1, len(cp) + 1)])
    month = pd.Series([dt.date.fromordinal(int(v)).isoformat()[:7] for v in index["day"]])
    group_of = {f: g for g, members in spec.FACILITY_GROUPS.items() for f in members}
    group = index["facility_id"].map(group_of)
    treated = np.where(index["rrt_evaluated"].to_numpy() == 1, index["p1"].to_numpy(), index["p0"].to_numpy())
    worst, cells = 0.0, 0
    for (m, g), part in mt.groupby(["month", "facility_group"], sort=False):
        cell = ((month == m) & ((group == g) if g != "all" else True)).to_numpy()
        row = part.iloc[0]
        cells += 1
        if int(row["index_encounters"]) != int(cell.sum()):
            worst = 1.0
            continue
        # six-decimal columns are compared as they stand; alert_rate has four decimals, so it is scaled
        worst = max(worst,
                    abs(float(row["true_rate_no_response"]) - det_mean(index["p0"].to_numpy()[cell])),
                    abs(float(row["true_rate_as_treated"]) - det_mean(treated[cell])),
                    abs(float(row["vendor_expected_rate"]) - det_mean(index["vendor_risk"].to_numpy()[cell])),
                    abs(float(row["alert_rate"]) - float((index["vdi_score"].to_numpy()[cell] >= spec.VDI["threshold"]).sum()) / int(cell.sum())) / 100.0)
    months = len(set(month))
    rep.check("S33", "construction: change_points.csv carries the planted dates (alerts at each hospital, the assay change, the acquisition, version 3.0), and monthly_truth.csv equals a recount from the index files",
              f"{len(cp)} change points; {cells} month-by-group cells over {months} months; recount agrees to the printed decimals: {'yes' if worst < 1e-6 else 'no'}",
              "dates right; recount agrees", bool(cp_ok) and worst < 1e-6 and len(mt) == cells)
    return {"sample": sample, "card": card, "trace": trace, "truth": truth, "refit": refit, "risk": risk,
            "review": review, "log": log, "dev_rows": first}


def check_m4_targets(rep, tables, adm, persons_truth, observed, index, x, m4, target):
    """Targets T33, T34 and T40 to T46."""
    R = spec.R30
    # ---- chart review and the rapid-response log
    rep.section("Chart review and rapid-response log")
    review, d = m4["review"], index.set_index("encounter_id")
    truth = d["y_true"].reindex(review["encounter_id"]).to_numpy() == 1
    flag = d["ehr"].reindex(review["encounter_id"]).to_numpy()
    said = review["reviewer_outcome"].to_numpy() == "1"
    weight = 1.0 / pd.to_numeric(review["incl_prob"]).to_numpy()
    sil = ((index["day"] >= day_number(spec.DATES["vdi_silent_start"])) & (index["day"] <= day_number(spec.DATES["vdi_silent_end"]))
           & (index["facility_id"] != "F06")).to_numpy()
    n_sil = int(sil.sum())
    weighted = det_sum(weight[said]) / n_sil
    flag_sens = det_sum(weight[said & flag]) / det_sum(weight[said])
    target("T33", len(review),
           f"{len(review)}; the reviewer found {int((said & truth).sum())} of {int(truth.sum())} true events and called {int((said & ~truth).sum())} of {int((~truth).sum())} non-events an event; "
           f"design-weighted event rate {weighted:.4f} against a true {float((index['y_true'].to_numpy()[sil] == 1).sum()) / n_sil:.4f} and an EHR-flag rate of {float(index['ehr'].to_numpy()[sil].sum()) / n_sil:.4f}; "
           f"design-weighted sensitivity of the flag {flag_sens:.3f}; unweighted event rate in the sample {float(said.sum()) / len(review):.4f}")
    log = m4["log"]
    nurse = det_mean(pd.to_numeric(log["nurse_minutes"]).to_numpy())
    physician = det_mean(pd.to_numeric(log["physician_minutes"]).to_numpy())
    target("T34", nurse, f"{nurse:.1f} over {len(log):,} evaluations", 1)
    target("T34b", physician, f"{physician:.1f}", 1)

    # ---- R30
    rep.section("Readmission model R30",
                "The observed outcome is the one an analyst derives from `data/`: the first return to a network hospital "
                "within 30 days, when it was not planned. Validation uses `r30_scores.csv` for 2023 discharges at F01 to F05. "
                "T41 and T43 are judged against variance V6, whose ranges were set after the values were seen "
                "(`DESIGN.md` decision A31); the brief's range is printed beside each.")
    refit, card = m4["refit"], m4["card"]
    n, events = refit["n"], refit["events"]
    rate = events / n
    target("T40", n, f"{n:,}")
    target("T40b", events, f"{events} ({rate:.4f})")
    kept = [s["term"] for s in refit["screen"] if s["kept"]]
    dropped = [s["term"] for s in refit["screen"] if not s["kept"]]
    apparent = refit["apparent_c"]
    target("T41", apparent, f"{apparent:.4f}, reported on the card as {card['reported_performance']['c_statistic']:.3f}; terms kept by the screen: {', '.join(kept)}; dropped: {', '.join(dropped)}", 2)

    disc = adm["disc_day"].to_numpy()
    risk = m4["risk"]
    val = (~np.isnan(risk) & (disc >= day_number("2023-01-01")) & (disc <= day_number("2023-12-31"))
           & (adm["facility_id"].to_numpy() != "F06"))
    y = observed[val]
    logit = det_log(risk[val] / (1.0 - risk[val]))
    c_val = c_statistic(risk[val], y)
    target("T42", c_val, f"{c_val:.4f} on {int(val.sum()):,} discharges with {int(y.sum()):,} observed readmissions; against the true outcome {c_statistic(risk[val], adm['readmit_any_30d'].to_numpy()[val] == 1):.4f}", 2)
    a, slope = logistic_fit(logit, y)
    oe = int(y.sum()) / det_sum(risk[val])
    fac = adm["facility_id"].to_numpy()
    by_fac = ", ".join(f"{f} {int(observed[val & (fac == f)].sum()) / det_sum(risk[val & (fac == f)]):.2f}" for f in sorted(set(fac[val])))
    target("T43", slope, f"{slope:.3f} (intercept {a:.3f}); overall O/E {oe:.3f}; O/E by hospital: {by_fac}", 2)

    # expected basis for the small northern cell: the hidden chance of a network readmission
    q = persons_truth.set_index("person_id")["outside_care_propensity"].astype(np.float64).reindex(adm["person_id"]).to_numpy()
    payer_term = adm["payer"].map(spec.INPATIENT["outside_readmission"]["payer"]).fillna(0.0).to_numpy()
    north = val & np.isin(fac, ("F04", "F05"))
    p_out = det_plogis(det_log(q[north] / (1.0 - q[north])) + payer_term[north])
    expected = det_sum(adm["readmit_prob"].to_numpy()[north] * (1.0 - p_out))
    t44 = expected / det_sum(risk[north])
    true_any = det_sum(adm["readmit_prob"].to_numpy()[north])
    target("T44", t44, f"{t44:.3f}; realised {int(observed[north].sum()) / det_sum(risk[north]):.3f} on {int(observed[north].sum())} observed readmissions of {int(north.sum()):,}; against readmission to any hospital the expected O/E is {true_any / det_sum(risk[north]):.3f}", 2)

    # ---- T45: the Riley minimum, under the assumption fixed in advance and four others
    k = R["candidate_parameters"]
    q = R["riley"]
    fixed = riley_minimum(r2_from_c(R["riley_anticipated_c"], rate), rate, k)
    others = [f"{riley_minimum(r2_from_c(c, rate), rate, k):,} at an anticipated C of {c:.2f}" for c in q["alternative_c"]]
    own = riley_minimum(r2_from_c(apparent, rate), rate, k)
    share = riley_minimum(q["share_of_max_r2"] * max_r2(rate), rate, k)
    rep.check("T45", f"realised: {T45_TEXT}",
              f"n {n:,} against a minimum of {fixed:,} at an anticipated C of {R['riley_anticipated_c']:.2f}, the value fixed before any data existed; "
              f"{others[0]}; {share:,} at {q['share_of_max_r2']:.0%} of the maximum R-squared; {own:,} at the model's own apparent C of {apparent:.3f}; {others[1]} "
              f"({k} candidate parameters, outcome rate {rate:.4f})",
              f"n below {fixed:,}", n < fixed)

    # ---- T46: the two noise predictors
    ref_fit = m4["truth"]["reference_fit"]["fits"]["true_outcome_any_hospital"]
    ref, ref_se = ref_fit["coefficients"], ref_fit["standard_errors"]
    noise = ("weekend_discharge", "winter_discharge")
    terms = set(spec.INPATIENT["readmission"])
    in_truth = [w for w in ("weekend", "weekday", "winter", "season") if any(w in t for t in terms)]
    on_card = {name: card["coefficients"].get(name) for name in noise}
    rep.check("T46", f"construction: {T46_TEXT}",
              "the true model has no term for either; "
              + "; ".join(f"{name}: " + (f"kept by the screen with coefficient {on_card[name]:.3f}" if on_card[name] is not None else "dropped by the screen")
                          + f", {ref[name]:+.3f} (standard error {ref_se[name]:.3f}) in the reference fit" for name in noise)
              + f"; the reference fit is R30's form on {m4['truth']['reference_fit']['discharges']:,} discharges, where a small coefficient is confounding, not an effect",
              "no such term in the true model", not in_truth and m4["truth"]["noise_predictors"] == {n_: 0.0 for n_ in noise})


T45_TEXT = [t[2] for t in spec.TARGETS if t[0] == "T45"][0]
T46_TEXT = [t[2] for t in spec.TARGETS if t[0] == "T46"][0]


# ------------------------------------------------------------------ structure
# ------------------------------------------------------------------ Milestone 5: the scribe
def _ints(series):
    return series.astype(np.int64).to_numpy()


def _floats(series):
    return pd.to_numeric(series).to_numpy(dtype=np.float64)


def kappa_from_table(both, first_only, second_only, neither):
    """Cohen's kappa from the four counts of a two-by-two agreement table."""
    n = both + first_only + second_only + neither
    agree = (both + neither) / n
    p1, p2 = (both + first_only) / n, (both + second_only) / n
    chance = p1 * p2 + (1.0 - p1) * (1.0 - p2)
    return (agree - chance) / (1.0 - chance)


def scribe_frame(tables):
    """The scribe tables with numbers as numbers, joined where the checks need them."""
    S = spec.SCRIBE
    d = {"clinics": tables["data/scribe/clinics.csv"], "clinicians": tables["data/scribe/clinicians.csv"],
         "rollout": tables["data/scribe/rollout.csv"], "panel": tables["data/scribe/clinician_weeks.csv"].copy(),
         "survey": tables["data/scribe/wellbeing_survey.csv"], "frame": tables["data/scribe/ai_notes_frame.csv"].copy(),
         "sample": tables["data/scribe/audit_sample.csv"], "ratings": tables["data/scribe/audit_ratings.csv"],
         "costs": tables["data/economics/scribe_costs.csv"], "wages": tables["data/economics/wage_rates.csv"],
         "errors": tables["hidden/scribe/note_errors_truth.csv"], "raters": tables["hidden/scribe/rater_parameters.csv"],
         "effects": tables["hidden/scribe/clinic_effects.csv"], "ctruth": tables["hidden/economics/clinician_truth.csv"],
         "wtruth": tables["hidden/economics/clinician_weeks_truth.csv"]}
    week0 = dt.date.fromisoformat(spec.DATES["scribe_measure_start"])
    d["week_iso"] = [(week0 + dt.timedelta(days=7 * w)).isoformat() for w in range(spec.SCRIBE_WEEKS)]
    wave = dict(zip(d["rollout"]["clinic_id"], _ints(d["rollout"]["wave"])))
    d["wave_of_clinic"] = wave
    clinic_of = dict(zip(d["clinicians"]["clinician_id"], d["clinicians"]["clinic_id"]))
    d["clinic_of"] = clinic_of
    p = d["panel"]
    for name in ("week_index", "clinic_live", "holiday_week", "visits", "scribe_visits"):
        p[name + "_n"] = _ints(p[name])
    p["go_week"] = np.array([S["wave_weeks"][wave[c] - 1] for c in p["clinic_id"]])
    p["k"] = p["week_index_n"] - p["go_week"]                 # weeks since go-live; negative before
    p["doc"] = _floats(p["doc_minutes_per_visit"])
    p["ah"] = _floats(p["after_hours_minutes"])
    f = d["frame"]
    f["minutes"] = _floats(f["visit_minutes"])
    f["interp"] = _ints(f["interpreter_used"])
    f["speakers"] = _ints(f["n_speakers"])
    f["v24"] = (f["scribe_version"] == "2.4").to_numpy()
    return d


def check_m5_structure(rep, root, tables):
    """S34 to S44. Returns the assembled scribe tables, or None if a key check fails."""
    S = spec.SCRIBE
    d = scribe_frame(tables)
    clinics, clinicians, rollout, p, f = d["clinics"], d["clinicians"], d["rollout"], d["panel"], d["frame"]
    week_iso = d["week_iso"]

    # ---- S34 clinics, clinicians, rollout
    listed = [tuple(row) for row in clinics[["clinic_id", "clinic_type", "specialty", "area"]].values.tolist()]
    counts = clinicians["clinic_id"].value_counts()
    sizes_ok = all(int(n) == int(counts.get(c, 0)) for c, n in zip(clinics["clinic_id"], clinics["n_clinicians"]))
    ids_ok = list(clinicians["clinician_id"]) == [f"K{i:03d}" for i in range(1, len(clinicians) + 1)]
    spec_of = dict(zip(clinics["clinic_id"], clinics["specialty"]))
    clin_ok = all(spec_of[c] == s for c, s in zip(clinicians["clinic_id"], clinicians["specialty"]))
    type_of = dict(zip(clinics["clinic_id"], clinics["clinic_type"]))
    waves = _ints(rollout["wave"])
    per_wave = {(w, t): 0 for w in (1, 2, 3, 4) for t in ("primary_care", "specialty")}
    for c, w in zip(rollout["clinic_id"], waves):
        per_wave[(int(w), type_of[c])] += 1
    dates_ok = all(spec.DATES[spec.SCRIBE_WAVE_KEYS[w - 1]] == g for w, g in zip(waves, rollout["go_live_date"]))
    roll_ok = (all(per_wave[(w, "primary_care")] == 4 and per_wave[(w, "specialty")] == 2 for w in (1, 2, 3, 4))
               and dates_ok and (rollout["stratum"].to_numpy() == clinics["clinic_type"].to_numpy()).all())
    ok34 = (listed == [tuple(c) for c in S["clinics"]] and sizes_ok and ids_ok and clin_ok and roll_ok
            and len(clinicians) == S["clinicians"])
    rep.check("S34", "construction: the 24 clinics are the spec's; clinician counts and specialties agree; each wave holds four primary care and two specialty clinics on its date",
              f"{len(clinics)} clinics, {len(clinicians)} clinicians; waves of {sorted(set(per_wave.values()))} clinics by type",
              f"24 clinics, {S['clinicians']} clinicians; 4 primary care and 2 specialty in each wave", ok34)
    if not ok34:
        return None

    # ---- S35 the panel's frame
    n = len(clinicians)
    rows_ok = (len(p) == n * spec.SCRIBE_WEEKS
               and (p["clinician_id"].to_numpy() == np.repeat(clinicians["clinician_id"].to_numpy(), spec.SCRIBE_WEEKS)).all()
               and (p["week_index_n"].to_numpy() == np.tile(np.arange(1, spec.SCRIBE_WEEKS + 1), n)).all())
    if not rows_ok:
        rep.check("S35", "construction: the panel has one row for every clinician and week", f"{len(p):,} rows",
                  f"{n * spec.SCRIBE_WEEKS:,} rows in order", False)
        return None
    live = p["k"].to_numpy() >= 0
    has = p["visits_n"].to_numpy() > 0
    share_text = np.array([format_float(s / v, 3) if v else "" for s, v in zip(p["scribe_visits_n"], p["visits_n"])],
                          dtype=object)
    holiday = np.array([1 if w in S["holiday_weeks"] else 0 for w in p["week_start"]])
    since = np.array([str(k) if k >= 0 else "" for k in p["k"]], dtype=object)
    bad = (int((p["week_start"].to_numpy() != np.array(week_iso, dtype=object)[p["week_index_n"].to_numpy() - 1]).sum())
           + int((p["clinic_id"].to_numpy() != np.array([d["clinic_of"][c] for c in p["clinician_id"]], dtype=object)).sum())
           + int((p["clinic_live_n"].to_numpy() != live.astype(int)).sum())
           + int((p["weeks_since_go_live"].to_numpy() != since).sum())
           + int((p["holiday_week_n"].to_numpy() != holiday).sum())
           + int((p["scribe_visits_n"].to_numpy() > p["visits_n"].to_numpy()).sum())
           + int((p["scribe_visits_n"].to_numpy()[~live] != 0).sum())
           + int((p["scribe_share"].to_numpy() != share_text).sum())
           + int(((p["doc_minutes_per_visit"] == "").to_numpy() != ~has).sum())
           + int(((p["same_day_close_share"] == "").to_numpy() != ~has).sum()))
    rep.check("S35", "construction: the panel has one row for every clinician and week; week dates, live flags, weeks since go-live, holiday weeks and scribe shares all follow from the rollout and the counts",
              f"{len(p):,} rows, {int(live.sum()):,} of them live, {int((~has).sum())} with no visits; {bad} rows out of line",
              f"{n * spec.SCRIBE_WEEKS:,} rows; 0 out of line", bad == 0)

    # ---- S36 the notes frame
    week0 = dt.date.fromisoformat(week_iso[0]).toordinal()
    day = ordinal(f["visit_date"])
    wstart = ordinal(f["week_start"])
    closed = {dt.date.fromisoformat(x).toordinal() for x in S["closed_dates"]}
    v24_day = dt.date.fromisoformat(spec.DATES["scribe_v24"]).toordinal()
    vm = S["notes"]["visit_minutes"]
    bad = (int((f["note_id"].to_numpy() != np.array([f"N{i:07d}" for i in range(1, len(f) + 1)], dtype=object)).sum())
           + int((np.diff(day) < 0).sum())
           + int((((wstart - week0) % 7) != 0).sum()) + int(((day - wstart < 0) | (day - wstart > 4)).sum())
           + int(np.isin(day, list(closed)).sum())
           + int((f["clinic_id"].to_numpy() != np.array([d["clinic_of"][c] for c in f["clinician_id"]], dtype=object)).sum())
           + int((f["specialty"].to_numpy() != np.array([spec_of[c] for c in f["clinic_id"]], dtype=object)).sum())
           + int((f["v24"].to_numpy() != (wstart >= v24_day)).sum())
           + int(((f["interp"].to_numpy() == 1) & (f["speakers"].to_numpy() < 3)).sum())
           + int(((f["minutes"].to_numpy() < vm["low"]) | (f["minutes"].to_numpy() > vm["high"])).sum()))
    rep.check("S36", "construction: note IDs run in date order; every visit falls on an open weekday of its week; clinic, specialty and scribe version follow from the clinician and the date; an interpreter makes at least three speakers",
              f"{len(f):,} notes; {bad} out of line", "0 out of line", bad == 0)

    # ---- S37 truth rows
    e = d["errors"]
    counts4 = np.stack([_ints(e[c]) for c in ("n_omission", "n_hallucination", "n_misattribution", "n_wrong_value")], axis=1)
    total = counts4.sum(axis=1)
    same_ids = len(e) == len(f) and (e["note_id"].to_numpy() == f["note_id"].to_numpy()).all()
    sev_ok = bool((((e["worst_severity"] == "none").to_numpy()) == (total == 0)).all())
    eff = _floats(d["effects"]["error_effect_logit"])
    mean = det_mean(eff)
    sd = float(np.sqrt(det_mean((eff - mean) * (eff - mean))))
    eff_ok = abs(mean) < 1e-5 and abs(sd - S["errors"]["clinic_logit_sd"]) < 1e-5
    rep.check("S37", "construction: the truth table has one row for every note in the frame; a note's worst severity is none exactly when it has no error; the 24 clinic effects have mean 0 and the design SD",
              f"{len(e):,} rows; clinic effects mean {format_float(mean, 4)}, SD {format_float(sd, 4)}",
              f"{len(f):,} rows; mean 0.0000, SD {S['errors']['clinic_logit_sd']:.4f}", same_ids and sev_ok and eff_ok)
    if not same_ids:
        return None
    d["counts4"], d["total"] = counts4, total
    d["has4"] = counts4 > 0

    # ---- S38 the hidden error model reproduces its targets
    with open(os.path.join(root, "hidden/scribe/error_model_truth.json"), encoding="utf-8") as fh:
        model = json.load(fh)
    d["model"] = model
    clinic_effect = dict(zip(d["effects"]["clinic_id"], eff))
    base = np.array([clinic_effect[c] for c in f["clinic_id"]])
    lor = model["log_odds_ratios"]
    E = S["errors"]
    drivers = {
        "omission": lor["omission_interpreter"] * f["interp"].to_numpy()
                    + lor["omission_long_visit"] * (f["minutes"].to_numpy() > E["long_visit_minutes"]),
        "hallucination": lor["hallucination_v24"] * f["v24"].to_numpy(),
        "misattribution": lor["misattribution_three_speakers"] * (f["speakers"].to_numpy() >= E["many_speakers"]),
        "wrong_value": np.zeros(len(f)),
    }
    v23 = ~f["v24"].to_numpy()
    parts, ok38 = [], True
    d["prob"] = {}
    for name in spec.ERROR_TYPES:
        prob = det_plogis(model["intercepts"][name] + base + drivers[name])
        d["prob"][name] = prob
        got = det_mean(prob[v23])
        parts.append(f"{name} {got:.6f}")
        ok38 = ok38 and abs(got - E["target_v23"][name]) < 1e-5
    q = model["severity"]["major_per_error"]
    major = det_mean(1.0 - det_exp(total[v23] * float(det_log(np.array([1.0 - q]))[0])))
    ok38 = ok38 and abs(major - E["major_target_v23"]) < 1e-5 and all(
        abs(float(det_exp(np.array([lor[k]]))[0]) - v) < 1e-5 for k, v in E["odds_ratio"].items())
    rep.check("S38", "expected: the hidden error model, applied to the frame, gives the solved rates on version 2.3 notes, and its odds ratios are the planted ones",
              "; ".join(parts) + f"; a major error {major:.6f}",
              "; ".join(f"{k} {v:.6f}" for k, v in E["target_v23"].items()) + f"; a major error {E['major_target_v23']:.6f}",
              ok38)

    # ---- S39 the audit sample
    s = d["sample"]
    group_of = {x: g for g, members in spec.SPECIALTY_GROUPS.items() for x in members}
    stratum_all = np.array([spec.audit_stratum_code(group_of[sp], i, "2.4" if v else "2.3")
                            for sp, i, v in zip(f["specialty"], f["interp"], f["v24"])], dtype=object)
    d["stratum_all"] = stratum_all
    sizes = pd.Series(stratum_all).value_counts()
    pos = pd.Series(np.arange(len(f)), index=f["note_id"])
    found = s["note_id"].isin(pos.index).all() and s["note_id"].is_unique
    ok39 = bool(found)
    if found:
        at = pos.reindex(s["note_id"]).to_numpy()
        d["sample_pos"] = at
        drawn = s["stratum"].value_counts()
        want = {spec.audit_stratum_code(*key): n for key, n in S["audit"]["allocation"].items()}
        prob_text = np.array([format_float(int(a) / int(b), 6) for a, b in zip(s["stratum_sampled"], s["stratum_size"])],
                             dtype=object)
        ok39 = ((s["stratum"].to_numpy() == stratum_all[at]).all()
                and (_ints(s["stratum_size"]) == sizes.reindex(s["stratum"]).to_numpy()).all()
                and (_ints(s["stratum_sampled"]) == drawn.reindex(s["stratum"]).to_numpy()).all()
                and {k: int(v) for k, v in drawn.items()} == want
                and (s["incl_prob"].to_numpy() == prob_text).all())
    smallest = int(sizes.min())
    rep.check("S39", "construction: each sampled note's stratum can be rebuilt from the frame; stratum sizes, the numbers drawn and the inclusion probabilities agree with the frame and with the spec's allocation",
              f"{len(s):,} notes in {s['stratum'].nunique()} strata; smallest stratum holds {smallest:,} notes",
              f"{spec.AUDIT['sample_size']:,} notes in 12 strata", bool(ok39) and len(s) == spec.AUDIT["sample_size"])
    if not ok39:
        return None

    # ---- S40 the ratings
    r = d["ratings"]
    rr = _ints(r["rating_round"])
    flag_cols = list(spec.ERROR_TYPES)
    fields = flag_cols + ["severity"]
    one = r[rr == 1].set_index("note_id")
    two = r[rr == 2].set_index("note_id")
    three = r[rr == 3].set_index("note_id")
    ids = s["note_id"].to_numpy()
    ok40 = (list(one.index) == list(ids) and list(two.index) == list(ids)
            and set(three.index) <= set(ids) and three.index.is_unique)
    if ok40:
        differ = (one[fields].to_numpy() != two[fields].to_numpy()).any(axis=1)
        raters = [f"R{i:02d}" for i in range(1, spec.AUDIT["raters"] + 1)]
        none_ok = bool((((r["severity"] == "none").to_numpy()) == ((r[flag_cols] == "1").to_numpy().sum(axis=1) == 0)).all())
        ok40 = (one["rater_id"].isin(raters).all() and two["rater_id"].isin(raters).all()
                and (one["rater_id"].to_numpy() != two["rater_id"].to_numpy()).all()
                and set(three.index) == set(ids[differ])
                and (three["rater_id"] == f"R{spec.AUDIT['raters'] + 1:02d}").all() and none_ok)
        d["one"], d["two"], d["three"], d["differ"] = one, two, three, differ
    rep.check("S40", "construction: every sampled note has two ratings from two different raters; the senior reviewer rates a note exactly when the two differ in any field; a rating's severity is none exactly when it has no flag",
              f"{len(one):,} first and {len(two):,} second ratings; {len(three):,} adjudicated", "consistent", bool(ok40))
    if not ok40:
        return None

    # ---- S41 the survey
    sv = d["survey"]
    wave_of = {c: d["wave_of_clinic"][d["clinic_of"][c]] for c in clinicians["clinician_id"]}
    months = S["survey"]["post_wave_months"]
    expected_rows = []
    for c in clinicians["clinician_id"]:
        expected_rows.append((c, "baseline", spec.SURVEY_MONTHS["baseline"]))
        expected_rows.append((c, "final", spec.SURVEY_MONTHS["final"]))
        if wave_of[c] <= len(months):
            expected_rows.append((c, "post_wave", months[wave_of[c] - 1]))
    got_rows = sorted(tuple(x) for x in sv[["clinician_id", "survey_wave", "survey_month"]].values.tolist())
    items = sv[[f"item{j}" for j in range(1, 6)]]
    answered = (items != "").to_numpy()
    resp = (sv["responded"] == "1").to_numpy()
    ok41 = got_rows == sorted(expected_rows) and bool((answered == resp[:, None]).all())
    rep.check("S41", "construction: every clinician has a baseline and a final survey row, and a post-wave row unless the clinic is in wave 4; items are filled exactly when the clinician responded",
              f"{len(sv)} rows, {int(resp.sum())} responses", f"{len(expected_rows)} rows", ok41)

    # ---- S42 costs and wages
    wages = d["wages"]
    E2 = spec.ECONOMICS
    loaded_ok = all(format_float(np.floor(float(w) * E2["loading"] * 100.0 + 0.5) / 100.0, 2) == l
                    for w, l in zip(wages["hourly_wage"], wages["loaded_hourly_cost"]))
    roles = set(wages["role"])
    costs = d["costs"]
    priced = (costs["unit_cost"] != "").to_numpy()
    by_role = (costs["wage_role"] != "").to_numpy()
    ok42 = (loaded_ok and set(clinicians["role"]) <= roles and {"rn", "hospitalist"} <= roles
            and bool((priced != by_role).all())
            and set(costs["wage_role"][by_role]) <= roles | {"clinician"}
            and len(costs) == len(E2["costs"]) and len(wages) == len(E2["wages"]))
    rep.check("S42", "construction: each loaded cost is the wage times the loading; every clinician role and both rapid-response roles have a wage; each cost line has a price or a wage role, never both",
              f"{len(wages)} roles, {len(costs)} cost lines, loading {E2['loading']}", "consistent", ok42)

    # ---- S43 the paired no-scribe values
    w = d["wtruth"]
    ct = d["ctruth"]
    same_rows = (len(w) == len(p) and (w["clinician_id"].to_numpy() == p["clinician_id"].to_numpy()).all()
                 and (w["week_start"].to_numpy() == p["week_start"].to_numpy()).all()
                 and list(ct["clinician_id"]) == list(clinicians["clinician_id"]))
    if not same_rows:
        rep.check("S43", "construction: the weekly truth table matches the panel row for row", f"{len(w):,} rows",
                  f"{len(p):,} rows", False)
        return None
    v0 = _ints(w["visits_no_scribe"])
    doc0 = _floats(w["doc_minutes_no_scribe"])
    ah0 = _floats(w["after_hours_no_scribe"])
    share = _floats(w["expected_scribe_share"])
    learning = _floats(w["learning"])
    saving = _floats(w["saving_per_scribe_visit"])
    kk = p["k"].to_numpy()
    P = S["panel"]
    want_learning = np.where(kk < 0, 0.0, np.array(list(P["learning"]) + [1.0] * spec.SCRIBE_WEEKS)[np.maximum(kk, 0)])
    ramp = np.array(list(S["adoption"]["ramp"]) + [1.0] * spec.SCRIBE_WEEKS)[np.maximum(kk, 0)]
    steady = dict(zip(ct["clinician_id"], _floats(ct["steady_share"])))
    effect = dict(zip(ct["clinician_id"], _floats(ct["individual_effect_minutes"])))
    steady_row = np.array([steady[c] for c in p["clinician_id"]])
    effect_row = np.array([effect[c] for c in p["clinician_id"]])
    realised = np.where(has, p["scribe_visits_n"].to_numpy() / np.where(has, p["visits_n"].to_numpy(), 1), 0.0)
    floor_rows = has & (p["doc"].to_numpy() <= P["doc_floor"] + 1e-9)
    gap = np.abs((doc0 - p["doc"].to_numpy()) - saving * realised)
    doc_bad = int((has & ~floor_rows & ~(gap <= 0.1 + 1e-9)).sum())
    pre = ~live
    bad = (int((v0 > p["visits_n"].to_numpy()).sum()) + int((v0[pre] != p["visits_n"].to_numpy()[pre]).sum())
           + int((w["doc_minutes_no_scribe"].to_numpy()[pre] != p["doc_minutes_per_visit"].to_numpy()[pre]).sum())
           + int((w["after_hours_no_scribe"].to_numpy()[pre] != p["after_hours_minutes"].to_numpy()[pre]).sum())
           + int((np.abs(learning - want_learning) > 1e-9).sum())
           + int((np.abs(share - np.where(live, np.floor(steady_row * ramp * 1e4 + 0.5) / 1e4, 0.0)) > 1e-9).sum())
           + int((np.abs(saving - np.floor(effect_row * want_learning * 100.0 + 0.5) / 100.0) > 1e-9).sum())
           + int((ah0 + 0.5 < p["ah"].to_numpy()).sum()) + doc_bad)
    rep.check("S43", "construction: without the scribe a clinician-week never has more visits or fewer after-hours minutes; before go-live the two worlds are identical; the learning share, expected scribe share and saving follow from the hidden parameters; the documentation minutes differ by the saving times the scribe share",
              f"{bad} rows out of line; {int(floor_rows.sum())} rows sit at the floor of {P['doc_floor']:.1f} minute, where the saving is cut short",
              "0 out of line", bad == 0)
    d.update({"v0": v0, "doc0": doc0, "ah0": ah0, "share": share, "learning": learning, "saving": saving,
              "realised": realised, "live": live, "has": has})

    # ---- S44 adoption types
    kinds = ct["adoption_type"].value_counts()
    ever = p.groupby("clinician_id", sort=False)["scribe_visits_n"].sum().reindex(ct["clinician_id"]).to_numpy()
    never = (ct["adoption_type"] == "never").to_numpy()
    ad = S["adoption"]
    ok44 = (int(kinds.get("never", 0)) == ad["never"] and int(kinds.get("partial", 0)) == ad["partial"]
            and bool(((ever == 0) == never).all()) and bool((_floats(ct["steady_share"])[never] == 0).all()))
    rep.check("S44", "construction: adoption types have the design's counts, and the clinicians with no scribe visit in the data are exactly the hidden never-adopters",
              f"{int(kinds.get('adopter', 0))} adopters, {int(kinds.get('partial', 0))} partial, {int(kinds.get('never', 0))} never",
              f"{len(ct) - ad['never'] - ad['partial']} adopters, {ad['partial']} partial, {ad['never']} never", ok44)
    return d


def check_m5_targets(rep, d, target, values):
    S = spec.SCRIBE
    f, p, ct = d["frame"], d["panel"], d["ctruth"]
    has4 = d["has4"]
    v23 = ~f["v24"].to_numpy()
    n23, n24 = int(v23.sum()), int((~v23).sum())
    names = list(spec.ERROR_TYPES)

    def rate(mask_num, mask_den):
        return float((mask_num & mask_den).sum()) / int(mask_den.sum())

    # ---------------------------------------------------------------- audit
    rep.section("Scribe audit",
                "The frame, the true errors, the committee's sample and the ratings. T57 is judged against "
                "variance V7, whose range was set after the value was seen (`DESIGN.md` decision A41); the "
                "brief's range is printed beside it. Rates under version 2.3 are over the "
                f"{n23:,} notes drafted before {spec.DATES['scribe_v24']}.")
    target("T50", len(f), f"{len(f):,} ({n23:,} under version 2.3, {n24:,} under version 2.4)")
    rates = {name: rate(has4[:, j], v23) for j, name in enumerate(names)}
    target("T51", rates["omission"], f"{rates['omission']:.4f}", 2)
    target("T52", rates["hallucination"], f"{rates['hallucination']:.4f}; under version 2.4 {rate(has4[:, 1], ~v23):.4f}", 2)
    target("T53", rates["misattribution"], f"{rates['misattribution']:.4f}", 2)
    major = (d["errors"]["worst_severity"] == "major").to_numpy()
    any_error = d["total"] > 0
    t54 = rate(major, v23)
    target("T54", t54, f"{t54:.4f} under version 2.3; {rate(major, np.ones(len(f), dtype=bool)):.4f} of all notes; "
                       f"any error {rate(any_error, np.ones(len(f), dtype=bool)):.4f} of all notes", 3)
    interp = f["interp"].to_numpy() == 1
    om = has4[:, 0]
    t55 = rate(om, interp) / rate(om, ~interp)
    target("T55", t55, f"{t55:.3f} ({rate(om, interp):.4f} against {rate(om, ~interp):.4f}; "
                       f"{int(interp.sum()):,} interpreter visits, {float(interp.sum()) / len(f):.4f} of notes)", 1)

    def odds_ratio(event, group):
        a, b = int((event & group).sum()), int((~event & group).sum())
        c, e = int((event & ~group).sum()), int((~event & ~group).sum())
        return (a * e) / (b * c)
    E = S["errors"]
    crude = (odds_ratio(om, interp), odds_ratio(om, f["minutes"].to_numpy() > E["long_visit_minutes"]),
             odds_ratio(has4[:, 2], f["speakers"].to_numpy() >= E["many_speakers"]),
             odds_ratio(has4[:, 1], ~v23))
    planted = E["odds_ratio"]
    near = (abs(crude[0] / planted["omission_interpreter"] - 1) < 0.15
            and abs(crude[1] / planted["omission_long_visit"] - 1) < 0.15
            and abs(crude[2] / planted["misattribution_three_speakers"] - 1) < 0.15
            and abs(crude[3] / planted["hallucination_v24"] - 1) < 0.15)
    rep.check("T55b", "realised: crude odds ratios in the whole frame sit near the planted ones (they are not adjusted for clinic or for each other)",
              f"omission with an interpreter {crude[0]:.2f}; omission in a visit over {E['long_visit_minutes']} minutes {crude[1]:.2f}; "
              f"misattribution with three or more speakers {crude[2]:.2f}; hallucination under version 2.4 {crude[3]:.2f}",
              f"within 15% of {planted['omission_interpreter']}, {planted['omission_long_visit']}, "
              f"{planted['misattribution_three_speakers']} and {planted['hallucination_v24']}", near)

    s, one, two, three = d["sample"], d["one"], d["two"], d["three"]
    target("T56", len(s), f"{len(s):,} notes; {len(one) + len(two):,} independent ratings; {len(three):,} notes adjudicated "
                          f"({float(len(three)) / len(s):.3f})")

    # T57 kappa for the hallucination flag, first against second rater
    a1 = (one["hallucination"] == "1").to_numpy()
    a2 = (two["hallucination"] == "1").to_numpy()
    k57 = kappa_from_table(int((a1 & a2).sum()), int((a1 & ~a2).sum()), int((~a1 & a2).sum()), int((~a1 & ~a2).sum()))
    raters = d["raters"].set_index("rater_id")
    at = d["sample_pos"]
    truth_h = has4[at, 1]
    sens = _floats(raters["sens_hallucination"].reindex(one["rater_id"])), _floats(raters["sens_hallucination"].reindex(two["rater_id"]))
    fpr = _floats(raters["false_positive_rate"].reindex(one["rater_id"])), _floats(raters["false_positive_rate"].reindex(two["rater_id"]))
    p1 = np.where(truth_h, sens[0], fpr[0])
    p2 = np.where(truth_h, sens[1], fpr[1])
    m = len(at)
    both, neither = det_sum(p1 * p2), det_sum((1.0 - p1) * (1.0 - p2))
    k_exp = kappa_from_table(both, det_sum(p1) - both, det_sum(p2) - both, neither)
    others = []
    for name in ("omission", "misattribution", "wrong_value"):
        b1, b2 = (one[name] == "1").to_numpy(), (two[name] == "1").to_numpy()
        others.append(f"{name} {kappa_from_table(int((b1 & b2).sum()), int((b1 & ~b2).sum()), int((~b1 & b2).sum()), int((~b1 & ~b2).sum())):.3f}")
    target("T57", k57, f"{k57:.3f} on {m:,} notes, {int(truth_h.sum())} of which truly have a hallucination; expected from the hidden rater "
                       f"parameters {k_exp:.3f}; other flags: {', '.join(others)}", 2)

    # T58 design-weighted omission prevalence from the adjudicated audit
    adjudicated = (one["omission"] == "1").to_numpy().copy()
    index_of = {note: i for i, note in enumerate(one.index)}
    for note, value in zip(three.index, three["omission"]):
        adjudicated[index_of[note]] = value == "1"
    size = _ints(s["stratum_size"]).astype(np.float64)
    drawn = _ints(s["stratum_sampled"]).astype(np.float64)
    weight = size / drawn
    total_weight = det_sum(weight)
    estimate = det_sum(weight * adjudicated) / total_weight
    truth_all = float(om.sum()) / len(f)
    truth_sample = det_sum(weight * has4[at, 0]) / total_weight
    raw = float(adjudicated.sum()) / m
    t58 = abs(estimate - truth_all)
    target("T58", t58, f"{t58:.4f}: estimate {estimate:.4f} against a true {truth_all:.4f} in the frame. Of the gap, "
                       f"{truth_sample - truth_all:+.4f} is the draw of the sample (true labels, same weights: {truth_sample:.4f}) and "
                       f"{estimate - truth_sample:+.4f} is rating error. Unweighted rate in the sample: {raw:.4f}", 2)
    values.update({"scribe_errors": f"omission {100 * rates['omission']:.1f}%, hallucination {100 * rates['hallucination']:.1f}% of version 2.3 notes; "
                                    f"no major error in {100 * (1 - rate(major, np.ones(len(f), dtype=bool))):.1f}% of all notes"})

    # T59 the count identity
    key = f["clinician_id"] + "|" + f["week_start"]
    per = key.value_counts()
    panel_key = (p["clinician_id"] + "|" + p["week_start"]).to_numpy()
    notes_n = per.reindex(panel_key).fillna(0).to_numpy().astype(np.int64)
    mismatched = int((notes_n != p["scribe_visits_n"].to_numpy()).sum())
    stray = int((~key.isin(set(panel_key))).sum())
    cid, _m, quantity, _lo, _hi, basis, _n = next(t for t in spec.TARGETS if t[0] == "T59")
    rep.check("T59", f"{basis}: {quantity}", f"{mismatched} of {len(p):,} clinician-weeks differ; {stray} notes outside the panel",
              "0 differ; 0 outside", mismatched == 0 and stray == 0)

    # T60 rater parameters
    A = S["audit"]
    rt = d["raters"]
    sens_all = np.stack([_floats(rt[c]) for c in ("sens_omission", "sens_hallucination", "sens_misattribution", "sens_wrong_value")], axis=1)
    fp = _floats(rt["false_positive_rate"])
    nr = spec.AUDIT["raters"]
    lenient = [i for i in range(nr) if sens_all[i].max() < A["rater_sensitivity"][0]]
    usual = [i for i in range(nr) if i not in lenient]
    ok60 = (len(rt) == nr + 1 and len(lenient) == 1
            and all(A["rater_sensitivity"][0] <= v <= A["rater_sensitivity"][1] for i in usual for v in sens_all[i])
            and all(A["lenient_sensitivity"][0] <= v <= A["lenient_sensitivity"][1] for v in sens_all[lenient[0]])
            and all(A["rater_false_positive"][0] <= v <= A["rater_false_positive"][1] for v in fp[:nr])
            and all(A["senior_sensitivity"][0] <= v <= A["senior_sensitivity"][1] for v in sens_all[nr])
            and A["senior_false_positive"][0] <= fp[nr] <= A["senior_false_positive"][1]
            and d["model"]["lenient_rater"] == rt["rater_id"].iloc[lenient[0]] if len(lenient) == 1 else False)
    cid, _m, quantity, _lo, _hi, basis, _n = next(t for t in spec.TARGETS if t[0] == "T60")
    if len(lenient) == 1:
        shown = (f"seven raters {min(sens_all[i].min() for i in usual):.4f} to {max(sens_all[i].max() for i in usual):.4f}; "
                 f"the lenient rater ({rt['rater_id'].iloc[lenient[0]]}) {sens_all[lenient[0]].min():.4f} to {sens_all[lenient[0]].max():.4f}; "
                 f"false-positive rates {fp[:nr].min():.4f} to {fp[:nr].max():.4f}; senior reviewer "
                 f"{sens_all[nr].min():.4f} to {sens_all[nr].max():.4f} and {fp[nr]:.4f}")
    else:
        shown = f"{len(lenient)} lenient raters"
    rep.check("T60", f"{basis}: {quantity}", shown,
              f"sensitivity {A['rater_sensitivity'][0]} to {A['rater_sensitivity'][1]}, one lenient rater near 0.60; false-positive rate "
              f"{A['rater_false_positive'][0]} to {A['rater_false_positive'][1]}; senior {A['senior_sensitivity'][0]} to "
              f"{A['senior_sensitivity'][1]} and at most 0.01", bool(ok60))

    # ---------------------------------------------------------------- value
    rep.section("Scribe value",
                "The clinician-week panel, adoption, the survey and the true effects. Where a row compares the world "
                "with the scribe to the world without it, both come from the same random draws "
                "(`hidden/economics/clinician_weeks_truth.csv`). Steady state means the clinic's eighth live week onward.")
    n = len(ct)
    target("T70", n, f"{n} clinicians, {len(p):,} clinician-weeks, mean {det_mean(p['visits_n'].to_numpy()):.1f} visits a week")
    k = p["k"].to_numpy()
    P = S["panel"]
    steady_from = P["steady_from_live_week"] - 1                    # weeks since go-live
    visits, sv = p["visits_n"].to_numpy(), p["scribe_visits_n"].to_numpy()
    window = (k >= steady_from) & (k <= steady_from + 3)
    g = p[window].groupby("clinician_id", sort=False)[["scribe_visits_n", "visits_n"]].sum()
    t71 = float((2 * g["scribe_visits_n"] >= g["visits_n"]).sum()) / n
    target("T71", t71, f"{t71:.4f} ({int((2 * g['scribe_visits_n'] >= g['visits_n']).sum())} of {n}), by the share of visits in live weeks 8 to 11", 2)
    ever = p.groupby("clinician_id", sort=False)["scribe_visits_n"].sum()
    t72 = float((ever == 0).sum()) / n
    target("T72", t72, f"{t72:.4f} ({int((ever == 0).sum())} of {n} have no scribe visit in the data)", 2)
    steady = k >= steady_from
    saving = d["saving"]
    t73 = det_sum(saving[steady] * sv[steady]) / int(sv[steady].sum())
    t73_all = det_sum(saving * sv) / int(sv.sum())
    effects = _floats(ct["individual_effect_minutes"])
    target("T73", t73, f"{t73:.3f} over {int(sv[steady].sum()):,} scribe visits; {t73_all:.3f} over all {int(sv.sum()):,} scribe visits, "
                       f"learning weeks included; mean of the {n} clinicians' own values {det_mean(effects):.3f}", 1)

    # T74 naive pre-post
    has = d["has"]
    doc = p["doc"].to_numpy()
    cl = p["clinician_id"].to_numpy()
    frame = pd.DataFrame({"c": cl, "doc": doc, "pre": (k < 0) & has, "post": steady & has, "sv": sv, "v": visits})
    pre_mean, post_mean = [], []
    for _c, grp in frame.groupby("c", sort=False):
        pre_mean.append(det_mean(grp["doc"].to_numpy()[grp["pre"].to_numpy()]))
        post_mean.append(det_mean(grp["doc"].to_numpy()[grp["post"].to_numpy()]))
    post_share = float(sv[steady].sum()) / int(visits[steady].sum())
    naive = (det_mean(np.array(pre_mean)) - det_mean(np.array(post_mean))) / post_share
    target("T74", naive - t73, f"{naive - t73:.3f}: naive {naive:.3f} against a true {t73:.3f}. Mean minutes per visit fell from "
                               f"{det_mean(np.array(pre_mean)):.2f} before go-live to {det_mean(np.array(post_mean)):.2f} at steady state, "
                               f"with the scribe on {post_share:.3f} of visits", 1)
    # P23: users against non-users
    kinds = dict(zip(ct["clinician_id"], ct["adoption_type"]))
    adopter_row = np.array([kinds[c] == "adopter" for c in cl])
    never_row = np.array([kinds[c] == "never" for c in cl])
    rows_a, rows_n = steady & has & adopter_row, steady & has & never_row
    doc_a, doc_n = det_mean(doc[rows_a]), det_mean(doc[rows_n])
    share_a = float(sv[rows_a].sum()) / int(visits[rows_a].sum())
    true_a = det_mean((d["doc0"] - doc)[rows_a])
    base = _floats(ct["baseline_doc_minutes"])
    is_a, is_n = (ct["adoption_type"] == "adopter").to_numpy(), (ct["adoption_type"] == "never").to_numpy()
    rep.check("T74b", "realised: comparing users with non-users understates the saving, because users documented more slowly to begin with (P23)",
              f"at steady state never-adopters average {doc_n:.2f} minutes per visit and adopters {doc_a:.2f}, a difference of {doc_n - doc_a:+.2f}; "
              f"the scribe truly cut the adopters' average by {true_a:.2f} (scribe on {share_a:.3f} of their visits). True baselines: "
              f"adopters {det_mean(base[is_a]):.2f}, never-adopters {det_mean(base[is_n]):.2f}",
              "difference below the true cut", (doc_n - doc_a) < true_a)

    # T75 after-hours and visits, on the paired values
    dose = d["realised"] * d["learning"]
    ah, ah0 = p["ah"].to_numpy(), d["ah0"]
    t75 = det_sum(ah - ah0) / det_sum(ah0 * dose)
    rel_a = det_sum((ah - ah0)[steady & adopter_row]) / det_sum(ah0[steady & adopter_row])
    target("T75", t75, f"{t75:.4f} for each unit of use (share of visits with the scribe, times the learning share); "
                       f"adopters at steady state: {rel_a:+.4f} of their after-hours minutes", 2)
    t75b = float((visits - d["v0"]).sum()) / det_sum(d["share"] * d["learning"])
    target("T75b", t75b, f"{t75b:.3f} for each unit of use; {int((visits - d['v0']).sum()):,} visits added in all", 1)

    # T76 survey response
    survey = d["survey"]
    resp = (survey["responded"] == "1").to_numpy()
    t76 = float(resp.sum()) / len(survey)
    latent_of = {"baseline": dict(zip(ct["clinician_id"], ct["latent_wellbeing_baseline"])),
                 "post_wave": dict(zip(ct["clinician_id"], ct["latent_wellbeing_post_wave"])),
                 "final": dict(zip(ct["clinician_id"], ct["latent_wellbeing_final"]))}
    latent = np.array([float(latent_of[wv][c]) for c, wv in zip(survey["clinician_id"], survey["survey_wave"])])
    cut = median(latent)
    low, high = latent < cut, latent >= cut
    r_low, r_high = float(resp[low].sum()) / int(low.sum()), float(resp[high].sum()) / int(high.sum())
    item_cols = [f"item{j}" for j in range(1, 6)]
    scores = survey.loc[resp, item_cols].astype(np.int64).to_numpy()
    mean_resp = det_mean(latent[resp])
    target("T76", t76, f"{t76:.4f} ({int(resp.sum())} of {len(survey)}); {r_low:.3f} in the lower half of true wellbeing and {r_high:.3f} in the upper half; "
                       f"respondents' mean true wellbeing {mean_resp:+.3f} against {det_mean(latent):+.3f} for everyone asked; "
                       f"mean item score {det_mean(scores.astype(np.float64)):.2f}", 2)
    rep.check("T76b", "realised: clinicians with lower true wellbeing respond less often (P24)",
              f"{r_low:.3f} against {r_high:.3f}", "lower half below upper half", r_low < r_high)
    eff = _floats(ct["wellbeing_effect"])
    t77 = det_mean(eff[is_a])
    target("T77", t77, f"{t77:.4f} among {int(is_a.sum())} adopters; partial users {det_mean(eff[(ct['adoption_type'] == 'partial').to_numpy()]):.4f}; never-adopters 0", 2)

    per_day = t73 * float(sv[rows_a].sum()) / (5.0 * int(rows_a.sum()))
    values["scribe_time"] = (f"{per_day:.1f} minutes a clinic day for an adopter at steady state "
                             f"({t73:.2f} minutes on each of {float(sv[rows_a].sum()) / (5.0 * int(rows_a.sum())):.1f} scribe visits a day)")


def check_files(rep, root, built, built_json):
    present = []
    for sub in ("data", "hidden"):
        for folder, _dirs, files in os.walk(os.path.join(root, sub)):
            for name in files:
                present.append(os.path.relpath(os.path.join(folder, name), root).replace(os.sep, "/"))
    expected = sorted(list(built) + built_json)
    missing = sorted(set(expected) - set(present))
    extra = sorted(set(present) - set(expected))
    rep.check("S01", "construction: files under data/ and hidden/ are exactly those the spec lists for the built milestones",
              f"{len(present)} files; {len(missing)} missing, {len(extra)} unexpected",
              f"{len(expected)} files; 0 missing, 0 unexpected", not missing and not extra)
    return not missing


def check_schema(rep, tables, built):
    bad_headers, bad_cells, cells = [], 0, 0
    for path, meta in built.items():
        df = tables[path]
        names = [c[0] for c in meta["columns"]]
        if list(df.columns) != names:
            bad_headers.append(path)
            continue
        for name, col_type, decimals, value_range, meaning in meta["columns"]:
            col = df[name]
            cells += len(col)
            empty = col == ""
            if "empty" not in meaning:
                bad_cells += int(empty.sum())
            filled = col[~empty]
            if col_type == "float":
                pattern = r"-?\d+" + (rf"\.\d{{{decimals}}}" if decimals else "")
            elif col_type == "code" and "|" in value_range:
                pattern = "|".join(re.escape(c) for c in value_range.split("|"))
            else:
                pattern = PATTERNS.get(col_type)
            if pattern is not None:
                bad_cells += int((~filled.str.fullmatch(pattern)).sum())
    rep.check("S02", "construction: every CSV header equals the spec's column list",
              f"{len(built) - len(bad_headers)} of {len(built)} files", f"{len(built)} of {len(built)} files",
              not bad_headers)
    rep.check("S03", "construction: every cell has its declared type, fixed decimals and code list; empty only where the dictionary allows",
              f"{bad_cells:,} bad cells of {cells:,}", "0 bad cells", bad_cells == 0)
    return not bad_headers


def check_dictionary(rep, root, built):
    columns = sum(len(meta["columns"]) for meta in built.values())
    rows = dictionary.rows()
    ok = len(rows) == columns and len({(r[0], r[1]) for r in rows}) == columns
    on_disk = os.path.join(root, "DICTIONARY.csv")
    state = "not present here"
    if os.path.exists(on_disk):
        with open(on_disk, encoding="utf-8", newline="") as fh:
            same = fh.read() == dictionary.text()
        state = "identical to the spec" if same else "DIFFERS from the spec"
        ok = ok and same
    rep.check("S04", "construction: the dictionary has one row for every file and column",
              f"{len(rows)} rows for {columns} columns; DICTIONARY.csv {state}",
              f"{columns} rows; identical if present", ok)


# ------------------------------------------------------------------ main body
def run(root):
    rep = Report()
    built = dictionary.built_files()
    built_json = dictionary.built_json_files()

    rep.section("Structure")
    if not check_files(rep, root, built, built_json):
        return rep
    tables = {path: read(root, path) for path in built}
    if not check_schema(rep, tables, built):
        return rep
    check_dictionary(rep, root, built)

    # ---- assemble the inpatient tables
    pub = pd.concat([tables[f"data/inpatient/admissions_{y}.csv"] for y in spec.PUBLISHED_YEARS],
                    ignore_index=True)
    burn = tables["hidden/inpatient/burnin_admissions_2021.csv"]
    truth = pd.concat([tables[f"hidden/inpatient/admissions_truth_{y}.csv"] for y in spec.SIMULATED_YEARS],
                      ignore_index=True)
    persons = tables["data/inpatient/persons.csv"]
    persons_truth = tables["hidden/inpatient/persons_truth.csv"]
    outside = tables["hidden/inpatient/outside_readmissions.csv"]
    fac_truth = tables["hidden/inpatient/facility_truth.csv"]

    adm = pd.concat([burn, pub], ignore_index=True)
    adm["published"] = np.r_[np.zeros(len(burn), dtype=bool), np.ones(len(pub), dtype=bool)]
    adm["admit_day"] = ordinal(adm["admit_datetime"])
    adm["disc_day"] = ordinal(adm["discharge_date"])
    for name in ("age", "comorbidity_count", "prior_admits_12m", "planned_admission",
                 "icu_at_12h", "comfort_care_12h", "died_in_hospital"):
        adm[name] = adm[name].astype(np.int64)
    adm["los"] = pd.to_numeric(adm["los_days"])           # empty -> NaN
    adm["year"] = adm["admit_datetime"].str[:4].astype(np.int64)
    adm["month"] = adm["admit_datetime"].str[5:7].astype(np.int64)

    # ---- S05 keys
    truth_ok = (len(truth) == len(adm)
                and (truth["encounter_id"].to_numpy() == adm["encounter_id"].to_numpy()).all()
                and (truth["person_id"].to_numpy() == adm["person_id"].to_numpy()).all())
    pub_persons = set(pub["person_id"])
    all_persons = set(adm["person_id"])
    in_pub = persons_truth.loc[persons_truth["in_published_data"] == "1", "person_id"]
    keys_ok = (adm["encounter_id"].is_unique and persons["person_id"].is_unique
               and persons_truth["person_id"].is_unique and truth_ok
               and set(persons["person_id"]) == pub_persons
               and set(persons_truth["person_id"]) == all_persons
               and set(in_pub) == pub_persons
               and (truth["in_published_data"].to_numpy() == adm["published"].astype(int).astype(str).to_numpy()).all())
    rep.check("S05", "construction: IDs are unique; persons.csv holds exactly the people with a published admission; each truth row matches its admission",
              f"{len(adm):,} admissions ({len(pub):,} published), {len(persons):,} persons, {len(persons_truth):,} persons in truth",
              "all keys consistent", bool(keys_ok))
    if not truth_ok:
        return rep
    for name in ("readmit_eligible", "readmit_any_30d", "readmit_outside", "planned_return", "lactate_drawn"):
        adm[name] = truth[name].astype(np.int64).to_numpy()
    adm["readmit_prob"] = pd.to_numeric(truth["readmit_prob"]).to_numpy()
    adm["readmit_gap"] = pd.to_numeric(truth["readmit_gap_days"]).to_numpy()
    adm["readmit_encounter_id"] = truth["readmit_encounter_id"].to_numpy()
    adm["severity"] = pd.to_numeric(truth["severity_latent"]).to_numpy()

    # ---- S06 ages
    birth = persons.set_index("person_id")["birth_year"].astype(np.int64)
    p = adm[adm["published"]]
    diff = p["year"].to_numpy() - birth.reindex(p["person_id"]).to_numpy() - p["age"].to_numpy()
    ages_ok = (adm["age"].between(18, 105).all() and birth.between(1915, 2008).all()
               and np.isin(diff, (0, 1)).all())
    rep.check("S06", "construction: age is 18 to 105, birth year 1915 to 2008, and age agrees with birth year and admission year",
              f"age {int(adm['age'].min())} to {int(adm['age'].max())}; birth year {int(birth.min())} to {int(birth.max())}",
              "within range; admission year minus birth year minus age is 0 or 1", bool(ages_ok))

    # ---- order by person and time
    codes, _ = pd.factorize(adm["person_id"], sort=True)
    adm["pcode"] = codes
    adm = adm.sort_values(["pcode", "admit_day"], kind="mergesort").reset_index(drop=True)
    same_next = np.r_[adm["pcode"].to_numpy()[1:] == adm["pcode"].to_numpy()[:-1], False]
    next_admit = np.r_[adm["admit_day"].to_numpy()[1:], 0]
    next_planned = np.r_[adm["planned_admission"].to_numpy()[1:], 0]
    next_enc = np.append(adm["encounter_id"].to_numpy(dtype=object)[1:], "")
    closed = adm["disc_day"].to_numpy() >= 0
    gap_next = np.where(same_next & closed, next_admit - adm["disc_day"].to_numpy(), -1)

    # ---- S07 no overlap
    overlap = int((same_next & (~closed | (next_admit <= adm["disc_day"].to_numpy()))).sum())
    rep.check("S07", "construction: no person is admitted again before the day after a discharge, or while a stay is open",
              f"{overlap} overlapping stays", "0", overlap == 0)

    # ---- S08 prior admissions recount
    big = 10 ** 7
    key = adm["pcode"].to_numpy() * big + adm["admit_day"].to_numpy()
    lo = np.searchsorted(key, key - 365, side="left")
    recount = np.arange(len(adm)) - lo
    wrong = int(((recount != adm["prior_admits_12m"].to_numpy()) & adm["published"].to_numpy()).sum())
    rep.check("S08", "construction: prior_admits_12m equals a recount from the admission files, 2021 burn-in included",
              f"{wrong} of {int(adm['published'].sum()):,} published admissions differ", "0 differ", wrong == 0)

    # ---- S09 readmission: the record against the truth
    last_complete = DATA_END.toordinal() - 30
    eligible_disp = adm["disposition"].isin(spec.READMIT_ELIGIBLE_DISPOSITIONS).to_numpy()
    index = eligible_disp & closed & (adm["disc_day"].to_numpy() <= last_complete)
    returned = (gap_next >= 1) & (gap_next <= 30)
    observed = index & returned & (next_planned == 0)
    observed_planned = index & returned & (next_planned == 1)
    true_network = (adm["readmit_any_30d"].to_numpy() == 1) & (adm["readmit_outside"].to_numpy() == 0)
    mism = int((index & (observed != true_network)).sum())
    mism_planned = int((index & (observed_planned != (adm["planned_return"].to_numpy() == 1))).sum())
    elig_mism = int((closed & (eligible_disp != (adm["readmit_eligible"].to_numpy() == 1))).sum())
    rep.check("S09", "construction: for every eligible discharge with 30 days of follow-up, the readmission an analyst derives from data/ (first return within 30 days, not planned) equals the truth for network readmissions",
              f"{mism} of {int(index.sum()):,} index discharges differ; planned returns: {mism_planned} differ; eligibility: {elig_mism} differ",
              "0 differ", mism == 0 and mism_planned == 0 and elig_mism == 0)

    # ---- S10 truth links
    has_link = adm["readmit_encounter_id"].to_numpy() != ""
    link_ok = (has_link <= true_network).all() and (next_enc[has_link] == adm["readmit_encounter_id"].to_numpy()[has_link]).all() \
        and (gap_next[has_link] == adm["readmit_gap"].to_numpy()[has_link]).all()
    unlinked = true_network & ~has_link
    late = adm["disc_day"].to_numpy() + np.nan_to_num(adm["readmit_gap"].to_numpy(), nan=0).astype(np.int64) > DATA_END.toordinal()
    link_ok = bool(link_ok) and bool((~unlinked | ~closed | late).all())
    rep.check("S10", "construction: readmit_encounter_id names the same person's next admission, readmit_gap_days after the discharge; it is empty only for outside readmissions and returns after the data end",
              f"{int(has_link.sum()):,} links checked; {int(unlinked.sum()):,} network readmissions fall after the data end",
              "all links right", link_ok)

    # ---- S11 outside readmissions
    is_out = (adm["readmit_outside"].to_numpy() == 1) & closed
    out_day = adm["disc_day"].to_numpy() + np.nan_to_num(adm["readmit_gap"].to_numpy(), nan=0).astype(np.int64)
    want = adm.loc[is_out & (out_day <= DATA_END.toordinal()), ["encounter_id", "person_id"]].copy()
    want["day"] = out_day[is_out & (out_day <= DATA_END.toordinal())]
    want["gap"] = adm["readmit_gap"].to_numpy()[is_out & (out_day <= DATA_END.toordinal())].astype(np.int64)
    want = want.sort_values("encounter_id").reset_index(drop=True)
    got = outside.sort_values("index_encounter_id").reset_index(drop=True)
    out_ok = (len(want) == len(got)
              and (want["encounter_id"].to_numpy() == got["index_encounter_id"].to_numpy()).all()
              and (want["person_id"].to_numpy() == got["person_id"].to_numpy()).all()
              and (want["day"].to_numpy() == ordinal(got["outside_admit_date"])).all()
              and (want["gap"].to_numpy() == got["gap_days"].astype(np.int64).to_numpy()).all())
    rep.check("S11", "construction: outside_readmissions.csv lists exactly the true readmissions that went outside the network, up to the data end",
              f"{len(got):,} rows against {len(want):,} in the truth", "equal, row for row", bool(out_ok))

    # ---- S12 planned admissions
    prev_same = np.r_[False, same_next[:-1]]
    prev_planned_return = np.r_[0, adm["planned_return"].to_numpy()[:-1]]
    prev_gap = np.r_[-1, gap_next[:-1]]
    is_planned = adm["planned_admission"].to_numpy() == 1
    planned_ok = (prev_same & (prev_planned_return == 1) & (prev_gap >= 7) & (prev_gap <= 30))[is_planned]
    elective_ok = (adm["admission_type"].to_numpy() == "elective")[is_planned]
    weekday_ok = (adm["admit_day"].to_numpy()[is_planned] - 1) % 7 < 5      # ordinal 1 is a Monday
    rep.check("S12", "construction: every planned admission is elective, falls on a weekday and follows a discharge flagged planned_return 7 to 30 days earlier",
              f"{int(planned_ok.sum()):,} of {int(is_planned.sum()):,} planned admissions",
              "all", bool(planned_ok.all() and elective_ok.all() and weekday_ok.all()))

    # ---- S13 open stays
    open_rows = adm[~closed]
    open_ok = ((open_rows["los_days"] == "").all() and (open_rows["disposition"] == "").all()
               and (open_rows["died_in_hospital"] == 0).all()
               and (adm.loc[closed, "los_days"] != "").all() and (adm.loc[closed, "disposition"] != "").all())
    rep.check("S13", "construction: a stay still open when the data end has an empty discharge date, length of stay and disposition",
              f"{len(open_rows):,} open stays, the earliest admitted {dt.date.fromordinal(int(open_rows['admit_day'].min())).isoformat() if len(open_rows) else 'none'}",
              "blanks consistent", bool(open_ok))

    # ---- S14 deaths
    died = adm["died_in_hospital"].to_numpy() == 1
    death_day = pd.Series(ordinal(persons_truth["death_date"]), index=persons_truth["person_id"])
    place = persons_truth.set_index("person_id")["death_place"]
    dd = death_day.reindex(adm["person_id"]).to_numpy()
    after_death = int(((dd >= 0) & (adm["admit_day"].to_numpy() > dd)).sum())
    died_rows = adm[died]
    deaths_ok = ((adm["disposition"].to_numpy() == "died") == died).all() \
        and (death_day.reindex(died_rows["person_id"]).to_numpy() == died_rows["disc_day"].to_numpy()).all() \
        and (place.reindex(died_rows["person_id"]) == "network_hospital").all() \
        and ((persons_truth["death_date"] == "") == (persons_truth["death_place"] == "")).all()
    rep.check("S14", "construction: a death in hospital is the person's last admission and its date and place are in persons_truth; nobody is admitted after dying",
              f"{int(died.sum()):,} deaths in hospital, {int((place == 'outside').sum()):,} outside; {after_death} admissions after a death",
              "consistent; 0 after a death", bool(deaths_ok) and after_death == 0)

    # ---- S15 budgets
    sizes = {}
    for sub in ("data", "hidden"):
        for folder, _dirs, files in os.walk(os.path.join(root, sub)):
            for name in files:
                full = os.path.join(folder, name)
                sizes[os.path.relpath(full, root).replace(os.sep, "/")] = os.path.getsize(full)
    mb = 1024 * 1024
    data_mb = sum(v for k, v in sizes.items() if k.startswith("data/")) / mb
    hidden_mb = sum(v for k, v in sizes.items() if k.startswith("hidden/")) / mb
    biggest = max(sizes, key=lambda k: (sizes[k], k))
    b = spec.BUDGET
    rep.check("S15", "construction: sizes are inside the budget",
              f"data/ {data_mb:.1f} MB, hidden/ {hidden_mb:.1f} MB, largest file {sizes[biggest] / mb:.1f} MB ({biggest})",
              f"data/ at most {b['data_mb']} MB, hidden/ at most {b['hidden_mb']} MB, any file at most {b['file_mb']} MB",
              data_mb <= b["data_mb"] and hidden_mb <= b["hidden_mb"] and sizes[biggest] / mb <= b["file_mb"])

    # ---- S16 intercepts
    with open(os.path.join(root, "hidden/calibrated_intercepts.json"), encoding="utf-8") as fh:
        solved = json.load(fh)
    want_names = sorted(spec.INPATIENT["reference"]["targets"])
    worst = max(abs(v["reference_mean"] - v["target"]) for v in solved["intercepts"].values())
    rep.check("S16", "construction: each solved intercept reproduces its target on the reference cohort",
              f"{len(solved['intercepts'])} intercepts; largest gap {worst:.1e}",
              f"{len(want_names)} intercepts; gap below 1e-09",
              sorted(solved["intercepts"]) == want_names and worst < 1e-9)

    # ---- S17 hospital effects
    sd_target = spec.INPATIENT["facility_effect_sd"]
    eff_ok, parts = True, []
    for column, name in (("readmit_effect_logit", "readmission"), ("deterioration_effect_logit", "deterioration")):
        v = pd.to_numeric(fac_truth[column]).to_numpy()
        mean = det_mean(v)
        sd = float(np.sqrt(det_mean((v - mean) * (v - mean))))
        parts.append(f"{name} mean {format_float(mean, 4)}, SD {format_float(sd, 4)}")
        eff_ok = eff_ok and abs(mean) < 1e-5 and abs(sd - sd_target[name]) < 1e-5
    rep.check("S17", "construction: the six hospital effects have mean 0 and the design SD",
              "; ".join(parts), f"mean 0.0000, SD {sd_target['readmission']:.4f}", eff_ok)

    # ---- S18 zero effects
    allowed = {"age_per_year", "comorbidity", "prior_admits", "prior_admits_cap", "log_los", "emergency",
               "severity", "frailty", "hemoglobin_below_12_per_g", "sodium_below_138_per_mmol",
               "disposition", "payer", "dx", "gap_weight_offset", "same_facility"}
    terms = set(spec.INPATIENT["readmission"])
    rep.check("S18", "construction: the true readmission model has no term for sex, day of week or season, so those effects are zero",
              f"{len(terms - allowed)} unexpected terms", "0", terms <= allowed)

    # ---- S19 to S26: the Milestone 3 files
    m3 = "M3" in spec.BUILT_MILESTONES
    if m3:
        index, truth_rows_ok, found_ok = index_frame(tables, adm, persons)
        if not check_deterioration_structure(rep, root, tables, adm, index, truth_rows_ok, found_ok):
            return rep

    # ---- S27 to S33: the Milestone 4 files
    m4 = None
    if "M4" in spec.BUILT_MILESTONES:
        x4 = r30_frame(adm, persons, observed)
        m4 = check_m4_structure(rep, root, tables, adm, persons, observed, index, x4)
        if m4 is None:
            return rep

    # ---- S34 to S44: the Milestone 5 files
    m5 = None
    if "M5" in spec.BUILT_MILESTONES:
        m5 = check_m5_structure(rep, root, tables)
        if m5 is None:
            return rep

    # ------------------------------------------------------------ inpatient targets
    values = {}
    T = {t[0]: t for t in spec.TARGETS}
    T.update({t[0]: t for t in spec.SECONDARY_TARGETS})

    def target(cid, value, shown, decimals=None):
        _id, _module, quantity, lo, hi, basis, _note = T[cid]
        wanted = range_text(lo, hi, decimals)
        for name, ranges in spec.VARIANCES.items():  # judged on the variance; the brief's range is shown
            if cid in ranges:
                lo, hi = ranges[cid]
                wanted = f"{range_text(lo, hi, decimals)} (variance {name}; the brief's range was {wanted})"
        return rep.check(cid, f"{basis}: {quantity}", shown, wanted, in_range(value, lo, hi))

    pb = adm[adm["published"]]
    n = len(pb)
    rep.section("Inpatient")
    target("T01", n, f"{n:,}")
    age = pb["age"].to_numpy()
    q1, med, q3 = int(quantile(age, 0.25)), median(age), int(quantile(age, 0.75))
    target("T02", med, f"{med:g}")
    target("T02b", q1, f"{q1}")
    target("T02c", q3, f"{q3}")
    sex = persons.set_index("person_id")["sex"].reindex(pb["person_id"]).to_numpy()
    female = float((sex == "f").sum()) / n
    target("T03", female, fmt(female), 2)
    payer = pb["payer"].to_numpy()
    share = {c: float((payer == c).sum()) / n for c in spec.PAYERS}
    target("T04", share["medicare"], fmt(share["medicare"]), 2)
    target("T04b", share["medicaid"], fmt(share["medicaid"]), 2)
    target("T04c", share["commercial"], fmt(share["commercial"]), 2)
    target("T04d", share["self_pay"], fmt(share["self_pay"]), 2)
    f06 = pb["facility_id"].to_numpy() == "F06"
    f06_medicare = float(((payer == "medicare") & f06).sum()) / int(f06.sum())
    target("T04e", f06_medicare, fmt(f06_medicare), 2)
    unknown = float((persons["race_ethnicity"] == "unknown").sum()) / len(persons)
    target("T05", unknown, fmt(unknown) + " of persons", 2)
    interp = float((persons["interpreter_needed"] == "1").sum()) / len(persons)
    target("T05b", interp, fmt(interp) + " of persons", 2)
    emergency = float((pb["admission_type"] == "emergency").sum()) / n
    target("T06", emergency, fmt(emergency), 2)
    # winter: F01 to F05, calendar years 2022 to 2025, admissions per day
    w = pb[(pb["facility_id"] != "F06") & pb["year"].between(2022, 2025)]
    days = [dt.date(2022, 1, 1) + dt.timedelta(days=i) for i in range((dt.date(2025, 12, 31) - dt.date(2022, 1, 1)).days + 1)]
    winter_days = sum(1 for d in days if d.month in spec.WINTER_MONTHS)
    winter = (int(w["month"].isin(spec.WINTER_MONTHS).sum()) / winter_days) / (len(w) / len(days))
    target("T07", winter, fmt(winter) + " (F01 to F05, 2022 to 2025)", 2)
    los = pb["los"].dropna().to_numpy()
    los_median = median(los)
    target("T08", los_median, f"{los_median:.1f}", 1)
    death = float(pb["died_in_hospital"].sum()) / n
    target("T08b", death, fmt(death), 3)
    drawn = (pb["lactate"] != "").to_numpy()
    lactate = float(drawn.sum()) / n
    target("T09", lactate, fmt(lactate), 2)
    icu = pb["icu_at_12h"].to_numpy() == 1
    sev = pb["severity"].to_numpy()
    top = sev >= quantile(sev, 0.75)
    bottom = sev <= quantile(sev, 0.25)
    shares = (float(drawn[icu].sum()) / int(icu.sum()), float(drawn[~icu].sum()) / int((~icu).sum()),
              float(drawn[top].sum()) / int(top.sum()), float(drawn[bottom].sum()) / int(bottom.sum()))
    rep.check("T09b", "realised: lactate is drawn more often when sicker",
              f"in intensive care at 12 hours {shares[0]:.3f}, others {shares[1]:.3f}; top quarter of hidden severity {shares[2]:.3f}, bottom quarter {shares[3]:.3f}",
              "higher in the sicker group, both ways", shares[0] > shares[1] and shares[2] > shares[3])

    # ------------------------------------------------------------ readmission truth
    rep.section("Readmission truth")
    disc = adm["disc_day"].to_numpy()
    y0, y1 = dt.date(2023, 1, 1).toordinal(), dt.date(2023, 12, 31).toordinal()
    in_2023 = closed & (disc >= y0) & (disc <= y1) & adm["published"].to_numpy()
    elig_2023 = in_2023 & (adm["readmit_eligible"].to_numpy() == 1)
    any_ = adm["readmit_any_30d"].to_numpy() == 1
    out = adm["readmit_outside"].to_numpy() == 1
    n23 = int(elig_2023.sum())
    t10 = float((any_ & elig_2023).sum()) / n23
    target("T10", t10, f"{t10:.4f} of {n23:,} eligible discharges", 2)
    mean_prob = det_mean(adm["readmit_prob"].to_numpy()[elig_2023])
    rep.check("T10b", "realised: the mean hidden probability agrees with the realised rate, 2023 discharges",
              f"mean probability {mean_prob:.4f}, realised {t10:.4f}", "within 0.01", abs(mean_prob - t10) <= 0.01)
    index_2023 = in_2023 & eligible_disp
    t11 = float((observed & index_2023).sum()) / int(index_2023.sum())
    target("T11", t11, f"{t11:.4f}, derived from data/ alone", 2)
    t12 = float((out & elig_2023).sum()) / int((any_ & elig_2023).sum())
    all_elig = (adm["readmit_eligible"].to_numpy() == 1) & adm["published"].to_numpy()
    t12_all = float((out & all_elig).sum()) / int((any_ & all_elig).sum())
    target("T12", t12, f"{t12:.4f} for 2023 discharges; {t12_all:.4f} for all published years", 2)
    y2 = dt.date(2025, 12, 31).toordinal()
    span = closed & (disc >= y0) & (disc <= y2) & (adm["readmit_eligible"].to_numpy() == 1)
    cstat = c_statistic(adm["readmit_prob"].to_numpy()[span], any_[span])
    target("T13", cstat, f"{cstat:.4f} on {int(span.sum()):,} eligible discharges", 2)

    # ------------------------------------------------------------ deterioration
    if m3:
        check_deterioration_targets(rep, tables, adm, index, target, values)
    if m4 is not None:
        check_m4_targets(rep, tables, adm, persons_truth, observed, index, x4, m4, target)
    if m5 is not None:
        check_m5_targets(rep, m5, target, values)

    # ------------------------------------------------------------ benchmarks
    rep.section("Benchmarks",
                "No pass or fail. These rows set the world's headline rates beside published United States "
                "figures, so a reader can judge plausibility. Sources and dates are in `PROVENANCE.md`. "
                "The published studies of proprietary scores concern real products that this world does not "
                "model; they show only that a local C-statistic below a vendor's claim is ordinary.")
    pay = adm["payer"].to_numpy()
    by_payer = ", ".join(
        f"{100 * float((any_ & elig_2023 & (pay == c)).sum()) / int((elig_2023 & (pay == c)).sum()):.1f}"
        for c in ("medicare", "medicaid", "self_pay", "commercial"))
    values.update({"t10": f"{100 * t10:.1f} per 100 eligible discharges", "by_payer": by_payer + " per 100",
                   "death": f"{100 * death:.1f}% of published admissions",
                   "los_mean": f"{det_mean(los):.1f} (median {los_median:.1f})"})
    for text, key, published, source in (BENCHMARKS + (VDI_BENCHMARKS if m3 else [])
                                         + (SCRIBE_BENCHMARKS if m5 is not None else [])):
        rep.info(text, values[key], published, source)

    # ------------------------------------------------------------ not built yet
    done = {r[0].split(" ")[0] for sec in rep.sections for r in sec["rows"]}
    later = [t for t in spec.TARGETS if t[0] not in done]
    rep.section("Not in this release",
                "Targets whose module is not part of version 1.0.0. Their ranges are fixed in `generator/spec.py`, "
                "and would be checked in an append-only release that adds the module.")
    rep.sections[-1]["header"] = ("Module", "Targets", "Status", "Count")
    for module in spec.TARGET_MODULES:
        ids = [t[0] for t in later if t[1] == module]
        if ids:
            status = "not built; held for a later release"
            rep.sections[-1]["rows"].append((module, f"{ids[0]} to {ids[-1]}", status, len(ids)))
    return rep


def main(argv):
    if len(argv) not in (2, 3):
        print(__doc__, file=sys.stderr)
        return 2
    root = argv[1]
    outfile = argv[2] if len(argv) == 3 else os.path.join(root, "CHECKS.md")
    rep = run(root)
    with open(outfile, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(rep.markdown())
    for sec in rep.sections:
        for row in sec["rows"]:
            if row[-1] in ("pass", "FAIL"):
                print(f"{row[3]:4s}  {row[0]}  ->  {row[1]}  [{row[2]}]")
    print(f"{rep.count} checks, {rep.failures} failed. Wrote {outfile}.")
    return 1 if rep.failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
