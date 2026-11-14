"""Tonmick Health: the single source of truth.

Everything the generator, the checks, the dictionary and the tests need to know
about the world is declared here. WORLD_SPEC.md mirrors this file in prose; if
the two ever differ, this file wins and the prose is fixed.

Milestone 1 fixed the world structure: timeline, block IDs, targets and the column
metadata for every CSV. Simulation coefficients arrive with their modules and are
added to this file then. Milestone 2 added INPATIENT (the inpatient core),
SECONDARY_TARGETS, TIMELINE_EVENTS, BUILT_MILESTONES and block 3. Milestone 3
added DETERIORATION, EVENT_TYPES, VENDOR_MODEL_CARD and nine secondary targets.

Everything here is fictional. `hidden/` holds simulator truth and is never evidence.
"""

WORLD = "tonmick-health"
VERSION = "1.0.0"              # frozen at Milestone 7
FREEZE_DATE = "2026-11-13"     # the day the freeze overlay was built; the commit date is in git
# From the freeze on, data/ and hidden/ are committed and nothing in SHA256SUMS may
# change. Later releases add files under derived/ with new block IDs (README.md).
DATA_COMMITTED = True
ROOT_SEED = 20261110
PINS = {"numpy": "2.5.3", "pandas": "3.0.5"}
PYTHON_SERIES = "3.13"         # the patch release is not pinned; no output depends on it

BOOK = {
    "status": "one-book plan adopted by Nick on 2026-11-11; title set on 2026-11-12",
    "title": "Validating Health AI Before and After Go-Live",
    "subtitle": ("A Field Manual for Local Performance Checks, Monitoring and Audit, "
                 "with Known Answers in Python and R"),
}

# --------------------------------------------------------------------------
# Random-number blocks. One PCG64 stream per block; IDs are never renumbered,
# and a dropped block's ID is retired, never reused.
# --------------------------------------------------------------------------
BLOCK_IDS = {
    # 1-9: network and persons. Block 3 (added in Milestone 2) draws the reference
    # cohort that the intercepts are solved on; it feeds no data file.
    "network": 1, "persons": 2, "calibration": 3,
    # 10-29: the coupled inpatient simulation and its products
    "arrivals": 10, "admission_attributes": 11, "comorbidity": 12,
    "labs_true": 13, "labs_recorded": 14, "vitals_true": 15,
    "vitals_recorded": 16, "index_eligibility": 17, "alert_response": 18,
    "deterioration": 19, "ehr_outcome": 20, "los_disposition": 21,
    "inpatient_death": 22, "readmission": 23, "outside_care": 24,
    "planned_readmission": 25, "chart_review": 26, "rrt_log": 27,
    "lab_change_log": 28,
    # 30-39: scribe audit
    "clinics_clinicians": 30, "rollout_draw": 31, "notes_frame": 32,
    "note_errors": 33, "audit_sample": 34, "rater_parameters": 35, "ratings": 36,
    # 40-49: scribe value and costs
    "clinician_traits": 40, "adoption": 41, "clinician_weeks": 42,
    "survey": 43, "costs": 44,
    # 50-59: hospice (held until after the v1.0.0 freeze; IDs stay reserved)
    "hospice_patients": 50, "hospice_trajectories": 51, "hospice_events": 52,
    "hospice_visits": 53, "hospice_predictions": 54,
    # 90s: test-only blocks; they never feed a data file
    "dummy": 90, "platform_probe": 99,
}
RESERVED_BLOCK_IDS = {
    "omop_export": 101, "literature_layer": 102,
    "claims_layer": 103, "second_vendor_tool": 104,
}
DERIVED_BLOCK_ID_START = 201
BLOCK_RANGES = {            # module -> inclusive ID range
    "network_persons": (1, 9), "inpatient": (10, 29), "scribe_audit": (30, 39),
    "scribe_value": (40, 49), "hospice": (50, 59), "test_only": (90, 99),
}
DEFERRED_BLOCKS = ("hospice_patients", "hospice_trajectories", "hospice_events",
                   "hospice_visits", "hospice_predictions")

# Append-only test: with this variable set to "1", the generator draws
# DUMMY_DRAWS values from the dummy block right after the network block.
DUMMY_ENV_VAR = "TONMICK_DUMMY_BLOCK"
DUMMY_DRAWS = 1_000_000

# --------------------------------------------------------------------------
# Timeline (ISO dates). The backstory tells the same story.
# --------------------------------------------------------------------------
DATES = {
    "burn_in_start": "2021-01-01",        # simulated, not published
    "published_start": "2022-01-01",
    "r30_dev_start": "2022-01-01",
    "r30_dev_end": "2022-06-30",
    "r30_worklist_start": "2023-02-01",   # true effect on readmission: zero
    "r30_scores_start": "2023-01-01",
    "vdi_silent_start": "2023-07-01",
    "vdi_silent_end": "2023-12-31",       # official silent-mode evaluation window
    "vdi_live_f01_f03": "2024-01-15",
    "lactate_assay_change": "2024-03-01", # central lab: F01 to F03
    "vdi_live_f04_f05": "2024-04-01",
    "f06_acquired": "2024-10-01",
    "scribe_measure_start": "2025-01-06", # a Monday; weeks start on Mondays
    "vdi_live_f06": "2025-01-15",         # no silent mode at F06
    "scribe_wave_1": "2025-04-07",
    "scribe_wave_2": "2025-07-07",
    "oversight_committee_formed": "2025-09-01",
    "scribe_wave_3": "2025-10-06",
    "scribe_v24": "2025-11-03",
    "scribe_wave_4": "2026-01-05",
    "vdi_v3": "2026-02-01",
    "scribe_observe_end": "2026-03-29",   # a Sunday; 64 full weeks
    "hospice_last_admission": "2026-03-31",
    "data_end": "2026-06-30",             # administrative censoring
}
MONDAY_DATES = ("scribe_measure_start", "scribe_wave_1", "scribe_wave_2",
                "scribe_wave_3", "scribe_wave_4", "scribe_v24")
SCRIBE_WEEKS = 64
SCRIBE_WAVE_KEYS = ("scribe_wave_1", "scribe_wave_2", "scribe_wave_3", "scribe_wave_4")
SURVEY_MONTHS = {"baseline": "2025-02", "final": "2026-03"}
WINTER_MONTHS = (12, 1, 2)

# --------------------------------------------------------------------------
# Network
# --------------------------------------------------------------------------
AREAS = ("north", "central", "south")
FACILITIES = [
    # id, name, type, area, beds, adult non-obstetric admissions a year,
    # in network data from, VDI scored from, VDI alerts from, central lab
    {"facility_id": "F01", "facility_name": "Tonmick University Medical Center",
     "facility_type": "academic", "area": "central", "beds": 452, "admissions_per_year": 17500,
     "network_data_from": "2021-01-01", "vdi_scoring_from": "2023-07-01",
     "vdi_alerts_from": "2024-01-15", "central_lab": 1},
    {"facility_id": "F02", "facility_name": "Brenmoor Community Hospital",
     "facility_type": "community", "area": "central", "beds": 218, "admissions_per_year": 7000,
     "network_data_from": "2021-01-01", "vdi_scoring_from": "2023-07-01",
     "vdi_alerts_from": "2024-01-15", "central_lab": 1},
    {"facility_id": "F03", "facility_name": "Tolvane Regional Hospital",
     "facility_type": "community", "area": "south", "beds": 164, "admissions_per_year": 4800,
     "network_data_from": "2021-01-01", "vdi_scoring_from": "2023-07-01",
     "vdi_alerts_from": "2024-01-15", "central_lab": 1},
    {"facility_id": "F04", "facility_name": "Northfen Hospital",
     "facility_type": "critical_access", "area": "north", "beds": 25, "admissions_per_year": 700,
     "network_data_from": "2021-01-01", "vdi_scoring_from": "2023-07-01",
     "vdi_alerts_from": "2024-04-01", "central_lab": 0},
    {"facility_id": "F05", "facility_name": "Pellow Lake Hospital",
     "facility_type": "critical_access", "area": "north", "beds": 22, "admissions_per_year": 600,
     "network_data_from": "2021-01-01", "vdi_scoring_from": "2023-07-01",
     "vdi_alerts_from": "2024-04-01", "central_lab": 0},
    {"facility_id": "F06", "facility_name": "Sallowfield Memorial Hospital",
     "facility_type": "community", "area": "south", "beds": 148, "admissions_per_year": 6000,
     "network_data_from": "2024-10-01", "vdi_scoring_from": "2025-01-15",
     "vdi_alerts_from": "2025-01-15", "central_lab": 0},
]
FACILITY_TYPES = ("academic", "community", "critical_access")
MEDICAL_GROUP = {"clinics": 24, "primary_care_clinics": 16, "specialty_clinics": 8,
                 "clinicians_about": 130, "clinics_per_wave": 6}
SPECIALTIES = ("cardiology", "oncology", "orthopaedics", "endocrinology",
               "pulmonology", "gastroenterology")   # behavioural health is outside the pilot

# --------------------------------------------------------------------------
# People, payers and case mix (targets and code lists; shares are design choices)
# --------------------------------------------------------------------------
PAYERS = {"medicare": 0.48, "medicaid": 0.18, "commercial": 0.28, "self_pay": 0.06}
F06_MEDICARE_SHARE = 0.60
RACE_ETHNICITY = {      # one combined field; shares are design choices
    "white": 0.62, "black": 0.13, "hispanic": 0.12, "asian": 0.04, "multiple": 0.03,
    "mena": 0.01, "aian": 0.007, "nhpi": 0.003, "unknown": 0.04,
}
SEX_CODES = ("f", "m")
FEMALE_SHARE = 0.52
INTERPRETER_SHARE = 0.06
DX_GROUPS = ("sepsis", "heart_failure", "copd", "pneumonia", "gi", "renal", "stroke",
             "cancer", "other_cardiac", "diabetes", "ortho_surgical", "other")
ADMISSION_TYPES = ("emergency", "elective")
EMERGENCY_SHARE = 0.75
SERVICES = ("medicine", "surgery")
DISPOSITIONS = ("home", "home_health", "snf", "hospice", "ama", "transfer", "died")
READMIT_ELIGIBLE_DISPOSITIONS = ("home", "home_health", "snf")
COMORBIDITY_MAX = 12
O2_SUPPORT = ("none", "low_flow", "high_flow")
ALERTNESS = ("alert", "drowsy", "confused", "unresponsive")   # invented categories
VDI = {"threshold": 60, "score_min": 0, "score_max": 100, "versions": ("2.0", "3.0"),
       "vendor_claimed_c": 0.84, "index_hours_after_admission": 12,
       "outcome_window_hours": 48, "label_delay_days": 3}
ERROR_TYPES = ("omission", "hallucination", "misattribution", "wrong_value")
SEVERITIES = ("none", "minor", "moderate", "major")
SCRIBE_VERSIONS = ("2.3", "2.4")
AUDIT = {"sample_size": 1200, "raters": 8, "chart_review_size": 800}
R30 = {
    "candidate_parameters": 17, "screen_p": 0.20, "coef_decimals": 6,
    "riley_anticipated_c": 0.70,        # fixed before any data exist (DESIGN section 9.3)
    # ---- added at Milestone 4
    # p < 0.20 on a likelihood-ratio test means a statistic above the chi-square
    # critical value: 1.2815515655446004 squared for 1 df, and -2 ln 0.2 for 2 df.
    "screen_critical": {1: 1.642374415149818, 2: 3.2188758248682006},
    "irls_iterations": 25,
    "reported_c_decimals": 3,
    # Mechanism P14: who is in the development sample.
    "development": {"facility": "F01", "service": "medicine",
                    "from": "2022-01-01", "to": "2022-06-30",
                    "panel": ("sodium", "creatinine", "hemoglobin", "wbc", "lactate"),
                    "first_discharge_per_person": True},
    # Mechanism P15: where the team cut continuous values.
    "cut": {"age": 65, "los_days": 5, "sodium": 135, "hemoglobin": 12},
    # The candidate terms: name, parameters, and the definition printed on the model card.
    "terms": [
        ("age_65_plus", ("age_65_plus",), "Age 65 or over at admission"),
        ("female", ("female",), "Recorded sex female"),
        ("los_over_5", ("los_over_5",), "Length of stay over 5 days"),
        ("prior_admits", ("prior_admits_1", "prior_admits_2_plus"),
         "Network admissions in the 12 months before this one: one, or two or more, against none"),
        ("comorbidity_count", ("comorbidity_count",), "Comorbidity count, as a number"),
        ("disp_snf", ("disp_snf",), "Discharged to skilled nursing"),
        ("disp_home_health", ("disp_home_health",), "Discharged home with home health"),
        ("medicaid", ("medicaid",), "Payer is Medicaid"),
        ("sodium_low", ("sodium_low",), "Admission sodium below 135; not low if not measured"),
        ("hemoglobin_low", ("hemoglobin_low",), "Admission hemoglobin below 12; not low if not measured"),
        ("dx_cancer", ("dx_cancer",), "Diagnosis group cancer"),
        ("dx_heart_failure", ("dx_heart_failure",), "Diagnosis group heart failure"),
        ("dx_copd", ("dx_copd",), "Diagnosis group COPD or respiratory"),
        ("emergency", ("emergency",), "Emergency admission"),
        ("weekend_discharge", ("weekend_discharge",), "Discharged on a Saturday or Sunday"),
        ("winter_discharge", ("winter_discharge",), "Discharged in December, January or February"),
    ],
    # hidden/readmission/r30_truth.json: all 17 parameters fitted, with no screen, to these discharges.
    "reference_fit": {"from": "2023-01-01", "to": "2023-12-31",
                      "facilities": ("F01", "F02", "F03", "F04", "F05"), "irls_iterations": 10},
    # Riley minimum sample size (checks.py): criteria and the alternative assumptions shown.
    "riley": {"shrinkage": 0.9, "r2_difference": 0.05, "risk_margin": 0.05,
              "alternative_c": (0.72, 0.75), "share_of_max_r2": 0.15},
}

