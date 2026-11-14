# Provenance

**Everything in this repository is fictional.** No record describes a real person, hospital, vendor or product. `hidden/` holds what the simulator did and is never evidence. No result here says anything about any real hospital, product or patient group.

This file records where the world's numbers came from: which were written down before the generator existed, which were solved, which were adjusted, and which rest on a published source. It covers the frozen world, version 1.0.0 (Milestones 2 to 5, frozen at Milestone 7); hospice is not in this release. Run-by-run results on each machine are in `HANDOFF.md`, which is not hashed.

## 1. How the world is produced

- **Code only.** Every file under `data/` and `hidden/` is written by `generator/generate_world.py` from the root seed `20261110`. No real data of any kind is read.
- **Pins.** Python 3.13, NumPy 2.5.3, pandas 3.0.5 (`requirements.txt`).
- **Regenerate and compare.** `python3 generator/verify_world.py` rebuilds every generated file in a temporary folder and compares it with `SHA256SUMS`. CI does the same on every push.
- **A matching hash confirms file identity only.** It cannot validate any assumption about recruitment, measurement, causation or transport.

## 2. What was written down first

The order of commits is the evidence that the answers were not tuned after the fact.

| Commit | What it holds |
| --- | --- |
| `6ee3ade` (Milestone 1) | The targets (`spec.TARGETS`), the planted mechanisms (`DESIGN.md` section 6), every column, and no generator |
| `dcd2c27` (Milestone 1b) | Deterministic maths helpers. Still no generator |
| `83ac07e` (Milestone 2) | The first generator code, and the first data |
| `6df4c4a` (Milestone 3) | Vital signs, the vendor's index, alerts and deterioration, in the same simulation |
| `54271c2` (Milestone 4) | The readmission model R30, chart review, logs, change points and monthly truth |
| `71f1d0f` (Milestone 5) | The AI scribe: clinics, rollout, panel, survey, notes, true errors, audit, costs and wages; the Python and R cross-check |
| Milestone 7 (the commit that adds `data/` and `hidden/`) | The freeze: version 1.0.0, the data committed once, `BOOK_MAP.md`. No generator change and no change to any data file |

What Milestone 2 added to `spec.py`, in the same commit as the generator, is listed in `DESIGN.md` section 15 (decision A16). It includes the ranges in `spec.SECONDARY_TARGETS`. Those ranges were not written first, and `CHECKS.md` marks them. Milestone 3 added nine more of the same kind (T14b to T32c) and every number in `spec.DETERIORATION`, in the same commit as its generator code.

For Milestone 3 the things written first, in `6ee3ade`, were: the target ranges T14 to T32; the planted mechanisms P1 to P12 and the sizes `DESIGN.md` section 6.1 gives them; the columns of the index files, with the two changes listed in `DESIGN.md` decision A25; and decisions D5 and D6 on common random numbers and paired counterfactuals. Section 4 below says which of those sizes were kept and which were not.

For Milestone 4 the things written first, in `6ee3ade`, were: the target ranges T33, T34 and T40 to T46; mechanisms P14 to P17; the columns of every Milestone 4 file; the list of R30's 17 candidate parameters and its screen at p < 0.20; and the anticipated C-statistic of 0.70 for the sample-size calculation, fixed in `spec.R30` before any data existed. Two of those target ranges did not survive: see variance V6 in section 4.

For Milestone 5 the things written first, in `6ee3ade`, were: the target ranges T50 to T60 and T70 to T77, with variances V2 and V3 already applied; mechanisms P19 to P24 with their sizes (`DESIGN.md` section 6.3); decision D11, that the panel comes before the notes frame; the definition of the naive pre-post estimate (`DESIGN.md` section 9.5); and the columns of the scribe files, with the changes listed in `DESIGN.md` decision A43. Every number in `spec.SCRIBE` and `spec.ECONOMICS` arrived in the same commit as the generator code. One target range did not survive: see variance V7 in section 4.

## 3. Numbers that were solved

Solved by bisection on the reference cohort (`WORLD_SPEC.md` section 6). The full values are in `hidden/calibrated_intercepts.json`.

