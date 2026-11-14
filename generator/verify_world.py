"""Regenerate the world in a temporary folder and compare with SHA256SUMS.

    python3 generator/verify_world.py [ROOT]

ROOT is the repository (default: the folder above generator/). The generated
files, DICTIONARY.csv and CHECKS.md are rebuilt from code in a temporary folder
and hashed there. The other documents in SHA256SUMS, and MANIFEST.json, are
hashed where they stand. Nothing under ROOT is changed.

Exits 0 if every hash matches and the checks pass, 1 otherwise. For a CSV that
does not match, the hash of each column is printed, to show where it differs.

A matching hash confirms file identity only.
"""
import hashlib
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd       # noqa: E402

import checks             # noqa: E402
import dictionary         # noqa: E402
import generate_world     # noqa: E402
import make_manifest      # noqa: E402
import spec               # noqa: E402


def read_sums(path):
    out = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if line:
                digest, name = line.split("  ", 1)
                out[name] = digest
    return out


def build(tmp):
    """Rebuild every generated file under `tmp`. Returns the number of failed checks."""
    generate_world.generate(tmp)
    with open(os.path.join(tmp, "DICTIONARY.csv"), "w", encoding="utf-8", newline="") as fh:
        fh.write(dictionary.text())
    report = checks.run(tmp)
    with open(os.path.join(tmp, "CHECKS.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(report.markdown())
    return report.failures


def column_hashes(path):
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    return [(name, hashlib.sha256("\n".join(df[name]).encode("utf-8")).hexdigest()[:16], len(df))
            for name in df.columns]


def main(argv):
    if len(argv) > 2:
        print(__doc__, file=sys.stderr)
        return 2
    root = argv[1] if len(argv) == 2 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sums_path = os.path.join(root, "SHA256SUMS")
    if not os.path.exists(sums_path):
        print(f"No SHA256SUMS in {root}.", file=sys.stderr)
        return 1
    want = read_sums(sums_path)
    generated = set(make_manifest.generated_paths())
    start = time.time()
    bad = []
    with tempfile.TemporaryDirectory(prefix="tonmick-verify-") as tmp:
        failures = build(tmp)
        for name in sorted(want):
            full = os.path.join(tmp if name in generated else root, name)
            got = make_manifest.sha256(full) if os.path.exists(full) else "missing"
            if got != want[name]:
                bad.append(name)
                where = "regenerated" if name in generated else "in the repository"
                print(f"DIFFERS  {name}  ({where})")
                print(f"    expected {want[name]}")
                print(f"    got      {got}")
                if name in generated and name.endswith(".csv") and got != "missing":
                    for column, digest, rows in column_hashes(full):
                        print(f"    column {column:28s} {digest}  ({rows} rows)")
        unlisted = sorted(generated - set(want))
        for name in unlisted:
            print(f"NOT LISTED  {name}  (generated, but absent from SHA256SUMS)")
    took = time.time() - start
    print(f"verify_world: {spec.WORLD} {spec.VERSION}, {len(want)} files in SHA256SUMS, "
          f"{len(generated)} regenerated in {took:.0f} seconds.")
    print(f"verify_world: {len(want) - len(bad)} match, {len(bad)} differ, "
          f"{len(unlisted)} not listed; {failures} checks failed.")
    ok = not bad and not unlisted and failures == 0
    print("verify_world: " + ("OK. A matching hash confirms file identity only." if ok else "FAILED."))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
