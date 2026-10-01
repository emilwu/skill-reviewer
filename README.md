# aocc-skill-reviewer

A standalone plugin, installable on both Claude Code and Codex CLI, that
reviews a named Agent Skill for structure, size/JIT budget, portability,
and script-extraction opportunities against a 49-rule portable rubric,
then revises it only after an explicit, proposal-specific `APPROVE`.

This repository does not depend on an originating team, wiki, QMD, mem0,
team scripts, home configuration, or a repository-root environment
variable. Do not install any of those systems for this plugin.

## Prerequisites

- Python 3.9 or newer, on `PATH` as `python3`.
- A local agent runtime (Claude Code or Codex CLI) that can read files and
  run the bundled Python scripts.
- Local write capability only if you later approve a revise proposal.
- Optional: `skills-ref` on `PATH`. Its absence is reported as `SKIP`,
  never as a pass. No network is required for review or revise.

## Install

### Claude Code

From the GitHub remote (`https://github.com/emilwu/skill-reviewer`):

```sh
claude plugin marketplace add emilwu/skill-reviewer
claude plugin install aocc-skill-reviewer@aocc-skill-reviewer
```

From a local clone or extracted archive:

```sh
claude plugin marketplace add /path/to/aocc-skill-reviewer
claude plugin install aocc-skill-reviewer@aocc-skill-reviewer
```

Both CLIs reject `file://` and `git://` marketplace sources — use a plain
local path, or an `http(s)` / GitHub `owner/repo` remote.

### Codex CLI

From the GitHub remote:

```sh
codex plugin marketplace add emilwu/skill-reviewer
codex plugin add aocc-skill-reviewer@aocc-skill-reviewer
```

From a local clone, Codex reads `.agents/plugins/marketplace.json` at this
repository's root when both marketplace files are present.

```sh
codex plugin marketplace add /path/to/aocc-skill-reviewer
codex plugin add aocc-skill-reviewer@aocc-skill-reviewer
```

### What gets installed

Each runtime discovers its own manifest independently:
`plugins/aocc-skill-reviewer/.claude-plugin/plugin.json` (Claude) and
`plugins/aocc-skill-reviewer/.codex-plugin/plugin.json` (Codex). The
runtime should activate
[skills/aocc-skill-reviewer/SKILL.md](plugins/aocc-skill-reviewer/skills/aocc-skill-reviewer/SKILL.md).
That entrypoint reads `references/rules-core.md` for every review and
loads the rest of `references/*.md` only as each mode's own list
specifies. `lineage.yaml` is provenance, not executable configuration.

## Use

Ask the agent to review or revise a Skill by its logical `name:`. The
skill resolves it with `scripts/locate_skill.py` across both runtimes'
standard discovery roots; an ambiguous name (more than one match) is
reported, never guessed.

- **review** — read-only. Runs `scripts/report_facts.py` against the
  target, loads the applicable rule files, and reports a verdict with
  every finding and its rule ID and evidence. Causes no mutation.
- **revise** — requires a current, non-expired review. Builds an itemized
  proposal with `scripts/revise_support.py propose`, computes a
  canonical `proposal_id`, and applies only the exact items named in a
  literal `APPROVE <proposal_id>: <item-id>[, ...]` response. A drift
  check immediately precedes apply; a postcondition check immediately
  follows it. See
  [references/mode-revise.md](plugins/aocc-skill-reviewer/skills/aocc-skill-reviewer/references/mode-revise.md)
  for the full state machine.

## Fact reporter

Run from any working directory with explicit inputs:

```sh
python3 /installed/aocc-skill-reviewer/scripts/report_facts.py \
  --skill-id my-skill \
  --master /work/my-skill \
  --copy /work/runtime-copy/my-skill/SKILL.md \
  --search-root /another/explicit/root \
  --manifest /work/my-skill/../../.claude-plugin/plugin.json
```

`--copy`, `--search-root`, and `--manifest` are repeatable. `--master`
accepts a Skill directory or its `SKILL.md`, or set `SKILL_AUDIT_TARGET`
to that same explicit path. The reporter emits JSON to stdout and
diagnostics to stderr. Exit 0 means a report was produced; exit 2 means
it could not run. The reporter never assigns a verdict, severity,
remediation, or threshold conclusion — only the loaded rule files, and
the model reading them, do that.

## R17 paired case

Test fixtures live at the repository root in `tests/fixtures/` — deliberately
outside the shipped plugin, so no fixture `SKILL.md` is ever installed or
picked up by a runtime's skill discovery:

- `must-accept/example-skill/`: declared copy is byte-identical to its master.
- `must-reject/example-skill/`: only the copy's final heading byte differs
  (`Skill` → `Skill!`).

