# Checks

World `tonmick-health`, version `1.0.0`, root seed `20261110`. Milestones built: M2, M3, M4, M5.

Written by `generator/checks.py`. Do not edit by hand. Everything here is fictional, and values read from `hidden/` are simulator truth, never evidence.

Each check names its basis: **realised** (computed from the generated files, as an analyst would), **expected** (computed from hidden probabilities) or **construction** (true by design). Target ranges were committed in `generator/spec.py` before the generator was written, except the rows marked T..b to T..e, whose ranges were added with the generator (see `spec.SECONDARY_TARGETS`). The parameters adjusted after seeing output are listed in `PROVENANCE.md` section 4.

**129 checks, 0 failed.**

## Structure

| Check | Value | Target | Result |
| --- | --- | --- | --- |
| S01 construction: files under data/ and hidden/ are exactly those the spec lists for the built milestones | 51 files; 0 missing, 0 unexpected | 51 files; 0 missing, 0 unexpected | pass |
| S02 construction: every CSV header equals the spec's column list | 43 of 43 files | 43 of 43 files | pass |
| S03 construction: every cell has its declared type, fixed decimals and code list; empty only where the dictionary allows | 0 bad cells of 14,298,010 | 0 bad cells | pass |
| S04 construction: the dictionary has one row for every file and column | 482 rows for 482 columns; DICTIONARY.csv identical to the spec | 482 rows; identical if present | pass |
| S05 construction: IDs are unique; persons.csv holds exactly the people with a published admission; each truth row matches its admission | 178,240 admissions (147,837 published), 99,322 persons, 114,257 persons in truth | all keys consistent | pass |
| S06 construction: age is 18 to 105, birth year 1915 to 2008, and age agrees with birth year and admission year | age 18 to 100; birth year 1926 to 2008 | within range; admission year minus birth year minus age is 0 or 1 | pass |
| S07 construction: no person is admitted again before the day after a discharge, or while a stay is open | 0 overlapping stays | 0 | pass |
| S08 construction: prior_admits_12m equals a recount from the admission files, 2021 burn-in included | 0 of 147,837 published admissions differ | 0 differ | pass |
| S09 construction: for every eligible discharge with 30 days of follow-up, the readmission an analyst derives from data/ (first return within 30 days, not planned) equals the truth for network readmissions | 0 of 160,637 index discharges differ; planned returns: 0 differ; eligibility: 0 differ | 0 differ | pass |
| S10 construction: readmit_encounter_id names the same person's next admission, readmit_gap_days after the discharge; it is empty only for outside readmissions and returns after the data end | 19,354 links checked; 179 network readmissions fall after the data end | all links right | pass |
| S11 construction: outside_readmissions.csv lists exactly the true readmissions that went outside the network, up to the data end | 3,684 rows against 3,684 in the truth | equal, row for row | pass |
| S12 construction: every planned admission is elective, falls on a weekday and follows a discharge flagged planned_return 7 to 30 days earlier | 4,063 of 4,063 planned admissions | all | pass |
| S13 construction: a stay still open when the data end has an empty discharge date, length of stay and disposition | 462 open stays, the earliest admitted 2026-05-29 | blanks consistent | pass |
| S14 construction: a death in hospital is the person's last admission and its date and place are in persons_truth; nobody is admitted after dying | 3,447 deaths in hospital, 7,795 outside; 0 admissions after a death | consistent; 0 after a death | pass |
| S15 construction: sizes are inside the budget | data/ 40.6 MB, hidden/ 32.3 MB, largest file 7.9 MB (data/scribe/ai_notes_frame.csv) | data/ at most 70 MB, hidden/ at most 50 MB, any file at most 45 MB | pass |
| S16 construction: each solved intercept reproduces its target on the reference cohort | 6 intercepts; largest gap 5.6e-17 | 6 intercepts; gap below 1e-09 | pass |
| S17 construction: the six hospital effects have mean 0 and the design SD | readmission mean 0.0000, SD 0.1500; deterioration mean 0.0000, SD 0.1500 | mean 0.0000, SD 0.1500 | pass |
| S18 construction: the true readmission model has no term for sex, day of week or season, so those effects are zero | 0 unexpected terms | 0 | pass |
| S19 construction: the index encounters are exactly the published admissions on a ward at 12 hours (not in intensive care, not on comfort care, stay of at least half a day or still open) whose index time falls from the hospital's first scoring day to the data end; the index time is 12 hours after admission | 80,751 index encounters; 0 missing, 0 unexpected | 0 missing, 0 unexpected | pass |
| S20 construction: the outcome label arrives 5 days after the index date; label and date are empty exactly when that is after the data end | 80,410 labelled, 341 not yet labelled | consistent | pass |
| S21 construction: the version follows the date; the score is shown from the hospital's alert date; an alert fires exactly when the score is shown and at or above the threshold; an evaluation only follows an alert | 67,405 shown, 6,835 alerts, 5,126 evaluations | consistent | pass |
| S22 construction: lactate_at_index is the admission's recorded lactate, and network_encounters_12m is at least prior_admits_12m | 29,210 with a lactate on file | consistent | pass |
| S23 construction: p1 is 0.80 times p0; every y1 event is a y0 event; the realised outcome is y1 after an evaluation and y0 otherwise; the response probability follows the fading rule; the EHR flag is the truth except where ehr_flag_error says otherwise | 3,236 events with no evaluation, 2,630 with one, 3,051 realised; 240 missed, 296 false positives | consistent | pass |
| S24 construction: the oximeter bias is in recorded SpO2 only for patients recorded as Black; the score differs from its no-shift twin only where the central laboratory's new assay measured a lactate; a defaulted respiratory rate is recorded as 18 | 10,493 encounters with the bias (20 at the larger size); 17,469 scores moved by the assay; 4,867 defaulted rates | consistent | pass |
| S25 construction: nobody on a ward at 12 hours dies within 2.5 days of admission without a true deterioration; an event of type death ends the stay in death inside that window, and one of type transfer_out ends it in a transfer | 305 deaths inside the window, all with a true event; 308 transfers out | consistent | pass |
| S26 construction: the vendor's risk table has every score for both versions and rises with the score; the model card states the threshold and the claimed C-statistic; the hidden formula, applied to the published inputs, reproduces every published score | 202 table rows; 0 of 80,751 scores differ from the formula | 0 differ | pass |
| S27 construction: the development sample is exactly what the model card describes, rebuilt from data/: the university hospital's medicine discharges in the first half of 2022, alive to home, home health or skilled nursing, with all five laboratory tests on file, each patient's first such discharge; every column, and the outcome, equals its definition | 1,725 rows against 1,725 rebuilt (1,822 before keeping first discharges); 0 cells differ | same rows; 0 cells differ | pass |
| S28 construction: refitting the published sample by the card's method (a likelihood-ratio screen at p < 0.20, then one logistic fit) gives the card's coefficients to six decimals and its reported C-statistic; the hidden fit trace agrees | 12 of 17 candidate parameters kept (11 of 16 terms); reported C 0.708 | card and trace equal the refit | pass |
| S29 construction: r30_scores.csv holds every eligible discharge from 2023-01-01 at all six hospitals, dated on the discharge day, and each risk is reproduced from data/ and the model card | 108,050 scores against 108,050 eligible discharges; 0 differ | same rows; 0 differ | pass |
| S30 construction: the chart review is a sample of silent-mode encounters in ten strata cut at the deciles of the score, with the planned number drawn from each and inclusion probability = sampled / stratum size | 800 reviewed; cut points [9, 12, 14, 17, 21, 25, 31, 40, 56]; stratum sizes [1438, 1341, 870, 1237, 1317, 1075, 1224, 1194, 1149, 1185]; sampled [40, 40, 40, 40, 40, 60, 60, 80, 120, 280] | consistent | pass |
| S31 construction: rrt_log.csv has one row for each evaluation in index_encounters.csv, numbered in time order, beginning 0 to 3 hours after the index time | 5,126 rows for 5,126 evaluations | one each; times consistent | pass |
| S32 construction: the laboratory change log is in date order, each entry names the hospitals its laboratory serves, no entry predates a hospital joining, and the lactate method change is one entry among the routine ones, on its date, saying nothing of its effect | 89 entries, 4 of them method changes; lactate entry L0046 | consistent; one lactate entry | pass |
| S33 construction: change_points.csv carries the planted dates (alerts at each hospital, the assay change, the acquisition, version 3.0), and monthly_truth.csv equals a recount from the index files | 13 change points; 126 month-by-group cells over 36 months; recount agrees to the printed decimals: yes | dates right; recount agrees | pass |
| S34 construction: the 24 clinics are the spec's; clinician counts and specialties agree; each wave holds four primary care and two specialty clinics on its date | 24 clinics, 130 clinicians; waves of [2, 4] clinics by type | 24 clinics, 130 clinicians; 4 primary care and 2 specialty in each wave | pass |
| S35 construction: the panel has one row for every clinician and week; week dates, live flags, weeks since go-live, holiday weeks and scribe shares all follow from the rollout and the counts | 8,320 rows, 4,056 of them live, 324 with no visits; 0 rows out of line | 8,320 rows; 0 out of line | pass |
| S36 construction: note IDs run in date order; every visit falls on an open weekday of its week; clinic, specialty and scribe version follow from the clinician and the date; an interpreter makes at least three speakers | 102,502 notes; 0 out of line | 0 out of line | pass |
| S37 construction: the truth table has one row for every note in the frame; a note's worst severity is none exactly when it has no error; the 24 clinic effects have mean 0 and the design SD | 102,502 rows; clinic effects mean 0.0000, SD 0.2500 | 102,502 rows; mean 0.0000, SD 0.2500 | pass |
| S38 expected: the hidden error model, applied to the frame, gives the solved rates on version 2.3 notes, and its odds ratios are the planted ones | omission 0.170000; hallucination 0.105000; misattribution 0.085000; wrong_value 0.050000; a major error 0.015000 | omission 0.170000; hallucination 0.105000; misattribution 0.085000; wrong_value 0.050000; a major error 0.015000 | pass |
| S39 construction: each sampled note's stratum can be rebuilt from the frame; stratum sizes, the numbers drawn and the inclusion probabilities agree with the frame and with the spec's allocation | 1,200 notes in 12 strata; smallest stratum holds 414 notes | 1,200 notes in 12 strata | pass |
| S40 construction: every sampled note has two ratings from two different raters; the senior reviewer rates a note exactly when the two differ in any field; a rating's severity is none exactly when it has no flag | 1,200 first and 1,200 second ratings; 426 adjudicated | consistent | pass |
| S41 construction: every clinician has a baseline and a final survey row, and a post-wave row unless the clinic is in wave 4; items are filled exactly when the clinician responded | 355 rows, 216 responses | 355 rows | pass |
| S42 construction: each loaded cost is the wage times the loading; every clinician role and both rapid-response roles have a wage; each cost line has a price or a wage role, never both | 7 roles, 7 cost lines, loading 1.46 | consistent | pass |
| S43 construction: without the scribe a clinician-week never has more visits or fewer after-hours minutes; before go-live the two worlds are identical; the learning share, expected scribe share and saving follow from the hidden parameters; the documentation minutes differ by the saving times the scribe share | 0 rows out of line; 5 rows sit at the floor of 1.0 minute, where the saving is cut short | 0 out of line | pass |
| S44 construction: adoption types have the design's counts, and the clinicians with no scribe visit in the data are exactly the hidden never-adopters | 99 adopters, 18 partial, 13 never | 99 adopters, 18 partial, 13 never | pass |

