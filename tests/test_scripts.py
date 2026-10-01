#!/usr/bin/env python3
"""Fixture-driven self-tests for the bundled scripts (stdlib unittest, Python 3.9+).

Run from the repository root:  python3 tests/test_scripts.py
Fixtures live in tests/fixtures/ (never inside the shipped plugin). The
symlink-cycle fixture is created only inside a temporary directory at test
time, so the repository itself contains no symlinks.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "plugins/aocc-skill-reviewer/skills/aocc-skill-reviewer/scripts"
FIXTURES = ROOT / "tests/fixtures"
ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")


def report(*args, timeout=30):
    start = time.monotonic()
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "report_facts.py"), *args],
        capture_output=True, text=True, timeout=timeout, env=ENV,
    )
    return proc, json.loads(proc.stdout), time.monotonic() - start


def find_key(obj, key):
    """Yield every value stored under `key` anywhere in a JSON tree."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key:
                yield v
            yield from find_key(v, key)
    elif isinstance(obj, list):
        for item in obj:
            yield from find_key(item, key)


class ReporterTests(unittest.TestCase):
    def test_r17_pair(self):
        results = {}
        for name in ("must-accept", "must-reject"):
            base = FIXTURES / name / "example-skill"
            proc, data, _ = report("--skill-id", "example-skill",
                                   "--master", str(base), "--copy", str(base / "copy"))
            self.assertEqual(proc.returncode, 0)
            results[name] = list(find_key(data, "identical_to_master"))
        self.assertTrue(results["must-accept"] and all(results["must-accept"]))
        self.assertIn(False, results["must-reject"])

    def test_unbounded_walk_is_bounded(self):
        proc, data, elapsed = report("--skill-id", "u",
                                     "--master", str(FIXTURES / "unbounded-walk-skill"))
        self.assertEqual(proc.returncode, 0)
        self.assertLess(elapsed, 5)
        dirs = {d["path"] for d in data["references"]["out_of_scope_directories"]}
        self.assertEqual(dirs, {"/", "/home", "/mnt/d"})

    def test_case_mismatch_entrypoint(self):
        _, bad, _ = report("--skill-id", "c", "--master",
                           str(FIXTURES / "case-mismatch-skill" / "skill.md"))
        _, good, _ = report("--skill-id", "c", "--master", str(FIXTURES / "clean-skill"))
        self.assertEqual(bad["entrypoint"]["exact_case_match"], False)
        self.assertEqual(good["entrypoint"]["exact_case_match"], True)

    def test_bom_parses(self):
        _, data, _ = report("--skill-id", "bom-skill", "--master", str(FIXTURES / "bom-skill"))
        self.assertEqual(list(find_key(data, "bom_present")), [True])

    def test_seeded_defect_dangling_and_env_var(self):
        _, data, _ = report("--skill-id", "seeded-defect-skill",
                            "--master", str(FIXTURES / "seeded-defect-skill"))
        self.assertTrue(data["references"]["dangling"])
        self.assertTrue(data["env_var_path_candidates"])

    def test_clean_skill_has_no_dangling(self):
        _, data, _ = report("--skill-id", "clean-skill", "--master", str(FIXTURES / "clean-skill"))
        self.assertEqual(data["references"]["dangling"], [])

    def test_symlink_cycle_terminates(self):
        """A directory symlink pointing at an ancestor must not loop the walk."""
        with tempfile.TemporaryDirectory(prefix="aocc-symcycle.") as tmp:
            skill = Path(tmp) / "cycle-skill"
            skill.mkdir()
            (skill / "SKILL.md").write_text(
                "---\nname: cycle-skill\ndescription: fixture\n---\n\n# Cycle\n",
                encoding="utf-8")
            sub = skill / "sub"
            sub.mkdir()
            try:
                os.symlink(str(skill), str(sub / "loop"), target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest("cannot create symlinks here: %s" % exc)
            proc, data, elapsed = report("--skill-id", "cycle-skill", "--master", str(skill))
            self.assertEqual(proc.returncode, 0)
            self.assertLess(elapsed, 5)
            self.assertFalse(data["references"]["truncated"])
            # the search-root walk (locate_skill) must terminate too
            loc = subprocess.run(
                [sys.executable, str(SCRIPTS / "locate_skill.py"), "--name", "cycle-skill",
                 "--root", tmp],
                capture_output=True, text=True, timeout=30, env=ENV)
            self.assertIn(loc.returncode, (0, 1, 2))


if __name__ == "__main__":
    unittest.main(verbosity=2)
