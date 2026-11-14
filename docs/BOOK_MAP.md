# Book map

**`hidden/` is never evidence.** It holds what the simulator did: true risks, true outcomes, true errors, planted mechanisms. It exists so that a method can be checked against a known answer, in a clearly marked known-answer step. An analyst works from `data/` alone, and no result in this world says anything about a real hospital, product, patient or clinician. Everything here is fictional.

This file maps the frozen world, version 1.0.0, to the sixteen chapters of *Validating Health AI Before and After Go-Live*. For each chapter it lists the files the reader works from, the questions those files can answer, where the known answer is, and the planted traps. Numbers are quoted from `CHECKS.md`, by check ID; that file is the authority and this one only points to it.

The brief's map of seven books is on hold (`DESIGN.md` decision A1). Hospice, the fourth of those books, is not in this release.

## How to read an entry

- **Works from:** files under `data/`, plus documents at the top level. All a reader needs for the chapter's analysis.
- **Known answer:** files under `hidden/`, and the rows of `CHECKS.md` that print the value.
- **Traps:** what was planted, with its ID in `DESIGN.md` section 6 where it has one.

A value marked V6 or V7 differs from the brief's original target under a variance Nick approved on 13 November 2026 (`DESIGN.md` decisions A31 and A41).

## Part I. The claim and the data

### Chapter 1. What exactly is being claimed?

- **Works from:** `BACKSTORY.md`; `data/deterioration/vendor_model_card.json`; `data/readmission/r30_model_card.json`; `data/network/timeline.csv`; `data/network/facilities.csv`.
- **Questions:** What is each tool for, in whom, predicting what, by when, to support which decision? What does each model card not say?
- **Known answer:** `hidden/deterioration/vdi_formula.json` is the formula the vendor's card withholds. `hidden/readmission/r30_fit_trace.json` is how R30 was really built.
- **Traps:** the vendor's claimed C-statistic of 0.84 describes the vendor's own patients (P6). The card gives no event rate and no subgroup results. R30's card reports only an apparent C-statistic.

### Chapter 2. A hospital where the truth is known

- **Works from:** `BACKSTORY.md`, `DESIGN.md`, `DICTIONARY.csv`, `SHA256SUMS`; `data/network/`; `data/inpatient/persons.csv` and `admissions_2022.csv` to `admissions_2026.csv`.
- **Questions:** Is my copy the published one? Can I regenerate a file from the seed? Do the headline rates look like a real hospital's?
- **Known answer:** `python3 generator/verify_world.py`; the "Benchmarks" section of `CHECKS.md`; `hidden/inpatient/persons_truth.csv` and `admissions_truth_2022.csv` to `admissions_truth_2026.csv` for a first look at what "the truth" is; `hidden/calibrated_intercepts.json`.
- **Traps:** none planted in this chapter. The table of every planted problem, each with its source or the label "design choice", is `PROVENANCE.md` section 5. `PROVENANCE.md` section 2 shows that targets and mechanisms were committed before any generator code.

## Part II. An open model: the readmission model R30

### Chapter 3. Discrimination and calibration from first principles

- **Works from:** `data/readmission/r30_model_card.json`; `data/readmission/r30_development_sample.csv`.
- **Questions:** Can I rebuild the score from the card? What are its C-statistic and calibration on the patients it was built from?
- **Known answer:** `hidden/readmission/r30_fit_trace.json`. A refit matches the card's coefficients to six decimals (S28). Apparent C-statistic 0.708 (T41, V6).
- **Traps:** performance on the development patients is not evidence about any others (P15).

### Chapter 4. Optimism and sample size

- **Works from:** `data/readmission/r30_development_sample.csv`.
- **Questions:** How much of the apparent performance is optimism? Was the sample large enough for 17 candidate parameters?
- **Known answer:** `hidden/readmission/r30_truth.json`: the true model, and a reference fit of R30's terms on a large sample. T45: 1,725 discharges against a minimum of 2,604 at an anticipated C-statistic of 0.70; an optimistic guess of 0.75 would have asked for only 1,607. T46: neither noise predictor is in the true model.
- **Traps:** the screen at p < 0.20 kept both noise predictors and dropped real ones (P15). The reference fit gives weekend discharge a small coefficient through confounding, so "no term in the true model" is the accurate statement, not "a coefficient of zero".

### Chapter 5. Does it travel?

