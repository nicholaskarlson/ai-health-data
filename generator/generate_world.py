"""Generate the Tonmick Health world.

    python3 generator/generate_world.py OUTDIR     # writes data/ and hidden/ under OUTDIR

Built (spec.BUILT_MILESTONES): the inpatient core (Milestone 2); in the same
simulation, deterioration with the vendor's index and alerts (Milestone 3);
computed afterwards, the readmission model R30, the chart review, the logs,
change points and monthly truth (Milestone 4); and, from its own random blocks,
the AI scribe with its cost and wage tables (Milestone 5).
The run prints its time to the screen only; no output file depends on the
clock or on the machine.

Everything generated is fictional. `hidden/` is simulator truth and is never evidence.
"""
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import economics      # noqa: E402
import inpatient      # noqa: E402
import scribe         # noqa: E402
import spec           # noqa: E402


def generate(outdir):
    """Write data/ and hidden/ under `outdir`, replacing any earlier copy."""
    for sub in ("data", "hidden"):
        full = os.path.join(outdir, sub)
        if os.path.isdir(full):
            shutil.rmtree(full)
    summary = inpatient.generate(outdir)
    # The scribe and the cost tables use their own blocks and read nothing above.
    summary.update(scribe.generate(outdir))
    summary.update(economics.write(outdir))
    return summary


def main(argv):
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    outdir = argv[1]
    os.makedirs(outdir, exist_ok=True)
    start = time.time()
    summary = generate(outdir)
    took = time.time() - start
    print(f"{spec.WORLD} {spec.VERSION}, root seed {spec.ROOT_SEED}: "
          f"{summary['admissions']:,} admissions simulated, "
          f"{summary['published_admissions']:,} published, "
          f"{summary['persons']:,} persons, "
          f"{summary['outside_readmissions']:,} outside readmissions, "
          f"{summary['index_encounters']:,} index encounters; "
          f"{summary['clinician_weeks']:,} clinician-weeks, {summary['notes']:,} AI-drafted notes, "
          f"{summary['audit_notes']:,} audited.")
    print(f"Wrote data/ and hidden/ under {os.path.abspath(outdir)} in {took:.0f} seconds.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