# The R30 model card, as the analytics team wrote it (data/readmission/r30_model_card.json).
# The generator adds the sample size, the screen's result, the coefficients and the reported C.
R30_MODEL_CARD = {
    "fictional": ("Tonmick Health and this model are invented. Nothing here describes a real "
                  "hospital, team or model."),
    "model": "Tonmick R30",
    "built_by": "Tonmick Health clinical analytics team",
    "built": "2022-12",
    "intended_use": ("Rank adult discharges by risk of an unplanned readmission within 30 days, so "
                     "that discharge planners can follow up the highest first. Shown on the "
                     "discharge-planning worklist at every hospital from 2023-02-01."),
    "outcome": ("An unplanned admission to a Tonmick Health hospital within 30 days of discharge. "
                "A return flagged as planned does not count."),
    "eligible_discharges": ("Alive, to home, home with home health, or skilled nursing. Not deaths, "
                            "hospice, discharges against advice or transfers."),
    "development_population": ("Medicine-service discharges from Tonmick University Medical Center, "
                               "1 January to 30 June 2022, with a complete admission laboratory panel "
                               "(sodium, creatinine, hemoglobin, white cell count, lactate). Each "
                               "patient's first such discharge in the period."),
    "method": ("Each candidate term was tested alone in a logistic model and kept when p < 0.20 on "
               "a likelihood-ratio test. The terms kept were then fitted together. Risk is the "
               "logistic function of the intercept plus the sum of coefficient times value."),
    "missing_values": "In production a laboratory value that was not measured counts as not low.",
    "validation": "None beyond the development sample.",
}

# --------------------------------------------------------------------------
# Milestone 4 products of the deterioration module. Design choices throughout.
# --------------------------------------------------------------------------
# The committee's chart review (block chart_review): silent-mode encounters in ten
# strata cut at the deciles of the score, the high strata sampled more heavily.
CHART_REVIEW = {"allocation": (40, 40, 40, 40, 40, 60, 60, 80, 120, 280),
                "reviewer_sensitivity": 0.99, "reviewer_specificity": 0.999}
# The rapid-response log (block rrt_log). Minutes are gamma draws: shape, and the mean
# the scale is set to. The evaluation starts 0 to 3 hours after the index time.
RRT_LOG = {"nurse": {"shape": 4.0, "mean": 25.0, "added": 5.0},
           "physician": {"shape": 2.0, "mean": 10.0, "added": 0.0},
           "delay_hours": (0.55, 0.30, 0.10, 0.05)}
# The laboratory change log (block lab_change_log): routine entries drawn from the
# templates, plus the fixed entries. The lactate entry is written as a laboratory
# would write it and says nothing about its effect (mechanism P4).
LAB_SITES = {"central": ("F01", "F02", "F03"), "northfen": ("F04",), "pellow_lake": ("F05",),
             "sallowfield": ("F06",)}
LAB_LOG = {
    "from": "2022-01-01", "routine_entries": 84,
    "site_weight": {"central": 0.52, "northfen": 0.14, "pellow_lake": 0.14, "sallowfield": 0.20},
    # test_area, change_type, description
    "templates": [
        ("chemistry", "reagent_lot", "New reagent lot for the basic metabolic panel. Lot-to-lot check within limits."),
        ("chemistry", "reagent_lot", "New reagent lot for liver enzymes. Lot-to-lot check within limits."),
        ("chemistry", "calibration", "Six-monthly calibration of the main chemistry line. Controls in range."),
        ("chemistry", "calibration", "Potassium recalibrated after a control drift. Controls in range afterwards."),
        ("chemistry", "maintenance", "Planned maintenance on the main chemistry line. Backup line used for four hours."),
        ("chemistry", "quality_control", "Glucose control out of range on the night shift. Rerun in range; no patient results held."),
        ("hematology", "reagent_lot", "New reagent lot for the blood count analyser. Lot-to-lot check within limits."),
        ("hematology", "calibration", "Blood count analyser calibrated after service. Controls in range."),
        ("hematology", "maintenance", "Blood count analyser serviced. Samples run on the second analyser meanwhile."),
        ("hematology", "quality_control", "Platelet control flagged once. Rerun in range."),
        ("coagulation", "reagent_lot", "New thromboplastin lot. Reference values rechecked; no change."),
        ("coagulation", "calibration", "Coagulation analyser calibrated. Controls in range."),
        ("blood_gas", "maintenance", "Blood gas analyser cartridge replaced ahead of schedule."),
        ("blood_gas", "quality_control", "Blood gas analyser failed its daily check. Cartridge replaced; check passed."),
        ("point_of_care", "quality_control", "Ward glucose meters: quarterly comparison with the laboratory. All within limits."),
        ("point_of_care", "software", "Ward glucose meters updated to the current software. Operator list reloaded."),
        ("microbiology", "reagent_lot", "New lot of blood culture bottles in use."),
        ("microbiology", "maintenance", "Blood culture incubator serviced. No samples affected."),
        ("immunoassay", "reagent_lot", "New reagent lot for thyroid tests. Lot-to-lot check within limits."),
        ("immunoassay", "calibration", "Immunoassay analyser calibrated after a lot change. Controls in range."),
        ("general", "software", "Laboratory information system patch applied overnight. Interfaces checked."),
        ("general", "staffing", "Evening phlebotomy round moved one hour earlier."),
        ("general", "reference_interval", "Annual review of reference intervals. No changes."),
        ("general", "quality_control", "External quality assessment results received. All analytes acceptable."),
    ],
    # date, lab site, test_area, change_type, description. Sorted into the log by date.
    "fixed": [
        ("2022-09-12", "central", "immunoassay", "method_change",
         "Troponin moved to the high-sensitivity method. Clinical teams notified; new reference interval issued."),
        ("2023-05-08", "northfen", "hematology", "method_change",
         "Blood count analyser replaced with the current model. Comparison study complete."),
        ("2024-03-01", "central", "chemistry", "method_change",
         "Lactate moved to the enzymatic method on the main chemistry line. Verification complete. Reference interval unchanged."),
        ("2024-11-18", "sallowfield", "general", "software",
         "Laboratory moved onto the network's laboratory information system. Test codes mapped."),
        ("2025-06-02", "central", "coagulation", "method_change",
         "Coagulation analyser replaced. Comparison study complete; reference values unchanged."),
    ],
}
LAB_TEST_AREAS = ("chemistry", "hematology", "coagulation", "blood_gas", "point_of_care",
                  "microbiology", "immunoassay", "general")
LAB_CHANGE_TYPES = ("reagent_lot", "calibration", "maintenance", "quality_control", "software",
                    "staffing", "reference_interval", "method_change")
FACILITY_GROUPS = {"f01_f03": ("F01", "F02", "F03"), "f04_f05": ("F04", "F05"), "f06": ("F06",)}

# --------------------------------------------------------------------------
# Targets. Each row: id, module, quantity, low, high, basis, note.
#   basis "realised": computed from the generated files, as an analyst would.
#   basis "expected": computed from hidden probabilities; the realised value is
#                     printed beside it (small cells, DESIGN section 9.1).
#   basis "construction": true by design; the check confirms it.
# low/high None means the row is a structural check defined in checks.py.
# Variances V1 to V5 (DESIGN section 10, approved 2026-11-10) are applied here.
# --------------------------------------------------------------------------
TARGETS = [
    ("T01", "inpatient", "published admissions, 2022-01-01 to 2026-06-30", 140000, 160000, "realised", ""),
    ("T02", "inpatient", "median age", 62.0, 66.0, "realised", "IQR about 50 to 76 reported beside it"),
    ("T03", "inpatient", "female share", 0.50, 0.54, "realised", ""),
    ("T04", "inpatient", "Medicare share overall", 0.45, 0.51, "realised", "F06 about 0.60 reported beside it"),
    ("T05", "inpatient", "race and ethnicity unknown share", 0.03, 0.05, "realised", "interpreter needed about 0.06 beside it"),
    ("T06", "inpatient", "emergency admission share", 0.72, 0.78, "realised", ""),
    ("T07", "inpatient", "December to February admissions relative to annual mean", 1.09, 1.15, "realised", ""),
    ("T08", "inpatient", "median length of stay, days", 3.5, 4.1, "realised", "in-hospital death about 0.02 beside it"),
    ("T09", "inpatient", "lactate drawn share", 0.37, 0.43, "realised", "higher when sicker"),
    ("T10", "readmission", "true 30-day readmission, any hospital, 2023 discharges", 0.13, 0.15, "realised", ""),
    ("T11", "readmission", "observed network-only readmission, 2023", 0.11, 0.13, "realised", ""),
    ("T12", "readmission", "share of true readmissions outside the network", 0.12, 0.18, "realised", ""),
    ("T13", "readmission", "true-model C-statistic, hidden probabilities, 2023 to 2025", 0.70, 0.74, "realised", ""),
    ("T14", "deterioration", "index encounters, 2023-07-01 to 2026-06-30", 76000, 84000, "realised", "eligibility about 0.80"),
    ("T15", "deterioration", "silent-mode EHR event rate", 0.036, 0.044, "realised", "about 12,000 encounters"),
    ("T16", "deterioration", "VDI v2 C-statistic, silent mode", 0.76, 0.80, "realised", ""),
    ("T17", "deterioration", "VDI v2 calibration slope, silent mode", 0.80, 0.92, "realised", ""),
    ("T18", "deterioration", "VDI v2 overall O/E, silent mode", 0.85, 0.95, "realised", ""),
    ("T19", "deterioration", "O/E, patients recorded as Black, silent mode", 1.15, 1.35, "expected", "V5"),
    ("T20", "deterioration", "O/E, F04 and F05, silent mode", 1.15, 1.35, "expected", "V5"),
    ("T21", "deterioration", "O/E, Medicaid and self-pay, silent mode", 1.15, 1.35, "expected", "V5"),
    ("T22", "deterioration", "alert rate at threshold 60, silent mode", 0.07, 0.09, "realised", ""),
    ("T23", "deterioration", "positive predictive value at threshold 60", 0.15, 0.22, "realised", ""),
    ("T24", "deterioration", "sensitivity at threshold 60", 0.35, 0.50, "realised", "expected to land at 0.35 to 0.41"),
    ("T25", "deterioration", "alert-rate rise from the assay change, F01 to F03, April 2024", 0.02, 0.04, "expected", "V4: paired counterfactual"),
    ("T26", "deterioration", "true event-rate change from the assay change, absolute", 0.0, 0.003, "expected", "V4: paired counterfactual"),
    ("T27", "deterioration", "F06 event rate", 0.050, 0.060, "realised", "O/E 1.10 to 1.35 beside it"),
    ("T28", "deterioration", "risk ratio of response, hidden potential outcomes", 0.78, 0.82, "realised", ""),
    ("T29", "deterioration", "EHR outcome flag sensitivity overall", 0.90, 0.94, "realised", "F04 and F05 about 0.85 (expected); false-positive rate about 0.004"),
    ("T30", "deterioration", "default respiratory rate share at F04 and F05", 0.36, 0.44, "realised", ""),
    ("T31", "deterioration", "response to alerts at go-live", 0.82, 0.88, "realised", "about 0.70 by late 2025 beside it"),
    ("T32", "deterioration", "VDI v3.0 alert rate", 0.05, 0.06, "realised", "slope about 1.0, calibration-in-the-large about 0"),
    ("T33", "deterioration", "chart review sample size", 800, 800, "construction", "reviewer sensitivity about 0.99, specificity about 0.999"),
    ("T34", "deterioration", "mean rapid-response nurse minutes", 27.0, 33.0, "realised", "physician about 10"),
    ("T40", "r30", "development discharges", 1500, 1900, "realised", "170 to 230 observed events"),
    ("T41", "r30", "apparent C-statistic", 0.73, 0.77, "realised", "risk R2"),
    ("T42", "r30", "validation C-statistic, 2023 discharges, F01 to F05", 0.66, 0.70, "realised", ""),
    ("T43", "r30", "calibration slope at validation", 0.70, 0.85, "realised", ""),
    ("T44", "r30", "O/E at F04 and F05, observed outcome", 0.75, 0.90, "expected", "V5"),
    ("T45", "r30", "development n below the Riley minimum (anticipated C 0.70)", None, None, "realised", "four-row table shown"),
    ("T46", "r30", "noise predictors have true effect zero", None, None, "construction", ""),
    ("T50", "scribe_audit", "AI-drafted notes in the frame", 90000, 120000, "realised", "V2"),
    ("T51", "scribe_audit", "notes with an omission, v2.3", 0.15, 0.19, "realised", ""),
    ("T52", "scribe_audit", "notes with a hallucination, v2.3", 0.09, 0.12, "realised", ""),
    ("T53", "scribe_audit", "notes with a misattribution, v2.3", 0.07, 0.10, "realised", ""),
    ("T54", "scribe_audit", "notes with a major error", 0.010, 0.020, "realised", ""),
    ("T55", "scribe_audit", "omission rate ratio, interpreter visits to others", 1.5, 2.2, "realised", ""),
    ("T56", "scribe_audit", "audit sample size", 1200, 1200, "construction", "two ratings per note plus adjudication"),
    ("T57", "scribe_audit", "Cohen's kappa, hallucination, first against second rater", 0.55, 0.75, "realised", ""),
    ("T58", "scribe_audit", "design-weighted omission prevalence minus truth, absolute", 0.0, 0.02, "realised", "gap reported"),
    ("T59", "scribe_audit", "notes per clinician-week equal scribe visits in the panel", None, None, "construction", ""),
    ("T60", "scribe_audit", "rater parameters within the planted ranges", None, None, "construction", ""),
    ("T70", "scribe_value", "clinicians in the panel", 120, 140, "realised", "64 weeks each"),
    ("T71", "scribe_value", "clinicians in live clinics on at least half their visits by week 8", 0.70, 0.80, "realised", ""),
    ("T72", "scribe_value", "never adopt", 0.07, 0.13, "realised", ""),
    ("T73", "scribe_value", "true mean saving per scribe visit at steady state, minutes", 1.8, 2.2, "realised", "V3; all-visit mean reported beside it"),
    ("T74", "scribe_value", "naive pre-post estimate minus true saving, minutes", 0.3, None, "realised", "definition in DESIGN section 9.5"),
    ("T75", "scribe_value", "after-hours minutes, relative change", -0.24, -0.16, "realised", "visits +0.4 a week beside it"),
    ("T76", "scribe_value", "survey response rate", 0.55, 0.70, "realised", "lower when latent wellbeing is lower"),
    ("T77", "scribe_value", "true effect on latent wellbeing among adopters, SD units", 0.20, 0.30, "realised", ""),
    # Hospice is held until after the v1.0.0 freeze. Its targets (V1 applied) are
    # kept so the later release starts from the approved design.
    ("T80", "hospice", "admissions, 2021-01-01 to 2026-03-31", 4700, 5300, "realised", "deferred"),
    ("T81", "hospice", "function-visit rows", 60000, 90000, "realised", "deferred"),
    ("T84", "hospice", "median survival from admission, days", 17, 25, "realised", "deferred"),
    ("T85", "hospice", "death in hospice by 180 days, cumulative incidence", 0.73, 0.79, "realised", "deferred; V1"),
    ("T86", "hospice", "live discharge by 180 days, cumulative incidence", 0.13, 0.17, "realised", "deferred; V1"),
    ("T86b", "hospice", "still in care at 180 days", 0.07, 0.11, "realised", "deferred; V1"),
    ("T87", "hospice", "dementia median survival relative to cancer", 2.0, 3.0, "realised", "deferred"),
    ("T88", "hospice", "Harrell's C, admission TDFS for death", 0.68, 0.75, "realised", "deferred"),
    ("T90", "hospice", "1 minus Kaplan-Meier minus death incidence at 180 days", 0.03, None, "realised", "deferred"),
    ("T91", "hospice", "clinician-predicted to actual median survival", 1.3, 1.6, "realised", "deferred"),
]
TARGET_BASES = ("realised", "expected", "construction")
TARGET_MODULES = ("inpatient", "readmission", "deterioration", "r30",
                  "scribe_audit", "scribe_value", "hospice")

