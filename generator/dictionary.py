"""Write DICTIONARY.csv from the column metadata in spec.FILES.

    python3 generator/dictionary.py DICTIONARY.csv

One row per file and column: file, variable, type_or_range, meaning.
Only files whose milestone has been built (spec.BUILT_MILESTONES) are listed.
JSON files are described in WORLD_SPEC.md, not here.
"""
import csv
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import spec           # noqa: E402

HEADER = ["file", "variable", "type_or_range", "meaning"]


def built_files():
    """{path: metadata} for every CSV whose milestone has been built, in spec order."""
    return {path: meta for path, meta in spec.expand_files().items()
            if meta["milestone"] in spec.BUILT_MILESTONES}


def built_json_files():
    return [path for path, milestone in spec.JSON_FILES.items()
            if milestone in spec.BUILT_MILESTONES]


def rows():
    out = []
    for path, meta in built_files().items():
        for name, col_type, decimals, value_range, meaning in meta["columns"]:
            kind = col_type
            if col_type == "float":
                kind = f"float, {decimals} decimal" + ("" if decimals == 1 else "s")
            out.append([path, name, f"{kind}; {value_range}" if value_range else kind, meaning])
    return out


def text():
    """The exact bytes of DICTIONARY.csv, as text."""
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(HEADER)
    writer.writerows(rows())
    return buf.getvalue()


def main(argv):
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    with open(argv[1], "w", encoding="utf-8", newline="") as fh:
        fh.write(text())
    print(f"Wrote {argv[1]}: {len(rows())} rows for {len(built_files())} files.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
