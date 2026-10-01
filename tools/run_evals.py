#!/usr/bin/env python3
"""Run this repository's eval cases against a staged copy of the plugin.

Why staging: `claude plugin eval` only accepts an eval directory *inside* the
plugin root, but the eval suite is a repository-root release artifact that
must not ship to users. So for each run this tool copies
`plugins/aocc-skill-reviewer/` into a temp dir, places `evals/` inside the
copy and `tests/fixtures/` at `<copy>/_eval_fixtures/` (deliberately NOT
under `evals/`: `claude plugin eval` blocks model reads of the eval
directory, which holds the graders), rewrites `{{EVALS_DIR}}` and
`{{FIXTURES_DIR}}` in the staged eval files to the staged absolute paths,
and runs ONE case per `claude plugin eval` invocation (the --max-cost-usd
cap is per invocation). Eval subprocesses get a PATH without `/mnt/*`
entries (slow WSL mounts make the eval CLI refuse Bash-granting runs), and a
case whose result JSON holds an errored or 0-turn run is flagged
NOT A VALID MEASUREMENT.

Real runs spend real money. `--dry-run` stages, verifies paths and prints the
exact commands with zero model cost.

Usage:
  python3 tools/run_evals.py --dry-run --all
  python3 tools/run_evals.py --case c1 --results-dir /tmp/eval-results
  python3 tools/run_evals.py --all --results-dir /tmp/eval-results

Stdlib only, Python 3.9+.
"""
import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PLUGIN_SRC = REPO / "plugins" / "aocc-skill-reviewer"
EVALS_SRC = REPO / "evals"
FIXTURES_SRC = REPO / "tests" / "fixtures"
EVALS_PLACEHOLDER = "{{EVALS_DIR}}"
FIXTURES_PLACEHOLDER = "{{FIXTURES_DIR}}"
FIXTURES_DIRNAME = "_eval_fixtures"
PYTHON_GRANT = "Bash(python3:*)"


def discover_cases():
    return sorted(p.name for p in EVALS_SRC.iterdir()
                  if p.is_dir() and (p / "prompt.md").is_file())


def resolve_case(token, cases):
    """Exact name, else unique name prefix (so `c1` works)."""
    if token in cases:
        return token
    hits = [c for c in cases if c.startswith(token)]
    if len(hits) == 1:
        return hits[0]
    sys.exit("error: --case %r matches %s; known cases: %s"
             % (token, hits or "nothing", ", ".join(cases)))


def tool_grants(case):
    """Operator --allow-tools grant for a case.

    Review cases get only Bash(python3:*). A case whose prompt.md
    `allowed_tools` names Write or Edit is a revise case and also gets
    Write and Edit (review itself stays read-only).
    """
    text = (EVALS_SRC / case / "prompt.md").read_text(encoding="utf-8")
    m = re.search(r"^allowed_tools:\s*\[(.*?)\]", text, re.M)
    declared = [t.strip() for t in m.group(1).split(",")] if m else []
    grants = [PYTHON_GRANT]
    for tool in ("Write", "Edit"):
        if tool in declared:
            grants.append(tool)
    return grants


def stage(tmp):
    """Build the staged plugin copy; return (plugin_copy, evals_dir, fixtures_dir)."""
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".git")
    plugin = Path(tmp) / "aocc-skill-reviewer"
    shutil.copytree(PLUGIN_SRC, plugin, ignore=ignore, symlinks=True)
    evals = plugin / "evals"
    shutil.copytree(EVALS_SRC, evals, ignore=shutil.ignore_patterns(
        "__pycache__", "*.pyc", "results"), symlinks=True)
    fixtures = plugin / FIXTURES_DIRNAME
    shutil.copytree(FIXTURES_SRC, fixtures, ignore=ignore, symlinks=True)
    for md in evals.rglob("*.md"):
        text = md.read_text(encoding="utf-8")
        new = (text.replace(EVALS_PLACEHOLDER, evals.as_posix())
                   .replace(FIXTURES_PLACEHOLDER, fixtures.as_posix()))
        if new != text:
            md.write_text(new, encoding="utf-8")
    return plugin, evals, fixtures


def verify_staged(plugin, evals, fixtures, cases):
    problems = []
    if not (plugin / ".claude-plugin" / "plugin.json").is_file():
        problems.append("staged plugin has no .claude-plugin/plugin.json")
    if evals in fixtures.parents or fixtures == evals:
        problems.append("fixtures are staged under evals/ (model reads are blocked there)")
    for case in cases:
        case_dir = evals / case
        if not (case_dir / "prompt.md").is_file():
            problems.append("%s: staged prompt.md missing" % case)
            continue
        for md in [case_dir / "prompt.md"] + sorted(case_dir.rglob("graders/*.md")):
            text = md.read_text(encoding="utf-8")
            for ph in (EVALS_PLACEHOLDER, FIXTURES_PLACEHOLDER):
                if ph in text:
                    problems.append("%s: unresolved %s in %s" % (case, ph, md.name))
            # every staged absolute path the file points at must exist
            for root in (fixtures, evals):
                for raw in re.findall(re.escape(root.as_posix()) + r"[^\s`'\"),]*", text):
                    if not Path(raw.rstrip(".")).exists():
                        problems.append("%s: path does not resolve: %s" % (case, raw))
    return problems


