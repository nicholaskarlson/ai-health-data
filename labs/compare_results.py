"""Compare a lab's Python results with its R results.

    python3 labs/compare_results.py PYTHON.csv R.csv

Both files must list the same statistics. Counts (n.*) must be equal. Fitted
values (fit.*) may differ by 1e-6. Everything else (stat.*) must agree to a
relative 1e-8. Exits 0 if everything agrees, 1 otherwise.
"""
import csv
import sys

FIT_TOLERANCE = 1e-6
RELATIVE_TOLERANCE = 1e-8


def read(path):
    with open(path, encoding="utf-8", newline="") as fh:
        rows = list(csv.reader(fh))
    if not rows or rows[0] != ["statistic", "value"]:
        raise SystemExit(f"{path}: the header must be statistic,value")
    return dict(rows[1:])


def main(python_file, r_file):
    py, r = read(python_file), read(r_file)
    problems = [f"{name}: in one file only" for name in sorted(set(py) ^ set(r))]
    for name in py:
        if name not in r:
            continue
        if name.startswith("n."):
            ok = int(py[name]) == int(r[name])
        else:
            x, y = float(py[name]), float(r[name])
            if name.startswith("fit."):
                ok = abs(x - y) <= FIT_TOLERANCE
            else:
                ok = abs(x - y) <= RELATIVE_TOLERANCE * max(abs(x), abs(y))
        if not ok:
            problems.append(f"{name}: Python {py[name]}, R {r[name]}")
    for line in problems:
        print("DIFFERS  " + line)
    verdict = "OK. Python and R agree." if not problems else f"FAILED, {len(problems)} problems."
    print(f"compare_results: {len(py)} statistics in {python_file}, {len(r)} in {r_file}. {verdict}")
    return 1 if problems else 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2]))