# --------------------------------------------------------------------------
# Milestones whose files are in the world. dictionary.py, checks.py and
# make_manifest.py list only files whose milestone is here. Milestone 7, the
# freeze, added no file under data/ or hidden/.
# --------------------------------------------------------------------------
BUILT_MILESTONES = ("M2", "M3", "M4", "M5")

# --------------------------------------------------------------------------
# Secondary targets (added at Milestone 2). TARGETS above reports some values
# "beside" a main target without a range. The values themselves ("about 2%",
# "about 60%") were committed in DESIGN.md at Milestone 0. The ranges here were
# added with the generator, by the same rule decision A6 used for the main
# targets: a few points either side of the "about" value.
# --------------------------------------------------------------------------
SECONDARY_TARGETS = [
    ("T02b", "inpatient", "age, lower quartile", 48.0, 52.0, "realised", "about 50"),
    ("T02c", "inpatient", "age, upper quartile", 74.0, 78.0, "realised", "about 76"),
    ("T04b", "inpatient", "Medicaid share overall", 0.16, 0.20, "realised", "about 0.18"),
    ("T04c", "inpatient", "commercial share overall", 0.26, 0.30, "realised", "about 0.28"),
    ("T04d", "inpatient", "self-pay share overall", 0.05, 0.07, "realised", "about 0.06"),
    ("T04e", "inpatient", "Medicare share at F06", 0.57, 0.63, "realised", "about 0.60"),
    ("T05b", "inpatient", "interpreter needed share", 0.05, 0.07, "realised", "about 0.06"),
    ("T08b", "inpatient", "in-hospital death share", 0.017, 0.023, "realised", "about 0.02"),
    # Added at Milestone 3, by the same rule. T27b's range is the brief's own.
    ("T14b", "deterioration", "share of published admissions on a ward at 12 hours", 0.77, 0.83, "realised", "about 0.80"),
    ("T15b", "deterioration", "silent-mode index encounters", 11000, 13000, "realised", "about 12,000"),
    ("T15c", "deterioration", "true risk, December to February relative to other months", 1.05, 1.15, "expected", "about 10% higher"),
    ("T27b", "deterioration", "O/E at F06 under version 2.0", 1.10, 1.35, "realised", "range from the brief"),
    ("T29b", "deterioration", "EHR outcome flag sensitivity at F04 and F05", 0.82, 0.88, "expected", "about 0.85"),
    ("T29c", "deterioration", "EHR outcome flag false-positive rate", 0.003, 0.005, "realised", "about 0.004"),
    ("T31b", "deterioration", "response to alerts, F01 to F03, October to December 2025", 0.66, 0.74, "realised", "about 0.70"),
    ("T32b", "deterioration", "VDI v3.0 calibration slope", 0.90, 1.10, "realised", "about 1.0"),
    ("T32c", "deterioration", "VDI v3.0 calibration-in-the-large", -0.10, 0.10, "realised", "about 0"),
    # Added at Milestone 4. T40b's range is the brief's own.
    ("T34b", "deterioration", "mean rapid-response physician minutes", 8.0, 12.0, "realised", "about 10"),
    ("T40b", "r30", "observed readmissions in the development sample", 170, 230, "realised", "range from the brief"),
    # Added at Milestone 5, by the same rule.
    ("T75b", "scribe_value", "visits per clinician-week added at full use", 0.3, 0.5, "realised", "about 0.4"),
]

# --------------------------------------------------------------------------
# Variance V6, set at Milestone 4 (DESIGN.md section 15, decision A31).
# Two R30 targets cannot hold together with the rest: with about 230 events and
# 17 candidate parameters, a model of this form does not reach an apparent
# C-statistic of 0.73 while the true model itself reaches only 0.72 (T13), and
# its overfitting is too mild for a validation slope below 0.85. DESIGN.md risk
# R2 foresaw this at Milestone 0. The ranges below were set AFTER the values
# were seen, so they test nothing; they only guard against later drift.
# CHECKS.md prints the brief's range beside each. Nick approved V6 in writing
# on 13 November 2026, before the freeze (PROVENANCE.md, Milestone 7).
# --------------------------------------------------------------------------
VARIANCE_V6 = {"T41": (0.69, 0.73), "T43": (0.80, 0.94)}

# --------------------------------------------------------------------------
# Variance V7, set at Milestone 5 (DESIGN.md section 15, decision A41).
# The brief gives the raters a sensitivity of 0.70 to 0.92, one lenient rater
# near 0.60 and a false-positive rate of 0.01 to 0.05. With hallucinations in
# about 9% of audited notes, those figures put the expected kappa between two
# raters at about 0.53, under the brief's own range of 0.55 to 0.75. The rater
# figures are kept as the brief wrote them, and the range for kappa moves.
# It was set AFTER the value was seen, so it tests nothing. CHECKS.md prints
# the brief's range beside it. Nick approved V7 in writing on 13 November
# 2026, before the freeze (PROVENANCE.md, Milestone 7).
# --------------------------------------------------------------------------
VARIANCE_V7 = {"T57": (0.45, 0.65)}
VARIANCES = {"V6": VARIANCE_V6, "V7": VARIANCE_V7}

# --------------------------------------------------------------------------
# Public timeline (data/network/timeline.csv). The lactate assay change is
# left out on purpose: it appears only in the laboratory's change log
# (DESIGN section 4.2). Burn-in and hospice dates are not public events.
# Each row: date key in DATES, event code, scope, description.
# --------------------------------------------------------------------------
TIMELINE_EVENTS = [
    ("published_start", "extract_start", "F01;F02;F03;F04;F05", "First admission date in this extract"),
    ("r30_scores_start", "r30_scores_start", "F01;F02;F03;F04;F05", "Tonmick R30 readmission scores calculated at discharge from this date"),
    ("r30_worklist_start", "r30_worklist_start", "F01;F02;F03;F04;F05", "Tonmick R30 score shown on the discharge-planning worklist"),
    ("vdi_silent_start", "vdi_silent_start", "F01;F02;F03;F04;F05", "Venncroft Deterioration Index scoring begins in silent mode"),
    ("vdi_silent_end", "vdi_silent_end", "F01;F02;F03;F04;F05", "End of the planned silent-mode evaluation window"),
    ("vdi_live_f01_f03", "vdi_alerts_live", "F01;F02;F03", "Venncroft Deterioration Index alerts go live"),
    ("vdi_live_f04_f05", "vdi_alerts_live", "F04;F05", "Venncroft Deterioration Index alerts go live"),
    ("f06_acquired", "acquisition", "F06", "Sallowfield Memorial Hospital joins Tonmick Health; its admissions enter network data"),
    ("scribe_measure_start", "scribe_measure_start", "all clinics", "Measurement period for the Harkwell Ambient pilot begins"),
    ("vdi_live_f06", "vdi_alerts_live", "F06", "Venncroft Deterioration Index scoring and alerts go live together"),
    ("scribe_wave_1", "scribe_go_live", "wave 1 clinics", "Harkwell Ambient goes live at the first six clinics"),
    ("scribe_wave_2", "scribe_go_live", "wave 2 clinics", "Harkwell Ambient goes live at the second six clinics"),
    ("oversight_committee_formed", "committee_formed", "network", "The board forms the AI Oversight Committee"),
    ("scribe_wave_3", "scribe_go_live", "wave 3 clinics", "Harkwell Ambient goes live at the third six clinics"),
    ("scribe_v24", "scribe_version", "all live clinics", "Harkwell Ambient version 2.4 replaces version 2.3"),
    ("scribe_wave_4", "scribe_go_live", "wave 4 clinics", "Harkwell Ambient goes live at the last six clinics"),
    ("vdi_v3", "vdi_version", "F01;F02;F03;F04;F05;F06", "Venncroft Deterioration Index version 3.0 replaces version 2.0; the vendor describes it as a recalibration"),
    ("scribe_observe_end", "scribe_measure_end", "all clinics", "Measurement period for the Harkwell Ambient pilot ends"),
    ("data_end", "extract_end", "network", "Last date in this extract; later events are not recorded"),
]