| Model | Target mean on the reference cohort | Solved intercept |
| --- | --- | --- |
| Lactate drawn | 0.400 | -0.8543 |
| Intensive care at 12 hours | 0.158 | -2.4491 |
| Comfort care at 12 hours | 0.028 | -5.4158 |
| Death in hospital, before any deterioration on the ward | 0.0175 | -6.0085 |
| Deterioration within 48 hours with no evaluation, ward stays at F01 to F05 | 0.0395 | -6.5515 |
| Readmission within 30 days | 0.143 | -3.1360 |

Severity is standardised with centre 0.6060 and scale 1.1488.

Three of these moved at Milestone 3. The lactate intercept moved because lactate is now drawn less often at the two northern hospitals. The death target fell from 0.0235 because deterioration now adds deaths of its own; realised in-hospital death is 1.9%, as at Milestone 2. The readmission intercept moved a little because lengths of stay changed.

**The scribe's solved numbers** (Milestone 5) are solved on the notes and survey rows themselves, not on a reference cohort, because the whole frame exists before the errors are drawn. They are rounded to six decimals before use. The error intercepts are in `hidden/scribe/error_model_truth.json` and the survey's is in `hidden/economics/effects_truth.json`; `hidden/calibrated_intercepts.json` is unchanged.

| Model | Target | Solved value |
| --- | --- | --- |
| A note has an omission, version 2.3 notes | 0.170 | intercept -1.702468 |
| A note has a hallucination, version 2.3 notes | 0.105 | intercept -2.122188 |
| A note has a misattribution, version 2.3 notes | 0.085 | intercept -2.578544 |
| A note has a wrong value, version 2.3 notes | 0.050 | intercept -2.927458 |
| A note has a major error, version 2.3 notes | 0.015 | logit of the chance that one error is major: -3.575826 (a chance of 0.0272) |
| A clinician answers the survey | 0.62 | intercept 0.413232 |

## 4. Numbers that were adjusted to meet the targets

The first run of the generator, on 12 November 2026, met most Milestone 2 targets and missed some. I then changed parameters in two rounds until all were met. No target range was changed. The parameters changed after seeing output were:

- the readmission coefficients for frailty, prior admissions, comorbidity, age, payer, disposition and diagnosis group, to bring the true model's C-statistic from 0.77 into 0.70 to 0.74 and to bring readmission by payer nearer the published pattern;
- the reference-cohort targets for intensive care, comfort care, death and readmission;
- the intercept of the outside-care propensity;
- the length-of-stay constant, and the share of very short stays, which was added to bring the share of patients still on a ward at 12 hours to about 80%;
- the disposition intercepts for skilled nursing, hospice and transfer;
- the age tilt at Sallowfield and the under-65 payer shares;
- the elective shares by hospital, the surgical share of emergency work at the university hospital, the share of admissions with each laboratory panel measured, and the university hospital's term for ordering lactate. These four were set with Milestone 4 in view: the readmission model's development sample has to be the size the design asks for.

### Milestone 3

The deterioration model was tuned over many runs on 12 November 2026, far more than Milestone 2 needed. No target range was changed. This is what happened, so that a reader can judge it.

**Kept at the size written first** (`DESIGN.md` section 6.1): the oximeter bias of 1.2 points, and 2.5 below a true SpO2 of 90; the assay shift of 0.4 mmol/L; a missing lactate taken as normal; the response of 0.85 falling by 0.0075 a month to 0.70; the risk ratio of 0.80; the false-positive rate of 0.004; the 3-day label delay; the threshold of 60; the vendor's claimed C-statistic of 0.84.

**Changed from what was written first:**

- *Default respiratory rate (P2).* The design said about 40% of recorded values at the two northern hospitals would be the default. The planted share is 0.33; with rates that really are 18, 41% of recorded values there equal 18. Target T30 is measured on that visible share.
- *EHR flag sensitivity (P9).* The design gave 0.92 overall and 0.85 at the northern hospitals. The simulator now sets a miss rate by type of event, and the hospital figures follow from the mix of events.
- *Sallowfield (P11).* A fixed 0.20 on the logit scale is added to its drawn hospital effect, which was slightly negative.

**Set after seeing output.** Everything else in `spec.DETERIORATION`: the vital-sign distributions, both sets of weights, the limits in `features`, the encounter model, the event types and what they do to a stay, and the miss rates. The constraints pull against each other. The targets ask for a C-statistic of 0.76 to 0.80 and a calibration slope of 0.80 to 0.92, and at the same time for three subgroups whose O/E is about 1.3 times the overall figure. Larger weights on the biased inputs raise the subgroup gaps but also raise discrimination. The settings that hold all of them have these features, each of which is a choice made to fit:

