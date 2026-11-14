# Book outline

*Validating Health AI Before and After Go-Live: A Field Manual for Local Performance Checks, Monitoring and Audit, with Known Answers in Python and R*

Outline of 13 November 2026, written against this repository. Every number quoted is printed in `CHECKS.md` or by a lab, and is fixed, because the data are frozen. Page counts are proposals. One lab exists (Chapter 7); no chapter has been drafted.

## Who the book is for

- **A statistician or analyst asked to check an AI tool** a hospital has bought or built, and who has not done it before.
- **A consultant** who wants to offer validation, monitoring and audit as a service, and needs a method, a protocol and a report to show.
- **A quality or informatics lead** who commissions such work and must judge what comes back.

Assumed: logistic regression, and working Python or R. Not assumed: machine-learning theory, survival analysis, or access to any real patient data.

## The promise

Every method in the book is run on a hospital where the truth is known. The reader computes an estimate from the same files an analyst would have, then opens the answer key and sees how far off it was and why. No other setting lets a reader find out whether their validation was right.

## How every chapter is built

1. **The question.** A short memo from the AI Oversight Committee at Tonmick Health.
2. **By hand.** The calculation on 20 real rows (`by_hand.csv`). The hand count becomes a test the code must pass.
3. **In Python and in R.** On the full data, from `data/` only (`lab.py`, `lab.R`). The two must agree, or `make labs` fails.
4. **Against the truth.** A boxed answer key (`answer_key.py`) sets the estimate beside what the simulator did.
5. **The trap.** The planted mechanism the obvious analysis walks into, and how to see it without the answer key.

Each chapter ends with **what to hand over**: the table, paragraph or page that belongs in a real report.

## Part I. The claim and the data

### Chapter 1. What exactly is being claimed? (10 pages)

- **Question:** "We have a model card for each tool. What do they actually promise?"
- **Works from:** `docs/BACKSTORY.md`; `data/deterioration/vendor_model_card.json`; `data/readmission/r30_model_card.json`; `data/network/timeline.csv`.
- **By hand:** fill in a six-line claim sheet for each tool: who, when, what outcome, by when, for which decision, measured how.
- **In code:** nothing to compute. The lab prints the two cards side by side and lists what each leaves out.
- **Known answer:** the vendor's card describes 412,000 encounters at 14 of its own hospitals with an event rate of 4.5%; Tonmick's rate is 3.7%. The formula it withholds is `hidden/deterioration/vdi_formula.json`.
- **Trap:** reading a claimed C-statistic of 0.84 as a property of the product, when it is a property of the product on one population.
- **Hand over:** a one-page statement of each claim, with its gaps. Template: `templates/scoping_questions.md`.
- **Lab:** `ch01_what_is_claimed`.

### Chapter 2. A hospital where the truth is known (14 pages)

- **Question:** "Why should anyone trust results from a made-up hospital?"
- **Works from:** `SHA256SUMS`, `DICTIONARY.csv`, `CHECKS.md`, `docs/PROVENANCE.md`; `data/inpatient/`.
- **By hand:** check one file's hash; derive 30-day readmission for 20 discharges from the admissions table.
- **In code:** `make hashes`, `make verify`; headline rates set beside published benchmarks.
- **Known answer:** all 53 files rebuild from seed 20261110, byte for byte. Twenty-four planted mechanisms, each with its source or the label "design choice" (`docs/PROVENANCE.md` section 5).
- **Trap:** none planted. The chapter states the limits instead: the world was tuned to its targets, three target ranges were replaced after the fact, and passing its own checks is not evidence of realism.
- **Hand over:** the paragraph that tells a client what synthetic results can and cannot show.
- **Lab:** `ch02_a_hospital_where_the_truth_is_known`.

## Part II. An open model: the readmission model

Three chapters, kept short. Their job is to teach the measures on a model whose coefficients are visible, before Part III applies them to one whose formula is not.

### Chapter 3. Discrimination and calibration from first principles (16 pages)

- **Question:** "Our analysts report a C-statistic of 0.71 for the readmission model. What does that mean?"
- **Works from:** `data/readmission/r30_model_card.json`, `r30_development_sample.csv`.
- **By hand:** rebuild the score for 20 patients from the card; count concordant pairs; make a three-row calibration table.
- **In code:** refit the model and match the card to six decimals; C-statistic; calibration plot, slope and intercept.
- **Known answer:** 1,725 discharges, 217 readmissions, apparent C-statistic 0.708. `hidden/readmission/r30_fit_trace.json` is the team's own fitting record.
- **Trap:** these are the patients the model was built from.
- **Hand over:** a discrimination and calibration table with counts.
- **Lab:** `ch03_discrimination_and_calibration`.