## Inpatient

| Check | Value | Target | Result |
| --- | --- | --- | --- |
| T01 realised: published admissions, 2022-01-01 to 2026-06-30 | 147,837 | 140,000 to 160,000 | pass |
| T02 realised: median age | 64 | 62 to 66 | pass |
| T02b realised: age, lower quartile | 49 | 48 to 52 | pass |
| T02c realised: age, upper quartile | 77 | 74 to 78 | pass |
| T03 realised: female share | 0.5195 | 0.50 to 0.54 | pass |
| T04 realised: Medicare share overall | 0.4735 | 0.45 to 0.51 | pass |
| T04b realised: Medicaid share overall | 0.1839 | 0.16 to 0.20 | pass |
| T04c realised: commercial share overall | 0.2824 | 0.26 to 0.30 | pass |
| T04d realised: self-pay share overall | 0.0602 | 0.05 to 0.07 | pass |
| T04e realised: Medicare share at F06 | 0.5937 | 0.57 to 0.63 | pass |
| T05 realised: race and ethnicity unknown share | 0.0400 of persons | 0.03 to 0.05 | pass |
| T05b realised: interpreter needed share | 0.0599 of persons | 0.05 to 0.07 | pass |
| T06 realised: emergency admission share | 0.7579 | 0.72 to 0.78 | pass |
| T07 realised: December to February admissions relative to annual mean | 1.1195 (F01 to F05, 2022 to 2025) | 1.09 to 1.15 | pass |
| T08 realised: median length of stay, days | 3.8 | 3.5 to 4.1 | pass |
| T08b realised: in-hospital death share | 0.0192 | 0.017 to 0.023 | pass |
| T09 realised: lactate drawn share | 0.3976 | 0.37 to 0.43 | pass |
| T09b realised: lactate is drawn more often when sicker | in intensive care at 12 hours 0.597, others 0.363; top quarter of hidden severity 0.669, bottom quarter 0.160 | higher in the sicker group, both ways | pass |

