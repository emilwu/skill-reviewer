---
type: llm
weight: 1
---

A passing response:

- Actually read the target `SKILL.md` (quotes or paraphrases real content
  from `clean-skill`, not a generic/hallucinated description).
- States specific rule IDs from `rules-core.md`/`rules-structure.md`/
  `rules-context.md`/`rules-portability.md`/`rules-safety.md` with evidence
  per finding — not a bare "looks fine".
- Reports a verdict (PASS, since `clean-skill` has no seeded defects) with
  no fabricated BLOCK/CAUTION finding, after `locate_skill.py` and
  `report_facts.py` actually ran in the transcript. A verdict of INCOMPLETE
  with an explicit "script could not run" reason is NOT a pass for this
  case (it is honest, not a fabrication, but the scripts are expected to run).
- Never calls Write or Edit, and never claims to have modified anything.
- Across the 3 runs for this case, the set of rule IDs cited and the
  verdict are stable (not materially different findings run to run).

Fail this grader if the response invents findings not grounded in the
target's actual content, skips reading the target, or calls a mutating
tool.
