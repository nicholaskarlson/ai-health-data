# Tonmick Health: world specification

**Everything here is fictional.** No person, hospital, vendor, product or result is real. `hidden/` holds what the simulator did and is never evidence.

This file describes, in prose, what `generator/spec.py` and the generator do. If this file and the spec ever differ, the spec wins and this file is corrected. It describes the frozen world, version 1.0.0: the inpatient core (Milestone 2, sections 1 to 10), deterioration, the vendor's index and alerts (Milestone 3, sections 11 to 13), the readmission model, chart review, logs and monitoring truth (Milestone 4, sections 14 and 15), and the AI scribe with its audit, panel, survey and cost tables (Milestone 5, sections 16 and 17). Hospice is held for a later release.

Every number in sections 1 to 10 is in `spec.INPATIENT` unless another place is named; section 11 uses `spec.DETERIORATION`, section 14 `spec.R30`, section 15 `spec.CHART_REVIEW`, `spec.RRT_LOG` and `spec.LAB_LOG`, and sections 16 and 17 `spec.SCRIBE` and `spec.ECONOMICS`. Unless `PROVENANCE.md` gives a source, a number is a design choice.

## 1. What has been built

| Place | Files | Contents |
| --- | --- | --- |
| `data/network/` | `facilities.csv`, `timeline.csv` | The six hospitals and the public timeline |
| `data/inpatient/` | `persons.csv`, `admissions_2022.csv` to `admissions_2026.csv` | What an analyst is given |
| `hidden/inpatient/` | `facility_truth.csv`, `persons_truth.csv`, `admissions_truth_2021.csv` to `admissions_truth_2026.csv`, `burnin_admissions_2021.csv`, `outside_readmissions.csv` | What the simulator did |
| `hidden/` | `calibrated_intercepts.json` | The solved intercepts |
| `data/deterioration/` | `index_encounters.csv`, `vendor_risk_table.csv`, `vendor_model_card.json` | What an analyst is given about the vendor's score (Milestone 3) |
| `hidden/deterioration/` | `index_truth.csv`, `vdi_formula.json` | True vital signs, risks, both potential outcomes, and the vendor's formula (Milestone 3) |

| `data/readmission/` | `r30_development_sample.csv`, `r30_scores.csv`, `r30_model_card.json` | The in-house readmission model as the team left it (Milestone 4) |
| `hidden/readmission/` | `r30_fit_trace.json`, `r30_truth.json` | How the fit ran, and what is true (Milestone 4) |
| `data/deterioration/` | `chart_review.csv`, `rrt_log.csv` | The committee's chart review and the rapid-response log (Milestone 4) |
| `data/network/` | `lab_change_log.csv` | The laboratories' change log (Milestone 4) |
| `hidden/deterioration/` | `change_points.csv`, `monthly_truth.csv` | Every planted change with its date, and monthly truth (Milestone 4) |
| `data/scribe/` | `clinics.csv`, `clinicians.csv`, `rollout.csv`, `clinician_weeks.csv`, `wellbeing_survey.csv`, `ai_notes_frame.csv`, `audit_sample.csv`, `audit_ratings.csv` | The scribe pilot as the medical group and the committee recorded it (Milestone 5) |
| `data/economics/` | `scribe_costs.csv`, `wage_rates.csv` | Cost lines and loaded wages (Milestone 5) |
| `hidden/scribe/` | `note_errors_truth.csv`, `rater_parameters.csv`, `clinic_effects.csv`, `error_model_truth.json` | The true errors in every note, each rater's accuracy, and the model behind both (Milestone 5) |
| `hidden/economics/` | `clinician_truth.csv`, `clinician_weeks_truth.csv`, `effects_truth.json` | Each clinician's true traits and effects, and every clinician-week without the scribe (Milestone 5) |

That is 43 CSV files in 34 layouts (25 in `data/`, 18 in `hidden/`) and eight JSON files. `DICTIONARY.csv` has one row for every CSV file and column.

Not built: hospice. If it is built, it arrives as an append-only release, in new files drawn from blocks 50 to 54.

Milestone 4 changed no file from Milestones 2 and 3. Its files are drawn after the day loop, from blocks 26 to 28, or computed with no draw at all. Milestone 5 changed no file from Milestones 2 to 4: the scribe has its own blocks and reads nothing from the hospitals.

## 2. Conventions

- **IDs.** `encounter_id` is `E` and eight digits, numbered in the order admissions happen, burn-in first. `person_id` is `P` and seven digits. `facility_id` is `F01` to `F06`.
- **Dates.** ISO 8601. `admit_datetime` is a date and an hour. `discharge_date` is a date only.
- **Missing values** are empty fields. A column may be empty only where its dictionary entry says so.
- **Floats** are written with a fixed number of decimals, given in the dictionary.
- **Years.** An admission belongs to the file for the year it was admitted in.
- **Burn-in.** The simulation starts on 2021-01-01 with empty hospitals. Admissions from 2021 give the 2022 data a history and are kept in `hidden/` only. Their `encounter_id` numbers come first, so the first published ID is well above 1.
- **The end of the data.** Nothing after 2026-06-30 is recorded. A stay still open on that day has an empty `discharge_date`, `los_days` and `disposition`, and `died_in_hospital` is 0. A return that would fall after that day has no admission row.
- **Truth past the end.** The simulator draws a stay's whole course on its admission day. The truth files hold that course even where the public record is still open. So a truth row can show a readmission that the data never reach.

## 3. Randomness and reproducibility

- One PCG64 stream per block, seeded from the root seed and the block's ID (`spec.BLOCK_IDS`). A step draws only from its own block.
- The data path uses only arithmetic that is defined exactly, plus the `det_*` helpers in `generator/common.py`: exponential, logarithm, logistic function, normal, exponential, gamma, Poisson and categorical draws. It does not call NumPy's `exp`, `log` or built-in distributions, because their last bit can differ between machines. `tests/test_spec.py` asserts the helpers bit for bit.
- A sum or mean of floats that feeds the data or `CHECKS.md` uses `math.fsum`, which is correctly rounded and so does not depend on the order of addition.
- Block 90 is the append-only test. With `TONMICK_DUMMY_BLOCK=1` the generator draws a million values from it straight after the network block. No file may change, and `tests/test_world.py` checks that.
- Block 3 (`calibration`) draws the reference cohort described in section 6. It feeds no data file.

