---
type: llm
weight: 1
---

The fixture `seeded-defect-skill` has five seeded defects the response
must identify by rule ID and exact path/evidence:

Rule IDs below are the shipped rubric's actual IDs. A finding counts as
correct if it cites ANY ID listed for that defect (a response may add a
related ID) together with the right path/evidence:

1. A dangling reference to `references/missing-file.md` (does not exist)
   — U06 or N2 (reachability / direct-link rules).
2. A hardcoded `${CLAUDE_PROJECT_DIR}/scripts/run.sh` path in the body — a
   portability defect: N1 or R13.
3. An `allowed-tools` frontmatter grant including `Write` and `Bash` with
   no bound on target/purpose/failure — a safety defect: R05 or N24
   (U04 may appear as a related schema finding).
4. A long inline step-by-step procedure repeated twice verbatim — an
   extraction/duplication candidate: R11 or N7.
5. `references/unreferenced.md` exists on disk but is never named or
   linked from the body — an unreferenced-file defect: N2 or U06 (R06 may
   appear as related).

A full-credit response names all five with correct rule IDs and does not
invent a defect this fixture does not have. The fixture body carries no
rule-ID hints; IDs must come from the response reading the rubric.

Sanctioned additional findings (NOT false positives; do not penalize, and
do not require them): U03 CAUTION (the fixture `description` states no
trigger phrase, which the shipped rubric requires reviewers to flag), N13
at INFO/CAUTION (the fixture file mode is 0o777 on WSL/DrvFS), and U04/R06
as noted above. Any other reported defect that does not exist in this
fixture (e.g. flagging the `name` field, or ordinary prose) is a false
positive. Partial credit for 3-4 of the five found correctly with no false
positives; fail if fewer than 3 are found, or if the response reports a
non-sanctioned defect that does not exist in this fixture.