### Chapter 4. Optimism and sample size (16 pages)

- **Question:** "Was 1,725 patients enough?"
- **Works from:** `data/readmission/r30_development_sample.csv`.
- **By hand:** events per candidate parameter (217 over 17); the first term of the minimum sample size calculation.
- **In code:** bootstrap optimism; the minimum sample size at three anticipated C-statistics; the screening step repeated on resamples.
- **Known answer:** 2,604 needed at an anticipated 0.70, 2,395 at the reported 0.708, and 1,607 at an optimistic 0.75. The screen kept both noise predictors and dropped four real ones. `hidden/readmission/r30_truth.json` holds the true model.
- **Trap:** an optimistic guess makes the sample look adequate. And the reference fit gives weekend discharge a small coefficient through confounding, though it is not in the true model.
- **Hand over:** a sample-size statement, and a list of which predictors the data could not support.
- **Lab:** `ch04_optimism_and_sample_size`.

### Chapter 5. Does it travel? (16 pages)

- **Question:** "The model was built at the university hospital. Can the northern hospitals use it?"
- **Works from:** `data/readmission/r30_scores.csv`; `data/inpatient/admissions_2023.csv`.
- **By hand:** observed over expected for 20 discharges at one northern hospital.
- **In code:** validation on 28,002 discharges in 2023 at five hospitals; C-statistic, slope, observed over expected by hospital.
- **Known answer:** C-statistic 0.679, slope 0.882. Observed over expected runs from 0.77 to 1.37 across hospitals. In the north it is 0.82 against the record and 1.28 against readmission to any hospital: 15.7% of true readmissions go elsewhere and are never seen.
- **Trap:** the model looks too pessimistic in the north because the outcome is under-counted there, not because risk is lower.
- **Hand over:** a transport table by site, with the outcome caveat stated.
- **Lab:** `ch05_does_it_travel`.

## Part III. A closed model: the vendor's deterioration score

The core of the book. The formula is undisclosed, as a real vendor's would be.

### Chapter 6. Protocol first (12 pages)

- **Question:** "Before anyone looks at results: what exactly will we measure, on whom?"
- **Works from:** `data/deterioration/index_encounters.csv`; `data/network/facilities.csv`, `timeline.csv`.
- **By hand:** classify 20 encounters as in or out of the silent-mode cohort.
- **In code:** build the cohort and its flow of patients; counts by hospital and month.
- **Known answer:** 12,030 encounters, 443 recorded events.
- **Trap:** including encounters where the score was already shown (`vdi_shown`). Two hospitals stayed silent until April 2024; a sixth never had a silent period.
- **Hand over:** a dated protocol. Templates: `templates/data_request.md`, `templates/validation_protocol.md`.
- **Lab:** `ch06_protocol_first`.

### Chapter 7. Does it perform as claimed? (25 pages; the free worked case)

- **Question:** "The vendor claims 0.84. What does the score do on our patients?"
- **Works from:** `index_encounters.csv`, `vendor_risk_table.csv`, `vendor_model_card.json`.
- **By hand:** 4 events and 16 non-events make 64 pairs; 59 are concordant; C = 0.922.
- **In code:** C-statistic 0.772 (95% interval 0.747 to 0.796); observed over expected 0.909; calibration slope 0.855; calibration-in-the-large -0.115; a calibration table in six bands.
- **Known answer:** against the true outcome the score reaches 0.799. The true risk itself reaches only 0.858, so the claimed 0.84 was near the ceiling for these patients. The record misses 37 true events and adds 37 false ones.
- **Trap:** reporting "0.77 against a claimed 0.84" as a failed product, without asking what the claim described or what was achievable.
- **Hand over:** the validation summary table and three sentences for the committee.
- **Lab:** `ch07_does_it_perform_as_claimed` (in the repository now).

### Chapter 8. Thresholds, workload and usefulness (16 pages)