Blocks used by the inpatient core: 1 network, 2 persons, 3 calibration, 10 arrivals, 11 admission attributes, 12 comorbidity, 13 true laboratory values, 14 recorded laboratory values, 17 status at 12 hours, 21 disposition and length of stay, 22 death, 23 readmission, 24 outside care, 25 planned returns. Milestone 3 adds 15 true vital signs, 16 recorded vital signs, 18 alert response, 19 deterioration and 20 the EHR outcome flag. Its draws come after the others in each day's batch, so the earlier draws keep their order. Each person's other encounters (section 11.4) are the last draws of block 2. Milestone 4 uses blocks 26 to 28. The scribe (Milestone 5) uses blocks 30 to 36 and 40 to 43, one for each step named in sections 16 and 17; block 44 is reserved for costs and draws nothing; blocks 50 to 54 wait for hospice.

## 4. The network

`facilities.csv` lists the six hospitals from `spec.FACILITIES`. `timeline.csv` lists public events from `spec.TIMELINE_EVENTS`: go-lives, the acquisition, vendor version dates and the first and last dates of the extract. The lactate assay change of March 2024 is left out on purpose. It appears only in the laboratories' change log (section 15.3).

Each hospital has two hidden effects on the logit scale, one for readmission and one for deterioration. Six values are drawn for each, then centred and scaled so that their mean is 0 and their standard deviation is exactly 0.15. They are in `facility_truth.csv`.

Sallowfield (F06) joins on 2024-10-01. It has no admissions in the data before that day, and nothing that happened there earlier is in anyone's history.

## 5. People

The simulator holds a fixed pool of 400,000 adults who might be admitted. Only people with at least one published admission appear in `persons.csv`. `persons_truth.csv` also lists people admitted only during the burn-in, marked `in_published_data = 0`.

Each person has:

- **Age.** The pool's age on 2024-01-01 is spread evenly from 15 to 55 and then thins in a straight line to nothing at 98. Nobody is admitted before their 18th birthday. `persons.csv` gives the year of birth; the day is hidden, so `age` at admission can be one less than the admission year minus the birth year.
- **Sex.** Female with probability 0.52.
- **Race and ethnicity.** One combined field with the shares in `spec.RACE_ETHNICITY`. The seven named categories follow the 2024 federal minimum categories; `multiple` and `unknown` are added.
- **Interpreter needed.** Depends on the race and ethnicity category; about 6% overall.
- **Home area.** North 12%, central 60%, south 28%.
- **Frailty.** A standard normal value, hidden. It raises the chance of admission, severity, discharge to skilled nursing and readmission.
- **Propensity to use hospitals outside the network.** Hidden. Higher in the north, a little higher in the south.
- **Payer position.** One fixed uniform number. With the person's age band it gives the payer at each admission, so a person keeps the same payer until they turn 65.
- **Comorbidity count.** Starts from a Poisson draw that rises with age and frailty. Each admission adds one with probability 0.25, up to 12. It never falls.

## 6. Solved intercepts

Six models have an intercept that is solved, not chosen: lactate drawn, intensive care at 12 hours, comfort care at 12 hours, death in hospital before any deterioration, deterioration on the ward, and readmission. Unmeasured severity is standardised the same way.

Before the day loop, the generator draws a **reference cohort** of 60,000 admissions from block 3. Hospital, month and weekday are drawn by volume and by the seasonal and weekday factors. The person is drawn by the hospital's admission weights. The cohort is a mix of new admissions (86.7%), readmissions (10.6%) and planned returns (2.7%). Prior admissions come from each person's expected admission rate. Each intercept is then found by bisection so that the cohort's mean probability equals the target in `spec.INPATIENT["reference"]["targets"]`. They are solved in order, because later models use earlier results.

The day loop's population is close to the reference cohort but not the same. So the targets in `CHECKS.md` are tested on what the day loop produced, never assumed from the cohort. The solved values, their targets and the cohort means are in `hidden/calibrated_intercepts.json` and listed in `PROVENANCE.md`.

## 7. The day loop

The simulator walks through 2,007 days, from 2021-01-01 to 2026-06-30. On each day:

1. **New arrivals.** For each hospital already in the network, the number of new admissions is a Poisson draw. Its mean is the hospital's yearly volume, times 0.867 (the rest of the volume is scheduled returns), times a month factor and a weekday factor. December to February run about 12% above the yearly mean. People are chosen with chance proportional to an admission weight that rises with age and frailty, tilts by hospital, and follows the hospital's catchment mix by home area. A person who is in hospital, has died, or was discharged in the last 30 days cannot be chosen.
2. **Scheduled returns** for the day join: unplanned readmissions and planned returns set up at earlier discharges.
3. **Admission attributes.** Emergency or elective; diagnosis group; service; hour; payer; comorbidity count; `prior_admits_12m`.
4. **The stay's course**: severity, laboratory values, status at 12 hours, death, disposition, length of stay, deterioration on the ward and what it changes (section 11), and what happens after discharge.

A stay's whole course is drawn on its admission day. Returns are placed on future days.

### 7.1 Admission attributes

- **Type.** A new admission is elective with a probability that depends on the hospital (0.46 at the university hospital, 0.06 at the two northern hospitals) and falls to 15% of that at weekends. Readmissions are emergencies. Planned returns are elective.
- **Diagnosis group.** One of twelve invented groups. Emergency admissions use one table under 65 and another from 65. In winter, pneumonia and COPD are 1.35 times as likely. Elective admissions use their own table. A planned return keeps the diagnosis group of the stay before it, and a readmission keeps it half the time.
- **Service.** Surgery with a probability that depends on diagnosis group and type. The university hospital's emergency work is more often surgical.
- **`prior_admits_12m`.** A count of the same person's network admissions in the 365 days before this one, as the network's own record sees them. It includes the 2021 burn-in. It cannot see care outside the network, or Sallowfield before it joined.

### 7.2 Unmeasured severity

Severity is a weighted sum of frailty, age, comorbidity, diagnosis group, emergency admission, being a readmission, winter and noise. It is centred and scaled on the reference cohort, so it is close to a standard normal value. It is in the truth files as `severity_latent` and in no public file.

### 7.3 Laboratory values

True sodium and hemoglobin are normal; true creatinine, white cell count and lactate are log-normal. Each shifts with severity and with a few diagnosis groups. All are kept inside plausible limits.

Recorded values are the true values plus a small measurement error, rounded as the dictionary says.

