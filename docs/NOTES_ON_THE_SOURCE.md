# Notes on the source

The data in this repository are version 1.0.0 of the Tonmick Health practice world, frozen on 13 November 2026. They were built in a separate repository, `tonmick-health`, which is private. This note says what was copied, what was not, and what the copied documents mean when they refer to things that are not here.

## What was copied unchanged

- The 51 files under `data/` and `hidden/`, with `DICTIONARY.csv` and `CHECKS.md`. `SHA256SUMS` lists their hashes. `FROZEN_SHA256SUMS` is the source's complete list of 62 files, kept for the record; the 53 lines of `SHA256SUMS` are a subset of it.
- `generator/` and `checks/`, so that `python3 generator/verify_world.py` rebuilds every file from the seed.
- Four documents, now under `docs/`: `BACKSTORY.md`, `WORLD_SPEC.md`, `PROVENANCE.md` and `BOOK_MAP.md`. A test confirms each has the hash on the frozen list. Where they name a document at the top level of the source, read `docs/`.

## What was not copied

| Source file | What it is | Why it is not here |
| --- | --- | --- |
| `DESIGN.md` | The design record: decisions, targets, and plans for further books | A working document. What a reader needs from it is below |
| `NAMES.md` | The record of name checks | It lists names that were rejected because a real organisation or product uses them |
| `HANDOFF.md` | Working notes between sessions | Not written for readers |
| The source's `README.md`, `MANIFEST.json`, `tests/` and `tools/` | Housekeeping for the source | This repository has its own |

`generator/make_manifest.py` is copied because the verifier imports it. Run on its own it expects the documents above at the top level; nothing here needs it run.

## Words the copied documents use

- **The brief.** The written specification the world was built to. It set the target ranges and named the mechanisms to plant.
- **Nick.** Nicholas Karlson, the author.
- **Claude.** An AI model made by Anthropic. It wrote the generator, the checks, the tests and the documents to the brief. The author ran every command on his own machine and on GitHub, and approved each milestone and each variance. Claude could not reach either machine.
- **Milestones.** M2 the inpatient core; M3 the vendor's score and alerts; M4 the readmission model, chart review and logs; M5 the AI scribe; M7 the freeze. M6, a hospice module, was not built.
- **Commit hashes** such as `6ee3ade` are commits in the private source. `PROVENANCE.md` section 2 uses them to show that targets and mechanisms were written down before any generator code. A reader of this repository cannot inspect them, and should weigh that claim accordingly.
- **P1 to P24.** The planted mechanisms. `DESIGN.md` section 6 is not here; the same list, with the source or the label "design choice" for each, is `PROVENANCE.md` section 5.
- **Decision A1.** One book is planned in place of an earlier plan for seven.

## Variances

A variance replaces one of the brief's target ranges. The author approved all seven. `CHECKS.md` prints the brief's range beside the two that were set after a value was seen.

| Variance | Targets | What changed | When it was set |
| --- | --- | --- | --- |
| V1 | Hospice at 180 days | Three ranges that sum to 100% | Before any code. Hospice is not in this release |
| V2 | T50, notes in the frame | 90,000 to 120,000 in place of 50,000 to 80,000, which the brief's own panel could not produce | Before any code |
| V3 | T73, saving per scribe visit | Judged from the eighth live week, when the learning period is over | Before any code |
| V4 | T25, T26, the laboratory method change | Judged on the same patients scored with and without the change | Before any code |
| V5 | T19 to T21, T29 in part, T44 | Small groups are judged on expected values, with the realised value shown | Before any code |
| V6 (decision A31) | T41, T43, the readmission model | Apparent C-statistic 0.69 to 0.73 in place of 0.73 to 0.77; calibration slope 0.80 to 0.94 in place of 0.70 to 0.85 | **After the values were seen.** These ranges test nothing |
| V7 (decision A41) | T57, agreement between raters | Kappa 0.45 to 0.65 in place of 0.55 to 0.75 | **After the value was seen.** This range tests nothing |

`PROVENANCE.md` section 4 gives the reasons for V6 and V7 in full.

## Names

Every proper name in the world was searched for on 10 to 12 November 2026, and any name in use by a real US healthcare organisation, health-IT product or town was replaced. The record of those searches stays in the source. If you find a name here that matches something real, it is a coincidence the search missed, and the author would like to know.