- SpO2 enters both formulas in a straight line below 100, with a narrow spread between patients, so that a 1.2-point bias moves the score enough;
- lactate counts only up to 3.0 mmol/L, and the vendor weights it above its true weight, so that a 0.4 shift moves alerts by two to four points;
- people on Medicaid or with no insurance have most of their other encounters outside the network;
- lactate is drawn less often at the two northern hospitals (a Milestone 2 parameter, changed here);
- the vendor's weights on heart rate, blood pressure, oxygen support and alertness are below the true ones.

**Set against this one realised world.** Silent mode holds about 12,000 encounters and about 440 flagged events. On a sample that size a C-statistic moves by about 0.012 from one draw to the next, and a calibration slope by about 0.05, which is a large part of each target range. So after the true model was settled, the vendor's intercept, its weights, both display shifts and the two version 3.0 parameters were adjusted until the realised values sat inside their ranges. Version 3.0's intercept and slope started from a logistic recalibration of version 2.0 on the world's own data from February 2025 to January 2026.

Two consequences follow. First, the realised C-statistic is 0.772, close to the floor of 0.76, and nothing more should be read into its exact value. Second, any later change to the true model redraws the silent-mode sample, and the vendor's settings would then need the same adjustment again. `HANDOFF.md` says how.

### Milestone 4

**Nothing in the true model changed, and no file from Milestones 2 and 3 changed.** Every Milestone 4 file is computed from the finished simulation, or drawn from its own block after it.

**The development sample was defined after seeing counts.** The brief's rule (the university hospital's medicine discharges, January to June 2022, complete laboratory panel) gave 1,880 discharges and 254 observed readmissions when discharges were counted without regard to admission date. The brief asks for 1,500 to 1,900 and 170 to 230. Two rules were then added, and both are on the model card:

- the admission must fall inside the extract, on or after 2022-01-01, so that every row can be found in `data/`. That leaves 1,822;
- only each patient's first such discharge counts. That leaves 1,725 discharges and 217 readmissions.

The first-discharge rule is a common analyst's choice, and it is also a flaw the book can use, because the model is then applied to every discharge. It was chosen after seeing that the count of events was too high, and it is recorded here for that reason.

**Variance V6: two targets were not met, and their ranges were replaced.** The brief asks for an apparent C-statistic of 0.73 to 0.77 (T41) and a calibration slope at validation of 0.70 to 0.85 (T43). The world gives 0.708 and 0.882. These cannot be reached by an honest fit:

- the true model, which knows each patient's severity and frailty, reaches a C-statistic of about 0.73 on these patients (`r30_truth.json`), and T13 fixes it between 0.70 and 0.74. R30 has cruder inputs and reaches about 0.68 in a large sample;
- with 217 events and 17 candidate parameters, overfitting adds about 0.03 to the apparent value, not 0.07, and shrinks the slope to about 0.88, not below 0.85.

`DESIGN.md` risk R2 named this at Milestone 0 and said a variance would be proposed if the gap could not be reached without contrivance. Reaching it would have meant inventing a mechanism for the purpose or changing the true model. Neither was done. `spec.VARIANCE_V6` sets T41 to 0.69 to 0.73 and T43 to 0.80 to 0.94. **Those ranges were chosen after the values were seen, so passing them shows nothing**; they only guard against a later change. `CHECKS.md` prints the brief's range beside each. Nick accepts V6 by applying the Milestone 4 overlay.

The other R30 targets hold as written: T40, T42, T44, T45 and T46.

**Set before any R30 result was looked at:** a likelihood-ratio test for the screen; 25 Newton steps; a missing laboratory value counting as not low; the reported C-statistic to three decimals; the reference fit on 2023 discharges at F01 to F05.

**The other Milestone 4 products.** The chart review's allocation across strata, the gamma shapes of the rapid-response minutes, and the number and wording of the laboratory log's entries were set once and not adjusted. The reviewer's accuracy and the mean minutes are the brief's.