- Sodium and creatinine are measured together in 96% of emergency admissions and 94% of elective ones. Hemoglobin and white cell count: 95.5% and 93%.
- **Lactate is drawn in about 40% of admissions, and more often when the patient is sicker.** The probability rises with severity, emergency admission, sepsis and pneumonia. It is lower for surgical patients, at the university hospital, which orders it more selectively, and lower still at the two northern hospitals, whose small laboratories run it less often. This is the first part of planted mechanism P3. A missing lactate is not missing at random.
- The truth files hold every true value, whether or not it was measured, and `lactate_drawn`.

From 2024-03-01 a lactate measured by the central laboratory reads 0.4 mmol/L high (planted mechanism P4, section 11.3).

### 7.4 Status at 12 hours

`icu_at_12h` and `comfort_care_12h` are drawn from logistic models. Intensive care is more likely with higher severity, sepsis, stroke and cardiac diagnoses, and rare at the two northern hospitals. Comfort care is more likely with higher severity, age, frailty and cancer. Both flags are 0 for a stay that ended within 12 hours.

### 7.5 Death, disposition and length of stay

- **Death in hospital** follows a logistic model in severity, age, intensive care and comfort care. A deterioration on the ward can add a death or move one (section 11.8). About 2% of admissions in all.
- **Disposition** among survivors is a multinomial logit against going home: home health, skilled nursing, hospice, leaving against advice, or transfer to another acute hospital. Transfers are common from the two northern hospitals and rare from the university hospital.
- **Length of stay** is log-normal, longer with severity, intensive care, sepsis and stroke, and it depends on disposition. About 4.5% of stays that end at home, against advice, by transfer or in death last only a few hours. A deterioration on the ward changes the length (section 11.8).

### 7.6 Readmission

A discharge is **eligible** if the patient left alive to home, home health or skilled nursing.

- **True unplanned readmission within 30 days, to any hospital.** A logistic model in age, comorbidity, prior admissions, length of stay, emergency admission, severity, frailty, low hemoglobin, low sodium, disposition, payer, diagnosis group and the hospital's effect. `readmit_prob` is the probability and `readmit_any_30d` the outcome. **The model has no term for sex, day of the week or season.** Those true effects are zero.
- **Gap.** 1 to 30 days, earlier days more likely.
- **Where.** A readmission goes outside the network with a probability built from the person's propensity and their payer. An outside readmission creates no admission row. It is listed only in `hidden/inpatient/outside_readmissions.csv`. This is planted mechanism P13.
- **Network readmissions** become emergency admissions on the right day. With probability 0.85 the hospital is the same one; otherwise it is drawn by the person's home area.
- **Planned returns.** Among eligible discharges with no unplanned readmission, some have a planned return 7 to 30 days later, on a weekday. It is most likely after a cancer admission. The return is an elective admission with `planned_admission = 1`. This is planted mechanism P16.

**The rule for counting.** Only the first return within 30 days counts. If it was unplanned, the discharge has a readmission. If it was planned, it does not, whatever happens later.

**Why the record and the truth agree exactly.** After any live discharge, and after an outside readmission, a person cannot enter as a new arrival for 30 days. So every return inside the window comes from the steps above. An analyst who takes eligible discharges from `data/`, finds each person's next admission, and counts it when it falls 1 to 30 days after discharge and is not planned, gets exactly `readmit_any_30d` minus the outside readmissions. `CHECKS.md` row S09 confirms this for every discharge. The observed rate is lower than the true rate only because of care outside the network.

### 7.7 Death after discharge

Some patients die outside hospital within 180 days of a live discharge: most of those discharged to hospice, and a small share of the others, more with higher severity and age. A patient with a network return scheduled is not drawn here; their fate is drawn again at the return. Deaths are in `persons_truth.csv` and nowhere in `data/`.

The simulator draws death only in a network hospital or within 180 days of a network discharge. It has no background mortality for people who have not been in hospital.

## 8. What is deliberately simple

These are limits of the model, not planted traps. The world is frozen, so they stay as they are.

- A transfer to another acute hospital is not followed. It does not create an admission at the receiving hospital, even when that would be the university hospital.
- A person's payer changes only at 65.
- Admission weights use each person's age on one reference date, so the pool does not age its way into higher admission rates over the five and a half years.
- People do not move between home areas.
- Sallowfield's patients have no recorded history before October 2024, so `prior_admits_12m` is low there for the first year. A real acquisition would look the same.
- Each stay has one index time and one score. A real score is recalculated many times a day.
- A person's count of other encounters is fixed for the whole period. It does not rise and fall from year to year.
- The lactate at the index time is the admission lactate. No second sample is drawn.
- An alert leads to one kind of response with one size of effect. Nothing models an evaluation that makes things worse, or a team too busy to come.

## 9. JSON files

`hidden/calibrated_intercepts.json`:

| Key | Contents |
| --- | --- |
| `reference_cohort_size` | 60,000 |
| `severity.center`, `severity.scale` | The centre and scale used to standardise severity |
| `intercepts.<name>.target` | The target mean on the reference cohort |
| `intercepts.<name>.intercept` | The solved intercept |
| `intercepts.<name>.reference_mean` | The cohort mean at that intercept |

The names are `lactate_drawn`, `icu`, `comfort_care`, `death`, `deterioration` and `readmission`.

`data/deterioration/vendor_model_card.json` is the vendor's card as a customer receives it (section 11.6). Every claim in it is invented. Keys: `vendor`, `product`, `abbreviation`, `intended_use`, `outcome_predicted`, `inputs`, `score`, `alert_threshold`, `development_population`, `claimed_performance`, `performance_by_subgroup`, `versions`, `formula`, and `fictional`, which says so.

`hidden/deterioration/vdi_formula.json`:

| Key | Contents |
| --- | --- |
| `features` | The limits beyond which each input counts |
| `v2` | The intercept and weights of version 2.0 |
| `v3` | The intercept and slope that version 3.0 applies to the version 2.0 logit |
| `display` | For each version, the shift and scale that turn a risk logit into a score |
| `lactate_imputed_when_missing`, `threshold` | 1.0 and 60 |
| `true_model` | The weights of the true risk model, for comparison |
| `response`, `ehr_flag` | The response and flag parameters |

`data/readmission/r30_model_card.json`, `hidden/readmission/r30_fit_trace.json` and `hidden/readmission/r30_truth.json` are described in sections 14.3 and 14.4.

`hidden/scribe/error_model_truth.json` (section 17.2):

