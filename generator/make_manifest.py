"""Write MANIFEST.json and SHA256SUMS.

    python3 generator/make_manifest.py ROOT

Run after the world, DICTIONARY.csv and CHECKS.md have been written under ROOT.
Both files cover the generated files, the two generated documents and the
documents in spec.HASHED_DOCUMENTS. HANDOFF.md is left out of both, because it
changes after every paste-back (DESIGN.md section 1).

Neither file holds a time, a path or a machine detail, so both are the same on
every machine. A matching hash confirms file identity only.
"""
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import dictionary     # noqa: E402
import spec           # noqa: E402


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def generated_paths():
    """Files that generate_world.py, dictionary.py and checks.py write."""
    return sorted(list(dictionary.built_files()) + dictionary.built_json_files()
                  + list(spec.GENERATED_DOCUMENTS))


def listed_paths():
    """Every path SHA256SUMS covers except MANIFEST.json itself."""
    return sorted(generated_paths() + list(spec.HASHED_DOCUMENTS))


def manifest(root):
    files = [{"path": path, "bytes": os.path.getsize(os.path.join(root, path))}
             for path in listed_paths()]
    return {
        "world": spec.WORLD,
        "version": spec.VERSION,
        "frozen": spec.FREEZE_DATE,
        "root_seed": spec.ROOT_SEED,
        "built_milestones": list(spec.BUILT_MILESTONES),
        "block_ids": spec.BLOCK_IDS,
        "reserved_block_ids": spec.RESERVED_BLOCK_IDS,
        "derived_block_id_start": spec.DERIVED_BLOCK_ID_START,
        "software": {"python": spec.PYTHON_SERIES, **spec.PINS},
        "note": ("Everything here is fictional. hidden/ is simulator truth and is never "
                 "evidence. This is the frozen release: data/ and hidden/ are committed, and no "
                 "file listed in SHA256SUMS may change. Later releases only add files. "
                 "generator/verify_world.py regenerates every file from the seed and compares "
                 "it with SHA256SUMS. A matching hash confirms file identity only."),
        "files": files,
    }


def main(argv):
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    root = argv[1]
    missing = [p for p in listed_paths() if not os.path.exists(os.path.join(root, p))]
    if missing:
        print("Cannot write the manifest; these files are missing:", file=sys.stderr)
        for p in missing:
            print(f"  {p}", file=sys.stderr)
        return 1
    with open(os.path.join(root, "MANIFEST.json"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(manifest(root), indent=2) + "\n")
    lines = [f"{sha256(os.path.join(root, p))}  {p}" for p in sorted(listed_paths() + ["MANIFEST.json"])]
    with open(os.path.join(root, "SHA256SUMS"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"Wrote MANIFEST.json and SHA256SUMS: {len(lines)} files.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