**What the screen did.** It kept both noise predictors, each with a likelihood-ratio statistic just above the critical value of 1.64 (1.81 and 1.73), and dropped four terms that have clear effects in the reference fit. Nothing was arranged to produce this. It is what a screen at p < 0.20 does on a sample of this size, and it would differ in another draw of the world.

**Hospital effects.** The six readmission effects were first drawn as plain normal values with standard deviation 0.15. The draw came out unusually spread: -0.318, 0.323, 0.330, -0.022, -0.029, 0.031, a standard deviation of 0.22. The design says about 0.15. After seeing this I changed the rule: the six draws are now centred and scaled so that their standard deviation is exactly 0.15. The same rule applies to the deterioration effects. The values in use are in `hidden/inpatient/facility_truth.csv`. This choice was made after seeing the draw, and it is recorded here for that reason.

### Milestone 5

**No file from Milestones 2 to 4 changed.** The scribe has its own blocks and reads nothing from the hospitals. `common.py` gained `poisson_from_uniform`, and `det_poisson` now calls it; the arithmetic is the same and the helper hashes in the tests did not move.

**No number in `spec.SCRIBE` was changed after the first run.** Every value was written before any scribe file existed, and the first run met every target except one. The values that are not the brief's own are design choices: visit volumes, baseline documentation and after-hours minutes, how adoption ramps up, the survey's item model, visit lengths, speakers, words, editing minutes, the rate of wrong values (0.05), how many errors a note has, the chance that an error is moderate, the audit's allocation, and how a rater assigns severity.

**Variance V7: one target was not met, and its range was replaced.** The brief asks for a Cohen's kappa of 0.55 to 0.75 between the first and second raters on the hallucination flag (T57). The world gives 0.509. This is arithmetic, not bad luck:

- the brief also fixes the raters: sensitivity 0.70 to 0.92, one lenient rater near 0.60, false-positive rate 0.01 to 0.05;
- a hallucination is present in about 9% of audited notes;
- with those figures the expected kappa is 0.518 (`CHECKS.md` prints it from the hidden rater parameters). A rare flag, read by raters who each miss one error in five, cannot reach 0.55 on average.

One change was tried and withdrawn: drawing the false-positive rates skewed towards 0.01. Kappa rose to 0.534, still short, and the skew had no reason behind it except the target. The raters are as the brief wrote them. `spec.VARIANCE_V7` sets T57 to 0.45 to 0.65. **That range was chosen after the value was seen, so passing it shows nothing.** `CHECKS.md` prints the brief's range beside it. Decision A41 in `DESIGN.md` records the variance for Nick's approval.

**How four targets are measured**, each fixed before its value was looked at except where said:

- T71: a clinician counts if the scribe was used on at least half of their visits over live weeks 8 to 11 together. Every wave has those weeks.
- T73: the mean of the true saving over scribe visits from the clinic's eighth live week (variance V3). It is 1.87, below the design's 2.0, because clinicians with more scribe visits happen to have smaller savings; the mean of the 130 clinicians' own values is 1.97.
- T75: the brief's "about 20%" and "about 0.4 visits" are effects at full use, and scale with the share of visits that use the scribe. The check divides the paired difference by the use. An adopter at steady state, with the scribe on three visits in four, sees about 15% fewer after-hours minutes. This reading was chosen while writing the generator, before any output.
- T58: within 2 points, as the brief says. The realised gap is 1.5 points, of which 0.6 is the draw of the sample and 0.9 is rating error. `DESIGN.md` section 9.4 warned that this target could miss in one realisation; it did not.

**Dealt by rank, so exact:** 13 never-adopters and 18 partial users of 130, and 130 clinicians in all. These are counts fixed in the spec, not draws that happened to land.

### Milestone 7, the freeze

**Nothing was adjusted.** The freeze changed no number in `spec.py` except the version and the freeze date, no line of any generator module, and no file under `data/` or `hidden/`: the 51 files have the hashes they had at `71f1d0f`. `CHECKS.md` changed in its version line and in the wording of its last section, which lists the hospice targets as not in this release; no value in it changed. `MANIFEST.json` changed in its version, its freeze date, its note and its list of documents, which now includes `BOOK_MAP.md`.