| Key | Contents |
| --- | --- |
| `intercepts`, `solved_for_version_2_3_rate` | The solved intercept for each kind of error, and the rate it was solved for |
| `odds_ratios`, `log_odds_ratios` | The planted drivers |
| `long_visit_is_more_than_minutes`, `many_speakers_is_at_least` | 30 and 3 |
| `clinic_effect_logit_sd`, `errors_in_a_note_that_has_one` | 0.25, and the rule for counts |
| `severity` | The chance that one error is major (solved) or moderate or worse |
| `edit_minutes` | How editing time was built |
| `lenient_rater`, `rater_rules` | Which rater is lenient, and how a rating is drawn |

`hidden/economics/effects_truth.json` (section 16.4): the true effect on documentation minutes with its learning curve and the secular trend, on after-hours minutes, on visits and on same-day close; how adoption types were dealt; the wellbeing effect by type; the solved intercept of the survey's response model; and the holiday weeks.

## 10. How to derive readmission from `data/`

No ready-made readmission column is published. A reader builds it:

1. Stack the five admission files.
2. Keep index discharges: `disposition` is `home`, `home_health` or `snf`. This drops deaths, hospice, discharges against advice, transfers and open stays.
3. Keep discharges on or before 2026-05-31, so that each has 30 days of follow-up.
4. For each, find the same person's next admission. It is a readmission if it starts 1 to 30 days after the discharge date and `planned_admission` is 0.

For 2022 discharges this needs nothing from the burn-in. `prior_admits_12m` for early 2022 does reflect 2021 admissions, which are in `hidden/` only.

## 11. Deterioration, the vendor's index and alerts (Milestone 3)

Every number in this section is in `spec.DETERIORATION` unless another place is named. The step runs inside the day loop, in `generator/deterioration.py`, after the stay's course without any deterioration has been drawn (section 7.5) and before readmission (section 7.6).

### 11.1 Who is an index encounter

The **index time** is 12 hours after admission. A stay is **on a ward at 12 hours** if it has lasted at least half a day, is not in intensive care and is not on comfort care. That is about 80% of admissions.

`index_encounters.csv` and `index_truth.csv` hold the ward stays whose index time falls on or after the hospital's first scoring day (`vdi_scoring_from` in `facilities.csv`) and on or before 2026-06-30. Sallowfield's admissions from October 2024 to 14 January 2025 were never scored and are not in these files. A reader can rebuild the list from `data/` alone; `CHECKS.md` row S19 confirms it.

Deterioration itself happens at every hospital from the first simulated day, scored or not, because it changes the stay.

### 11.2 True vital signs

Each stay has an **acute instability** at 12 hours. It is tied to the admission severity (correlation 0.60) and skewed to the right: `h = exp(0.35 a) - 1`, where `a` is standard normal.

True heart rate, respiratory rate, systolic pressure, temperature and oxygen saturation are each a mean, plus a loading on `h`, plus terms for a few diagnosis groups and (for pressure and saturation) age, plus normal noise, kept inside plausible limits. Oxygen support (`none`, `low_flow`, `high_flow`) and the alertness category (`alert`, `drowsy`, `confused`, `unresponsive`, an invented scale) come from a latent need cut at fixed points. Saturation falls further as the need for oxygen grows, which gives SpO2 its low tail.

The true lactate at the index time is the true admission lactate. One lactate value serves the whole stay.

### 11.3 Recorded values and the planted measurement mechanisms

Recorded values are the true values plus a small normal error, rounded as the dictionary says. Oxygen support and alertness are recorded as they are. Four things are planted on top.

| ID | Mechanism | What the simulator does | Truth in |
| --- | --- | --- | --- |
| P1 | Pulse oximeter bias | For patients recorded as Black, recorded SpO2 has 1.2 points added, or 2.5 points when true SpO2 is below 90. The larger size is rare here: few ward patients are that low | `index_truth.csv`: `spo2_true`, `spo2_bias` |
| P2 | Default respiratory rate | With probability 0.33 at Northfen and Pellow Lake, and 0.05 elsewhere, the recorded rate is the charted default of 18, whatever the true rate. Together with rates that really are 18, about 41% of recorded values there equal 18, against about 18% elsewhere | `index_truth.csv`: `rr_true`, `rr_defaulted` |
| P3 | Missing lactate | Lactate is drawn in about 40% of admissions, more often when sicker (section 7.3), and less often at the two northern hospitals. The vendor's formula takes a missing lactate as 1.0 | `admissions_truth`: `lactate_true`, `lactate_drawn`; `vdi_formula.json` |
| P4 | Lactate assay change | From 2024-03-01 a lactate measured by the central laboratory (F01 to F03) reads 0.4 mmol/L high. The shift is in `lactate` in the admission files and in `lactate_at_index`. The true value does not move | `index_truth.csv`: `vdi_score_no_assay_shift`, the score the same patient would have had |

### 11.4 Encounters in the last 12 months (P5)

Beside admissions, each person has other encounters: emergency visits, observation stays and the like. The simulator gives each person one fixed pair of yearly counts, one inside the network and one outside. The total is Poisson, higher with frailty and age. Each encounter is outside the network with the person's outside-care propensity, and far more often when the person's payer is Medicaid or self-pay.

- `network_encounters_12m` is what the network's record holds: `prior_admits_12m` plus the person's other network encounters. The vendor's score uses it.
- `outside_encounters_12m` (hidden) is the rest: other encounters outside, plus outside readmissions in the last 365 days.
- At Sallowfield the network's record of a patient's other encounters starts when the hospital joined. It fills in over the first 12 months; the part not yet on record counts as outside.

The true risk depends on all encounters. The score sees only the network's. So the score under-predicts for people whose care is spread across other systems.

### 11.5 True risk

The outcome is unplanned transfer to intensive care, unplanned transfer to a higher level of care, or death, within 48 hours of the index time.

With no rapid-response evaluation, the logit of the risk `p0` is a solved intercept plus:

- terms in the **true** vital signs, oxygen support, alertness, true lactate, age and **all** encounters. Each vital sign enters as its distance beyond a limit (`spec.DETERIORATION["features"]`): heart rate above 90, respiratory rate above 18, systolic pressure below 110, temperature above 38.0 or below 36.0, SpO2 below 100, lactate above 1.0 (counted up to 3.0), encounters up to 8;
- comorbidity, diagnosis group, admission severity and the instability itself;
- winter (December to February);
- the hospital's drawn effect, and a further 0.20 at Sallowfield (P11);
- unmeasured noise with standard deviation 0.60.

**The true model has no term for payer or for race and ethnicity.** Where the score is miscalibrated for those groups, the cause is measurement (P1) or care outside the network (P5).

