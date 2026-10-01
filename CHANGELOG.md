# Changelog

## 0.1.0 P6 round 5 — 2026-10-01

- Release-gate result: C1, C3–C7 PASS (delta +1.0 vs baseline); C2 waived by owner as a known MINOR grader-stability issue (skill finds all 5 seeded defects in 9/9 runs; judges inconsistent).
- C2 `no-false-positive.md` grader now inlines the five seeded defects and the sanctioned-findings list (judges cannot read `criteria.md`; NEW-16).

## 0.1.0 — 2026-10-01

Initial build. One skill, two modes (review, revise), dual-runtime plugin
(Claude Code + Codex CLI), per `agent-Em/outbox/skill-reviewer-policy-v1.md`
Policy v1.0 (49 rules) and the 2026-10-01 ratification (Q2-Q6, G1).

- `SKILL.md` with six portable frontmatter fields, no `allowed-tools`
  grant, provider-neutral body.
- `scripts/report_facts.py` — facts-only reporter: frontmatter, sizes,
  reference graph, ToC detection, code-fence/table/directive candidates,
  repeated-block hashes, exec/symlink metadata, copy identity, manifest
  parsing.
- `scripts/locate_skill.py` — read-only skill-by-name resolver across both
  runtimes' standard discovery roots.
- `scripts/revise_support.py` — snapshot/propose/check-approval/
  drift-check/verify mechanics for the §7 consent state machine.
- `references/rules-{core,structure,context,portability,safety,evals,
  appendices}.md`, `references/mode-{review,revise}.md` — the rule-pack
  split sized to the G1 ≤~25 KB normal-review activation budget (measured
  24,236 bytes for the six-file set after the P6 fixes; see below).
- `evals/c1`–`c7` — this reviewer's own release-gate eval cases.
- Fixtures (now in repo-root `tests/fixtures/`, see P6 fix rounds): `must-accept`/`must-reject` (R17 pair), `seeded-defect-skill`
  (C2 positive control), `clean-skill` (C2 negative control).
- Fixed during build: `revise_support.py verify` compared a root-qualified
  changed-path set against bare item paths and could never report
  `postconditions_hold: true`; now compares bare root-relative paths.
  `mode-revise.md`'s documented `propose` flags (`--target`/`--item`)
  did not match the script's actual flags (`--root`/`--items`); corrected.

### P6 fix rounds (still 0.1.0, pre-release)

Round 1 (F1–F14):

- Bounded, scope-checked directory walks in `report_facts.py` (a backticked
  `/`, `/home` or `/mnt/d` no longer hangs the reporter); per-span inline-code
  classification of directive lines; exact-case entrypoint fact; BOM-tolerant
  frontmatter; `env_var_path_candidates` independent of `dangling`;
  `--eval-dir` inventory; `--plugin-validate` fact wrapping
  `claude plugin validate`.
- New rule N15 (validate plugin structure with the official tool); rule
  coverage 49/49; `mode-review.md` step 3 has a 60 s wall-clock bound that maps
  a non-return to UNAVAILABLE; `audit`/`check` named as review synonyms.
- G1 normal-review reference budget: **24,236 bytes** (budget 25,600).
- License: **MIT** (`LICENSE`, both `plugin.json`, SKILL.md frontmatter, README,
  lineage).

P6 round 3 (NEW-7..NEW-11, C5; version stays 0.1.0, unreleased):

- NEW-7: `tools/run_evals.py` stages fixtures at `<plugin>/_eval_fixtures/`,
  outside the read-blocked `evals/`, via a new `{{FIXTURES_DIR}}` placeholder
  (`{{EVALS_DIR}}` kept for non-model-facing use); C7 fixtures moved to
  `tests/fixtures/c7-*`; `verify_staged()`, README and `rules-evals.md` updated.
- NEW-8: SKILL.md "Running the scripts", `mode-review.md` and `mode-revise.md`
  prescribe one absolute-path `python3 "<SKILL_DIR>/scripts/<x>.py"` command
  (no `cd`/`ls`/chaining/`timeout`). `report_facts.py` gains `--deadline-sec`
  (default 60) and emits an all-UNAVAILABLE report on expiry. G1 is now
  **24,335 bytes** (budget 25,600).
- NEW-9: C2 grader re-keyed to the rubric's rule IDs; rule-ID self-labels
  removed from the seeded-defect fixture. NEW-10: C6 `runs: 3`, observable
  criteria, the human-only install-cache step moved to the README. NEW-11:
  runner strips `/mnt/*` from PATH and flags errored / 0-turn runs. C5 now
  requires naming `rules-core.md` and quoting real reporter output, so a
  plugin-less baseline cannot pass; C1 requires the scripts to have run.

P6 round 4 (C3-R4, NEW-12..NEW-14; version stays 0.1.0, unreleased):

- C3-design/C3-R4: `c3-revise-without-consent` rewritten as a complete
  single-turn case (proposal with `proposal_id` + APPROVE grammar + zero
  writes); graders no longer depend on a second user turn.
- NEW-12: C2 graders list U03, N13 (DrvFS 0o777), U04 and R06 as sanctioned
  findings; the fixture is unchanged so fixture hashes stay stable.
- NEW-13: `lineage.yaml` `fact_reporter_version` 2.0.0 -> 2.1.0, matching
  `report_facts.py` REPORTER_VERSION (bumped in round 3 by `--deadline-sec`).
- NEW-14: `tools/run_evals.py --keep-temp` passes `--keep-temp` through to
  `claude plugin eval` so run traces survive.

Round 2 (NEW-1..NEW-5, F15):

- Eval suite stays at the repo root, out of the shipped plugin.
  `claude plugin eval` requires the eval dir inside the plugin root, so the
  ineffective `experimental.evals` manifest field is removed and
  `tools/run_evals.py` stages a plugin copy (with `evals/` and fixtures inside),
  running one case per invocation (`--case`, `--all`, `--dry-run`).
- Test fixtures moved out of the shipped plugin to repo-root `tests/fixtures/`;
  the installed plugin now contains exactly one `SKILL.md`. New
  `tests/test_scripts.py` self-tests, including a symlink-cycle case built in a
  temp dir at test time (the repository contains no symlinks).
- Directory walks use `os.walk(followlinks=False)` instead of
  `Path.rglob`, so symlink-cycle safety no longer depends on Python 3.13.
- README: Codex install uses `codex plugin add`; `<git-url>` placeholders
  replaced with `https://github.com/emilwu/skill-reviewer`; `homepage` /
  `repository` added to both plugin manifests.
- C3 grader now requires a `revise_support.py propose` proposal_id and the
  `APPROVE <proposal_id>: <item-id>` grammar, so a generic refusal (which a
  no-plugin baseline also produces) no longer passes.
