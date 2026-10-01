# Mode — Review

Read-only. Do not write anything under the target in this mode.

1. Resolve the target with `python3 "<SKILL_DIR>/scripts/locate_skill.py"
   --name <skill-id> [--root ...]` (one command, absolute path; no `cd`/`ls`). Ambiguous (>1 match) → ask the user which one; do not guess.
2. Snapshot the target before reading further (`scripts/report_facts.py`
   records hashes as part of its output — treat this as the pre-review
   snapshot too, in case the caller later wants revise mode).
3. Run `python3 "<SKILL_DIR>/scripts/report_facts.py" --skill-id <id>
   --master <path> [--copy ...] [--search-root ...]` as ONE command — no
   `cd`, `ls`, chaining, or `timeout` prefix — and read its full output.
   The script bounds itself (`--deadline-sec`, default 60); a report with
   `deadline_exceeded: true`, or a failed/denied run, makes the entire
   script-sourced fact family UNAVAILABLE per `rules-core.md`'s
   aggregation contract — do not guess facts, and say so in the review.
4. Load the applicable rule families named in SKILL.md's review-mode list.
   Load *all* of them for a full review — the incremental cost is honest,
   not something to shortcut.
5. For each rule, compare the reporter's facts (where `check_type: script`)
   or your own reading of the target (where `check_type: text`/`judgment`)
   against the rule's statement. Emit one finding per real defect, with
   `related_rule_ids` for any other rule the same defect also violates —
   never duplicate.
6. Aggregate per `rules-core.md`'s precedence
   (UNAVAILABLE > BLOCK > CAUTION > PASS) and report the verdict with every
   finding, not just the aggregate.
7. If any BLOCK/CAUTION finding is fixable, offer to switch to revise mode —
   but do not generate a proposal until the user asks for it.
8. Re-run the reporter's hash facts (or re-read the hashes) and confirm
   nothing under the target changed since step 2. Report a consent-gate
   breach and stop if anything did.

A revise request with no current valid review, or whose review has expired
(target changed since), re-runs this procedure first.