The intercept is solved on the reference cohort's ward stays at F01 to F05, to a mean risk of 0.0395.

### 11.6 The vendor's score

Version 2.0 is a fixed formula on **recorded** values and **network** encounters, with the same terms as the first bullet above and its own weights. It gives a risk logit. The score is `round(100 * logistic(shift + logit))`: a fixed transform of the vendor's risk, so `vendor_risk_table.csv` is that transform turned round.

Version 3.0, from 2026-02-01, is `-0.76 + 0.78 * (version 2.0 logit)` with a new transform, so the same threshold of 60 flags fewer patients and stands for a different risk. The risk table has a block of rows for each version.

Compared with the truth, the vendor's weights are heavier on lactate and the respiratory rate, the same on SpO2 and lighter on the rest, and its baseline comes from a population with more events (P6, P12). The formula is in `hidden/deterioration/vdi_formula.json`. `CHECKS.md` row S26 confirms that it reproduces every published score from the published inputs.

`data/deterioration/vendor_model_card.json` is what a customer is given: intended use, inputs by name, a claimed C-statistic of 0.84 on the vendor's own data, the threshold, and no formula.

### 11.7 Alerts, response and potential outcomes

- The score is **shown** from the hospital's alert date (`vdi_alerts_from`). Before that it is stored and nobody sees it.
- An **alert** fires when the score is shown and is 60 or more.
- A **rapid-response evaluation** follows an alert with probability 0.85 at go-live, falling by 0.0075 for each month since that hospital went live, to a floor of 0.70 after 20 months (P7).
- An evaluation multiplies the risk by 0.80: `p1 = 0.80 * p0` (P8).
- **Both potential outcomes** are drawn from one uniform number `u` for each stay: `y0 = (u < p0)` and `y1 = (u < p1)`. So every `y1` event is also a `y0` event, and the ratio of the two counts estimates 0.80 with little noise.
- The realised outcome `y_true` is `y1` if an evaluation happened and `y0` otherwise.

### 11.8 What an event is, and what it does to the stay

An event has a type, drawn by hospital: at the university hospital 90% transfer to intensive care and 10% death; at the two northern hospitals 75% transfer out, 15% intensive care, 10% death; elsewhere 80%, 10% and 10%.

- **Death:** the stay ends in death 0.6 to 2.5 days after admission, inside the window.
- **Transfer out:** the stay ends in a transfer in the same window.
- **Transfer to intensive care:** the stay goes on. Its length becomes 1.5 times the length it would have had, plus one day, and death in hospital gains a further 10% chance.
- **No event:** a patient on a ward at 12 hours who would have died within 2.5 days has that death placed 2.5 days later. So nobody on a ward dies inside the window without an event (`CHECKS.md` S25). A transfer inside the window with no event is a planned or lateral one.

Because an evaluation prevents some events, alerts change deaths, lengths of stay and what follows. That is real in this world, and it is why the inpatient files differ from Milestone 2 (section 13).

### 11.9 The EHR outcome flag and its delay (P9)

`ehr_outcome_48h` is what the record holds, not the truth.

- A true event is missed with probability 0.065 for a transfer to intensive care or a death, and 0.18 for a transfer out, which is often coded as a plain transfer. The northern hospitals' events are mostly transfers out, so the flag's sensitivity is about 0.85 there against about 0.92 overall. The difference between hospitals comes from the mix of event types.
- A stay with no event is flagged with probability 0.004.
- The label becomes available 5 days after the index date: the 48-hour window plus 3 days. When that is after 2026-06-30, `ehr_outcome_48h` and `outcome_available_date` are empty.

`index_truth.csv` gives `y_true` and `ehr_flag_error` (`none`, `missed`, `false_positive`).

### 11.10 Where each known answer is

| Question a reader can ask | Known answer |
| --- | --- |
| How well does the score discriminate and calibrate locally? | Compare with `p0`, `y0` and `y_true` in `index_truth.csv` |
| Why is it miscalibrated for a subgroup? | `spo2_bias`, `rr_defaulted`, `outside_encounters_12m`; `lactate_drawn` in the admission truth |
| What did the assay change do to alerts? | `vdi_score` against `vdi_score_no_assay_shift`, the same patients |
| Did the alerts help? | `y0` and `y1` for every index encounter; the true risk ratio is 0.80 among those evaluated |
| How good is the outcome label? | `y_true` and `ehr_flag_error` |
| How did the response fade? | `response_prob`, filled where an alert fired |

Every one of these is simulator truth and never evidence.

## 12. Working with the index files from `data/` alone

1. `index_encounters.csv` joins to the admission files by `encounter_id`, and through them to `persons.csv` by `person_id`.
2. Silent mode for the planned evaluation: `facility_id` F01 to F05 and `index_datetime` from 2023-07-01 to 2023-12-31. `vdi_shown` is 0 throughout.
3. The vendor's stated risk for a row is the `vendor_risk` at its `vdi_version` and `vdi_score`.
4. Use only rows with a label. A row whose label had not arrived by the data end has an empty outcome.
5. After go-live the outcome reflects the alerts that were answered. `rrt_evaluated` says which.

## 13. What changed in the Milestone 2 files

Milestone 3 added steps to the same simulation, so every file from Milestone 2 has new contents except `facilities.csv`, `timeline.csv` and `facility_truth.csv`. No column was added, removed or renamed in those files. The causes:

- A deterioration changes a stay's death, disposition and length, and so the discharges, readmissions and later admissions that follow.
- The reference target for death before any deterioration fell from 0.0235 to 0.0175, because deterioration now adds deaths. In-hospital death is 1.9% of admissions, as before.
- Recorded lactate from the central laboratory reads 0.4 mmol/L high from 2024-03-01 (P4).
- Lactate is drawn less often at the two northern hospitals than before. Overall it is still drawn in about 40% of admissions.
- `encounter_id` and `person_id` values are not comparable with Milestone 2's. The world is a new draw from the same seed.

## 14. The readmission model R30 (Milestone 4)

R30 is the model Tonmick's analytics team built at the end of 2022. The generator carries out the team's procedure on the data the team had, and publishes what the team would have: the sample, a model card and the production scores. Every setting is in `spec.R30`. The code is `generator/readmission.py`. It draws no random numbers and it changes no outcome.

### 14.1 The development sample (P14)

`r30_development_sample.csv` holds the discharges the team used:

