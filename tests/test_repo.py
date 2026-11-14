"""Tests for the companion repository.

    python3 -m unittest discover -s tests -v

They check that the data here are the frozen Tonmick Health files, that the
labs keep to the rule (an analysis reads data/ only), that the by-hand numbers
equal what the code gives, and that the labs reproduce the frozen checks.
"""
import csv
import hashlib
import os
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LABS = os.path.join(ROOT, "labs")
sys.path.insert(0, LABS)

import numpy as np            # noqa: E402

import common                 # noqa: E402


def sums(name):
    out = {}
    with open(os.path.join(ROOT, name), encoding="utf-8") as fh:
        for line in fh:
            digest, path = line.rstrip("\n").split("  ", 1)
            out[path] = digest
    return out


def sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def lab_folders():
    return sorted(name for name in os.listdir(LABS) if re.match(r"ch\d\d_", name))


class TestFrozenWorld(unittest.TestCase):
    def test_the_data_are_the_frozen_files(self):
        """Every file in SHA256SUMS is on the frozen list of tonmick-health 1.0.0 with the
        same hash, is present here with that hash, and data/ and hidden/ hold nothing else."""
        here, frozen = sums("SHA256SUMS"), sums("FROZEN_SHA256SUMS")
        self.assertEqual(len(here), 53)
        self.assertEqual(len(frozen), 62)
        for path, digest in here.items():
            self.assertEqual(frozen.get(path), digest, path)
            self.assertEqual(sha256(os.path.join(ROOT, path)), digest, path)
        on_disk = []
        for folder in ("data", "hidden"):
            for base, _dirs, files in os.walk(os.path.join(ROOT, folder)):
                on_disk += [os.path.relpath(os.path.join(base, f), ROOT).replace(os.sep, "/") for f in files]
        self.assertEqual(sorted(on_disk), sorted(p for p in here if p.startswith(("data/", "hidden/"))))

    def test_check_hashes_passes_here_and_fails_on_a_changed_or_missing_file(self):
        script = [sys.executable, os.path.join(ROOT, "tests", "check_hashes.py")]
        done = subprocess.run(script, capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertIn("53 files listed, 53 match, 0 differ, 0 missing.", done.stdout)
        with tempfile.TemporaryDirectory(prefix="ai-health-data-") as tmp:
            for name, text in (("same.txt", "one\n"), ("changed.txt", "two\n")):
                with open(os.path.join(tmp, name), "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(text)
            lines = [f"{sha256(os.path.join(tmp, 'same.txt'))}  same.txt",
                     f"{'0' * 64}  changed.txt",
                     f"{'0' * 64}  absent.txt"]
            with open(os.path.join(tmp, "SHA256SUMS"), "w", encoding="utf-8", newline="\n") as fh:
                fh.write("\n".join(lines) + "\n")
            done = subprocess.run(script + [tmp], capture_output=True, text=True)
            self.assertEqual(done.returncode, 1, done.stdout)
            self.assertIn("DIFFERS  changed.txt", done.stdout)
            self.assertIn("MISSING  absent.txt", done.stdout)
            self.assertIn("3 files listed, 1 match, 1 differ, 1 missing.", done.stdout)

    def test_the_world_documents_are_unchanged(self):
        frozen = sums("FROZEN_SHA256SUMS")
        for name in ("BACKSTORY.md", "WORLD_SPEC.md", "PROVENANCE.md", "BOOK_MAP.md"):
            self.assertEqual(sha256(os.path.join(ROOT, "docs", name)), frozen[name], name)


class TestLabRules(unittest.TestCase):
    def test_every_lab_has_its_parts(self):
        self.assertTrue(lab_folders())
        for folder in lab_folders():
            for part in ("README.md", "lab.py", "lab.R", "answer_key.py", "by_hand.csv"):
                self.assertTrue(os.path.exists(os.path.join(LABS, folder, part)), f"{folder}/{part}")

    def test_an_analysis_never_opens_hidden(self):
        """lab.py and lab.R read data/ only (comments and docstrings aside). Only answer_key.py may
        open hidden/, and it must do so."""
        for folder in lab_folders():
            for part in ("lab.py", "lab.R"):
                with open(os.path.join(LABS, folder, part), encoding="utf-8") as fh:
                    code = "\n".join(line for line in fh.read().splitlines()
                                     if not line.lstrip().startswith("#"))
                code = re.sub(r'""".*?"""', "", code, flags=re.S)
                self.assertNotIn("hidden", code, f"{folder}/{part}")
            with open(os.path.join(LABS, folder, "answer_key.py"), encoding="utf-8") as fh:
                self.assertIn('read("hidden/', fh.read(), folder)

    def test_workflow_values_are_plain_yaml(self):
        """A one-line run: or name: value may not hold a colon followed by a space, or a
        space followed by a hash; GitHub rejects the whole file if it does."""
        folder = os.path.join(ROOT, ".github", "workflows")
        for name in sorted(os.listdir(folder)):
            with open(os.path.join(folder, name), encoding="utf-8") as fh:
                text = fh.read()
            self.assertNotIn("\t", text, name)
            for number, line in enumerate(text.splitlines(), 1):
                found = re.match(r"^\s*(?:- )?(?:run|name): (.*)$", line)
                if found and found.group(1)[:1] not in ("|", ">", "'", '"'):
                    self.assertNotIn(": ", found.group(1), f"{name} line {number}")
                    self.assertNotIn(" #", found.group(1), f"{name} line {number}")

    def test_no_email_address_outside_the_data(self):
        pattern = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+\.[A-Za-z]{2,}")
        skip = {".git", ".venv", "data", "hidden", "__pycache__", "results", "build"}
        found = []
        for base, dirs, files in os.walk(ROOT):
            dirs[:] = [d for d in dirs if d not in skip]
            for name in files:
                if name.endswith((".md", ".py", ".R", ".yml", ".csv", ".txt")) or name == "Makefile":
                    with open(os.path.join(base, name), encoding="utf-8") as fh:
                        found += [f"{name}: {hit}" for hit in pattern.findall(fh.read())]
        self.assertFalse(found)


class TestChapter7(unittest.TestCase):
    FOLDER = os.path.join(LABS, "ch07_does_it_perform_as_claimed")

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="ai-health-data-")
        out = os.path.join(cls.tmp.name, "ch07_python.csv")
        subprocess.run([sys.executable, os.path.join(cls.FOLDER, "lab.py"), out], check=True,
                       stdout=subprocess.DEVNULL)
        with open(out, encoding="utf-8", newline="") as fh:
            cls.results = dict(list(csv.reader(fh))[1:])
        cls.out = out

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def by_hand(self):
        with open(os.path.join(self.FOLDER, "by_hand.csv"), encoding="utf-8", newline="") as fh:
            return list(csv.DictReader(fh))

    def test_by_hand_extract_is_real_data(self):
        rows = self.by_hand()
        self.assertEqual(len(rows), 20)
        ix = common.read("data/deterioration/index_encounters.csv").set_index("encounter_id")
        for row in rows:
            self.assertEqual(ix.loc[row["encounter_id"], "vdi_score"], row["vdi_score"])
            self.assertEqual(ix.loc[row["encounter_id"], "ehr_outcome_48h"], row["ehr_outcome_48h"])

    def test_by_hand_c_statistic(self):
        """The pencil count in the lab's README: 4 events and 16 non-events make 64 pairs,
        59 of them with the higher score on the event and none tied, so C = 59/64."""
        rows = self.by_hand()
        events = [int(r["vdi_score"]) for r in rows if r["ehr_outcome_48h"] == "1"]
        others = [int(r["vdi_score"]) for r in rows if r["ehr_outcome_48h"] == "0"]
        higher = sum(a > b for a in events for b in others)
        tied = sum(a == b for a in events for b in others)
        self.assertEqual((len(events), len(others), higher, tied), (4, 16, 59, 0))
        score = np.array([float(r["vdi_score"]) for r in rows])
        outcome = np.array([float(r["ehr_outcome_48h"]) for r in rows])
        self.assertEqual(common.c_statistic(score, outcome), 59 / 64)

    def test_the_lab_reproduces_the_frozen_checks(self):
        """CHECKS.md was written by the generator's own check script, with different code.
        The lab's numbers must equal its rows T15, T16, T17 and T18 as printed."""
        rows = {}
        with open(os.path.join(ROOT, "CHECKS.md"), encoding="utf-8") as fh:
            for line in fh:
                cells = [c.strip() for c in line.split("|")]
                if len(cells) > 3 and re.match(r"T1[5-8] ", cells[1]):
                    rows[cells[1].split(" ")[0]] = cells[2]
        r = self.results
        self.assertTrue(rows["T15"].startswith(f"{float(r['stat.ch07.event_rate']):.4f} "
                                               f"({r['n.ch07.events']} flagged of 12,030)"), rows["T15"])
        self.assertEqual(r["n.ch07.encounters"], "12030")
        self.assertTrue(rows["T16"].startswith(f"{float(r['stat.ch07.c_statistic']):.4f};"), rows["T16"])
        self.assertTrue(rows["T17"].startswith(f"{float(r['fit.ch07.calibration_slope']):.3f} (intercept "
                                               f"{float(r['fit.ch07.calibration_intercept']):.3f})"), rows["T17"])
        self.assertTrue(rows["T18"].startswith(f"{float(r['stat.ch07.observed_over_expected']):.3f};"), rows["T18"])

    def test_the_comparison_accepts_equal_files_and_rejects_a_changed_one(self):
        compare = [sys.executable, os.path.join(LABS, "compare_results.py")]
        self.assertEqual(subprocess.run(compare + [self.out, self.out], stdout=subprocess.DEVNULL).returncode, 0)
        changed = os.path.join(self.tmp.name, "changed.csv")
        with open(self.out, encoding="utf-8") as fh:
            text = fh.read()
        value = self.results["stat.ch07.c_statistic"]
        with open(changed, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text.replace(f"stat.ch07.c_statistic,{value}", f"stat.ch07.c_statistic,{float(value) + 1e-6:.12g}"))
        self.assertEqual(subprocess.run(compare + [self.out, changed], stdout=subprocess.DEVNULL).returncode, 1)

    def test_the_answer_key_runs(self):
        done = subprocess.run([sys.executable, os.path.join(self.FOLDER, "answer_key.py")], check=True,
                              capture_output=True, text=True)
        self.assertIn("against the truth", done.stdout)


class TestChapter6(unittest.TestCase):
    FOLDER = os.path.join(LABS, "ch06_protocol_first")

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="ai-health-data-")
        out = os.path.join(cls.tmp.name, "ch06_python.csv")
        done = subprocess.run([sys.executable, os.path.join(cls.FOLDER, "lab.py"), out],
                              capture_output=True, text=True, cwd=ROOT)
        assert done.returncode == 0, done.stderr
        with open(out, encoding="utf-8", newline="") as fh:
            cls.results = dict(list(csv.reader(fh))[1:])

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def by_hand(self):
        with open(os.path.join(self.FOLDER, "by_hand.csv"), encoding="utf-8", newline="") as fh:
            return list(csv.DictReader(fh))

    def test_by_hand_extract_is_real_data(self):
        rows = self.by_hand()
        self.assertEqual(len(rows), 20)
        ix = common.read("data/deterioration/index_encounters.csv").set_index("encounter_id")
        for row in rows:
            for column in ("facility_id", "index_datetime", "vdi_shown", "ehr_outcome_48h"):
                self.assertEqual(ix.loc[row["encounter_id"], column], row[column])

    def test_by_hand_classification(self):
        """The pencil exercise in the lab's README: 9 of the 20 encounters are in the cohort.
        The 11 that are out all fall after the window; 5 of them were still silent, 6 had the
        score shown, 2 of those at F06, and 1 has no recorded outcome."""
        rows = self.by_hand()
        late = [r for r in rows if not "2023-07-01" <= r["index_datetime"][:10] <= "2023-12-31"]
        inside = [r for r in rows if r not in late and r["facility_id"] != "F06"
                  and r["vdi_shown"] == "0" and r["ehr_outcome_48h"] != ""]
        self.assertEqual((len(inside), len(late)), (9, 11))
        self.assertEqual(sum(r["vdi_shown"] == "0" for r in late), 5)
        self.assertEqual(sum(r["vdi_shown"] == "1" for r in late), 6)
        self.assertEqual(sum(r["facility_id"] == "F06" for r in late), 2)
        self.assertEqual(sum(r["ehr_outcome_48h"] == "" for r in late), 1)

    def test_the_lab_agrees_with_the_frozen_checks_and_with_chapter_7(self):
        """CHECKS.md row T15 gives the cohort's size and events, and T16 its C-statistic."""
        rows = {}
        with open(os.path.join(ROOT, "CHECKS.md"), encoding="utf-8") as fh:
            for line in fh:
                cells = [c.strip() for c in line.split("|")]
                if len(cells) > 3 and re.match(r"T1[56] ", cells[1]):
                    rows[cells[1].split(" ")[0]] = cells[2]
        r = self.results
        self.assertEqual((r["n.ch06.cohort"], r["n.ch06.cohort_events"]), ("12030", "443"))
        self.assertIn("(443 flagged of 12,030)", rows["T15"])
        self.assertTrue(rows["T16"].startswith(f"{float(r['stat.ch06.protocol_c_statistic']):.4f};"), rows["T16"])
        hospitals = sum(int(r[f"n.ch06.f0{k}_encounters"]) for k in range(1, 6))
        months = sum(int(r[f"n.ch06.m2023_{m:02d}_encounters"]) for m in range(7, 13))
        self.assertEqual((hospitals, months), (12030, 12030))
        self.assertEqual(int(r["n.ch06.silent_as_run_encounters"]),
                         12030 + int(r["n.ch06.silent_after_window_encounters"]))

    def test_the_answer_key_runs(self):
        done = subprocess.run([sys.executable, os.path.join(self.FOLDER, "answer_key.py")],
                              capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("events prevented: 44", done.stdout)
        self.assertIn("the same outcome either way for 12,030 of 12,030 encounters", done.stdout)


if __name__ == "__main__":
    unittest.main()