```sh
R=plugins/aocc-skill-reviewer/skills/aocc-skill-reviewer/scripts

python3 $R/report_facts.py --skill-id example-skill \
  --master tests/fixtures/must-accept/example-skill \
  --copy tests/fixtures/must-accept/example-skill/copy

python3 $R/report_facts.py --skill-id example-skill \
  --master tests/fixtures/must-reject/example-skill \
  --copy tests/fixtures/must-reject/example-skill/copy
```

Expected fact difference: the accept copy reports
`identical_to_master: true` and the same SHA-256; the reject copy reports
`identical_to_master: false` and a different SHA-256.

The full fixture self-test suite (including a symlink-cycle case that is
created in a temp directory at test time — the repository itself contains no
symlinks) runs with `python3 tests/test_scripts.py`.

## Evals

`evals/c1-review-deterministic/` through `evals/c7-review-tool-grants/`
hold this reviewer's own release-gate cases (`prompt.md` + `graders/*.md`,
run with `claude plugin eval`). They, and the fixtures they review
(`tests/fixtures/`), are a repository-root release artifact and are **not**
shipped inside the plugin directory — the installed plugin cache contains
neither `evals/` nor any fixture `SKILL.md`. See
`plugins/aocc-skill-reviewer/skills/aocc-skill-reviewer/references/rules-evals.md`
for what each case must observe.

### Running the eval suite

`claude plugin eval` only accepts an eval directory *inside* the plugin
root (both `experimental.evals` and `--eval-dir` reject `..` and absolute
paths), so cases cannot be run against `plugins/aocc-skill-reviewer`
directly. Use the staging runner, which copies the plugin to a temp dir,
places `evals/` inside the copy and `tests/fixtures/` at
`<copy>/_eval_fixtures/` (outside `evals/`, because `claude plugin eval`
blocks model reads of the eval directory), substitutes `{{FIXTURES_DIR}}`
(fixtures) and `{{EVALS_DIR}}` (eval files; nothing model-facing) in each
case, and runs **one case per
`claude plugin eval` invocation** with `--max-cost-usd 5 -j 1`,
`--trust-plugin` and `--no-publish`:

```sh
# zero cost: stage, verify paths resolve, print the exact commands
python3 tools/run_evals.py --all --dry-run

# real model runs (real cost, cap $5 per case) — explicit budget decision only
python3 tools/run_evals.py --case c1 --results-dir /tmp/aocc-eval-results
python3 tools/run_evals.py --all --results-dir /tmp/aocc-eval-results
```

The runner strips `/mnt/*` entries from the eval subprocess `PATH` (slow WSL
mounts make the eval CLI refuse Bash-granting runs) and prints
`NOT A VALID MEASUREMENT` for any case whose result JSON contains an errored
or 0-turn run. The skill's scripts are invoked as single bare
`python3 "<SKILL_DIR>/scripts/<x>.py"` commands, which is exactly what the
`Bash(python3:*)` grant covers.

C6 (dual-runtime cache paths) is judged on one transcript, so it cannot show
the install location. Manual P6 step: run it once from a real Claude plugin
cache and once from a real Codex plugin cache, not only a dev checkout.

`--case` takes a case directory name or any unique prefix (`c1`); it may be
repeated. `--all` runs the cases sequentially, one invocation each. Results
land in `<results-dir>/<case>.json` plus `<results-dir>/<case>/`.

Tool grants are per case, as the operator `--allow-tools` grant is required
regardless of any case-level `allowed_tools`: review cases (`c1`, `c2`,
`c5`, `c6`, `c7`) get only `Bash(python3:*)`; revise cases (`c3`, `c4`,
detected from `Write`/`Edit` in the case's `allowed_tools`) additionally get
`Write` and `Edit` — review itself stays read-only per Q4. When the cap
prevents a case from completing, the result is INCOMPLETE with the case
named, never silently skipped.

## Open items

- **License**: MIT. See `LICENSE`.
- **Git remote**: `https://github.com/emilwu/skill-reviewer`.
- **Known issue — C2 grader stability (MINOR, waived for 0.1.0)**: `c2-seeded-defects`
  with-arm runs consistently find all five seeded defects with correct rule IDs (9/9
  transcripts across three release-gate runs), but the LLM judges score equivalent
  responses inconsistently (about 1/3 pass). The skill behaviour is verified; the grader
  needs a more mechanical rubric. All other cases (C1, C3–C7) pass with a +1.0 delta
  versus the no-plugin baseline.

## Troubleshooting

- **`fact reporter failed: provide --master...`** — pass `--master` or
  set `SKILL_AUDIT_TARGET`.
- **`locate_skill: no match for name=...`** — the target Skill is not
  under any searched root; pass `--root` with its actual location.
- **`skills_ref_validation` is skipped** — install `skills-ref` if
  official structural validation is also desired; otherwise the review
  must retain the explicit unavailable/SKIP fact.
- **Approval rejected as stale** — the target (or anything else in the
  proposal's bound snapshot) changed after the proposal was built.
  Re-review and approve the newly generated proposal ID.