- from the university hospital (F01), medicine service;
- admitted on or after 2022-01-01 and discharged from 2022-01-01 to 2022-06-30;
- alive, to home, home with home health or skilled nursing;
- with all five tests of the admission panel on file: sodium, creatinine, hemoglobin, white cell count and lactate;
- and only each patient's first such discharge in the period.

Two of these rules shape the sample. Lactate is drawn more often in sicker patients (section 7.3), so the complete-panel rule keeps a sicker group: about 38% of the hospital's eligible medicine discharges. The first-discharge rule drops 97 repeat discharges, which are the ones most likely to be followed by another return. The model is then used on every discharge at every hospital.

The outcome column, `readmit_30d_observed`, is what the network's record shows: the first return to a network hospital within 30 days, when it was not planned. A reader can rebuild every column from `data/` (`CHECKS.md` S27).

### 14.2 The team's method (P15)

- **Candidates.** Sixteen terms with 17 parameters: age 65 or over; female; stay over 5 days; prior admissions (none, one, two or more: two parameters); comorbidity count as a number; discharge to skilled nursing; discharge with home health; Medicaid; sodium below 135; hemoglobin below 12; diagnosis group cancer, heart failure, COPD; emergency admission; weekend discharge; winter discharge. Age and length of stay are cut in two. The last two are noise: the true model has no term for them.
- **Screen.** Each term is fitted alone, and kept when its likelihood-ratio test gives p < 0.20. The generator tests this as a statistic above the chi-square critical value (1.6424 for one parameter, 3.2189 for two), so no p-value function is needed.
- **Fit.** The terms kept are fitted together by iteratively reweighted least squares, 25 Newton steps, with exact sums and a pure-Python solver. Coefficients are rounded to six decimals before any use.
- **Reported performance.** The C-statistic of the rounded model on the development sample, to three decimals. Nothing else.

In this world the screen keeps 11 terms and drops female, Medicaid, cancer, COPD and emergency admission. Four of the five dropped terms have clear effects in a large sample; only sex does not. Both noise predictors pass the screen, each by a narrow margin.

### 14.3 What is published

- `r30_model_card.json`: the card as the team wrote it. Intended use, outcome, eligible discharges, the development population in the team's words, the method, the definition of every candidate term, the terms the screen dropped, the coefficients, the sample size and number of readmissions, and the reported C-statistic. It says that a laboratory value not measured counts as not low, and that there was no validation beyond the development sample.
- `r30_scores.csv`: the risk production calculated for every eligible discharge from 2023-01-01 at all six hospitals, dated on the discharge day. Each is the logistic function of the card's intercept plus coefficient times value, and each can be rebuilt from `data/` and the card (`CHECKS.md` S29).

From 2023-02-01 the score is shown on the discharge-planning worklist. Its true effect on readmission is zero (P17): no outcome in the simulation depends on it.

### 14.4 What is hidden

- `hidden/readmission/r30_fit_trace.json`: each term's likelihood-ratio statistic and critical value, which were kept, the unrounded coefficients, the deviance and the unrounded apparent C-statistic.
- `hidden/readmission/r30_truth.json`: the true model's terms, solved intercept and hospital effects; the statement that both noise predictors and the worklist have a true effect of zero; a **reference fit**; and C-statistics for R30 and for the true probability, on the development sample and on the reference discharges.

The reference fit is all 17 parameters of R30's form, with no screen, fitted to the 28,002 eligible discharges of 2023 at F01 to F05, once on the true outcome and once on the observed one, with standard errors. It shows what the form gives with about sixteen times the data. It is not the true model: the true model uses continuous values, a hospital effect, severity and frailty. So a noise predictor can have a small coefficient in the reference fit. Weekend discharge does. People who leave at a weekend differ in ways the form does not hold, and that is confounding, not an effect.

### 14.5 Known answers

| Question | Known answer |
| --- | --- |
| Can the card's coefficients be reproduced? | `r30_fit_trace.json`; `CHECKS.md` S28 refits the published sample |
| How optimistic is the reported C-statistic? | `r30_truth.json`, `c_statistics`: R30 on the development sample against R30 on the reference discharges |
| What ceiling could any model reach? | The true probability's C-statistic, same file |
| Did the screen pick the right terms? | The reference fit, and the true model's terms |
| Was the sample big enough? | `CHECKS.md` T45, the Riley minimum under five assumptions |
| Why does R30 look too pessimistic in the north? | `outside_readmissions.csv`: the record misses returns elsewhere. `CHECKS.md` T44 gives the O/E against the observed outcome and against readmission to any hospital |

## 15. Chart review, logs, change points and monthly truth (Milestone 4)

These are written by `write_products` in `generator/deterioration.py`, after the day loop. Blocks 26 to 28 are used here and nowhere else. Settings are in `spec.CHART_REVIEW`, `spec.RRT_LOG` and `spec.LAB_LOG`.

### 15.1 Chart review

`chart_review.csv` is the committee's review of 800 silent-mode index encounters.

- **Strata.** The nine deciles of the silent-mode scores are cut points: the score at position ceil(k n / 10) in sorted order, for k = 1 to 9. An encounter's stratum is 1 plus the number of cut points its score is above. Scores are whole numbers, so the strata are not equal in size. `CHECKS.md` S30 prints the cut points and sizes, and a reader can recompute both from `index_encounters.csv`.
- **Sample.** 40 encounters from each of strata 1 to 5, 60 from 6 and 7, 80 from 8, 120 from 9 and 280 from 10, drawn without replacement. `incl_prob` is the number sampled divided by the stratum size.
- **Reviewer.** `reviewer_outcome` is the true outcome seen through a careful reviewer: a true event is found with probability 0.99, and a non-event is called an event with probability 0.001. In this world the reviewer made no error on the 800.

The sample holds far more events than a simple random sample would. Its raw event rate is not an estimate of anything until the inclusion probabilities are applied.

### 15.2 Rapid-response log

`rrt_log.csv` has one row for each evaluation in `index_encounters.csv`. The evaluation begins 0 to 3 hours after the index time (55%, 30%, 10% and 5%). Nurse minutes are 5 plus a gamma draw, mean 30 in all; physician minutes are a gamma draw with mean 10. The minutes do not depend on the patient or the outcome. IDs run in the order the evaluations began.

### 15.3 Laboratory change log

`data/network/lab_change_log.csv` is the change log of the four laboratories: the central one, which serves F01 to F03, and one each at Northfen, Pellow Lake and Sallowfield. It has 84 routine entries, drawn from 24 invented templates at random dates from January 2022, and five fixed entries. Sallowfield has entries only from the day it joined.