**Both variances that changed a target after its value was seen are approved.** Nick approved V6 (T41 and T43, the readmission model) and V7 (T57, kappa between raters) in writing on 13 November 2026. The approval does not change what they are: ranges set after the fact, which test nothing. `CHECKS.md` goes on printing the brief's range beside each.

**What had been run before the data were committed.** Milestones 2 to 5 each regenerated byte for byte in three places: Claude's workspace, Nick's WSL machine and a GitHub runner. At Milestone 5 the cross-check's 104 statistics agreed between Python and R on Nick's machine (R 4.1.2) and on a GitHub runner, with the R30 coefficients refitted in both languages to within 1e-6 of the model card.

## 5. Planted mechanisms: source or design choice

Sizes are in `DESIGN.md` section 6. "Design choice" means the size was chosen by the author and rests on no source.

| ID | Mechanism | Built | Basis |
| --- | --- | --- | --- |
| P1 | Recorded SpO2 reads high for patients recorded as Black | Milestone 3 | The direction rests on Sjoding et al. (section 6). The sizes of 1.2 and 2.5 points are design choices |
| P2 | Respiratory rate charted as the default of 18 at the two northern hospitals | Milestone 3 | Design choice |
| P3 | Lactate drawn in about 40% of admissions, more often when sicker; the vendor takes a missing value as normal | Milestones 2 and 3 | Design choice |
| P4 | Central-laboratory lactate reads 0.4 mmol/L high from March 2024 | Milestone 3. The laboratory's change log arrives in Milestone 4 | Design choice |
| P5 | The score counts network encounters only | Milestone 3 | The idea of a proxy that under-counts need rests on Obermeyer et al. (section 6). Every size is a design choice |
| P6 | The vendor's baseline comes from a population with more events | Milestone 3 | Design choice |
| P7 | Fewer alerts answered as months pass | Milestone 3 | Design choice |
| P8 | An evaluation multiplies the risk by 0.80 | Milestone 3 | Design choice. No published effect of this size is claimed |
| P9 | The EHR flag misses some events, flags a few non-events, and arrives late | Milestone 3 | Design choice |
| P10 | Winter: admissions about 12% above the yearly mean, deterioration risk about 10% higher | Milestones 2 and 3 | Design choice |
| P11 | Sallowfield joins in October 2024: older patients, about 60% Medicare, more events, no silent period | Milestones 2 and 3 | Design choice |
| P12 | Version 3.0 of the score from February 2026 | Milestone 3 | Design choice |
| P13 | 12 to 18% of true readmissions go outside the network, more in the north | Milestone 2 | Design choice. The idea that a record misses care elsewhere is general knowledge |
| P16 | Planned returns, flagged and not counted as readmissions | Milestone 2 | Design choice |
| P18 | Hospital effect and person frailty, both unmeasured | Milestone 2 | Design choice |
| P14 | R30's development sample: one hospital, one service, complete laboratory panel, first discharge only | Milestone 4 | Design choice |
| P15 | R30's method: values cut in two, a screen at p < 0.20, 17 candidate parameters, two noise predictors | Milestone 4 | Design choice. The sample-size method it is judged by is Riley et al. (section 6) |
| P17 | R30 shown on the discharge worklist, with a true effect of zero | Milestone 4 | Design choice |
| P19 | Note errors rise with an interpreter (odds ratio 1.8), a visit over 30 minutes (1.5) and three or more speakers (1.6); version 2.4 lowers hallucination odds by 30%; clinics differ (logit SD 0.25) | Milestone 5 | The rates under version 2.3 sit near Taylor et al. (section 6). That interpreter visits are harder rests on the research letter in section 6. Every odds ratio is a design choice |
| P20 | Raters miss errors and raise false alarms; one is lenient; the senior reviewer is better but not perfect | Milestone 5 | Design choice |
| P21 | The audit oversamples interpreter visits | Milestone 5 | Design choice |
| P22 | Stepped rollout, a secular trend of -0.02 minutes a visit each week, a learning curve, holiday weeks | Milestone 5 | Design choice |
| P23 | Heavier documenters adopt the scribe more | Milestone 5 | Design choice |
| P24 | Clinicians with lower wellbeing answer the survey less often | Milestone 5 | Design choice |

## 6. Plausibility sources

Checked by web search on the date shown. Figures are quoted from the search results I saw, not from the full documents.

