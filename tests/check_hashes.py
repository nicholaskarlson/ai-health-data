"""Check every file listed in SHA256SUMS against its hash.

    python3 tests/check_hashes.py            # this repository
    python3 tests/check_hashes.py FOLDER     # any folder that holds a SHA256SUMS

The same check as `sha256sum -c SHA256SUMS`, for systems that do not have that
command. It needs Python only, no package. A matching hash confirms that a
file is the published file. It says nothing about whether the contents are
right.
"""
import hashlib
import os
import sys


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main(argv):
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    root = os.path.abspath(argv[1]) if len(argv) > 1 else here
    sums = os.path.join(root, "SHA256SUMS")
    if not os.path.isfile(sums):
        print(f"No SHA256SUMS in {root}.", file=sys.stderr)
        return 2
    listed = differ = missing = 0
    with open(sums, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line:
                continue
            want, name = line.split("  ", 1)
            listed += 1
            path = os.path.join(root, *name.split("/"))
            if not os.path.isfile(path):
                missing += 1
                print(f"MISSING  {name}")
            elif sha256(path) != want:
                differ += 1
                print(f"DIFFERS  {name}")
    print(f"check_hashes: {listed} files listed, {listed - differ - missing} match, "
          f"{differ} differ, {missing} missing.")
    if differ or missing:
        return 1
    print("A matching hash confirms file identity only.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