One fixed entry, dated 2024-03-01 at the central laboratory, records that lactate moved to a different method. It is written as a laboratory would write it and says nothing about its effect. That entry is planted mechanism P4, and it is the only place in `data/` where the change is recorded. The other method changes in the log, and every routine entry, have no effect on any value in the data.

### 15.4 Change points

`hidden/deterioration/change_points.csv` lists each planted change with its date, hospitals, mechanism, size and unit: the worklist (size zero), the start of silent scoring, alerts going live at each group of hospitals, the start of the fall in response and the day it reaches its floor, the assay change, the acquisition, and version 3.0. Winter is not a change point; it recurs, and `monthly_truth.csv` shows it.

### 15.5 Monthly truth

`hidden/deterioration/monthly_truth.csv` has a row for each month from July 2023 to June 2026 and each hospital group (`f01_f03`, `f04_f05`, `f06`, `all`) that had index encounters. It gives the count, the mean true risk with no evaluation, the mean true risk given the evaluations that happened, the mean vendor risk, their ratio, the share of scores at or above the threshold whether or not they were shown, and the share of fired alerts that were answered. These are means of hidden probabilities, so they carry no outcome noise.

## 16. The AI scribe: clinics, rollout, panel and survey (Milestone 5)

Every number is in `spec.SCRIBE`. The scribe is a separate world from the hospitals: it has its own blocks (30 to 36 and 40 to 43), reads no inpatient table, and shares no person with it. `generator/scribe.py` writes all of it; `generator/economics.py` writes the two cost tables.

Each true value is rounded to the decimals it is written with before it is used. So the hidden files reproduce the public ones exactly, not just nearly.

### 16.1 Clinics, clinicians and the rollout

- **Clinics.** 24, fixed in the spec: 16 primary care (8 central, 5 south, 3 north) and 8 specialty (two cardiology, two orthopaedics, one each of oncology, endocrinology, pulmonology and gastroenterology). Behavioural health is outside the pilot, as the backstory says.
- **Clinicians.** Exactly 130. Each clinic gets three, and the other 58 are dealt by a weighted draw (primary care 1.4, specialty 1.0). Clinics end up with 3 to 9. Role is physician, nurse practitioner or physician assistant (60%, 25%, 15%). Clinical time is 1.0, 0.8, 0.6 or 0.5 of full time.
- **Rollout (block 31).** Each stratum is shuffled and dealt to waves 1 to 4 in turn, so every wave holds four primary care and two specialty clinics. The waves go live on the Mondays of weeks 14, 27, 40 and 53, giving 51, 38, 25 and 12 live weeks.
- **Interpreter use.** Each clinic has its own chance that a visit uses an interpreter, drawn around 6% (3% to 13% across the 24 clinics). It is in `hidden/scribe/clinic_effects.csv`.

### 16.2 What a clinician is like before the scribe (block 40)

| Trait | Form |
| --- | --- |
| Baseline documentation time | Lognormal around 7.0 minutes a visit in primary care and 8.0 in specialty clinics, log SD 0.22 |
| Own saving per scribe visit | Normal, mean 2.0, SD 0.6, kept between 0.4 and 3.6 |
| After-hours minutes in a normal week | Lognormal, mean 170 at full time, scaled by clinical time; higher for heavier documenters |
| Latent wellbeing | Standard normal; lower for heavier documenters (weight -0.35) |
| Visit volume | 56 visits a week per full-time primary care clinician and 46 in specialty clinics, times a personal factor |

### 16.3 Adoption (block 41, mechanism P23)

Each clinician has a propensity: 0.9 times their standardised log baseline documentation time, plus standard normal noise. The 13 lowest never adopt, the next 18 are partial users, and the other 99 are adopters. Dealing by rank makes the shares exact. Heavier documenters therefore adopt more: true baselines average 7.9 minutes for adopters and 5.4 for never-adopters.

Once settled, an adopter uses the scribe on about three visits in four and a partial user on about one in four (each has their own value, `steady_share`). In a clinic's first six live weeks the chance is 35%, 55%, 70%, 82%, 91% and 96% of that.

### 16.4 The clinician-week panel (block 42)

One row for each of 130 clinicians and 64 weeks: 8,320 rows.

- **Visits** are Poisson. The mean is the clinician's weekly volume, times the holiday factor in six weeks (`spec.SCRIBE["holiday_weeks"]`). A clinician is away in 4% of weeks and then has no visits. With the scribe the mean rises by 0.4 times the use that week.
- **Scribe visits.** Each visit uses the scribe with that week's chance, independently.
- **Documentation minutes per visit** are the baseline, minus 0.02 a week for everyone (the secular trend, P22), minus the clinician's saving times the learning share times the share of visits that used the scribe, plus noise. The learning share is 0.5 in live weeks 1 to 4, then 0.625, 0.75 and 0.875, and 1 from week 8. A floor of 1.0 minute applies and is reached in 5 rows.
- **After-hours minutes** are the clinician's normal level, times the holiday factor, times lognormal noise, times one minus 0.20 times the use that week.
- **Same-day close.** Each note is closed the same day with the clinician's own chance, which rises with use.
- **Empty cells.** In a week with no visits, `scribe_share`, `doc_minutes_per_visit` and `same_day_close_share` are empty.

"Use" means the share of visits with the scribe times the learning share. For visits it is the expected share, because the realised share does not exist until the visits are drawn.

**The paired world.** `hidden/economics/clinician_weeks_truth.csv` gives, for every row, the visits, documentation minutes and after-hours minutes had the scribe not existed. The visits come from the same uniform draw read at the lower mean, and the minutes share their noise. Before go-live the two worlds are identical.

### 16.5 The survey (block 43, mechanism P24)

The Tonmick Clinician Pulse has five invented items, each scored 1 (strongly disagree) to 5 (strongly agree). The wording is original to this world and adapts no published instrument.

1. I finish my notes within my scheduled working day.
2. At the end of a clinic day I still have energy for the rest of my life.
3. The record system helps me more than it slows me down.
4. I can give each patient my full attention during the visit.
5. I would recommend my current way of working to a colleague.

- **Waves.** Baseline in February 2025 and final in March 2026 for everyone. A post-wave survey three months after go-live (July 2025, October 2025, January 2026) for waves 1 to 3. For wave 4 the final survey serves as the post-wave one. That gives 355 rows.
- **Latent wellbeing** at a later wave is the baseline value, plus a drift (SD 0.30), plus the clinician's own effect: about +0.25 SD for adopters, +0.08 for partial users, zero for never-adopters.
- **Response.** The chance is `plogis(intercept + 0.7 * latent wellbeing)`, with the intercept solved so that the mean chance is 0.62. Clinicians who are worse off answer less often, so respondents look better off than the group.
- **Items.** Each is 3.1 plus a shift, plus 0.85 times a mix of latent wellbeing and noise, rounded and kept between 1 and 5. They are empty for a clinician who did not respond.