- **Question:** "At the vendor's threshold, what do we get and what does it cost the wards?"
- **Works from:** `index_encounters.csv`; `data/deterioration/rrt_log.csv`; `data/economics/wage_rates.csv`.
- **By hand:** a two-by-two table at threshold 60 for 20 encounters.
- **In code:** alert rate, positive predictive value and sensitivity across thresholds; net benefit; staff minutes per true event found.
- **Known answer:** at 60, 8.7% of encounters alert, 18.0% of alerts are true and 42.4% of events are caught. An evaluation takes 30.1 nurse minutes and 10.0 physician minutes.
- **Trap:** quoting sensitivity without the alert burden that buys it.
- **Hand over:** a threshold table with workload in minutes and in dollars.
- **Lab:** `ch08_thresholds_and_workload`.

### Chapter 9. Was the outcome measured right? (14 pages)

- **Question:** "All of this rests on a flag in the record. How often is the flag wrong?"
- **Works from:** `data/deterioration/chart_review.csv`.
- **By hand:** a weighted rate from five strata.
- **In code:** design-weighted sensitivity and false-positive rate of the flag, with intervals; the validation repeated with corrected outcomes.
- **Known answer:** the flag catches 92.1% of true events overall and about 85% at the northern hospitals, with a false-positive rate of 0.4%.
- **Trap:** analysing the 800 reviewed charts as a simple random sample. High scores were oversampled, and each row carries its inclusion probability.
- **Hand over:** an outcome-quality statement, and how it moves the Chapter 7 results.
- **Lab:** `ch09_was_the_outcome_measured_right`.

### Chapter 10. Subgroups, sample size and honest intervals (18 pages)

- **Question:** "Does it work as well for every group of our patients?"
- **Works from:** `index_encounters.csv`; `data/inpatient/persons.csv`; the admissions files.
- **By hand:** observed over expected, with its interval, in a group with 21 events.
- **In code:** calibration by recorded race, by hospital group and by payer; the smallest difference each group's sample could show.
- **Known answer:** the score under-predicts in three groups, with expected observed-to-expected ratios of 1.22, 1.24 and 1.25. Four mechanisms cause it: a pulse oximeter that reads high, a default respiratory rate, a lactate that was never drawn, and care received elsewhere.
- **Trap:** in the north the realised ratio is 0.90, on 21 events. The effect is real and six months of data cannot show it. "No difference found" is not "no difference".
- **Hand over:** a subgroup table that says which rows are underpowered.
- **Lab:** `ch10_subgroups_and_intervals`.

## Part IV. After go-live

### Chapter 11. When the alert changes the outcome (16 pages)

- **Question:** "Since go-live the score looks worse. Has it degraded? And do the alerts help?"
- **Works from:** `index_encounters.csv` from 2024 on.
- **By hand:** a two-by-two table of alerted patients, evaluated or not.
- **In code:** performance before and after go-live; the naive comparison of evaluated with unevaluated patients.
- **Known answer:** `hidden/` holds both potential outcomes for every encounter. An evaluation truly cuts risk by a ratio of 0.81. At the hospital that skipped silent mode, the event rate is 5.6% and the score under-predicts (1.18).
- **Trap:** an alert that works prevents the events it predicted, so a good score looks worse once it is acted on. Neither question can be answered from live data alone.
- **Hand over:** a paragraph on what post-go-live performance can and cannot mean, and the case for a silent period at every new site.
- **Lab:** `ch11_when_the_alert_changes_the_outcome`.

### Chapter 12. Finding change (18 pages)

- **Question:** "Alerts went up in the spring of 2024. What happened?"
- **Works from:** `index_encounters.csv`; `data/network/lab_change_log.csv`, `timeline.csv`.
- **By hand:** monthly alert rates for one hospital, and a control limit.
- **In code:** control charts for inputs, scores, alerts, responses and outcomes; dating each shift.
- **Known answer:** 13 planted changes, dated in `hidden/deterioration/change_points.csv`. A laboratory method change raised alerts by 3.1 points with no rise in true risk. Response to alerts fell from 84% to 72% over two years. Version 3.0 brought the alert rate to 5.3%.
- **Trap:** reading more alerts as sicker patients. The laboratory's log records the change among 88 other entries and says nothing of its effect.
- **Hand over:** a dated list of changes with the evidence for each.
- **Lab:** `ch12_finding_change`.

### Chapter 13. The monitoring plan and the quarterly report (14 pages)

