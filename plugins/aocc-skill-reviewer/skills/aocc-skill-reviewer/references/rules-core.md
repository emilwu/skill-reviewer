# Rules — Core

Read this on every invocation, after SKILL.md. It defines the profile, the
finding contract, and the rules with no dedicated family file. Full
provenance/evidence-grade detail lives in `rules-appendices.md`, loaded only
on dispute.

## Profile

External standalone only. Both Claude Code and Codex CLI. Git-remote
distribution. One skill, two modes. `metadata.portability-scope: standalone`
for the reviewer package itself (`P`). A reviewed Skill (`S`) may be any
profile; apply only the rules whose `target` covers it.

## Rules owned by this file

| ID | Statement | severity | Fix pattern |
|---|---|---|---|
| R02 | Separate stable rationale (identity/methodology), reusable procedure (the Skill body), and per-task state (task/caller input) by lifetime and loading need. | CAUTION; BLOCK unsafe runtime coupling | Move task records outside instructions; keep enough local rationale for standalone use. |
| R04 | A standalone Skill may legitimately be a workflow Skill. Team/catalog-only knowledge-module restrictions do not apply to an external Skill. Mutation still requires R15 consent. | BLOCK on consent bypass only | Preserve review/revise phases; do not reject a workflow Skill for being a workflow. |
| R07 | One logical Skill resolves to one identity. An exact invocation-namespace collision (same `plugin:skill`, same caller-declared scope) BLOCKs; semantic/topic overlap alone is CAUTION, needing judgment about triggers, output, and audience before proposing a merge or rename. | BLOCK exact collision; CAUTION overlap | Record the plugin:skill id and master; clarify distinguishing triggers/output before any merge/rename proposal. |
| R10 | Before recommending or building custom checking logic, check whether an official tool already covers it (`claude plugin validate`, `claude plugin details`, `/doctor`). Keep this reporter only for the named gap it fills: identity/reference/size/extraction facts no official tool reports. `/skill-doctor` is usage telemetry, not a structure validator — never cite it as covering a structural rule. | CAUTION | Add the official check as a supplementary observation; do not claim it replaces the reporter. |
| R13 | A standalone target's runtime inputs must be bundle-local, explicit caller-supplied inputs, or declared external prerequisites. An operative dependency on an originating repository, team wiki/search/memory service, team script, team-root variable, or repository-root discovery is BLOCK. A documentary mention that such a thing is *not* required is fine. | BLOCK operative dependency | Inline the required method or rewrite the path to SKILL_DIR/caller input; historical/provenance mentions may stay. |

## Finding contract

Every finding carries: `finding_id`, `rule_id`, `related_rule_ids` (emit ONE
finding with multiple related IDs when one defect violates overlapping
rules — never duplicate), `target` (S/P/S+P), `status`
(pass/fail/not-applicable/unavailable), `severity` (BLOCK/CAUTION/INFO),
`evidence`, `affected_paths`, `fix_pattern`, `policy_status` (B/Δ/J),
`open_decision` (Q-ref if the rule is still OPEN per `rules-safety.md`
Q2/Q4 or elsewhere).

## Aggregation

Unavailable required evidence → **INCOMPLETE**. Else any established
**BLOCK** → BLOCK. Else any **CAUTION** → CAUTION. Else **PASS**. A
dangerous-action BLOCK is never hidden inside an INCOMPLETE summary — report
both. Optional missing estimators/validators are INFO when direct evidence
already covers the property; a missing *required* property is unavailable.
No debt-grandfathering mechanism exists here; an external caller may attach
its own historical baseline, but a violation never silently disappears. A
proposal-only Q-linked requirement cannot alone establish a BLOCK before the
caller ratifies it. PASS is never consent to revise. Reports are
human-consumed; stable IDs support review, not an automatic decision router.

## Identity and scope

Identify the logical Skill, its master, and only the copies the caller
explicitly supplied or that `locate_skill.py`/`report_facts.py --search-root`
found by name match. Never auto-scan home directories beyond declared roots.
Count logical Skills, not files.

## Anti-criteria (do not do these)

1. A zero-finding run on one corpus proves only that corpus, not discriminating
   power (see R17 in `rules-safety.md`'s neighbor table).
2. Never silently retire a BLOCK rule because it is inconvenient; if genuinely
   out of scope, say so and name the scoping reason.
3. A script producing output is not a verdict; you assign every verdict.
4. Style difference alone (declaration style, naming convention) is not a
   defect; judge reachability and consistency, not sameness.