# --------------------------------------------------------------------------
# Inpatient core (Milestone 2). Every number here is a design choice unless
# PROVENANCE.md gives a source. Intercepts marked "solved" are not here: they
# are found by bisection on a reference cohort and stored in
# hidden/calibrated_intercepts.json. WORLD_SPEC.md describes the model in prose.
# Diagnosis-group keys are spec.DX_GROUPS; a group left out of a table has 0.
# --------------------------------------------------------------------------
INPATIENT = {
    # ---- the catchment pool (block persons)
    "pool_size": 400000,
    "age_reference_date": "2024-01-01",
    # Pool age density at the reference date: flat from `min` to `knee`, then
    # falling in a straight line to zero at `top`. Whole years, plus a uniform fraction.
    "pool_age": {"min": 15, "max": 97, "knee": 55, "top": 98},
    "min_age": 18,
    "area_share": {"north": 0.12, "central": 0.60, "south": 0.28},
    "interpreter_by_race": {"white": 0.008, "black": 0.008, "hispanic": 0.30, "asian": 0.32,
                            "multiple": 0.02, "mena": 0.27, "aian": 0.01, "nhpi": 0.06,
                            "unknown": 0.03},
    # Payer at admission, from one fixed uniform per person and the age band.
    "payer_by_age": {
        "under_65": {"medicare": 0.09, "medicaid": 0.31, "commercial": 0.49, "self_pay": 0.11},
        "65_plus": {"medicare": 0.88, "medicaid": 0.04, "commercial": 0.07, "self_pay": 0.01},
    },
    # Logit of the person's propensity to use non-network hospitals.
    "outside_care": {"intercept": -2.15, "north": 1.45, "central": 0.0, "south": 0.40, "sd": 0.50},
    "comorbidity": {"log_mean": 0.55, "age_per_year": 0.024, "frailty": 0.30,
                    "gain_per_admission": 0.25},

    # ---- who is admitted where (block arrivals)
    # Share of each hospital's patients who live in each area.
    "catchment_mix": {
        "F01": {"north": 0.12, "central": 0.72, "south": 0.16},
        "F02": {"north": 0.03, "central": 0.93, "south": 0.04},
        "F03": {"north": 0.01, "central": 0.07, "south": 0.92},
        "F04": {"north": 0.96, "central": 0.03, "south": 0.01},
        "F05": {"north": 0.97, "central": 0.02, "south": 0.01},
        "F06": {"north": 0.01, "central": 0.04, "south": 0.95},
    },
    # A person's chance of admission is proportional to exp(age_per_year * (age - 50)
    # + frailty * frailty_z + tilt * (age - 64) / 15), times the catchment mix.
    "admission_rate": {"age_per_year": 0.038, "frailty": 0.60},
    "facility_age_tilt": {"F01": -0.05, "F02": 0.00, "F03": 0.05, "F04": 0.15, "F05": 0.15,
                          "F06": 0.30},
    # Share of admissions that are not scheduled returns (readmissions, planned returns).
    "new_arrival_share": 0.867,
    # Seasonal and weekday factors for new arrivals; each set is rescaled to mean 1.
    "month_factor": [1.14, 1.11, 1.03, 0.98, 0.95, 0.93, 0.92, 0.93, 0.95, 0.98, 1.02, 1.11],
    "weekday_factor": [1.08, 1.07, 1.05, 1.04, 1.02, 0.88, 0.86],        # Monday first

    # ---- admission attributes (block admission_attributes)
    "elective_share_weekday": {"F01": 0.46, "F02": 0.18, "F03": 0.16, "F04": 0.06,
                               "F05": 0.06, "F06": 0.16},
    "elective_weekend_multiplier": 0.15,
    "dx_emergency_under_65": {"sepsis": 0.08, "heart_failure": 0.06, "copd": 0.07, "pneumonia": 0.08,
                              "gi": 0.14, "renal": 0.06, "stroke": 0.04, "cancer": 0.04,
                              "other_cardiac": 0.09, "diabetes": 0.08, "ortho_surgical": 0.07,
                              "other": 0.19},
    "dx_emergency_65_plus": {"sepsis": 0.11, "heart_failure": 0.13, "copd": 0.09, "pneumonia": 0.10,
                             "gi": 0.09, "renal": 0.07, "stroke": 0.07, "cancer": 0.04,
                             "other_cardiac": 0.11, "diabetes": 0.03, "ortho_surgical": 0.07,
                             "other": 0.09},
    "dx_elective": {"ortho_surgical": 0.40, "cancer": 0.17, "other_cardiac": 0.14, "gi": 0.11,
                    "renal": 0.02, "other": 0.16},
    "dx_winter_multiplier": {"pneumonia": 1.35, "copd": 1.35},           # emergency admissions
    "readmission_same_dx": 0.50,
    "surgery_share_emergency": {"sepsis": 0.05, "heart_failure": 0.01, "copd": 0.01,
                                "pneumonia": 0.01, "gi": 0.22, "renal": 0.04, "stroke": 0.05,
                                "cancer": 0.25, "other_cardiac": 0.10, "diabetes": 0.04,
                                "ortho_surgical": 0.90, "other": 0.15},
    "surgery_share_elective": {"gi": 0.70, "renal": 0.30, "cancer": 0.65, "other_cardiac": 0.45,
                               "ortho_surgical": 0.97, "other": 0.60},
    # F01 is the trauma and tertiary centre: more of its emergency work is surgical.
    "surgery_emergency_multiplier": {"F01": 1.5},
    # Admission hour weights, hour 0 to hour 23.
    "hour_emergency": [2.0, 2.0, 1.5, 1.5, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 6.5,
                       6.5, 6.5, 6.5, 6.5, 6.5, 6.0, 6.0, 5.5, 5.0, 4.0, 3.0, 2.5],
    "hour_elective": [0, 0, 0, 0, 0, 1.0, 4.0, 5.0, 3.0, 2.0, 1.5, 1.0,
                      1.0, 0.5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],

    # ---- unmeasured severity (standardised on the reference cohort)
    "severity": {"frailty": 0.45, "age_per_15": 0.30, "comorbidity_per_2": 0.20,
                 "emergency": 0.35, "readmission": 0.30, "winter": 0.10, "noise_sd": 0.75,
                 "dx": {"sepsis": 0.70, "heart_failure": 0.25, "copd": 0.15, "pneumonia": 0.30,
                        "gi": -0.10, "renal": 0.15, "stroke": 0.40, "cancer": 0.20,
                        "other_cardiac": -0.05, "diabetes": -0.10, "ortho_surgical": -0.45,
                        "other": -0.15}},

    # ---- true laboratory values (block labs_true). s = severity, z = standard normal.
    "labs_true": {
        "sodium": {"mean": 139.0, "severity": -1.0, "sd": 3.4, "min": 112.0, "max": 165.0,
                   "dx": {"heart_failure": -1.0, "renal": -0.5}},
        "creatinine": {"median": 0.95, "severity": 0.16, "age_per_15": 0.10, "female": -0.15,
                       "log_sd": 0.30, "min": 0.3, "max": 14.0, "dx": {"renal": 0.65}},
        "hemoglobin": {"mean": 13.3, "severity": -0.55, "age_per_15": -0.25, "female": -1.0,
                       "sd": 1.55, "min": 4.5, "max": 19.0, "dx": {"cancer": -1.1, "renal": -0.5}},
        "wbc": {"median": 8.4, "severity": 0.14, "log_sd": 0.32, "min": 0.6, "max": 60.0,
                "dx": {"sepsis": 0.42, "pneumonia": 0.25, "cancer": -0.10}},
        "lactate": {"median": 1.25, "severity": 0.26, "log_sd": 0.36, "min": 0.4, "max": 18.0,
                    "dx": {"sepsis": 0.50}},
    },
    # ---- recorded laboratory values (block labs_recorded)
    "labs_recorded": {
        "chemistry_measured": {"emergency": 0.96, "elective": 0.94},     # sodium and creatinine
        "blood_count_measured": {"emergency": 0.955, "elective": 0.93},  # hemoglobin and white cells
        "noise": {"sodium_sd": 1.0, "creatinine_cv": 0.035, "hemoglobin_sd": 0.20,
                  "wbc_cv": 0.04, "lactate_cv": 0.06},
        "lactate_min": 0.3,
        # logit P(lactate drawn) = solved intercept + these terms
        # The university hospital orders lactate more selectively than the others.
        "lactate_drawn": {"severity": 0.85, "emergency": 0.70, "surgery": -0.30,
                          "facility": {"F01": -0.35, "F04": -1.2, "F05": -1.2},
                          "dx": {"sepsis": 1.50, "pneumonia": 0.40}},
    },

    # ---- status at 12 hours (block index_eligibility); intercepts solved
    "icu": {"severity": 1.35, "emergency_surgery": 0.30,
            "facility": {"F01": 0.25, "F04": -2.5, "F05": -2.5},
            "dx": {"sepsis": 0.70, "stroke": 0.50, "other_cardiac": 0.40}},
    "comfort_care": {"severity": 1.10, "age_per_year": 0.05, "frailty": 0.50,
                     "dx": {"cancer": 1.00}},

    # ---- death in hospital (block inpatient_death); intercept solved
    "death": {"severity": 1.20, "age_per_year": 0.02, "icu": 0.90, "comfort_care": 2.60},

    # ---- discharge disposition among survivors (block los_disposition).
    # Multinomial logit against "home"; age is (age - 64), comorbidity is (count - 2.5).
    "disposition": {
        "home_health": {"intercept": -1.45, "age_per_year": 0.030, "severity": 0.30,
                        "comorbidity": 0.075},
        "snf": {"intercept": -2.00, "age_per_year": 0.055, "severity": 0.45, "frailty": 0.30,
                "dx": {"ortho_surgical": 0.60, "stroke": 0.90}},
        "hospice": {"intercept": -3.90, "age_per_year": 0.035, "severity": 0.90,
                    "comfort_care": 2.80, "dx": {"cancer": 1.20}},
        "ama": {"intercept": -4.00, "age_per_year": -0.030, "elective": -2.30,
                "payer": {"self_pay": 0.80, "medicaid": 0.50}},
        "transfer": {"severity": 0.80, "icu": 0.70,
                     "facility": {"F01": -5.5, "F02": -3.6, "F03": -3.3, "F04": -1.5,
                                  "F05": -1.5, "F06": -3.2}},
    },
    # ---- length of stay in days: exp(mu + terms + sd * z), at least 0.1
    "los": {"mu": 1.32, "sd": 0.62, "severity": 0.30, "icu": 0.25, "elective_surgery": -0.25,
            "dx": {"ortho_surgical": -0.10, "stroke": 0.15, "sepsis": 0.25},
            "disposition": {"home_health": 0.15, "snf": 0.35, "hospice": 0.20, "ama": -0.90,
                            "transfer": -1.30, "died": 0.10},
            # Very short stays: a share of stays that end at home, against advice, by
            # transfer or in death last a few hours, uniform between min and max days.
            "short_stay": {"share": 0.045, "min": 0.1, "max": 0.4,
                           "dispositions": ("home", "ama", "transfer", "died")}},

    # ---- true 30-day unplanned readmission to any hospital (block readmission).
    # logit p = solved intercept + these terms + the hospital's effect.
    # No term for sex, day of week or season: those effects are zero by construction.
    "readmission": {
        "age_per_year": 0.008, "comorbidity": 0.11, "prior_admits": 0.26, "prior_admits_cap": 4,
        "log_los": 0.18, "emergency": 0.20, "severity": 0.08, "frailty": 0.34,
        "hemoglobin_below_12_per_g": 0.07, "sodium_below_138_per_mmol": 0.03,
        "disposition": {"snf": 0.15, "home_health": 0.12},
        "payer": {"medicaid": 0.38, "medicare": 0.12, "self_pay": 0.22},
        "dx": {"heart_failure": 0.35, "copd": 0.27, "cancer": 0.30, "renal": 0.18,
               "sepsis": 0.10, "ortho_surgical": -0.35, "stroke": -0.05},
        "gap_weight_offset": 6,          # P(gap = g) proportional to 1 / (g + offset), g = 1..30
        "same_facility": 0.85,
    },
    # Six draws per effect, then centred and scaled so that their mean is 0 and
    # their SD is exactly this value (DESIGN.md decision A12).
    "facility_effect_sd": {"readmission": 0.15, "deterioration": 0.15},
    # ---- where a readmission goes (block outside_care): logit P(outside) =
    # the person's outside-care logit + the payer term
    "outside_readmission": {"payer": {"medicaid": 0.40, "self_pay": 0.40}},
    # ---- planned returns (block planned_readmission): drawn among eligible
    # discharges with no unplanned readmission; gap uniform, then moved to a weekday
    "planned_return": {"default": 0.008, "gap_min": 7, "gap_max": 28,
                       "dx": {"cancer": 0.14, "ortho_surgical": 0.04, "other_cardiac": 0.05,
                              "gi": 0.02, "renal": 0.02}},
    # ---- death after discharge, outside hospital (block inpatient_death)
    "death_after_discharge": {
        "severity": 0.90, "age_per_year": 0.03, "horizon_days": 180,
        "intercept": {"home": -5.0, "home_health": -3.9, "snf": -3.3, "hospice": 1.9,
                      "ama": -4.2, "transfer": -2.6},
        "mean_gap_days": {"hospice": 14.0, "other": 45.0},
    },
    # After any live discharge (and after an outside readmission) a person is out of
    # the new-arrival process for this many days. Every return inside the window
    # then comes from the readmission and planned-return steps, so the truth in
    # hidden/ and the record in data/ agree exactly on network readmissions.
    "block_after_discharge_days": 30,

    # ---- the reference cohort the intercepts are solved on (block calibration)
    "reference": {
        "size": 60000,
        "source_mix": {"new": 0.867, "readmission": 0.106, "planned": 0.027},
        "f06_weight": 0.40,              # F06 is in the data for about 21 of 54 months
        "prior_admits_factor": 1.15,
        # Reference-cohort means the intercepts are solved to. The day loop's
        # population differs a little, so CHECKS.md tests the realised values.
        # "deterioration" is the mean true risk among stays on a ward at 12 hours at F01 to F05.
        "targets": {"lactate_drawn": 0.40, "icu": 0.158, "comfort_care": 0.028,
                    "death": 0.0175, "deterioration": 0.0395, "readmission": 0.143},
    },
}

