# Labs

One folder for each chapter of the book. Every lab has the same parts, in the order the chapter uses them.

| File | What it is |
| --- | --- |
| `README.md` | The committee's question, the files to work from, and the trap. No answers |
| `by_hand.csv` | Twenty real rows, small enough for a pencil. The hand count is a test the code must pass |
| `lab.py` | The analysis in Python, from `data/` only |
| `lab.R` | The same analysis in base R. The two must agree |
| `answer_key.py` | The one script that opens `hidden/`: how close the analysis came, and why |

`common.py` and `common.R` hold the shared functions, each written twice under the same name. `compare_results.py` compares a lab's two result files: counts must be equal, fitted values within 1e-6, everything else to a relative 1e-8.

```bash
make labs        # every lab, both languages, compared
```

Results go to `results/`, which git ignores. A lab is not finished until `make labs` and `make test` both pass.
