# Chapter 2. A hospital where the truth is known

**The committee's question:** why should anyone trust results from a made-up hospital?

| File | What it is |
| --- | --- |
| `by_hand.csv` | Twenty real discharges from 2023, each with the same person's next admission. Decide by pencil which count as a readmission |
| `lab.py`, `lab.R` | The headline figures of the extract (who is admitted, how they pay, how long they stay, how many die) and 30-day readmission derived from the admission files. They read `data/` only and must agree |
| `answer_key.py` | Opens `hidden/`: what the readmission rule recovers, and what no rule applied to `data/` can |

```bash
make hashes                                   # the files on disk are the published ones
sha256sum data/network/facilities.csv         # one file by hand; compare with its line in SHA256SUMS
make verify                                   # rebuild every file from the seed and compare
python3 labs/ch02_a_hospital_where_the_truth_is_known/lab.py
Rscript labs/ch02_a_hospital_where_the_truth_is_known/lab.R
python3 labs/compare_results.py results/ch02_python.csv results/ch02_r.csv
python3 labs/ch02_a_hospital_where_the_truth_is_known/answer_key.py      # last
```

Base R 4.1 has no SHA-256 function, so the hash check is a command, not part of `lab.R`.

## The readmission rule

A discharge counts if the patient left alive to home, home health or skilled nursing. It has a readmission if the same person's next admission starts 1 to 30 days after the discharge date and was not planned (`planned_admission` is 0). Only the next admission matters: a planned return first means no readmission, whatever follows. `docs/WORLD_SPEC.md` section 10 gives the same rule.

## By hand

`by_hand.csv` holds 2023 discharges in order of discharge date: the first four of each kind among discharges the rule counts (readmitted; a planned return within 30 days; a return after 30 days; no later admission at all), and the first discharge that ended in death, in hospice, against advice and in a transfer. Apply the rule. Sixteen discharges count, and four of them are readmissions. Four in sixteen is far above the rate in the full data, because the rows were picked four of each kind. The companion's tests make the same count.

## What the lab finds

- 147,837 admissions of 99,322 people at six hospitals, from January 2022 to June 2026. Median age 64; 47% Medicare; median stay 3.8 days; 1.9% die in hospital; 462 stays still open when the data end.
- Lactate is drawn in 40% of admissions: 60% of those in intensive care at 12 hours and 36% of the rest. A missing value is not missing at random.
- Of 28,002 discharges in 2023 that the rule counts, 3,334 were followed by a readmission the record can see: 11.9 per 100.
- None of the 1,862 live discharges the rule leaves out (hospice, against advice, transfer) came back within 30 days. That is a simplification of this world, and a real extract would not show it.

## The trap

Setting the 11.9 beside a published national rate and drawing a conclusion. The published rate counts returns to any hospital in a state; this extract sees one network. Run `answer_key.py` to see how much the record misses: 621 of 3,955 true readmissions went to a hospital outside the network.