# --------------------------------------------------------------------------
# Deterioration, the vendor's index and alerts (Milestone 3). Every number
# here is a design choice unless PROVENANCE.md gives a source. The intercept of
# the true model is solved on the reference cohort like the others.
# WORLD_SPEC.md section 11 describes the model in prose.
# --------------------------------------------------------------------------
EVENT_TYPES = ("icu_transfer", "transfer_out", "death")
DETERIORATION = {
    # ---- other encounters in the last 12 months (block persons): emergency visits,
    # observation stays and the like, beside admissions. One fixed pair of counts per
    # person. The total is Poisson with mean exp(log_mean + frailty * z + age term);
    # each encounter is outside the network with the person's outside-care
    # propensity, moved by `outside_payer` on the logit scale (mechanism P5).
    "encounters": {"log_mean": 0.95, "frailty": 0.25, "age_per_15": 0.10,
                   "outside_payer": {"medicaid": 3.5, "self_pay": 3.5}},

    # ---- acute instability at the index time (block vitals_true):
    # a = corr * severity + sqrt(1 - corr^2) * z;  h = exp(log_sd * a) - 1
    "acute": {"severity_corr": 0.60, "log_sd": 0.35},
    # true value = mean + instability * h + age term + dx term + sd * z, kept inside min and max
    "vitals_true": {
        "hr": {"mean": 80.0, "instability": 16.0, "sd": 11.0, "min": 35.0, "max": 190.0,
               "dx": {"sepsis": 6.0, "other_cardiac": 3.0, "heart_failure": 2.0, "pneumonia": 3.0}},
        "rr": {"mean": 16.8, "instability": 4.0, "sd": 2.1, "min": 8.0, "max": 48.0,
               "dx": {"copd": 1.6, "pneumonia": 1.6, "heart_failure": 1.0, "sepsis": 1.0}},
        "sbp": {"mean": 127.0, "instability": -14.0, "age_per_15": 3.0, "sd": 17.0, "min": 60.0,
                "max": 230.0, "dx": {"sepsis": -7.0, "heart_failure": -3.0, "stroke": 10.0}},
        "temp_c": {"mean": 36.85, "instability": 0.30, "sd": 0.45, "min": 34.0, "max": 41.5,
                   "dx": {"sepsis": 0.45, "pneumonia": 0.40}},
        # SpO2 also falls by per_unit_of_need for each unit of oxygen need above need_above.
        "spo2": {"mean": 96.8, "instability": -1.1, "age_per_15": -0.2, "sd": 1.0, "min": 70.0,
                 "max": 100.0, "dx": {"copd": -1.0, "pneumonia": -0.8, "heart_failure": -0.5},
                 "need_above": 2.4, "per_unit_of_need": 2.5},
    },
    # Oxygen support and alertness: a latent need (instability * h + terms + z) cut at fixed points.
    "o2_support": {"instability": 1.8, "low_flow_at": 1.5, "high_flow_at": 3.4,
                   "dx": {"copd": 1.2, "pneumonia": 1.1, "heart_failure": 0.6, "sepsis": 0.3}},
    "alertness": {"instability": 1.45, "age_per_15": 0.25, "drowsy_at": 2.0, "confused_at": 2.6,
                  "unresponsive_at": 3.8, "dx": {"stroke": 1.0, "sepsis": 0.3}},

    # ---- recorded vital signs (block vitals_recorded): true value + normal error, rounded
    "vitals_recorded": {
        "hr_sd": 3.0, "rr_sd": 0.8, "sbp_sd": 5.0, "temp_sd": 0.15, "spo2_sd": 0.5,
        # Mechanism P2: the charted default respiratory rate.
        "rr_default": 18, "rr_default_share": {"F04": 0.33, "F05": 0.33, "elsewhere": 0.05},
        # Mechanism P1: upward bias in recorded SpO2 for patients recorded as Black.
        "spo2_bias": {"group": "black", "size": 1.2, "below": 90.0, "size_below": 2.5},
    },
    # Mechanism P4: from DATES["lactate_assay_change"], lactate from the central
    # laboratory (FACILITIES central_lab = 1) reads this much high.
    "assay_shift_mmol": 0.4,

    # ---- how each input enters both formulas: distance beyond a limit
    "features": {"hr_above": 90.0, "rr_above": 18.0, "sbp_below": 110.0, "temp_above": 38.0,
                 "temp_below": 36.0, "spo2_below": 100.0, "lactate_above": 1.0, "lactate_cap": 3.0,
                 "encounters_cap": 8},

    # ---- true risk of deterioration within 48 hours, with no evaluation (block deterioration).
    # logit p0 = solved intercept + the shared terms on TRUE values and on ALL encounters
    #            + comorbidity + dx + severity + winter + hospital effect + unmeasured noise
    "truth": {
        "hr_per_10": 0.12, "rr_per_2": 0.38, "sbp_per_10": 0.18, "temp_per_degree": 0.25,
        "spo2_per_point": 0.34, "o2_low_flow": 0.15, "o2_high_flow": 0.40,
        "drowsy": 0.30, "confused": 0.45, "unresponsive": 1.10,
        "lactate_per_mmol": 0.85, "age_per_10": 0.08, "encounters": 0.24,
        "instability": 0.05,
        "comorbidity": 0.04, "severity": 0.10, "winter": 0.06, "unmeasured_sd": 0.60,
        "dx": {"sepsis": 0.35, "pneumonia": 0.20, "heart_failure": 0.15, "copd": 0.10,
               "stroke": 0.15, "gi": -0.10, "ortho_surgical": -0.40, "diabetes": -0.15},
        # Mechanism P11: Sallowfield's higher event rate, beside its drawn hospital effect.
        "facility_shift": {"F06": 0.20},
        # The intercept is solved on ward stays at the five hospitals that had a silent
        # period, so nothing about Sallowfield moves it.
        "intercept_solved_on": ("F01", "F02", "F03", "F04", "F05"),
    },

    # ---- the vendor's formula (hidden/deterioration/vdi_formula.json), on RECORDED
    # values and NETWORK encounters only. A missing lactate is taken as normal (P3).
    "vendor": {
        "lactate_imputed": 1.0,
        "v2": {"intercept": -5.75,
               "hr_per_10": 0.10, "rr_per_2": 0.43, "sbp_per_10": 0.15, "temp_per_degree": 0.20,
               "spo2_per_point": 0.34, "o2_low_flow": 0.12, "o2_high_flow": 0.35,
               "drowsy": 0.20, "confused": 0.30, "unresponsive": 0.80,
               "lactate_per_mmol": 1.00, "age_per_10": 0.06, "encounters": 0.205},
        # Version 3.0: risk logit = intercept + slope * (version 2.0 risk logit).
        "v3": {"intercept": -0.76, "slope": 0.78},
        # score = round(100 * logistic(shift + scale * risk logit)); one transform per version
        "display": {"2.0": {"shift": 2.63, "scale": 1.00}, "3.0": {"shift": 2.34, "scale": 1.00}},
    },

    # ---- alerts and the rapid-response evaluation (block alert_response)
    # P7: the chance an alert is answered falls with months since the hospital's go-live.
    # P8: an evaluation multiplies the risk by risk_ratio.
    "response": {"start": 0.85, "fall_per_month": 0.0075, "floor": 0.70, "risk_ratio": 0.80},

    # ---- what the event is (block deterioration), by hospital
    "event_type": {
        "elsewhere": {"icu_transfer": 0.80, "transfer_out": 0.10, "death": 0.10},
        "by_facility": {"F01": {"icu_transfer": 0.90, "transfer_out": 0.00, "death": 0.10},
                        "F04": {"icu_transfer": 0.15, "transfer_out": 0.75, "death": 0.10},
                        "F05": {"icu_transfer": 0.15, "transfer_out": 0.75, "death": 0.10}},
    },
    # ---- what the event does to the stay
    "course": {
        # death or transfer out: the stay ends inside the 48-hour window after the index time
        "window_los": {"min": 0.6, "max": 2.5},
        # transfer to intensive care: a longer stay and an added chance of death
        "icu_transfer_los_factor": 1.5, "icu_transfer_los_add": 1.0,
        "death_after_icu_transfer": 0.10,
    },
    # ---- the EHR outcome flag (block ehr_outcome), mechanism P9. A transfer out is
    # often coded as a plain transfer, so the flag misses it more often.
    "ehr_flag": {"miss": {"icu_transfer": 0.065, "death": 0.065, "transfer_out": 0.18},
                 "false_positive": 0.004},
}

# The vendor's model card, as a customer receives it (data/deterioration/vendor_model_card.json).
# Every claim in it is invented, like the vendor.
VENDOR_MODEL_CARD = {
    "fictional": ("Venncroft and the Venncroft Deterioration Index are invented for the Tonmick "
                  "Health practice world. Nothing here describes a real vendor, product or study."),
    "vendor": "Venncroft",
    "product": "Venncroft Deterioration Index",
    "abbreviation": "VDI",
    "intended_use": ("Adults admitted to a general ward. One score 12 hours after admission. Not for "
                     "patients in intensive care or on comfort care at that time."),
    "outcome_predicted": ("Unplanned transfer to intensive care, unplanned transfer to a higher level "
                          "of care, or death, within 48 hours of the score."),
    "inputs": [
        "Heart rate", "Respiratory rate", "Systolic blood pressure", "Temperature",
        "Oxygen saturation by pulse oximeter", "Oxygen support", "Alertness category",
        "Latest lactate (a normal value is assumed when none is on file)",
        "Age", "Encounters at the customer's organisation in the last 12 months",
    ],
    "score": ("0 to 100; a higher score means a higher risk. vendor_risk_table.csv gives the "
              "vendor's stated risk at each score."),
    "alert_threshold": VDI["threshold"],
    "development_population": {
        "description": "Adult ward admissions at 14 hospitals in the vendor's development network",
        "years": "2018 to 2021",
        "encounters": 412000,
        "event_rate": 0.045,
    },
    "claimed_performance": {"c_statistic": VDI["vendor_claimed_c"],
                            "basis": "The vendor's own multi-site data, split-sample validation"},
    "performance_by_subgroup": "Not reported",
    "versions": [
        {"version": "2.0", "at_tonmick_from": DATES["vdi_silent_start"],
         "note": "Scored in silent mode at first; alert dates are in facilities.csv"},
        {"version": "3.0", "at_tonmick_from": DATES["vdi_v3"],
         "note": ("Recalibration on pooled customer data. Inputs and alert threshold are unchanged. "
                  "The score still runs from 0 to 100; its risk table is new. Customers were told to "
                  "expect fewer alerts.")},
    ],
    "formula": "Proprietary. Not disclosed to customers.",
}

# --------------------------------------------------------------------------
# The AI scribe (Milestone 5). Every number here is a design choice unless
# DESIGN.md sections 6.3 and 9.4 to 9.5 fixed it at Milestone 0; PROVENANCE.md
# section 4 says which is which. The scribe shares no random block and no
# person with the inpatient world.
# --------------------------------------------------------------------------
SPECIALTY_GROUPS = {            # audit strata use these three groups
    "primary_care": ("primary_care",),
    "medical": ("cardiology", "oncology", "endocrinology", "pulmonology"),
    "procedural": ("orthopaedics", "gastroenterology"),
}
VISIT_TYPES = ("new", "follow_up", "annual", "procedure")
ADOPTION_TYPES = ("adopter", "partial", "never")
SURVEY_WAVES = ("baseline", "post_wave", "final")
SCRIBE = {
    # ---- clinics and clinicians (block clinics_clinicians)
    "clinics": [    # clinic_id, clinic_type, specialty, area
        ("C01", "primary_care", "primary_care", "central"), ("C02", "primary_care", "primary_care", "central"),
        ("C03", "primary_care", "primary_care", "central"), ("C04", "primary_care", "primary_care", "central"),
        ("C05", "primary_care", "primary_care", "central"), ("C06", "primary_care", "primary_care", "central"),
        ("C07", "primary_care", "primary_care", "central"), ("C08", "primary_care", "primary_care", "central"),
        ("C09", "primary_care", "primary_care", "south"), ("C10", "primary_care", "primary_care", "south"),
        ("C11", "primary_care", "primary_care", "south"), ("C12", "primary_care", "primary_care", "south"),
        ("C13", "primary_care", "primary_care", "south"), ("C14", "primary_care", "primary_care", "north"),
        ("C15", "primary_care", "primary_care", "north"), ("C16", "primary_care", "primary_care", "north"),
        ("C17", "specialty", "cardiology", "central"), ("C18", "specialty", "cardiology", "south"),
        ("C19", "specialty", "oncology", "central"), ("C20", "specialty", "orthopaedics", "central"),
        ("C21", "specialty", "orthopaedics", "south"), ("C22", "specialty", "endocrinology", "central"),
        ("C23", "specialty", "pulmonology", "central"), ("C24", "specialty", "gastroenterology", "central"),
    ],
    "clinicians": 130,                       # exact: three to each clinic, the rest by weighted draw
    "clinic_min_clinicians": 3,
    "clinic_size_weight": {"primary_care": 1.4, "specialty": 1.0},
    "roles": {"physician": 0.60, "np": 0.25, "pa": 0.15},
    "fte": ((1.0, 0.55), (0.8, 0.20), (0.6, 0.15), (0.5, 0.10)),
    "interpreter_logit": {"mean": -2.75, "sd": 0.45},     # clinic's share of visits with an interpreter
    # ---- rollout (block rollout_draw): each stratum is shuffled and dealt to the waves in turn
    "wave_weeks": (14, 27, 40, 53),          # week_index of each go-live; 51, 38, 25 and 12 live weeks
    "version_24_week": 44,                   # week_index of the Monday version 2.4 arrived
    # ---- calendar
    "holiday_weeks": {                       # week_start -> share of normal volume
        "2025-05-26": 0.80, "2025-06-30": 0.80, "2025-09-01": 0.80,
        "2025-11-24": 0.60, "2025-12-22": 0.55, "2025-12-29": 0.60,
    },
    "closed_dates": ("2025-05-26", "2025-07-04", "2025-09-01", "2025-11-27", "2025-11-28",
                     "2025-12-25", "2026-01-01"),
    # ---- clinician traits (block clinician_traits)
    "baseline_doc": {"primary_care": 7.0, "specialty": 8.0, "log_sd": 0.22},   # minutes per visit
    "effect_minutes": {"mean": 2.0, "sd": 0.6, "low": 0.4, "high": 3.6},      # saving per scribe visit
    "after_hours": {"mean_at_full_time": 170.0, "log_sd": 0.45, "weight_on_baseline_doc": 0.5,
                    "week_log_sd": 0.30, "away_share": 0.20},
    "same_day_close": {"logit_mean": 0.9, "logit_sd": 0.7, "week_logit_sd": 0.35},
    "wellbeing": {"weight_on_baseline_doc": -0.35, "wave_drift_sd": 0.30,
                  "effect": {"adopter": (0.25, 0.08, 0.05, 0.45),      # mean, SD, low, high
                             "partial": (0.08, 0.05, 0.00, 0.20),
                             "never": (0.0, 0.0, 0.0, 0.0)}},
    "visit_volume": {"per_fte_week": {"primary_care": 56.0, "specialty": 46.0},
                     "clinician_log_sd": 0.12, "away_probability": 0.04},
    # ---- adoption (block adoption). Types are dealt by rank of a latent propensity, so the
    #      shares are exact: the 13 lowest never adopt, the next 18 are partial users.
    "adoption": {"weight_on_baseline_doc": 0.9, "never": 13, "partial": 18,
                 "steady_share_logit": {"adopter": (1.2, 0.6), "partial": (-1.2, 0.5)},
                 "ramp": (0.35, 0.55, 0.70, 0.82, 0.91, 0.96)},   # share of the steady share, by live week
    # ---- the clinician-week panel (block clinician_weeks)
    "panel": {
        "trend_per_week": -0.02,             # minutes per visit, every clinician, scribe or not
        "learning": (0.5, 0.5, 0.5, 0.5, 0.625, 0.75, 0.875),    # share of the effect, live weeks 1 to 7; then 1
        "steady_from_live_week": 8,
        "week_shock_sd": 0.30, "visit_sd": 3.0, "doc_floor": 1.0,
        "after_hours_effect": -0.20,         # relative, at full use
        "visits_effect": 0.4,                # visits per clinician-week, at full use
        "same_day_close_effect_logit": 0.5,  # at full use
    },
    # ---- survey (block survey). The Tonmick Clinician Pulse: five invented items, 1 to 5.
    "survey": {
        "response_target": 0.62, "response_slope": 0.7,
        "post_wave_months": ("2025-07", "2025-10", "2026-01"),     # waves 1 to 3; wave 4 has none
        "items": [   # loading on latent wellbeing, shift, wording
            (0.75, 0.0, "I finish my notes within my scheduled working day."),
            (0.80, -0.2, "At the end of a clinic day I still have energy for the rest of my life."),
            (0.65, 0.1, "The record system helps me more than it slows me down."),
            (0.70, 0.2, "I can give each patient my full attention during the visit."),
            (0.75, -0.1, "I would recommend my current way of working to a colleague."),
        ],
        "item_centre": 3.1, "item_scale": 0.85,
        "scale": "1 = strongly disagree, 2 = disagree, 3 = neither, 4 = agree, 5 = strongly agree",
    },
    # ---- notes frame (block notes_frame)
    "notes": {
        "visit_type": {"primary_care": (0.10, 0.62, 0.25, 0.03), "specialty": (0.22, 0.58, 0.02, 0.18)},
        "visit_minutes": {"new": 32.0, "follow_up": 19.0, "annual": 30.0, "procedure": 26.0,
                          "log_sd": 0.30, "interpreter_factor": 1.25, "low": 5, "high": 90},
        "speakers": (0.62, 0.27, 0.08, 0.02, 0.01),      # 2 to 6 speakers before any interpreter
        "words_per_minute": 17.0, "words_log_sd": 0.25, "words_low": 60,
        "edit": {"base": 0.8, "per_error": 0.5, "per_visit_minute": 0.02, "gamma_shape": 3.0},
    },
    # ---- true errors (block note_errors). Intercepts are solved on the version 2.3 notes.
    "errors": {
        "target_v23": {"omission": 0.170, "hallucination": 0.105, "misattribution": 0.085,
                       "wrong_value": 0.050},
        "major_target_v23": 0.015,
        "odds_ratio": {"omission_interpreter": 1.8, "omission_long_visit": 1.5,
                       "misattribution_three_speakers": 1.6, "hallucination_v24": 0.70},
        "long_visit_minutes": 30, "many_speakers": 3,
        "clinic_logit_sd": 0.25,             # 24 draws, centred and scaled to this SD exactly
        "extra_count_mean": 0.35,            # a note with an error has 1 + Poisson(this) of them
        "moderate_per_error": 0.30,          # chance that one error is moderate or worse
        "intercept_decimals": 6,
    },
    # ---- audit (blocks audit_sample, rater_parameters, ratings)
    "audit": {
        "allocation": {      # (specialty group, interpreter, version) -> notes drawn; 1,200 in all
            ("primary_care", 0, "2.3"): 220, ("primary_care", 0, "2.4"): 220,
            ("medical", 0, "2.3"): 110, ("medical", 0, "2.4"): 110,
            ("procedural", 0, "2.3"): 90, ("procedural", 0, "2.4"): 90,
            ("primary_care", 1, "2.3"): 60, ("primary_care", 1, "2.4"): 60,
            ("medical", 1, "2.3"): 60, ("medical", 1, "2.4"): 60,
            ("procedural", 1, "2.3"): 60, ("procedural", 1, "2.4"): 60,
        },
        "rater_sensitivity": (0.70, 0.92), "lenient_sensitivity": (0.57, 0.63),
        "rater_false_positive": (0.01, 0.05),
        "senior_sensitivity": (0.95, 0.98), "senior_false_positive": (0.004, 0.010),
        "severity_agree": 0.75, "severity_lower": 0.17,       # the rest rate one level higher
        "false_alarm_minor": 0.85,
    },
}


