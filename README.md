# AI Health Data: a hospital where the truth is known

Synthetic data for practising how to check a health AI tool on your own patients, before it goes live and after. Every question here has a known answer, because the hospital is simulated and the simulator's truth is published beside the data.

This is the companion repository to the book *Validating Health AI Before and After Go-Live: A Field Manual for Local Performance Checks, Monitoring and Audit, with Known Answers in Python and R* (NEKpress, in preparation). It is usable without the book.

**Everything here is fictional.** Tonmick Health, its hospitals, its vendors and their products are invented. No row describes a real person. Nothing here is medical advice or a finding about any real hospital or product.

## Why it exists

Real validation work has no answer key. You estimate a C-statistic, a calibration slope or an error rate, and you never learn how close you were. Public clinical data sets have the same limit, and their access terms often bar sharing worked results.

Here you can find out. Tonmick Health is a made-up network of six hospitals and 24 clinics that bought two AI tools and built a third:

| Tool | What the network knows | What you can check |
| --- | --- | --- |
| A vendor's deterioration score, formula undisclosed | A model card claiming a C-statistic of 0.84 | Local performance in six silent months, subgroups, alerts, drift over three years |
| An in-house 30-day readmission model | Its coefficients and one reported number | Optimism, sample size, transport to other hospitals |
| An AI scribe that drafts clinic notes | An audit of 1,200 notes by two raters each | The true error rate in all 102,502 notes |

Twenty-four mechanisms are planted in the data, each documented: a laboratory method change that raises alerts without raising risk, a pulse oximeter that reads high in some patients, an outcome flag that misses transfers, a lenient rater, and more. `docs/BOOK_MAP.md` says where each one is.

## The one rule

- **`data/`** is what an analyst at the network could see. Do your analysis from it alone.
- **`hidden/`** is what the simulator did: true risks, true outcomes, both potential outcomes of every alert, the true errors in every note. It is never evidence. Open it only to mark your own work.

Each lab keeps to this. Its `lab.py` and `lab.R` read `data/` only, and a test fails if they do not. Its `answer_key.py` is the one script that opens `hidden/`.

## What is in the repository

| Path | Contents |
| --- | --- |
| `data/` | 27 files: 99,322 people, 147,837 admissions over four and a half years, 80,751 scored encounters, 102,502 AI-drafted notes, the audit, model cards, logs. 41 MB |
| `hidden/` | 24 files of simulator truth. 32 MB |
| `DICTIONARY.csv` | Every column of every CSV: type, range, meaning |
| `CHECKS.md` | 129 checks the world passes, with each value printed |
| `docs/` | The backstory, the full specification, the provenance record, and a map from book chapters to files, all unchanged from the source. `NOTES_ON_THE_SOURCE.md` explains their references |
| `labs/` | One folder per chapter: a pencil exercise, the analysis in Python and in R, and an answer key |
| `templates/` | Scoping questions, a data request and a validation protocol, ready to adapt |
| `generator/` | The code that makes every file from one seed |
| `checks/` | The world's own cross-check: 104 statistics computed in Python and in R |
| `BOOK_OUTLINE.md` | The book, chapter by chapter, with the files and numbers each one uses |

## Quick start

```bash
git clone https://github.com/nicholaskarlson/ai-health-data.git
cd ai-health-data
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # numpy 2.5.3 and pandas 3.0.5, pinned

make hashes      # the files on disk are the published ones
make verify      # rebuild the whole world from its seed and compare, about 30 seconds
make test        # the labs keep the rule and reproduce the published checks
make labs        # every lab in Python and in R; the two must agree (needs R)
```

Then try the first lab:

```bash
python3 labs/ch07_does_it_perform_as_claimed/lab.py          # the analysis, from data/ only
python3 labs/ch07_does_it_perform_as_claimed/answer_key.py   # how close it came, and why
```

Without `make`, run what each target runs:

```bash
python3 tests/check_hashes.py                  # make hashes
python3 generator/verify_world.py              # make verify
python3 -m unittest discover -s tests -v       # make test
```

What you need, and what has been tried:

- **Python 3.12 or later,** which numpy 2.5.3 requires. The hashes were made with Python 3.13, and that is the only version `make verify` has been run on.
- **R is optional.** Base R is enough for the R side; no package is needed. It has been run on R 4.1.2.
- **Linux is the only system this has been run on.** macOS and Windows should work and have not been tried. On Windows, `make` needs WSL or Git Bash; the three commands above need neither, with `python` in place of `python3`.

## Labs

Labs arrive with the chapters. Each has the same five parts as its chapter: the question, a calculation by hand on 20 rows, the analysis in Python and in R, the answer key, and the trap.

| Lab | Question | Status |
| --- | --- | --- |
| `ch07_does_it_perform_as_claimed` | The vendor claims 0.84. What does the score do on our patients? | Ready |
| Chapters 1 to 6 and 8 to 16 | See `BOOK_OUTLINE.md` | To come |

## How this was made, and what that means

- **It is synthetic and it was tuned.** Target ranges and planted mechanisms were written down first; the generator was then built and adjusted until the checks passed. `docs/PROVENANCE.md` says what was fixed in advance, what was adjusted, and which target ranges were replaced, three of them after the value was seen. Passing its own checks is not evidence of realism.
- **Real figures are cited where they were used,** with the date each source was seen, in `docs/PROVENANCE.md` section 6. Everything else is labelled a design choice.
- **It is reproducible.** The same 53 files came out byte for byte on three machines, all running Linux, and Python and R agree on 104 statistics computed from them. A matching hash confirms file identity only.
- **An AI model wrote the code.** The generator, checks, tests and documents were written by Claude, an AI model made by Anthropic, to the author's written brief. The author ran every command and approved every milestone. `docs/NOTES_ON_THE_SOURCE.md` has the detail.
- **It is frozen.** These files are version 1.0.0 of the Tonmick Health world and will not change. Anything new will be added beside them.

## Licence and citation

Data and documents: CC BY 4.0. Code: MIT. See `LICENSES.md`. No licence covers the NEKpress name or branding.

To cite: Karlson NE. *AI Health Data: the Tonmick Health practice world, version 1.0.0.* 2026. https://github.com/nicholaskarlson/ai-health-data