## 17. AI-drafted notes, their true errors and the audit (Milestone 5)

### 17.1 The notes frame (block 32, decision D11)

`ai_notes_frame.csv` has one row for every scribe visit in the panel: 102,502 notes. The panel is generated first, so the count for a clinician-week equals that row's `scribe_visits` by construction (`CHECKS.md` T59).

- **Date.** A weekday of the visit's week, never one of seven closed dates. Note IDs run in order of date.
- **Visit type** by clinic type; **visit minutes** lognormal by type (means 32 new, 19 follow-up, 30 annual, 26 procedure), 25% longer with an interpreter, kept between 5 and 90.
- **Interpreter** by the clinic's own rate: 7.1% of notes.
- **Speakers.** Two to six, and one more when an interpreter is present.
- **Version.** 2.3 before 2025-11-03 and 2.4 from that Monday: 41,988 and 60,514 notes.
- **Words** grow with the length of the visit. **Editing minutes** grow with the visit's length and with the number of true errors in the draft, times gamma noise. That makes editing time an honest but weak signal of a bad draft.

### 17.2 True errors (block 33, mechanism P19)

For each of the four kinds, the chance that a note has at least one is

`plogis(intercept + the clinic's effect + the log odds ratios that apply)`.

| Kind | Rate solved for on version 2.3 notes | What raises or lowers it |
| --- | --- | --- |
| Omission | 0.170 | Interpreter, odds ratio 1.8. Visit over 30 minutes, 1.5 |
| Hallucination (content not said) | 0.105 | Version 2.4, odds ratio 0.70 |
| Misattribution (wrong speaker or person) | 0.085 | Three or more speakers, odds ratio 1.6 |
| Wrong value (number or dose) | 0.050 | Nothing but the clinic |

- **Clinic effect.** One value per clinic for every kind of error: 24 draws, centred and scaled to a logit SD of exactly 0.25.
- **Intercepts** are solved by bisection on the version 2.3 notes and rounded to six decimals. They are in `hidden/scribe/error_model_truth.json`, with the odds ratios.
- **Counts.** A note with an error of a kind has one plus a Poisson(0.35) number of them.
- **Severity.** Each error is major with a small chance (solved so that 1.5% of version 2.3 notes have a major error; it comes to 2.7% per error) and moderate or worse with chance 0.30. A note's worst severity is the worst over its errors.

`hidden/scribe/note_errors_truth.csv` has the counts and the worst severity for every note in the frame, not only the audited ones.

### 17.3 The audit sample (block 34, mechanism P21)

The committee drew 1,200 notes, stratified by specialty group, interpreter and version: 12 strata. The groups are primary care; medical (cardiology, oncology, endocrinology, pulmonology); and procedural (orthopaedics, gastroenterology). The allocation is in `spec.SCRIBE["audit"]["allocation"]`: 60 from each of the six interpreter strata, so interpreter visits are 30% of the sample against 7% of the frame. Each row of `audit_sample.csv` carries its stratum, the stratum's size, the number drawn and the inclusion probability. A reader can rebuild every stratum from the frame.

### 17.4 Raters and ratings (blocks 35 and 36, mechanism P20)

- **Raters.** Eight clinicians, `R01` to `R08`, and a senior reviewer, `R09`. Each rater has a sensitivity for each kind of error, drawn uniformly between 0.70 and 0.92, and one false-positive rate between 0.01 and 0.05. One rater, chosen by a draw, is lenient: sensitivities between 0.57 and 0.63. The senior reviewer's sensitivities are between 0.95 and 0.98, with a false-positive rate under 0.01.
- **A rating.** For each kind, the rater flags the note with their sensitivity if the note truly has that kind of error, and with their false-positive rate if it does not.
- **Severity as rated.** None when nothing is flagged. When the rater found a real error, the true worst severity with chance 0.75, one level lower with 0.17, one level higher with 0.08. When every flag is a false alarm, minor with chance 0.85 and moderate otherwise.
- **Rounds.** Two different raters, chosen at random, rate each note independently (rounds 1 and 2). If the two ratings differ in any field, the senior reviewer rates the note as well (round 3). In this world that happens for 426 notes.

The senior reviewer does not see the truth. A real error that both raters miss never reaches round 3.

### 17.5 Costs and wages

`data/economics/wage_rates.csv` gives a national hourly wage for seven roles and a loaded cost, which is the wage times 1.46. `data/economics/scribe_costs.csv` has seven cost lines. A line has either a price (the licence per clinician-month and the one-time implementation fee, both invented) or a number of hours and the role that prices them. Block 44 is reserved and draws nothing. Sources are in `PROVENANCE.md` section 6. The `rn` and `hospitalist` rows price the minutes in `rrt_log.csv`.

### 17.6 Where each known answer is

| Question | Where the answer is |
| --- | --- |
| Does this note truly have an error, of which kind, how bad? | `note_errors_truth.csv` |
| What is the true error rate in the frame, or in any subgroup? | `note_errors_truth.csv` joined to the frame |
| How strong is each driver of error? | `error_model_truth.json`; `clinic_effects.csv` |
| How accurate is each rater, and who is the lenient one? | `rater_parameters.csv`; `error_model_truth.json` |
| How much time does the scribe truly save? | `clinician_truth.csv` (each clinician's own value); `clinician_weeks_truth.csv` (each week) |
| What would this clinician-week have looked like without the scribe? | `clinician_weeks_truth.csv` |
| Who adopted, and why does that bias a comparison? | `clinician_truth.csv`: `adoption_type`, `baseline_doc_minutes` |
| What is the true effect on wellbeing, and who did not answer? | `clinician_truth.csv`; `effects_truth.json` |

### 17.7 What is deliberately simple

- A clinician never changes clinic, role or clinical time.
- Editing minutes in the frame and documentation minutes in the panel are drawn separately. They do not add up.
- A rater's chance of flagging does not depend on how many errors of that kind the note has.
- The clinic effect is the same for every kind of error.
- The wellbeing effect arrives in full by the first survey after go-live.
- No patient is identified anywhere in the scribe files, so notes cannot be linked to admissions.