def audit_stratum_code(group, interpreter, version):
    return f"{group}-{'interp' if interpreter else 'no_interp'}-v{version}"


AUDIT_STRATA = tuple(audit_stratum_code(g, i, v) for g in SPECIALTY_GROUPS for i in (0, 1)
                     for v in SCRIBE_VERSIONS)

# --------------------------------------------------------------------------
# Costs and wages (Milestone 5). Block 44 (costs) draws nothing: these tables
# are written as they stand. Prices are invented. Wages are public national
# figures; PROVENANCE.md section 6 gives each source and the date it was seen.
# --------------------------------------------------------------------------
ECONOMICS = {
    "loading": 1.46,     # total compensation over wages, all civilian workers, March 2026
    "wages": [           # role, hourly wage, what the figure is
        ("physician", 122.99, "family medicine physicians, national mean annual wage 255,820 over 2,080 hours, May 2025"),
        ("hospitalist", 128.46, "general internal medicine physicians, national mean annual wage 267,200 over 2,080 hours, May 2025"),
        ("np", 66.01, "nurse practitioners, national mean annual wage 137,300 over 2,080 hours, May 2025"),
        ("pa", 67.92, "physician assistants, national mean annual wage 141,280 over 2,080 hours, May 2025"),
        ("rn", 48.76, "registered nurses, national mean annual wage 101,420 over 2,080 hours, May 2025"),
        ("it_analyst", 50.89, "computer systems analysts, national median annual wage 105,850 over 2,080 hours, May 2025"),
        ("manager", 67.77, "medical and health services managers, national mean annual wage 140,970 over 2,080 hours, May 2025"),
    ],
    "wage_source": "US Bureau of Labor Statistics, Occupational Employment and Wage Statistics",
    "costs": [   # cost_line, unit, unit_cost, quantity, wage_role, quantity_basis, notes
        ("licence", "clinician-month", 275.00, None, None,
         "count the calendar months in which a clinician has at least one scribe visit",
         "invented price; public reporting puts ambient scribes at about 100 to 600 US dollars per clinician per month"),
        ("implementation", "one time", 60000.00, 1.0, None, "once, before the first wave", "invented price; design choice"),
        ("it_integration", "hour", None, 480.0, "it_analyst", "hours in total, before and during the rollout", "design choice"),
        ("training", "hour", None, 2.0, "clinician", "hours for each clinician, at that clinician's own role in wage_rates.csv", "design choice"),
        ("audit_rating", "hour", None, 0.2, "physician", "hours for each rating in rounds 1 and 2 of audit_ratings.csv", "design choice"),
        ("audit_adjudication", "hour", None, 0.25, "physician", "hours for each round 3 rating in audit_ratings.csv", "design choice"),
        ("committee", "hour", None, 120.0, "manager", "committee hours spent on the scribe review, in total", "design choice"),
    ],
}

# --------------------------------------------------------------------------
# Budgets
# --------------------------------------------------------------------------
BUDGET = {"data_mb": 70, "hidden_mb": 50, "file_mb": 45, "generation_minutes": 5}

# --------------------------------------------------------------------------
# File metadata. One entry per CSV (a "{year}" in the path means one file per
# year in `years`). The writer, dictionary.py, the schema tests and the
# dictionary-coverage check all read this table.
#
# Column tuple: (name, type, decimals, type_or_range, meaning)
#   type: id | int | float | flag | code | date | datetime | month | text
#   decimals: fixed number of decimals for float columns, else None
# Dates are ISO 8601; missing values are empty fields; flags are 0 or 1.
# --------------------------------------------------------------------------
COLUMN_TYPES = ("id", "int", "float", "flag", "code", "date", "datetime", "month", "text")
PUBLISHED_YEARS = (2022, 2023, 2024, 2025, 2026)
SIMULATED_YEARS = (2021,) + PUBLISHED_YEARS

_ADMISSION_COLUMNS = [
    ("encounter_id", "id", None, "E00000001", "Encounter (admission) ID"),
    ("person_id", "id", None, "P0000001", "Person ID; key to persons.csv"),
    ("facility_id", "id", None, "F01-F06", "Admitting hospital"),
    ("admit_datetime", "datetime", None, "YYYY-MM-DDTHH:00", "Admission date and hour"),
    ("discharge_date", "date", None, "YYYY-MM-DD", "Discharge or death date; empty if still in hospital when the data end"),
    ("los_days", "float", 1, ">= 0.1", "Length of stay in days; empty if still in hospital"),
    ("age", "int", None, "18-105", "Age in years at admission"),
    ("payer", "code", None, "medicare|medicaid|commercial|self_pay", "Payer at admission"),
    ("admission_type", "code", None, "emergency|elective", "Emergency or elective admission"),
    ("service", "code", None, "medicine|surgery", "Admitting service"),
    ("dx_group", "code", None, "|".join(DX_GROUPS), "Invented principal diagnosis group"),
    ("comorbidity_count", "int", None, "0-12", "Invented count of chronic-condition flags"),
    ("prior_admits_12m", "int", None, ">= 0", "Network admissions in the 12 months before this one, as the network's record sees them"),
    ("planned_admission", "flag", None, "0|1", "1 = a planned return, scheduled at an earlier discharge"),
    ("sodium", "float", 0, "mmol/L", "Admission sodium, as recorded; empty if not measured"),
    ("creatinine", "float", 2, "mg/dL", "Admission creatinine, as recorded; empty if not measured"),
    ("hemoglobin", "float", 1, "g/dL", "Admission hemoglobin, as recorded; empty if not measured"),
    ("wbc", "float", 1, "10^9/L", "Admission white cell count, as recorded; empty if not measured"),
    ("lactate", "float", 1, "mmol/L", "Admission lactate, as recorded; empty if not drawn"),
    ("icu_at_12h", "flag", None, "0|1", "1 = in intensive care 12 hours after admission"),
    ("comfort_care_12h", "flag", None, "0|1", "1 = on comfort care 12 hours after admission"),
    ("disposition", "code", None, "|".join(DISPOSITIONS), "Discharge disposition; empty if still in hospital"),
    ("died_in_hospital", "flag", None, "0|1", "1 = died during this admission"),
]