- **Works from:** `data/readmission/r30_scores.csv`; the admissions files.
- **Questions:** How does R30 perform on later discharges and at other hospitals? Is it calibrated in the north?
- **Known answer:** the admissions truth files and `hidden/inpatient/outside_readmissions.csv`. Observed readmission 0.119 against a true 0.141 (T11, T10); 15.7% of true readmissions go outside the network (T12). Validation C-statistic 0.679 (T42); slope 0.882 (T43, V6). At the two northern hospitals the expected observed-to-expected ratio is 0.82 against the recorded outcome and 1.28 against readmission to any hospital (T44).
- **Traps:** the model looks too pessimistic in the north only because the record misses returns elsewhere (P13). The development sample was one hospital, one service, complete laboratory panels and first discharges only (P14).

## Part III. A closed model: the vendor's deterioration index

### Chapter 6. Protocol first

- **Works from:** `data/deterioration/index_encounters.csv`; `data/network/facilities.csv` and `timeline.csv`.
- **Questions:** Which encounters belong in a silent-mode validation? What is the outcome, and when is it known?
- **Known answer:** 12,030 silent-mode encounters with a flagged event rate of 3.68% (T15, T15b).
- **Traps:** including encounters where the score was already shown; `vdi_shown` separates them. The two northern hospitals stayed silent until 2024-04-01. Sallowfield had no silent period at all (P11).

### Chapter 7. Does it perform as claimed?

- **Works from:** `data/deterioration/index_encounters.csv`, `vendor_model_card.json`, `vendor_risk_table.csv`.
- **Questions:** What are the local C-statistic, calibration slope and observed-to-expected ratio? How do they compare with the claim?
- **Known answer:** `hidden/deterioration/index_truth.csv`. C-statistic 0.772 (T16); slope 0.855 (T17); observed-to-expected 0.909 (T18). The true risk gives the ceiling no score could beat.
- **Traps:** treating a local value below the claimed 0.84 as a scandal. The vendor's baseline comes from a population with more events (P6), so the score over-predicts here overall.

### Chapter 8. Thresholds, workload and usefulness

- **Works from:** `data/deterioration/index_encounters.csv`; `data/deterioration/rrt_log.csv`.
- **Questions:** At the vendor's threshold, how many alerts, how many true, how many events caught, at what cost in staff time?
- **Known answer:** alert rate 0.087, positive predictive value 0.180, sensitivity 0.424 (T22 to T24). A rapid-response evaluation takes 30.1 nurse minutes and 10.0 physician minutes on average (T34).
- **Traps:** quoting sensitivity without the alert burden that buys it.

### Chapter 9. Was the outcome measured right?

- **Works from:** `data/deterioration/chart_review.csv`, with `index_encounters.csv`.
- **Questions:** How often is the record's outcome flag wrong? Does that change the validation?
- **Known answer:** `index_truth.csv` columns `y_true` and `ehr_flag_error`. Flag sensitivity 0.921 overall (T29) and 0.85 at the northern hospitals on the expected basis (T29b); false-positive rate 0.4% (T29c).
- **Traps:** analysing the review as a simple random sample: it is stratified by score, with high scores oversampled, and each row carries its inclusion probability. In the north, transfers out hide events (P9).

### Chapter 10. Subgroups, sample size and honest intervals

- **Works from:** `data/deterioration/index_encounters.csv`; `data/inpatient/persons.csv`; the admissions files.
- **Questions:** Does the score under-predict in any group? Which groups are too small to say?
- **Known answer:** `index_truth.csv` columns `spo2_bias`, `rr_defaulted`, `lactate_true` and `outside_encounters_12m`; `hidden/deterioration/vdi_formula.json`. Expected observed-to-expected ratios of 1.215 for patients recorded as Black, 1.240 at the northern hospitals and 1.253 for Medicaid and self-pay (T19 to T21).
- **Traps:** four mechanisms (P1, P2, P3, P5). The realised ratio in the north is 0.90, on 21 flagged events: the planted effect is there and six months of data cannot show it.

## Part IV. After go-live

### Chapter 11. When the alert changes the outcome

- **Works from:** `data/deterioration/index_encounters.csv` from 2024 on.
- **Questions:** Has the score degraded? Do the alerts work?
- **Known answer:** `index_truth.csv` holds both potential outcomes for every encounter (`y0`, `y1`) and both risks (`p0`, `p1`). True risk ratio of an evaluation 0.813 (T28). Sallowfield: event rate 5.6%, observed-to-expected 1.178 (T27, T27b).
- **Traps:** an alert that works lowers the observed risk of the patients it flags, so live data make a good score look worse (P8). Neither question can be answered from live data alone.

