"""Compare the Python and R sides of the cross-check.

    python3 checks/compare_crosscheck.py PYTHON.csv R.csv

Both files must list the same statistics. Counts (rows.*, n.*) must be equal.
Fitted coefficients (fit.*) may differ by 1e-6. Everything else (stat.*) must
agree to a relative 1e-8. In the Python file, each refitted R30 coefficient
must also sit within 1e-6 of the value on the model card.

Exits 0 if everything agrees, 1 otherwise.
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
    out = {}
    for name, value in rows[1:]:
        if name in out:
            raise SystemExit(f"{path}: {name} is listed twice")
        out[name] = value
    return out


def differs(name, a, b):
    """A message if the two values disagree, else None."""
    if name.startswith(("rows.", "n.")):
        return None if int(a) == int(b) else "counts differ"
    x, y = float(a), float(b)
    if name.startswith("fit."):
        return None if abs(x - y) <= FIT_TOLERANCE else f"differ by {abs(x - y):.3g}, more than {FIT_TOLERANCE:g}"
    scale = max(abs(x), abs(y))
    if scale == 0.0 or abs(x - y) <= RELATIVE_TOLERANCE * scale:
        return None
    return f"relative difference {abs(x - y) / scale:.3g}, more than {RELATIVE_TOLERANCE:g}"


def main(python_file, r_file):
    py, r = read(python_file), read(r_file)
    problems = []
    for name in sorted(set(py) - set(r)):
        problems.append(f"{name}: in the Python file only")
    for name in sorted(set(r) - set(py)):
        problems.append(f"{name}: in the R file only")
    worst = 0.0
    for name in py:
        if name not in r:
            continue
        message = differs(name, py[name], r[name])
        if message:
            problems.append(f"{name}: Python {py[name]}, R {r[name]}: {message}")
        if name.startswith("stat."):
            x, y = float(py[name]), float(r[name])
            if max(abs(x), abs(y)) > 0.0:
                worst = max(worst, abs(x - y) / max(abs(x), abs(y)))
    refits = [n for n in py if n.startswith("fit.r30.coef.")]
    for name in refits:
        card = "stat.r30.card." + name[len("fit.r30.coef."):]
        if card not in py:
            problems.append(f"{name}: no model-card value to compare with")
        elif abs(float(py[name]) - float(py[card])) > FIT_TOLERANCE:
            problems.append(f"{name}: refit {py[name]} against the card's {py[card]}")
    counts = sum(1 for n in py if n.startswith(("rows.", "n.")))
    fits = sum(1 for n in py if n.startswith("fit."))
    print(f"compare_crosscheck: {len(py)} statistics in the Python file, {len(r)} in the R file: "
          f"{counts} counts, {fits} fitted coefficients, {len(py) - counts - fits} other values.")
    print(f"compare_crosscheck: largest relative difference among the other values {worst:.3g}; "
          f"{len(refits)} R30 coefficients refitted and compared with the model card.")
    for line in problems:
        print("DIFFERS  " + line)
    print("compare_crosscheck: " + ("OK. Python and R agree." if not problems else f"FAILED, {len(problems)} problems."))
    return 1 if problems else 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2]))