| Used for | Source | Figure | Checked |
| --- | --- | --- | --- |
| Race and ethnicity categories | US Office of Management and Budget, 2024 Statistical Policy Directive No. 15, https://spd15revision.gov/content/spd15revision/en/2024-spd15.html | Seven minimum categories: American Indian or Alaska Native, Asian, Black or African American, Hispanic or Latino, Middle Eastern or North African, Native Hawaiian or Pacific Islander, White. The page was last revised on 7 April 2026. The repository's seven named codes match; `multiple` and `unknown` are additions. Shares are design choices | 12 November 2026 |
| In-hospital death, about 2% | AHRQ HCUP Statistical Brief 300 (December 2022), https://hcup-us.ahrq.gov/reports/statbriefs/sb300-COVID-19-AllHospital.jsp | All-cause in-hospital mortality of 2.1% in December 2019, in 38 States and DC, before it rose during the pandemic | 12 November 2026 |
| Length of stay | AHRQ HCUP Statistical Brief 180, https://hcup-us.ahrq.gov/reports/statbriefs/sb180-Hospitalizations-United-States-2012.pdf | Mean of 4.5 days for all stays in 2012; 4.8 days (female) and 5.0 days (male) outside maternal and neonatal stays. I found no published median, so the target median of 3.8 days stays a design choice; the world's mean is 5.2 days | 12 November 2026 |
| Readmission rate and its pattern by payer | AHRQ HCUP Statistical Brief 304 (September 2023), https://hcup-us.ahrq.gov/reports/statbriefs/sb304-readmissions-2016-2020.jsp | 13.9 per 100 index admissions, 2016 to 2020; Medicare 17.0, Medicaid 13.6, self-pay 11.9, private 8.5 in 2020 | 10 November 2026 |

| P1, pulse oximeter bias | Sjoding MW, Dickson RP, Iwashyna TJ, et al. Racial bias in pulse oximetry measurement. N Engl J Med 2020;383(25):2477-2478. doi:10.1056/NEJMc2029240 | Occult hypoxemia in 11.7% of measurements from Black patients against 3.6% from White patients. This world does not reproduce those rates: its ward patients rarely have a true SpO2 below 90 | 10 November 2026 |
| P5, a proxy that under-counts need | Obermeyer Z, Powers B, Vogeli C, Mullainathan S. Dissecting racial bias in an algorithm used to manage the health of populations. Science 2019;366(6464):447-453. doi:10.1126/science.aax2342 | Bias arose from predicting cost as a proxy for need. Motivation only | 10 November 2026 |
| A proprietary score on local data | Singh K, Valley TS, Tang S, et al. Evaluating a widely implemented proprietary deterioration index model among hospitalized patients with COVID-19. Ann Am Thorac Soc 2021;18(7):1129-1137. doi:10.1513/AnnalsATS.202006-698OC | 392 hospitalisations at one academic centre; area under the curve 0.79 (95% CI 0.74 to 0.84), as given in the abstract of the study's preprint; the journal abstract reports good discrimination and low sensitivity as an early warning | 12 November 2026 |
| A vendor's claim against local performance | Wong A, Otles E, Donnelly JP, et al. External validation of a widely implemented proprietary sepsis prediction model in hospitalized patients. JAMA Intern Med 2021;181(8). doi:10.1001/jamainternmed.2021.2626 | 38,455 hospitalisations; area under the curve 0.63 (95% CI 0.62 to 0.64) against 0.76 to 0.83 reported by the developer; alerts on 18% of hospitalisations while 67% of sepsis cases were not identified | 12 November 2026 |

| Minimum sample size for developing a model (T45) | Riley RD, Ensor J, Snell KIE, et al. Calculating the sample size required for developing a clinical prediction model. BMJ 2020;368:m441. doi:10.1136/bmj.m441 | The three criteria `checks.py` applies: shrinkage of at least 0.9, a small difference between apparent and adjusted R-squared, and a precise overall risk | 10 November 2026 |
| R-squared from a reported C-statistic (T45) | Riley RD, Van Calster B, Collins GS. A note on estimating the Cox-Snell R2 from a reported C statistic (AUROC) to inform sample size calculations for developing a prediction model with a binary outcome. Stat Med 2021;40(4):859-864. doi:10.1002/sim.8806 | The authors simulate a large sample with a normal linear predictor in events and non-events. `checks.py` computes the same large-sample value by numerical integration, so that `CHECKS.md` is the same on every machine | 12 November 2026 |