FILES = {
    # ------------------------------------------------------------ data/network
    "data/network/facilities.csv": {
        "module": "network", "milestone": "M2", "sort_by": ["facility_id"], "columns": [
            ("facility_id", "id", None, "F01-F06", "Hospital ID"),
            ("facility_name", "text", None, "", "Fictional hospital name"),
            ("facility_type", "code", None, "|".join(FACILITY_TYPES), "Type of hospital"),
            ("area", "code", None, "|".join(AREAS), "Coarse fictional area"),
            ("beds", "int", None, "> 0", "Staffed beds"),
            ("network_data_from", "date", None, "YYYY-MM-DD", "First date the hospital's admissions are in network data"),
            ("vdi_scoring_from", "date", None, "YYYY-MM-DD", "First date VDI scores were calculated here"),
            ("vdi_alerts_from", "date", None, "YYYY-MM-DD", "First date VDI alerts were shown here"),
            ("central_lab", "flag", None, "0|1", "1 = served by the central laboratory"),
        ]},
    "data/network/timeline.csv": {
        "module": "network", "milestone": "M2", "sort_by": ["event_date", "event_code"], "columns": [
            ("event_date", "date", None, "YYYY-MM-DD", "Date of the event"),
            ("event_code", "code", None, "short code", "Event code"),
            ("scope", "text", None, "", "Facilities or clinics affected"),
            ("description", "text", None, "", "What happened, as the network announced it"),
        ]},
    "data/network/lab_change_log.csv": {
        "module": "deterioration", "milestone": "M4", "sort_by": ["log_id"], "columns": [
            ("log_id", "id", None, "L0001", "Change-log entry ID"),
            ("effective_date", "date", None, "YYYY-MM-DD", "Date the change took effect"),
            ("lab_site", "code", None, "central|northfen|pellow_lake|sallowfield", "Laboratory that made the change"),
            ("facilities", "text", None, "F01;F02", "Hospitals served, separated by semicolons"),
            ("test_area", "code", None, "|".join(LAB_TEST_AREAS), "Area of testing"),
            ("change_type", "code", None, "|".join(LAB_CHANGE_TYPES), "Kind of change"),
            ("description", "text", None, "", "The entry as the laboratory wrote it"),
        ]},
    # ---------------------------------------------------------- data/inpatient
    "data/inpatient/persons.csv": {
        "module": "inpatient", "milestone": "M2", "sort_by": ["person_id"], "columns": [
            ("person_id", "id", None, "P0000001", "Person ID"),
            ("sex", "code", None, "f|m", "Recorded sex"),
            ("birth_year", "int", None, "1915-2008", "Year of birth"),
            ("race_ethnicity", "code", None, "|".join(RACE_ETHNICITY), "Recorded race and ethnicity, one combined field"),
            ("interpreter_needed", "flag", None, "0|1", "1 = an interpreter is needed"),
            ("home_area", "code", None, "|".join(AREAS), "Coarse fictional home area"),
        ]},
    "data/inpatient/admissions_{year}.csv": {
        "module": "inpatient", "milestone": "M2", "years": PUBLISHED_YEARS,
        "sort_by": ["encounter_id"], "columns": _ADMISSION_COLUMNS},
    # -------------------------------------------------------- data/readmission
    "data/readmission/r30_development_sample.csv": {
        "module": "r30", "milestone": "M4", "sort_by": ["encounter_id"], "columns": [
            ("encounter_id", "id", None, "E00000001", "Index discharge"),
            ("readmit_30d_observed", "flag", None, "0|1", "Unplanned network readmission within 30 days, as the team recorded it"),
            ("age_65_plus", "flag", None, "0|1", "Age 65 or over"),
            ("female", "flag", None, "0|1", "Recorded sex female"),
            ("los_over_5", "flag", None, "0|1", "Length of stay over 5 days"),
            ("prior_admits_cat", "int", None, "0|1|2", "Prior admissions in 12 months: 0, 1, 2 or more"),
            ("comorbidity_count", "int", None, "0-12", "Comorbidity count"),
            ("disp_snf", "flag", None, "0|1", "Discharged to skilled nursing"),
            ("disp_home_health", "flag", None, "0|1", "Discharged home with home health"),
            ("medicaid", "flag", None, "0|1", "Payer is Medicaid"),
            ("sodium_low", "flag", None, "0|1", "Sodium below 135"),
            ("hemoglobin_low", "flag", None, "0|1", "Hemoglobin below 12"),
            ("dx_cancer", "flag", None, "0|1", "Diagnosis group cancer"),
            ("dx_heart_failure", "flag", None, "0|1", "Diagnosis group heart failure"),
            ("dx_copd", "flag", None, "0|1", "Diagnosis group COPD or respiratory"),
            ("emergency", "flag", None, "0|1", "Emergency admission"),
            ("weekend_discharge", "flag", None, "0|1", "Discharged on a Saturday or Sunday"),
            ("winter_discharge", "flag", None, "0|1", "Discharged in December, January or February"),
        ]},
    "data/readmission/r30_scores.csv": {
        "module": "r30", "milestone": "M4", "sort_by": ["encounter_id"], "columns": [
            ("encounter_id", "id", None, "E00000001", "Index discharge"),
            ("score_date", "date", None, "YYYY-MM-DD", "Date production calculated the score"),
            ("r30_risk", "float", 6, "0-1", "Predicted 30-day readmission risk from R30"),
        ]},
    # ------------------------------------------------------ data/deterioration
    "data/deterioration/index_encounters.csv": {
        "module": "deterioration", "milestone": "M3", "sort_by": ["encounter_id"], "columns": [
            ("encounter_id", "id", None, "E00000001", "Encounter ID; key to the admissions files"),
            ("facility_id", "id", None, "F01-F06", "Hospital"),
            ("index_datetime", "datetime", None, "YYYY-MM-DDTHH:00", "Index time: 12 hours after admission"),
            ("hr", "float", 0, "beats/min", "Heart rate, as recorded"),
            ("rr", "float", 0, "breaths/min", "Respiratory rate, as recorded"),
            ("sbp", "float", 0, "mmHg", "Systolic blood pressure, as recorded"),
            ("temp_c", "float", 1, "deg C", "Temperature, as recorded"),
            ("spo2", "float", 0, "percent", "Oxygen saturation by pulse oximeter, as recorded"),
            ("o2_support", "code", None, "|".join(O2_SUPPORT), "Oxygen support"),
            ("alertness", "code", None, "|".join(ALERTNESS), "Alertness category (invented scale)"),
            ("lactate_at_index", "float", 1, "mmol/L", "Latest lactate available at the index time; empty if none"),
            ("network_encounters_12m", "int", None, ">= 0", "Network encounters in the last 12 months, as VDI sees them"),
            ("vdi_score", "int", None, "0-100", "Vendor deterioration index"),
            ("vdi_version", "code", None, "2.0|3.0", "VDI version in force"),
            ("vdi_shown", "flag", None, "0|1", "1 = the score was visible to staff (alerts live)"),
            ("alert_fired", "flag", None, "0|1", "1 = score shown and at or above the threshold"),
            ("rrt_evaluated", "flag", None, "0|1", "1 = a rapid-response evaluation followed the alert"),
            ("ehr_outcome_48h", "flag", None, "0|1", "EHR flag for deterioration within 48 hours; empty if the label was not yet available when the data end"),
            ("outcome_available_date", "date", None, "YYYY-MM-DD", "Date the outcome label became available; empty if that is after the data end"),
        ]},
    "data/deterioration/vendor_risk_table.csv": {
        "module": "deterioration", "milestone": "M3", "sort_by": ["vdi_version", "vdi_score"], "columns": [
            ("vdi_version", "code", None, "2.0|3.0", "VDI version"),
            ("vdi_score", "int", None, "0-100", "Score"),
            ("vendor_risk", "float", 4, "0-1", "Vendor's stated risk of deterioration within 48 hours at this score"),
        ]},
    "data/deterioration/chart_review.csv": {
        "module": "deterioration", "milestone": "M4", "sort_by": ["encounter_id"], "columns": [
            ("encounter_id", "id", None, "E00000001", "Reviewed silent-mode encounter"),
            ("stratum", "int", None, "1-10", "Stratum: 1 plus the number of score deciles the encounter's score is above, among silent-mode encounters"),
            ("stratum_size", "int", None, "> 0", "Encounters in the stratum"),
            ("stratum_sampled", "int", None, "> 0", "Encounters sampled from the stratum"),
            ("incl_prob", "float", 6, "0-1", "Inclusion probability"),
            ("reviewer_outcome", "flag", None, "0|1", "Deterioration within 48 hours, by clinician chart review"),
        ]},
    "data/deterioration/rrt_log.csv": {
        "module": "deterioration", "milestone": "M4", "sort_by": ["rrt_id"], "columns": [
            ("rrt_id", "id", None, "RR000001", "Rapid-response evaluation ID"),
            ("encounter_id", "id", None, "E00000001", "Encounter evaluated"),
            ("rrt_datetime", "datetime", None, "YYYY-MM-DDTHH:00", "Time the evaluation began"),
            ("nurse_minutes", "float", 0, "minutes", "Nurse time spent"),
            ("physician_minutes", "float", 0, "minutes", "Physician time spent"),
        ]},
    # ------------------------------------------------------------- data/scribe
    "data/scribe/clinics.csv": {
        "module": "scribe_audit", "milestone": "M5", "sort_by": ["clinic_id"], "columns": [
            ("clinic_id", "id", None, "C01-C24", "Clinic ID"),
            ("clinic_type", "code", None, "primary_care|specialty", "Clinic type"),
            ("specialty", "code", None, "primary_care|" + "|".join(SPECIALTIES), "Clinic specialty"),
            ("area", "code", None, "|".join(AREAS), "Coarse fictional area"),
            ("n_clinicians", "int", None, "> 0", "Clinicians in the pilot at this clinic"),
        ]},
    "data/scribe/clinicians.csv": {
        "module": "scribe_audit", "milestone": "M5", "sort_by": ["clinician_id"], "columns": [
            ("clinician_id", "id", None, "K001", "Clinician ID"),
            ("clinic_id", "id", None, "C01-C24", "Clinic"),
            ("role", "code", None, "physician|np|pa", "Role"),
            ("specialty", "code", None, "primary_care|" + "|".join(SPECIALTIES), "Specialty"),
            ("fte", "float", 1, "0.5-1.0", "Clinical full-time equivalent"),
        ]},
    "data/scribe/rollout.csv": {
        "module": "scribe_audit", "milestone": "M5", "sort_by": ["clinic_id"], "columns": [
            ("clinic_id", "id", None, "C01-C24", "Clinic"),
            ("stratum", "code", None, "primary_care|specialty", "Randomisation stratum"),
            ("wave", "int", None, "1-4", "Rollout wave drawn"),
            ("go_live_date", "date", None, "YYYY-MM-DD", "Monday the scribe went live at the clinic"),
        ]},
    "data/scribe/clinician_weeks.csv": {
        "module": "scribe_value", "milestone": "M5", "sort_by": ["clinician_id", "week_start"], "columns": [
            ("clinician_id", "id", None, "K001", "Clinician"),
            ("clinic_id", "id", None, "C01-C24", "Clinic"),
            ("week_start", "date", None, "YYYY-MM-DD", "Monday starting the week"),
            ("week_index", "int", None, "1-64", "Week of the measurement period"),
            ("clinic_live", "flag", None, "0|1", "1 = the scribe is live at the clinic this week"),
            ("weeks_since_go_live", "int", None, ">= 0", "Whole weeks since the clinic went live, 0 in the go-live week; empty before go-live"),
            ("holiday_week", "flag", None, "0|1", "1 = a low-volume holiday week"),
            ("visits", "int", None, ">= 0", "Visits this week"),
            ("scribe_visits", "int", None, ">= 0", "Visits where the scribe drafted the note"),
            ("scribe_share", "float", 3, "0-1", "scribe_visits divided by visits; empty when visits is 0"),
            ("doc_minutes_per_visit", "float", 1, "minutes", "Documentation time per visit, from EHR audit logs; empty when visits is 0"),
            ("after_hours_minutes", "float", 0, "minutes", "EHR time outside scheduled hours this week"),
            ("same_day_close_share", "float", 3, "0-1", "Share of notes closed the same day; empty when visits is 0"),
        ]},
    "data/scribe/wellbeing_survey.csv": {
        "module": "scribe_value", "milestone": "M5", "sort_by": ["clinician_id", "survey_wave"], "columns": [
            ("clinician_id", "id", None, "K001", "Clinician"),
            ("survey_wave", "code", None, "baseline|post_wave|final", "Survey wave; clinicians at wave 4 clinics have no post_wave row"),
            ("survey_month", "month", None, "YYYY-MM", "Month the survey was fielded"),
            ("responded", "flag", None, "0|1", "1 = the clinician responded"),
            ("item1", "int", None, "1-5", "Tonmick Clinician Pulse item 1; empty if no response"),
            ("item2", "int", None, "1-5", "Tonmick Clinician Pulse item 2; empty if no response"),
            ("item3", "int", None, "1-5", "Tonmick Clinician Pulse item 3; empty if no response"),
            ("item4", "int", None, "1-5", "Tonmick Clinician Pulse item 4; empty if no response"),
            ("item5", "int", None, "1-5", "Tonmick Clinician Pulse item 5; empty if no response"),
        ]},
    "data/scribe/ai_notes_frame.csv": {
        "module": "scribe_audit", "milestone": "M5", "sort_by": ["note_id"], "columns": [
            ("note_id", "id", None, "N0000001", "Note ID"),
            ("visit_date", "date", None, "YYYY-MM-DD", "Date of the visit"),
            ("week_start", "date", None, "YYYY-MM-DD", "Monday starting the visit's week"),
            ("clinic_id", "id", None, "C01-C24", "Clinic"),
            ("clinician_id", "id", None, "K001", "Clinician"),
            ("specialty", "code", None, "primary_care|" + "|".join(SPECIALTIES), "Specialty"),
            ("visit_type", "code", None, "|".join(VISIT_TYPES), "Visit type"),
            ("visit_minutes", "float", 0, "minutes", "Length of the visit"),
            ("interpreter_used", "flag", None, "0|1", "1 = an interpreter took part"),
            ("n_speakers", "int", None, "2-6", "Speakers in the room, the interpreter included"),
            ("scribe_version", "code", None, "2.3|2.4", "Scribe model version"),
            ("note_words", "int", None, "> 0", "Words in the AI draft"),
            ("edit_minutes", "float", 1, "minutes", "Clinician time editing the draft"),
        ]},
    "data/scribe/audit_sample.csv": {
        "module": "scribe_audit", "milestone": "M5", "sort_by": ["note_id"], "columns": [
            ("note_id", "id", None, "N0000001", "Sampled note"),
            ("stratum", "code", None, "|".join(AUDIT_STRATA), "Sampling stratum: specialty group (primary_care; medical = cardiology, oncology, endocrinology, pulmonology; procedural = orthopaedics, gastroenterology), interpreter used or not, scribe version"),
            ("stratum_size", "int", None, "> 0", "Notes in the stratum"),
            ("stratum_sampled", "int", None, "> 0", "Notes sampled from the stratum"),
            ("incl_prob", "float", 6, "0-1", "Inclusion probability"),
        ]},
    "data/scribe/audit_ratings.csv": {
        "module": "scribe_audit", "milestone": "M5", "sort_by": ["note_id", "rating_round"], "columns": [
            ("note_id", "id", None, "N0000001", "Rated note"),
            ("rating_round", "int", None, "1|2|3", "1 and 2 = independent ratings; 3 = the senior reviewer's rating, present when rounds 1 and 2 differ in any field"),
            ("rater_id", "id", None, "R01-R09", "Rater; R09 is the senior reviewer"),
            ("omission", "flag", None, "0|1", "Rater found at least one omission"),
            ("hallucination", "flag", None, "0|1", "Rater found content that was not said"),
            ("misattribution", "flag", None, "0|1", "Rater found content attributed to the wrong speaker or person"),
            ("wrong_value", "flag", None, "0|1", "Rater found a wrong number or dose"),
            ("severity", "code", None, "|".join(SEVERITIES), "Worst severity the rater assigned; none when the rater found no error"),
        ]},
    # ---------------------------------------------------------- data/economics
    "data/economics/scribe_costs.csv": {
        "module": "scribe_value", "milestone": "M5", "sort_by": ["cost_line"], "columns": [
            ("cost_line", "code", None, "short code", "Cost line"),
            ("unit", "text", None, "", "Unit the cost is quoted in"),
            ("unit_cost", "float", 2, "USD", "Cost per unit (invented price); empty when the unit is an hour, costed from wage_rates.csv"),
            ("quantity", "float", 2, ">= 0", "Number of units; empty when the units are counted from the data"),
            ("wage_role", "code", None, "physician|it_analyst|manager|clinician", "Role in wage_rates.csv that prices an hour; clinician = the clinician's own role; empty when unit_cost is given"),
            ("quantity_basis", "text", None, "", "How to count units"),
            ("notes", "text", None, "", "Source note or 'design choice'"),
        ]},
    "data/economics/wage_rates.csv": {
        "module": "scribe_value", "milestone": "M5", "sort_by": ["role"], "columns": [
            ("role", "code", None, "physician|hospitalist|np|pa|rn|it_analyst|manager", "Staff role; physician, np and pa match clinicians.csv; rn and hospitalist price the rapid-response log"),
            ("hourly_wage", "float", 2, "USD per hour", "Published national wage per hour, before benefits"),
            ("loaded_hourly_cost", "float", 2, "USD per hour", "Hourly wage times the loading for benefits"),
            ("source_note", "text", None, "", "What the wage figure is and where it was published"),
        ]},
    # -------------------------------------------------------- hidden/inpatient
    "hidden/inpatient/facility_truth.csv": {
        "module": "inpatient", "milestone": "M2", "sort_by": ["facility_id"], "columns": [
            ("facility_id", "id", None, "F01-F06", "Hospital"),
            ("readmit_effect_logit", "float", 6, "logit", "True facility effect on readmission"),
            ("deterioration_effect_logit", "float", 6, "logit", "True facility effect on deterioration"),
        ]},
    "hidden/inpatient/persons_truth.csv": {
        "module": "inpatient", "milestone": "M2", "sort_by": ["person_id"], "columns": [
            ("person_id", "id", None, "P0000001", "Person"),
            ("in_published_data", "flag", None, "0|1", "1 = the person is in data/inpatient/persons.csv; 0 = admitted only in the 2021 burn-in"),
            ("frailty", "float", 6, "standardised", "Unmeasured frailty"),
            ("outside_care_propensity", "float", 6, "0-1", "Propensity to use non-network hospitals"),
            ("death_date", "date", None, "YYYY-MM-DD", "Date of death, in a network hospital or within 180 days of a network discharge; empty if no such death by the end of the data"),
            ("death_place", "code", None, "network_hospital|outside", "Where the person died; empty if alive"),
        ]},
    "hidden/inpatient/admissions_truth_{year}.csv": {
        "module": "inpatient", "milestone": "M2", "years": SIMULATED_YEARS,
        "sort_by": ["encounter_id"], "columns": [
            ("encounter_id", "id", None, "E00000001", "Encounter"),
            ("person_id", "id", None, "P0000001", "Person"),
            ("in_published_data", "flag", None, "0|1", "0 = a 2021 burn-in admission, not in data/"),
            ("severity_latent", "float", 6, "standardised", "Unmeasured severity at admission"),
            ("sodium_true", "float", 1, "mmol/L", "True sodium"),
            ("creatinine_true", "float", 2, "mg/dL", "True creatinine"),
            ("hemoglobin_true", "float", 1, "g/dL", "True hemoglobin"),
            ("wbc_true", "float", 1, "10^9/L", "True white cell count"),
            ("lactate_true", "float", 2, "mmol/L", "True lactate, whether or not it was drawn"),
            ("lactate_drawn", "flag", None, "0|1", "1 = lactate was drawn"),
            ("readmit_eligible", "flag", None, "0|1", "1 = a live discharge home, with home health or to skilled nursing"),
            ("readmit_lp", "float", 6, "logit", "True linear predictor for 30-day readmission; empty if not eligible"),
            ("readmit_prob", "float", 6, "0-1", "True probability of unplanned 30-day readmission to any hospital; empty if not eligible"),
            ("readmit_any_30d", "flag", None, "0|1", "True unplanned readmission to any hospital within 30 days: the first return after discharge, when that return was not planned"),
            ("readmit_outside", "flag", None, "0|1", "1 = that readmission was to a non-network hospital"),
            ("readmit_gap_days", "int", None, "1-30", "Days from discharge to readmission; empty if none"),
            ("planned_return", "flag", None, "0|1", "1 = the first return within 30 days was a planned one (not counted as a readmission)"),
            ("readmit_encounter_id", "id", None, "E00000001", "The readmission's encounter ID; empty if none, outside the network, or after the data end"),
        ]},
    "hidden/inpatient/burnin_admissions_2021.csv": {
        "module": "inpatient", "milestone": "M2", "sort_by": ["encounter_id"],
        "columns": _ADMISSION_COLUMNS},
    "hidden/inpatient/outside_readmissions.csv": {
        "module": "inpatient", "milestone": "M2", "sort_by": ["index_encounter_id"], "columns": [
            ("index_encounter_id", "id", None, "E00000001", "Network discharge that was followed by an outside readmission"),
            ("person_id", "id", None, "P0000001", "Person"),
            ("outside_admit_date", "date", None, "YYYY-MM-DD", "Admission date at the non-network hospital"),
            ("gap_days", "int", None, "1-30", "Days from discharge to the outside admission"),
        ]},
    # ---------------------------------------------------- hidden/deterioration
    "hidden/deterioration/index_truth.csv": {
        "module": "deterioration", "milestone": "M3", "sort_by": ["encounter_id"], "columns": [
            ("encounter_id", "id", None, "E00000001", "Index encounter"),
            ("hr_true", "float", 1, "beats/min", "True heart rate"),
            ("rr_true", "float", 1, "breaths/min", "True respiratory rate"),
            ("sbp_true", "float", 1, "mmHg", "True systolic blood pressure"),
            ("temp_c_true", "float", 2, "deg C", "True temperature"),
            ("spo2_true", "float", 1, "percent", "True oxygen saturation"),
            ("lactate_true", "float", 2, "mmol/L", "True lactate at the index time"),
            ("spo2_bias", "float", 2, "points", "Planted upward bias in recorded SpO2"),
            ("rr_defaulted", "flag", None, "0|1", "1 = the recorded respiratory rate is the charted default"),
            ("outside_encounters_12m", "int", None, ">= 0", "Encounters at non-network hospitals in the last 12 months"),
            ("deterioration_lp", "float", 6, "logit", "True linear predictor for deterioration with no response"),
            ("p0", "float", 6, "0-1", "True risk of deterioration with no rapid-response evaluation"),
            ("p1", "float", 6, "0-1", "True risk with an evaluation (0.80 x p0)"),
            ("y0", "flag", None, "0|1", "Potential outcome with no evaluation"),
            ("y1", "flag", None, "0|1", "Potential outcome with an evaluation"),
            ("event_type", "code", None, "|".join(EVENT_TYPES), "What the event is when the patient deteriorates; empty if y0 is 0"),
            ("response_prob", "float", 6, "0-1", "Probability an alert is answered; empty if no alert"),
            ("y_true", "flag", None, "0|1", "Realised true deterioration within 48 hours"),
            ("ehr_flag_error", "code", None, "none|missed|false_positive", "How the EHR flag differs from the truth"),
            ("vdi_score_no_assay_shift", "int", None, "0-100", "VDI score the same patient would have had without the lactate assay shift"),
        ]},
    "hidden/deterioration/change_points.csv": {
        "module": "deterioration", "milestone": "M4", "sort_by": ["change_date", "change_id"], "columns": [
            ("change_id", "id", None, "CP01", "Planted change ID"),
            ("change_date", "date", None, "YYYY-MM-DD", "Date the change took effect"),
            ("facilities", "text", None, "F01;F02", "Hospitals affected"),
            ("mechanism", "code", None, "short code", "Planted mechanism"),
            ("size", "float", 4, "see unit", "Size of the change"),
            ("unit", "text", None, "", "Unit of size"),
            ("description", "text", None, "", "What the simulator did"),
        ]},
    "hidden/deterioration/monthly_truth.csv": {
        "module": "deterioration", "milestone": "M4", "sort_by": ["month", "facility_group"], "columns": [
            ("month", "month", None, "YYYY-MM", "Calendar month of the index time"),
            ("facility_group", "code", None, "f01_f03|f04_f05|f06|all", "Hospital group"),
            ("index_encounters", "int", None, ">= 0", "Index encounters"),
            ("true_rate_no_response", "float", 6, "0-1", "Mean true risk with no evaluation (p0)"),
            ("true_rate_as_treated", "float", 6, "0-1", "Mean true risk given the responses that happened"),
            ("vendor_expected_rate", "float", 6, "0-1", "Mean vendor risk from the score-to-risk table"),
            ("true_oe", "float", 4, "ratio", "true_rate_as_treated divided by vendor_expected_rate"),
            ("alert_rate", "float", 4, "0-1", "Share of encounters at or above the threshold"),
            ("response_rate", "float", 4, "0-1", "Share of fired alerts answered; empty if none fired"),
        ]},
    # ----------------------------------------------------------- hidden/scribe
    "hidden/scribe/note_errors_truth.csv": {
        "module": "scribe_audit", "milestone": "M5", "sort_by": ["note_id"], "columns": [
            ("note_id", "id", None, "N0000001", "Note"),
            ("n_omission", "int", None, ">= 0", "True omissions"),
            ("n_hallucination", "int", None, ">= 0", "True items of content that were not said"),
            ("n_misattribution", "int", None, ">= 0", "True misattributions"),
            ("n_wrong_value", "int", None, ">= 0", "True wrong numbers or doses"),
            ("worst_severity", "code", None, "|".join(SEVERITIES), "True worst severity"),
        ]},
    "hidden/scribe/rater_parameters.csv": {
        "module": "scribe_audit", "milestone": "M5", "sort_by": ["rater_id"], "columns": [
            ("rater_id", "id", None, "R01-R09", "Rater"),
            ("rater_role", "code", None, "rater|senior", "Role in the audit"),
            ("sens_omission", "float", 4, "0-1", "True sensitivity for omissions"),
            ("sens_hallucination", "float", 4, "0-1", "True sensitivity for hallucinations"),
            ("sens_misattribution", "float", 4, "0-1", "True sensitivity for misattributions"),
            ("sens_wrong_value", "float", 4, "0-1", "True sensitivity for wrong values"),
            ("false_positive_rate", "float", 4, "0-1", "True false-positive rate per error type"),
        ]},
    "hidden/scribe/clinic_effects.csv": {
        "module": "scribe_audit", "milestone": "M5", "sort_by": ["clinic_id"], "columns": [
            ("clinic_id", "id", None, "C01-C24", "Clinic"),
            ("error_effect_logit", "float", 6, "logit", "True clinic effect on every kind of note error"),
            ("interpreter_rate", "float", 4, "0-1", "True chance that a visit at the clinic uses an interpreter"),
        ]},
    # -------------------------------------------------------- hidden/economics
    "hidden/economics/clinician_truth.csv": {
        "module": "scribe_value", "milestone": "M5", "sort_by": ["clinician_id"], "columns": [
            ("clinician_id", "id", None, "K001", "Clinician"),
            ("baseline_doc_minutes", "float", 2, "minutes", "True baseline documentation minutes per visit"),
            ("adoption_type", "code", None, "adopter|partial|never", "True adoption type"),
            ("individual_effect_minutes", "float", 2, "minutes", "True steady-state saving per scribe visit for this clinician"),
            ("steady_share", "float", 4, "0-1", "True share of visits on which the clinician uses the scribe once settled; 0 for never"),
            ("after_hours_baseline", "float", 1, "minutes", "True typical after-hours minutes in a normal week without the scribe"),
            ("latent_wellbeing_baseline", "float", 4, "SD units", "True latent wellbeing at baseline"),
            ("wellbeing_effect", "float", 4, "SD units", "True effect of the scribe on latent wellbeing once the clinic is live"),
            ("latent_wellbeing_post_wave", "float", 4, "SD units", "True latent wellbeing at the post-wave survey, effect included; empty at wave 4 clinics"),
            ("latent_wellbeing_final", "float", 4, "SD units", "True latent wellbeing at the final survey, effect included"),
        ]},
    "hidden/economics/clinician_weeks_truth.csv": {
        "module": "scribe_value", "milestone": "M5", "sort_by": ["clinician_id", "week_start"], "columns": [
            ("clinician_id", "id", None, "K001", "Clinician"),
            ("week_start", "date", None, "YYYY-MM-DD", "Monday starting the week"),
            ("expected_scribe_share", "float", 4, "0-1", "True chance that a visit this week uses the scribe"),
            ("learning", "float", 3, "0-1", "Share of the full effect in force this week; 0 before go-live"),
            ("saving_per_scribe_visit", "float", 2, "minutes", "True documentation minutes saved on each scribe visit this week"),
            ("visits_no_scribe", "int", None, ">= 0", "Visits this week had the scribe not existed (same random draw)"),
            ("doc_minutes_no_scribe", "float", 1, "minutes", "Documentation minutes per visit had the scribe not existed; empty when visits is 0"),
            ("after_hours_no_scribe", "float", 0, "minutes", "After-hours minutes had the scribe not existed"),
        ]},
}