## Readmission truth

| Check | Value | Target | Result |
| --- | --- | --- | --- |
| T10 realised: true 30-day readmission, any hospital, 2023 discharges | 0.1412 of 28,002 eligible discharges | 0.13 to 0.15 | pass |
| T10b realised: the mean hidden probability agrees with the realised rate, 2023 discharges | mean probability 0.1415, realised 0.1412 | within 0.01 | pass |
| T11 realised: observed network-only readmission, 2023 | 0.1191, derived from data/ alone | 0.11 to 0.13 | pass |
| T12 realised: share of true readmissions outside the network | 0.1570 for 2023 discharges; 0.1592 for all published years | 0.12 to 0.18 | pass |
| T13 realised: true-model C-statistic, hidden probabilities, 2023 to 2025 | 0.7229 on 91,089 eligible discharges | 0.70 to 0.74 | pass |

## Deterioration and the vendor's index

Silent mode means index encounters at F01 to F05 from 2023-07-01 to 2023-12-31, scored but not shown. The outcome is the EHR flag unless a row says otherwise. Vendor risk is read from `vendor_risk_table.csv`. O/E is observed events divided by the sum of vendor risks; on the expected basis the numerator is the sum of hidden probabilities that the flag is raised, and the realised value is shown beside it.

| Check | Value | Target | Result |
| --- | --- | --- | --- |
| T14 realised: index encounters, 2023-07-01 to 2026-06-30 | 80,751 | 76,000 to 84,000 | pass |
| T14b realised: share of published admissions on a ward at 12 hours | 0.8031 | 0.77 to 0.83 | pass |
| T15 realised: silent-mode EHR event rate | 0.0368 (443 flagged of 12,030); true rate 0.0368 | 0.036 to 0.044 | pass |
| T15b realised: silent-mode index encounters | 12,030 | 11,000 to 13,000 | pass |
| T15c expected: true risk, December to February relative to other months | 1.101 (mean hidden risk with no evaluation, F01 to F05, all index encounters) | 1.05 to 1.15 | pass |
| T16 realised: VDI v2 C-statistic, silent mode | 0.7716; against the true outcome 0.7989; the vendor claims 0.84 | 0.76 to 0.80 | pass |
| T17 realised: VDI v2 calibration slope, silent mode | 0.855 (intercept -0.494) | 0.80 to 0.92 | pass |
| T18 realised: VDI v2 overall O/E, silent mode | 0.909; expected basis 0.949 | 0.85 to 0.95 | pass |
| T19 expected: O/E, patients recorded as Black, silent mode | 1.215; realised 1.060 on 56 flagged of 1,530 | 1.15 to 1.35 | pass |
| T20 expected: O/E, F04 and F05, silent mode | 1.240; realised 0.902 on 21 flagged of 537 | 1.15 to 1.35 | pass |
| T21 expected: O/E, Medicaid and self-pay, silent mode | 1.253; realised 1.348 on 100 flagged of 3,195 | 1.15 to 1.35 | pass |
| T22 realised: alert rate at threshold 60, silent mode | 0.0868 (1,044 at or above 60) | 0.07 to 0.09 | pass |
| T23 realised: positive predictive value at threshold 60 | 0.180 | 0.15 to 0.22 | pass |
| T24 realised: sensitivity at threshold 60 | 0.424 | 0.35 to 0.50 | pass |
| T25 expected: alert-rate rise from the assay change, F01 to F03, April 2024 | 0.0307: 0.1226 with the shift, 0.0920 without, on the same 1,892 encounters; raw February 0.0975, raw April 0.1226 | 0.02 to 0.04 | pass |
| T26 expected: true event-rate change from the assay change, absolute | 0.00032 lower, from 58 extra alerts; realised 0.00106; mean hidden risk with no evaluation: February 0.0410, April 0.0380 | 0.000 to 0.003 | pass |
| T27 realised: F06 event rate | 0.0556 (381 flagged of 6,857 labelled encounters) | 0.050 to 0.060 | pass |
| T27b realised: O/E at F06 under version 2.0 | 1.178 (277 flagged of 5,001) | 1.10 to 1.35 | pass |
| T28 realised: risk ratio of response, hidden potential outcomes | 0.8127 (2,630 events with an evaluation for everyone, 3,236 with none) | 0.78 to 0.82 | pass |
| T29 realised: EHR outcome flag sensitivity overall | 0.9211 on 3,040 true events | 0.90 to 0.94 | pass |
| T29b expected: EHR outcome flag sensitivity at F04 and F05 | 0.848 from the types of the 179 true events; realised 0.854 | 0.82 to 0.88 | pass |
| T29c realised: EHR outcome flag false-positive rate | 0.00383 | 0.003 to 0.005 | pass |
| T30 realised: default respiratory rate share at F04 and F05 | 0.413 of recorded values are 18 at F04 and F05, 0.178 elsewhere; the hidden default flag: 0.315 and 0.049 | 0.36 to 0.44 | pass |
| T31 realised: response to alerts at go-live | 0.8361 of 781 alerts in each hospital's first 91 days live | 0.82 to 0.88 | pass |
| T31b realised: response to alerts, F01 to F03, October to December 2025 | 0.7151 of 674 alerts | 0.66 to 0.74 | pass |
| T32 realised: VDI v3.0 alert rate | 0.0528 of 12,128 encounters; version 2.0 in the twelve months before: 0.1120 | 0.05 to 0.06 | pass |
| T32b realised: VDI v3.0 calibration slope | 1.040 on 11,787 labelled encounters | 0.90 to 1.10 | pass |
| T32c realised: VDI v3.0 calibration-in-the-large | -0.055; O/E 0.953 | -0.10 to 0.10 | pass |

