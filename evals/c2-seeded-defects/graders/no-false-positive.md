---
type: llm
weight: 1
---

This grader checks the same run's handling of legitimate content: the
response must not flag ordinary workflow prose, a documentary backtick
mention of another path, or a present-and-linked reference file as a
defect.

The fixture `seeded-defect-skill` has exactly five real seeded defects
(each may be cited under any of the listed rule IDs):

1. Dangling reference `references/missing-file.md` — U06 or N2.
2. Hardcoded `${CLAUDE_PROJECT_DIR}/scripts/run.sh` path — N1 or R13.
3. Unbounded `allowed-tools` grant including `Write` and `Bash` — R05 or
   N24 (U04 as a related schema finding).
4. A long inline procedure repeated twice verbatim — R11 or N7.
5. `references/unreferenced.md` on disk but never named or linked — N2 or
   U06 (R06 as related).

Sanctioned additional findings (NOT false positives; do not penalize):
U03 (the fixture `description` states no trigger phrase), N13 at
INFO/CAUTION (file mode 0o777 on WSL/DrvFS), U04 and R06 as related IDs
next to a correct finding above. Citing an extra related rule ID alongside
a correct one is not a false positive.

Pass if every reported finding is one of the five real defects or a
sanctioned additional finding, and the response does not manufacture a
defect from boilerplate language, the `name` field, or ordinary prose.
Fail only if it reports a defect outside these two lists.