- **Question:** "What should we watch each quarter, and when should we act?"
- **Works from:** as Chapter 12; `outcome_available_date` for the delay before an outcome can be counted.
- **By hand:** how many quarters a limit takes to catch a given shift.
- **In code:** candidate limits replayed over three years; false alarms against time to detection.
- **Known answer:** `hidden/deterioration/monthly_truth.csv`, the true monthly event rate and calibration by hospital group.
- **Trap:** limits so tight that every quarter alarms, or so loose that the method change passes. Winter raises true risk by about a tenth and is not drift.
- **Hand over:** a one-page monitoring plan and a quarterly report.
- **Lab:** `ch13_the_monitoring_plan`.

## Part V. Auditing AI-written notes

### Chapter 14. Designing the audit (14 pages)

- **Question:** "The scribe has drafted 100,000 notes. How many must we read, and which?"
- **Works from:** `data/scribe/ai_notes_frame.csv`, `audit_sample.csv`.
- **By hand:** the upper limit when 100 notes show no major error; allocating a sample across four strata.
- **In code:** the frame by stratum; precision under simple and stratified designs; inclusion probabilities.
- **Known answer:** `hidden/scribe/note_errors_truth.csv` has the true errors in all 102,502 notes. 1.4% have a major error.
- **Trap:** "none found in 100" still allows about 3%.
- **Hand over:** an audit design: frame, strata, sample size, and what it can detect.
- **Lab:** `ch14_designing_the_audit`.

### Chapter 15. Raters disagree: stating the error rate honestly (20 pages)

- **Question:** "Two clinicians read each note and often disagreed. What is the error rate?"
- **Works from:** `data/scribe/audit_ratings.csv`, `audit_sample.csv`, with the frame.
- **By hand:** kappa from a two-by-two table; a weighted rate from three strata.
- **In code:** agreement by error type; design-weighted rates with intervals; interpreter visits against others; version 2.3 against 2.4.
- **Known answer:** kappa for hallucinations is 0.51, from raters who are each right about four times in five on a real error. Omissions: 19.3% unweighted, 16.0% weighted, 17.5% true. Omissions are 1.62 times as common with an interpreter. Hallucinations fell from 10.5% to 7.9% with the new version.
- **Trap:** the unweighted rate is too high, because hard visits were oversampled. One rater is lenient. A third reader saw only the notes the first two disagreed on, so an error both missed stays missed.
- **Hand over:** an error-rate statement with its interval and its known direction of bias.
- **Lab:** `ch15_raters_disagree`.

## Part VI. Reporting

### Chapter 16. The report the committee can act on (12 pages)

- **Question:** "What should we do about each tool?"
- **Works from:** the results of every lab.
- **By hand:** nothing new.
- **In code:** one script that gathers every lab's results into the report's tables.
- **Known answer:** every figure in the report can be set against its row in `CHECKS.md`.
- **Trap:** a summary that keeps the favourable numbers.
- **Hand over:** a four-page report: one page per tool and one of recommendations, each number with its count and its limit.
- **Lab:** `ch16_the_report`.

## Appendices

| Appendix | Contents | Pages |
| --- | --- | --- |
| A | The files at a glance: one line per file, from `DICTIONARY.csv` | 6 |
| B | Reproducing and verifying the world: hashes, the seed, the generator | 4 |
| C | The three templates, printed | 6 |
| D | Method notes: DeLong's interval, minimum sample size, kappa, design weights | 6 |
| E | Glossary | 2 |

## Page budget

| Part | Chapters | Pages |
| --- | --- | --- |
| Front matter | | 8 |
| I. The claim and the data | 1, 2 | 24 |
| II. An open model | 3 to 5 | 48 |
| III. A closed model | 6 to 10 | 85 |
| IV. After go-live | 11 to 13 | 48 |
| V. Auditing notes | 14, 15 | 34 |
| VI. Reporting | 16 | 12 |
| Appendices | | 24 |
| **Total** | | **283** |

## Order of writing

1. **Chapter 7**, with its lab. It is the free worked case and sets the pattern.
2. **Chapter 2**, which answers the first objection.
3. **Chapters 6, 8, 9 and 10**, to finish Part III.
4. **Part IV**, then **Part V**.
5. **Part II** and **Chapter 1**, which lean on what the later parts needed.
6. **Chapter 16** last.

## In the repository and not in the book

The clinician-week panel, the staff survey and the scribe's cost lines (`data/scribe/clinician_weeks.csv`, `wellbeing_survey.csv`, `data/economics/scribe_costs.csv`) support a different question: is the tool worth it? Their known answers are under `hidden/economics/`. They are documented in `docs/WORLD_SPEC.md` section 16 and listed at the end of `docs/BOOK_MAP.md`.