# Documents that SHA256SUMS and MANIFEST.json cover, beside the generated files.
# HANDOFF.md is left out because it changes after every paste-back (DESIGN section 1).
HASHED_DOCUMENTS = ("README.md", "DESIGN.md", "BACKSTORY.md", "NAMES.md", "LICENSES.md",
                    "WORLD_SPEC.md", "PROVENANCE.md", "BOOK_MAP.md")
GENERATED_DOCUMENTS = ("CHECKS.md", "DICTIONARY.csv")

# JSON files are documented here and described in WORLD_SPEC.md; they are not in DICTIONARY.csv.
JSON_FILES = {
    "data/readmission/r30_model_card.json": "M4",
    "data/deterioration/vendor_model_card.json": "M3",
    "hidden/calibrated_intercepts.json": "M2",
    "hidden/readmission/r30_fit_trace.json": "M4",
    "hidden/readmission/r30_truth.json": "M4",
    "hidden/deterioration/vdi_formula.json": "M3",
    "hidden/scribe/error_model_truth.json": "M5",
    "hidden/economics/effects_truth.json": "M5",
}
MILESTONES = ("M2", "M3", "M4", "M5")


def expand_files():
    """Return {concrete path: metadata}, with one entry per year where a path has {year}."""
    out = {}
    for pattern, meta in FILES.items():
        if "{year}" in pattern:
            for year in meta["years"]:
                out[pattern.format(year=year)] = meta
        else:
            out[pattern] = meta
    return out
