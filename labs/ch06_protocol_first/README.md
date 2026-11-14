# Chapter 6. Protocol first

**The committee's question:** before anyone looks at results, what exactly will we measure, and on whom?

| File | What it is |
| --- | --- |
| `by_hand.csv` | Twenty real encounters to classify with a pencil: in the cohort, or out, and why |
| `lab.py`, `lab.R` | The cohort and its flow, by hospital and by month, and three cohorts a team might have chosen instead. They read `data/` only and must agree |
| `answer_key.py` | Opens `hidden/`: what showing the score did to the outcomes it would be judged against |

```bash
python3 labs/ch06_protocol_first/lab.py
Rscript labs/ch06_protocol_first/lab.R
python3 labs/compare_results.py results/ch06_python.csv results/ch06_r.csv
python3 labs/ch06_protocol_first/answer_key.py      # last
```

## The protocol's four conditions

An index encounter is in the cohort if all four hold:

1. it falls in the planned silent window, July 1 to December 31, 2023 (`data/network/timeline.csv`);
2. it is at one of the five hospitals that ran the score silently, which leaves out `F06`;
3. the score was not shown (`vdi_shown` is 0);
4. the record holds an outcome for it (`ehr_outcome_48h` is not empty).

## By hand

Apply the four conditions to the 20 rows of `by_hand.csv`. Nine are in. Eleven are out, all of them after the window: five were still silent, at hospitals that went live later than planned for; six had the score shown, two of them at `F06`; and one of those six has no recorded outcome yet. The companion's tests make the same count.

## What the lab finds

- Of 80,751 index encounters, 12,030 are in the cohort, with 443 recorded events. Within the window the other three conditions remove nobody: they are there for the encounters a wider window would let in.
- Silent scoring ran past the planned window: to January 14, 2024 at three hospitals and to the end of March at the two small ones. Taking every silent encounter gives 13,346.
- The first twelve months, shown or not, give 24,746 encounters, 11,400 of them with the score shown.
- The C-statistic is 0.772 in the protocol's cohort, 0.760 among all silent encounters and 0.756 over the first year. The intervals overlap. The point is not that one cohort is right because of its result. It is that a team that chooses after looking can choose its result.

## The trap

Letting in encounters where the score was shown. Run `answer_key.py` to see why: among the 11,400 shown encounters, 453 patients would have deteriorated with no evaluation and 409 did. The alerts prevented 44 events, every one of them in a patient the score had flagged, so the score is marked down for its own successes.