| Note errors under version 2.3 (T51 to T54) | Taylor SL, Jost M, MacDonald S, et al. Quality of clinical notes created by ambient listening generative AI. JMIR Med Inform 2026;14:e86474. doi:10.2196/86474 | 356 of 7,545 notes reviewed; omissions 18%, hallucinations 11.5%, accidental inclusions 9.3%; 94.7% free of significant errors | 10 November 2026 |
| Interpreter visits are harder (P19) | Research letter, JMIR Med Inform 2026;14:e88734. doi:10.2196/88734 | AI scribes carried interpreter errors into notes in simulated encounters. Motivation only; the odds ratio of 1.8 is a design choice | 10 November 2026 |
| Time saved (T73) | Prospective study, JMIR Med Inform 2026;14:e84104. doi:10.2196/84104 | 79 clinicians, more than 25,600 notes, about 13.6 fewer minutes a day on notes. The brief's 2.0 minutes per scribe visit is a design choice at the generous end | 10 November 2026 |
| Wages of nurses, physicians and physician assistants (`wage_rates.csv`) | US Bureau of Labor Statistics, Occupational Employment and Wage Statistics, May 2025, as reported in Becker's Hospital Review, "38 hospital jobs ranked by pay", https://www.beckershospitalreview.com/hr/38-hospital-jobs-ranked-by-pay-2/ . The registered nurses' figure is also in the Bureau's own release, https://www.bls.gov/news.release/archives/ocwage_05152026.htm | National mean annual wages: registered nurses 101,420; physician assistants 141,280; family medicine physicians 255,820; general internal medicine physicians 267,200 | 12 November 2026 |
| Wages of nurse practitioners and managers | The same survey, as reported in Becker's Hospital Review, "41 hospital jobs ranked by pay", https://www.beckershospitalreview.com/hr/37-hospital-jobs-ranked-by-pay-2// | National mean annual wages: nurse practitioners 137,300; medical and health services managers 140,970 | 12 November 2026 |
| Wage of an IT analyst | US Bureau of Labor Statistics, Occupational Outlook Handbook, computer systems analysts, https://www.bls.gov/ooh/computer-and-information-technology/computer-systems-analysts.htm | Median annual wage 105,850 in May 2025. A median, because I did not see the mean for that year | 12 November 2026 |
| Loading for benefits, 1.46 | US Bureau of Labor Statistics, Employer Costs for Employee Compensation, March 2026, https://www.bls.gov/opub/ted/2026/compensation-costs-for-civilian-workers-averaged-49-32-per-hour-worked-in-march-2026.htm | Civilian workers: total compensation 49.32 US dollars an hour, of which wages and salaries 33.72; the ratio is 1.46. Applying the all-worker ratio to every role is a design choice | 12 November 2026 |
| The scribe's licence price | Becker's Hospital Review, "Ambient AI scales across health systems as burnout data emerges", https://www.beckershospitalreview.com/healthcare-information-technology/ai/ambient-ai-scales-across-health-systems-as-burnout-data-emerges/ ; Medical Economics, "Take note: The AI scribe era is here", 30 March 2026, https://www.medicaleconomics.com/view/take-note-the-ai-scribe-era-is-here | The first reports a range of about 100 to 600 US dollars per provider per month, citing a health technology institute's report; the second says prices run from free to several hundred dollars per clinician per month. The world's 275 is invented and sits inside that range | 12 November 2026 |

Hourly wages in `wage_rates.csv` are the annual figures divided by 2,080 hours. They are national figures for real occupations, used as they stand; the world's own prices and hours are invented.

`CHECKS.md` prints the world's values beside these figures. The two studies of proprietary scores concern real products, which this world does not model and this repository does not name. They are cited for one point only: a local C-statistic below a vendor's claim is ordinary. The world's 0.77 against a claimed 0.84 is a design choice inside that pattern. The other sources gathered at Milestone 0 are in `DESIGN.md` section 13 and will be copied here as their modules are built.

