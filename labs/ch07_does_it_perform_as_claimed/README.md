# Chapter 7. Does it perform as claimed?

## The question

Tonmick Health bought a deterioration score. The vendor's model card claims a C-statistic of 0.84 on the vendor's own data. For six months in 2023 the score ran silently at five hospitals: every eligible patient was scored 12 hours after admission, and nobody was shown the result.

The AI Oversight Committee asks: **what does this score do on our patients?**

## Work from

- `data/deterioration/index_encounters.csv`: one row per scored encounter. You need `facility_id`, `index_datetime`, `vdi_score`, `vdi_shown` and `ehr_outcome_48h`.
- `data/deterioration/vendor_risk_table.csv`: the vendor's predicted risk for each score.
- `data/deterioration/vendor_model_card.json`: what the vendor says.

The silent period is 2023-07-01 to 2023-12-31, at every hospital except `F06`, which joined the network later.

## By hand

`by_hand.csv` has 20 of those encounters: the first 4 with the outcome and the first 16 without.

1. Pair each of the 4 with each of the 16. That is 64 pairs.
2. Count the pairs in which the patient with the outcome has the higher score, and the pairs that tie.
3. The C-statistic is (higher + half the ties) / 64.

You should count 59 and 0, so 59/64 = 0.922. A test holds the code to that.

Do not compute observed over expected on these 20 rows. One row in five has the outcome because they were picked that way; in the hospital it is about one in 27. A C-statistic survives that kind of sampling and a calibration measure does not.

## Then in code

```bash
python3 labs/ch07_does_it_perform_as_claimed/lab.py
Rscript labs/ch07_does_it_perform_as_claimed/lab.R
python3 labs/compare_results.py results/ch07_python.csv results/ch07_r.csv
```

Each writes 40 numbers: the cohort and its events, the C-statistic with DeLong's standard error, observed over expected, the calibration slope and intercept, calibration-in-the-large, and a calibration table in six bands of predicted risk.

## The trap

A local C-statistic below 0.84 is easy to report as a failure of the product. Before you do, ask what the vendor's number describes, how many events your own estimate rests on, and how good any score could be on these patients.

## Then, and only then, the answer key

```bash
python3 labs/ch07_does_it_perform_as_claimed/answer_key.py
```

It opens `hidden/deterioration/index_truth.csv` and sets each estimate beside the truth. No real hospital has that file.
