# Rules — Appendices (provenance, disputes, open policy)

Load only on a dispute, a provenance question, a build/maintenance decision,
or an unresolved Q2–Q6 policy question. Not part of a normal review.

## Lineage

Rules in this package descend from `agent-Em/outbox/skill-structure-audit-criteria.md`
(baseline, 2026-09-22, 27 criteria) as updated by
`agent-Em/outbox/skill-reviewer-policy-v1.md` (Policy v1.0, 49 active rows:
16 KEPT, 9 CHANGED, 0 RETIRED, 2 SCOPED-OUT, 24 NEW) and ratified by Emil on
2026-10-01 (`agent-chord-team/project-aocc-skill-reviewer-2026-10-01/ratification-2026-10-01.md`).
Full evidence grading per rule lives in the Policy document and the
dual-runtime evidence pack v3 (`evidence-pack.md` in the same directory) —
not reproduced here, because this package carries no runtime dependency on
the team repository (R13).

## Scoped out (not active in this package)

- **R01** (catalog five-field contract) — team-catalog-only; this package
  uses only the open six-field core.
- **R03** (catalog no-orchestration/type gate) — team-catalog-only; a
  standalone workflow Skill is legitimate (R04).

## Open decisions still OPEN at build time (not ratified away)

- **Q5** (ToC threshold authority): no universal mandate; `rules-context.md`
  N3 keeps both the >100 and >300 figures as advisory, not a hard rule.
- **Q3/Q4 extension**: whether to ever add Claude-only `arguments`/
  `argument-hint` remains closed for this build (six-field core only, per
  ratification); revisit only with an explicit caller decision.

## Known hedges (do not upgrade these to settled)

- Codex plugin-installed self-locate/plugin-root reach (B2) is inferred from
  the Codex skill listing + vendor precedent, not observed end-to-end on a
  real-home install. Deferred to a later authorized round-trip (ratification
  record, P6).
- HTTPS/GitHub `owner/repo`/ssh marketplace install was not exercised during
  policy authoring (only localhost http was); treat as the documented path,
  not a verified one, until this package's own install test (README) runs
  against a real remote.
- Whether Codex's `allowed-tools`, `license`, `compatibility`, or `metadata`
  fields have any runtime effect is unverified; treat them as tolerated-but-
  unproven on Codex.

## Why this file is separate from the rule families

Policy §6 owns this split; it keeps the normal-review activation set (core +
structure + context + portability + safety + mode-review) under the
ratified G1 ≤~25 KB budget by excluding provenance/evidence-grade prose and
the eval-release gate from every ordinary review. Loading this file costs
nothing on a normal review precisely because nothing in the review procedure
links to it unconditionally.