def sanitized_env():
    """Child env with PATH stripped of /mnt/* entries (WSL slow mounts)."""
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    kept = [e for e in env.get("PATH", "").split(os.pathsep)
            if e and not (e == "/mnt" or e.startswith("/mnt/"))]
    env["PATH"] = os.pathsep.join(kept)
    return env


def invalid_runs(result_json):
    """Return reasons a case result is not a valid measurement (errored or
    0-turn runs). Tolerant of the result schema: walks the whole JSON."""
    try:
        data = json.loads(Path(result_json).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return ["result JSON unreadable: %s" % exc]
    reasons = []

    def walk(node, where):
        if isinstance(node, dict):
            if node.get("error"):
                reasons.append("%s: error=%s" % (where, str(node["error"])[:120]))
            for key in ("turns", "num_turns", "n_turns"):
                if node.get(key) == 0:
                    reasons.append("%s: %s=0" % (where, key))
            for k, v in node.items():
                walk(v, "%s/%s" % (where, k))
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, "%s[%d]" % (where, i))

    walk(data, "$")
    return reasons


def build_command(plugin, case, grants, results_dir, keep_temp=False):
    cmd = ["claude", "plugin", "eval", str(plugin),
           "--case", case,
           "--max-cost-usd", "5", "-j", "1",
           "--trust-plugin", "--no-publish"]
    if keep_temp:
        cmd.append("--keep-temp")  # preserve scaffold dirs + traces (NEW-14)
    if results_dir is not None:
        out = results_dir / case
        cmd += ["--output-dir", str(out), "--json", str(results_dir / (case + ".json"))]
    cmd += ["--allow-tools"] + grants  # variadic: keep last
    return cmd


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sel = ap.add_mutually_exclusive_group(required=True)
    sel.add_argument("--case", action="append", metavar="ID",
                     help="case directory name or unique prefix (repeatable)")
    sel.add_argument("--all", action="store_true", help="every case, sequentially")
    ap.add_argument("--dry-run", action="store_true",
                    help="stage + verify paths and print commands; no model run, zero cost")
    ap.add_argument("--results-dir", type=Path, default=None,
                    help="where --json / --output-dir results go (required for real runs)")
    ap.add_argument("--keep-stage", action="store_true",
                    help="keep the temp staging dir (always printed)")
    ap.add_argument("--keep-temp", action="store_true",
                    help="pass --keep-temp to `claude plugin eval` so run traces/scaffold dirs survive")
    args = ap.parse_args()

    cases = discover_cases()
    if not cases:
        sys.exit("error: no eval cases under %s" % EVALS_SRC)
    selected = cases if args.all else [resolve_case(t, cases) for t in args.case]
    if not args.dry_run:
        if args.results_dir is None:
            sys.exit("error: real runs need --results-dir (choose a location outside the plugin)")
        if shutil.which("claude") is None:
            sys.exit("error: `claude` is not on PATH")
        args.results_dir.mkdir(parents=True, exist_ok=True)
    results_dir = args.results_dir.resolve() if args.results_dir else None

    rc_total = 0
    for case in selected:
        # fresh staging per case: a revise case may mutate scratch state
        tmp = tempfile.mkdtemp(prefix="aocc-eval-stage.")
        try:
            plugin, evals, fixtures = stage(tmp)
            problems = verify_staged(plugin, evals, fixtures, [case])
            cmd = build_command(plugin, case, tool_grants(case), results_dir, args.keep_temp)
            print("# %s" % case)
            print(" ".join(shlex.quote(c) for c in cmd))
            if problems:
                print("PATH CHECK FAILED:\n  " + "\n  ".join(problems), file=sys.stderr)
                rc_total = 1
                continue
            if args.dry_run:
                print("# staged paths resolve OK (dry-run: nothing executed)")
                continue
            started = time.monotonic()
            rc = subprocess.call(cmd, env=sanitized_env())
            print("# %s exit=%d wall=%.0fs" % (case, rc, time.monotonic() - started))
            rc_total = max(rc_total, rc)
            bad = invalid_runs(results_dir / (case + ".json"))
            if bad:
                print("# %s: NOT A VALID MEASUREMENT (errored / 0-turn runs):\n#   %s"
                      % (case, "\n#   ".join(bad)))
                rc_total = max(rc_total, 3)
        finally:
            if args.keep_stage:
                print("# stage kept: %s" % tmp)
            else:
                shutil.rmtree(tmp, ignore_errors=True)
    return rc_total


if __name__ == "__main__":
    sys.exit(main())