### Chapter 12. Finding change

- **Works from:** `data/deterioration/index_encounters.csv`; `data/network/lab_change_log.csv` and `timeline.csv`.
- **Questions:** What changed, and when? Was it the patients, the measurement, the score or the response?
- **Known answer:** `hidden/deterioration/change_points.csv` lists the 13 planted changes with dates. `index_truth.csv` column `vdi_score_no_assay_shift` scores the same patients without the laboratory change. Alerts rose 3.1 points from the assay change with no rise in true risk (T25, T26). Response to alerts fell from 0.836 to 0.715 (T31, T31b). Version 3.0: alert rate 0.053, slope 1.04 (T32).
- **Traps:** calling a rise in alerts a rise in risk (P4). The laboratory log records the method change among 88 other entries and says nothing of its effect; one other method change in the log is a false lead with no effect.

### Chapter 13. The monitoring plan and the quarterly report

- **Works from:** as Chapter 12. The column `outcome_available_date` gives the delay before an outcome can be counted.
- **Questions:** Which measures, at what limits, would have caught each change without crying wolf?
- **Known answer:** `hidden/deterioration/monthly_truth.csv`, true monthly event rates and observed-to-expected ratios by hospital group; `change_points.csv`.
- **Traps:** limits so tight that every quarter alarms, or so loose that the assay change passes. Winter raises true risk by about 10% (P10), which is not drift.

## Part V. Auditing AI-written notes

### Chapter 14. Designing the audit

- **Works from:** `data/scribe/ai_notes_frame.csv`, `audit_sample.csv`, `clinics.csv`, `clinicians.csv`.
- **Questions:** What is the frame? How should a sample be drawn, and how large? What can "none found" support?
- **Known answer:** `hidden/scribe/note_errors_truth.csv` has the true errors in all 102,502 notes. A major error is in 1.4% of them (T54).
- **Traps:** reading "no major errors in 100 notes" as "no major errors". Interpreter visits are 30% of the sample and 7% of the frame (P21).

### Chapter 15. Raters disagree: stating the error rate honestly

- **Works from:** `data/scribe/audit_ratings.csv`, `audit_sample.csv`, with the frame.
- **Questions:** How well do raters agree? What is the error rate in the frame, with what uncertainty? Did version 2.4 help?
- **Known answer:** `hidden/scribe/rater_parameters.csv` and `error_model_truth.json`. Kappa for the hallucination flag 0.509 (T57, V7). Design-weighted omission rate 0.160 against a true 0.175; unweighted 0.193 (T58). Omissions are 1.62 times as common in interpreter visits (T55). Hallucinations: 10.5% of version 2.3 notes and 7.9% of version 2.4 notes (T52).
- **Traps:** the unweighted rate is too high, because difficult visits were oversampled. One rater is lenient (P20). The senior reviewer rates only notes on which the two raters differ, so an error both missed is never recovered.

## Part VI. Reporting

### Chapter 16. The report the committee can act on

- **Works from:** the results of every earlier chapter; `data/deterioration/rrt_log.csv`; `data/economics/wage_rates.csv`.
- **Questions:** What should the committee do about each tool? What does the alert workload cost?
- **Known answer:** the `rn` and `hospitalist` rows of `wage_rates.csv` price the minutes in the rapid-response log. Every figure a report quotes can be set against its row in `CHECKS.md`.
- **Traps:** a summary that reports only the favourable numbers.

## Files the book does not use

These are built, checked and documented, and are part of the frozen release.

| Files | What they support |
| --- | --- |
| `data/scribe/rollout.csv`, `clinician_weeks.csv`, `wellbeing_survey.csv`; `data/economics/scribe_costs.csv` | Whether the scribe is worth it: a stepped rollout, documentation time, adoption, a survey with nonresponse, and costs |
| `hidden/economics/clinician_truth.csv`, `clinician_weeks_truth.csv`, `effects_truth.json` | The true saving (1.87 minutes per scribe visit, T73), each clinician-week without the scribe, who adopted, and the true wellbeing effect |
| `hidden/scribe/clinic_effects.csv` | Each clinic's true effect on note errors and its interpreter rate |
| `hidden/inpatient/facility_truth.csv`, `burnin_admissions_2021.csv` | Hospital effects, and the unpublished year that gives prior-admission history |

Traps in the unused files: a before-and-after comparison overstates the saving because of a secular trend (P22, T74); comparing users with non-users gets the sign wrong because heavier documenters adopt more (P23, T74b); clinicians who are worse off answer the survey less often (P24, T76).