**Not checked, so design choices:** the payer mix, the diagnosis-group mix, the disposition mix, the share of admissions in intensive care or on comfort care at 12 hours, the share with lactate drawn, the size of every effect in `spec.INPATIENT`, and death after discharge. For Milestone 4: the time a rapid-response evaluation takes, the reviewer's accuracy, and everything in the laboratory change log. For Milestone 3: the distribution of every vital sign, the rate of deterioration (about 4% of ward stays in 48 hours), the share of alerts answered, the effect of an evaluation, the accuracy of the EHR flag, and every claim in the vendor's model card.

**Not checked for Milestone 5, so design choices:** visits per clinician-week, documentation and after-hours minutes, the shares of adopters, the survey's response rate, the share of visits with an interpreter, visit lengths, every rater's accuracy, the hours in each cost line, the implementation fee, and the effects on after-hours time, visits and wellbeing. Nothing remains to be checked before the freeze.

## 7. What this world cannot show

- Effect sizes are design choices. They are not estimates of anything.
- Real data hold problems that nobody planted. This world holds only the ones listed in `DESIGN.md` section 6, plus the simplifications in `WORLD_SPEC.md` section 8.
- A method that recovers the known answer here has been shown to work on this structure. That is evidence about the method's code and logic. It is not evidence about any real hospital, product or patient group.

## 8. Versions, seed, blocks and commands

**Version.** `tonmick-health` 1.0.0, frozen on 13 November 2026. `MANIFEST.json` records the same.

**Software.** Python 3.13, NumPy 2.5.3 and pandas 3.0.5 for the generator, the checks and the tests. The cross-check also ran on base R: 4.1.2 on the author's machine, and the current release on GitHub.

**Seed.** The root seed is `20261110`. Each block has its own stream: `np.random.Generator(np.random.PCG64(np.random.SeedSequence(20261110, spawn_key=(block_id,))))`.

**Block IDs in use.** They are never renumbered, and a retired ID is never reused.

| IDs | Blocks |
| --- | --- |
| 1 to 3 | `network`, `persons`, `calibration` |
| 10 to 25 | `arrivals`, `admission_attributes`, `comorbidity`, `labs_true`, `labs_recorded`, `vitals_true`, `vitals_recorded`, `index_eligibility`, `alert_response`, `deterioration`, `ehr_outcome`, `los_disposition`, `inpatient_death`, `readmission`, `outside_care`, `planned_readmission` |
| 26 to 28 | `chart_review`, `rrt_log`, `lab_change_log` |
| 30 to 36 | `clinics_clinicians`, `rollout_draw`, `notes_frame`, `note_errors`, `audit_sample`, `rater_parameters`, `ratings` |
| 40 to 44 | `clinician_traits`, `adoption`, `clinician_weeks`, `survey`, `costs` (reserved; draws nothing) |
| 90 | `dummy`, drawn only by the append-only test |
| 99 | `platform_probe`, drawn only by the tests |

**Reserved IDs.** 50 to 54 for hospice (`hospice_patients`, `hospice_trajectories`, `hospice_events`, `hospice_visits`, `hospice_predictions`); 101 `omop_export`; 102 `literature_layer`; 103 `claims_layer`; 104 `second_vendor_tool`. IDs from 201 are for derived releases.

**Solved values.** Section 3, with `hidden/calibrated_intercepts.json`, `hidden/scribe/error_model_truth.json` and `hidden/economics/effects_truth.json`.

**The exact commands** that produced and checked the frozen files, run from the repository root inside the pinned environment:

```bash
python3 generator/generate_world.py .          # data/ and hidden/
python3 generator/dictionary.py DICTIONARY.csv
python3 generator/checks.py .                  # CHECKS.md; exits 1 if a check fails
python3 generator/make_manifest.py .           # MANIFEST.json and SHA256SUMS
sha256sum -c --quiet SHA256SUMS                # the files on disk are the listed ones
python3 generator/verify_world.py              # regenerate in a temporary folder and compare
python3 -m unittest discover -s tests -v
python3 checks/crosscheck.py . build/crosscheck_python.csv
Rscript checks/crosscheck.R . build/crosscheck_r.csv
python3 checks/compare_crosscheck.py build/crosscheck_python.csv build/crosscheck_r.csv
```

**Never evidence.** `hidden/` is what the simulator did. It is used only to check a method against a known answer. A matching hash confirms file identity only, and nothing in this repository is a finding about any real hospital, product, patient or clinician.