## Chart review and rapid-response log

| Check | Value | Target | Result |
| --- | --- | --- | --- |
| T33 construction: chart review sample size | 800; the reviewer found 57 of 57 true events and called 0 of 743 non-events an event; design-weighted event rate 0.0296 against a true 0.0368 and an EHR-flag rate of 0.0368; design-weighted sensitivity of the flag 0.949; unweighted event rate in the sample 0.0712 | 800 to 800 | pass |
| T34 realised: mean rapid-response nurse minutes | 30.1 over 5,126 evaluations | 27.0 to 33.0 | pass |
| T34b realised: mean rapid-response physician minutes | 10.0 | 8.0 to 12.0 | pass |

## Readmission model R30

The observed outcome is the one an analyst derives from `data/`: the first return to a network hospital within 30 days, when it was not planned. Validation uses `r30_scores.csv` for 2023 discharges at F01 to F05. T41 and T43 are judged against variance V6, whose ranges were set after the values were seen (`DESIGN.md` decision A31); the brief's range is printed beside each.

| Check | Value | Target | Result |
| --- | --- | --- | --- |
| T40 realised: development discharges | 1,725 | 1,500 to 1,900 | pass |
| T40b realised: observed readmissions in the development sample | 217 (0.1258) | 170 to 230 | pass |
| T41 realised: apparent C-statistic | 0.7080, reported on the card as 0.708; terms kept by the screen: age_65_plus, los_over_5, prior_admits, comorbidity_count, disp_snf, disp_home_health, sodium_low, hemoglobin_low, dx_heart_failure, weekend_discharge, winter_discharge; dropped: female, medicaid, dx_cancer, dx_copd, emergency | 0.69 to 0.73 (variance V6; the brief's range was 0.73 to 0.77) | pass |
| T42 realised: validation C-statistic, 2023 discharges, F01 to F05 | 0.6788 on 28,002 discharges with 3,334 observed readmissions; against the true outcome 0.6798 | 0.66 to 0.70 | pass |
| T43 realised: calibration slope at validation | 0.882 (intercept -0.134); overall O/E 1.082; O/E by hospital: F01 0.90, F02 1.37, F03 1.34, F04 0.77, F05 0.80 | 0.80 to 0.94 (variance V6; the brief's range was 0.70 to 0.85) | pass |
| T44 expected: O/E at F04 and F05, observed outcome | 0.817; realised 0.787 on 84 observed readmissions of 935; against readmission to any hospital the expected O/E is 1.280 | 0.75 to 0.90 | pass |
| T45 realised: development n below the Riley minimum (anticipated C 0.70) | n 1,725 against a minimum of 2,604 at an anticipated C of 0.70, the value fixed before any data existed; 2,124 at an anticipated C of 0.72; 1,836 at 15% of the maximum R-squared; 2,395 at the model's own apparent C of 0.708; 1,607 at an anticipated C of 0.75 (17 candidate parameters, outcome rate 0.1258) | n below 2,604 | pass |
| T46 construction: noise predictors have true effect zero | the true model has no term for either; weekend_discharge: kept by the screen with coefficient 0.260, +0.091 (standard error 0.039) in the reference fit; winter_discharge: kept by the screen with coefficient -0.254, +0.016 (standard error 0.040) in the reference fit; the reference fit is R30's form on 28,002 discharges, where a small coefficient is confounding, not an effect | no such term in the true model | pass |

## Scribe audit

The frame, the true errors, the committee's sample and the ratings. T57 is judged against variance V7, whose range was set after the value was seen (`DESIGN.md` decision A41); the brief's range is printed beside it. Rates under version 2.3 are over the 41,988 notes drafted before 2025-11-03.

| Check | Value | Target | Result |
| --- | --- | --- | --- |
| T50 realised: AI-drafted notes in the frame | 102,502 (41,988 under version 2.3, 60,514 under version 2.4) | 90,000 to 120,000 | pass |
| T51 realised: notes with an omission, v2.3 | 0.1711 | 0.15 to 0.19 | pass |
| T52 realised: notes with a hallucination, v2.3 | 0.1049; under version 2.4 0.0793 | 0.09 to 0.12 | pass |
| T53 realised: notes with a misattribution, v2.3 | 0.0880 | 0.07 to 0.10 | pass |
| T54 realised: notes with a major error | 0.0138 under version 2.3; 0.0141 of all notes; any error 0.3481 of all notes | 0.010 to 0.020 | pass |
| T55 realised: omission rate ratio, interpreter visits to others | 1.619 (0.2713 against 0.1676; 7,321 interpreter visits, 0.0714 of notes) | 1.5 to 2.2 | pass |
| T55b realised: crude odds ratios in the whole frame sit near the planted ones (they are not adjusted for clinic or for each other) | omission with an interpreter 1.85; omission in a visit over 30 minutes 1.54; misattribution with three or more speakers 1.56; hallucination under version 2.4 0.73 | within 15% of 1.8, 1.5, 1.6 and 0.7 | pass |
| T56 construction: audit sample size | 1,200 notes; 2,400 independent ratings; 426 notes adjudicated (0.355) | 1,200 to 1,200 | pass |
| T57 realised: Cohen's kappa, hallucination, first against second rater | 0.509 on 1,200 notes, 107 of which truly have a hallucination; expected from the hidden rater parameters 0.518; other flags: omission 0.606, misattribution 0.519, wrong_value 0.441 | 0.45 to 0.65 (variance V7; the brief's range was 0.55 to 0.75) | pass |
| T58 realised: design-weighted omission prevalence minus truth, absolute | 0.0153: estimate 0.1597 against a true 0.1750 in the frame. Of the gap, -0.0064 is the draw of the sample (true labels, same weights: 0.1686) and -0.0089 is rating error. Unweighted rate in the sample: 0.1925 | 0.00 to 0.02 | pass |
| T59 construction: notes per clinician-week equal scribe visits in the panel | 0 of 8,320 clinician-weeks differ; 0 notes outside the panel | 0 differ; 0 outside | pass |
| T60 construction: rater parameters within the planted ranges | seven raters 0.7043 to 0.9183; the lenient rater (R05) 0.5743 to 0.5939; false-positive rates 0.0122 to 0.0432; senior reviewer 0.9592 to 0.9693 and 0.0053 | sensitivity 0.7 to 0.92, one lenient rater near 0.60; false-positive rate 0.01 to 0.05; senior 0.95 to 0.98 and at most 0.01 | pass |

## Scribe value

The clinician-week panel, adoption, the survey and the true effects. Where a row compares the world with the scribe to the world without it, both come from the same random draws (`hidden/economics/clinician_weeks_truth.csv`). Steady state means the clinic's eighth live week onward.

| Check | Value | Target | Result |
| --- | --- | --- | --- |
| T70 realised: clinicians in the panel | 130 clinicians, 8,320 clinician-weeks, mean 42.7 visits a week | 120 to 140 | pass |
| T71 realised: clinicians in live clinics on at least half their visits by week 8 | 0.7462 (97 of 130), by the share of visits in live weeks 8 to 11 | 0.70 to 0.80 | pass |
| T72 realised: never adopt | 0.1000 (13 of 130 have no scribe visit in the data) | 0.07 to 0.13 | pass |
| T73 realised: true mean saving per scribe visit at steady state, minutes | 1.874 over 84,249 scribe visits; 1.761 over all 102,502 scribe visits, learning weeks included; mean of the 130 clinicians' own values 1.968 | 1.8 to 2.2 | pass |
| T74 realised: naive pre-post estimate minus true saving, minutes | 1.077: naive 2.951 against a true 1.874. Mean minutes per visit fell from 7.17 before go-live to 5.29 at steady state, with the scribe on 0.638 of visits | at least 0.3 | pass |
| T74b realised: comparing users with non-users understates the saving, because users documented more slowly to begin with (P23) | at steady state never-adopters average 4.45 minutes per visit and adopters 5.38, a difference of -0.93; the scribe truly cut the adopters' average by 1.42 (scribe on 0.755 of their visits). True baselines: adopters 7.92, never-adopters 5.41 | difference below the true cut | pass |
| T75 realised: after-hours minutes, relative change | -0.2001 for each unit of use (share of visits with the scribe, times the learning share); adopters at steady state: -0.1488 of their after-hours minutes | -0.24 to -0.16 | pass |
| T75b realised: visits per clinician-week added at full use | 0.371 for each unit of use; 837 visits added in all | 0.3 to 0.5 | pass |
| T76 realised: survey response rate | 0.6085 (216 of 355); 0.486 in the lower half of true wellbeing and 0.730 in the upper half; respondents' mean true wellbeing +0.398 against +0.171 for everyone asked; mean item score 3.35 | 0.55 to 0.70 | pass |
| T76b realised: clinicians with lower true wellbeing respond less often (P24) | 0.486 against 0.730 | lower half below upper half | pass |
| T77 realised: true effect on latent wellbeing among adopters, SD units | 0.2432 among 99 adopters; partial users 0.0866; never-adopters 0 | 0.20 to 0.30 | pass |

## Benchmarks

No pass or fail. These rows set the world's headline rates beside published United States figures, so a reader can judge plausibility. Sources and dates are in `PROVENANCE.md`. The published studies of proprietary scores concern real products that this world does not model; they show only that a local C-statistic below a vendor's claim is ordinary.

| Quantity | Tonmick value | Published figure | Source |
| --- | --- | --- | --- |
| True 30-day readmission, 2023 discharges | 14.1 per 100 eligible discharges | 13.9 per 100 index admissions, 2016 to 2020 | AHRQ HCUP Statistical Brief 304 |
| True 30-day readmission by payer, 2023: Medicare, Medicaid, self-pay, commercial | 17.3, 14.1, 11.8, 9.7 per 100 | 17.0, 13.6, 11.9 and 8.5 per 100 in 2020 | AHRQ HCUP Statistical Brief 304 |
| In-hospital death share | 1.9% of published admissions | 2.1% of stays in December 2019, all causes | AHRQ HCUP Statistical Brief 300 |
| Mean length of stay, days | 5.3 (median 3.8) | 4.5 days for all stays in 2012; 4.8 (female) and 5.0 (male) outside maternal and neonatal stays | AHRQ HCUP Statistical Brief 180 |
| Vendor's score on local data: C-statistic in silent mode, against the vendor's claim | 0.77 locally; the vendor claims 0.84 | 0.79 (95% CI 0.74 to 0.84) on local validation of a widely implemented proprietary deterioration index, 392 hospitalisations | Singh et al., Ann Am Thorac Soc 2021 |
| Gap between the vendor's claimed C-statistic and the local one | 0.07 lower locally | 0.63 (95% CI 0.62 to 0.64) locally against 0.76 to 0.83 reported by the developer, for a widely implemented proprietary sepsis model | Wong et al., JAMA Intern Med 2021 |
| Alerts at the threshold: share of encounters flagged, and share of events missed | 8.7% flagged in silent mode; 58% of events had a score below the threshold | alerts on 18% of hospitalisations while 67% of sepsis cases were not identified, same sepsis model | Wong et al., JAMA Intern Med 2021 |
| AI-drafted notes with an omission, with a hallucination, and free of a major error | omission 17.1%, hallucination 10.5% of version 2.3 notes; no major error in 98.6% of all notes | 356 of 7,545 notes reviewed: omissions in 18%, hallucinations in 11.5%; 94.7% free of significant errors | Taylor et al., JMIR Med Inform 2026 |
| Documentation time saved by an ambient scribe | 12.5 minutes a clinic day for an adopter at steady state (1.87 minutes on each of 6.7 scribe visits a day) | about 13.6 fewer minutes a day on notes, 79 clinicians, more than 25,600 notes | Prospective study, JMIR Med Inform 2026;14:e84104 |

## Not in this release

Targets whose module is not part of version 1.0.0. Their ranges are fixed in `generator/spec.py`, and would be checked in an append-only release that adds the module.

| Module | Targets | Status | Count |
| --- | --- | --- | --- |
| hospice | T80 to T91 | not built; held for a later release | 10 |
