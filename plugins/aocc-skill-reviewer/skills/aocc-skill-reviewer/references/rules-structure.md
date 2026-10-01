# Rules — Structure

Load for every full review, and for a revise fix touching schema,
descriptions, or claims. `report_facts.py` supplies the facts; this file
supplies interpretation and fix pattern only.

| ID | Statement + fix | severity |
|---|---|---|
| U01 | Exact-case `SKILL.md`; first content is valid YAML frontmatter then a non-empty body. Fix: correct entrypoint casing/delimiters, preserve content; unsupported YAML → unavailable, not a guessed pass. | BLOCK |
| U02 | `name`: 1–64 lowercase ASCII alphanumeric/single-hyphen, no edge/doubled hyphen, equals its directory basename. Fix: propose a coordinated rename + reference updates. | BLOCK |
| U03 | `description`: 1–1,024 chars, states capability+trigger, key use case first. Vague trigger alone (not length/presence) is CAUTION. Fix: rewrite preserving scope/near-miss exclusions; remeasure. | BLOCK missing/oversize; CAUTION vague |
| U04 | Optional `license`/`compatibility`(1–500 chars)/`metadata`(string map)/`allowed-tools`(space-separated) obey schema when present. Fix: normalize; don't invent catalog-only fields. | BLOCK malformed; CAUTION runtime ambiguity |
| U05 | Runtime targets declared consistently; six-field portable core (name, description, license, compatibility, metadata, allowed-tools) distinguished from any extension; standalone package sets `metadata.portability-scope: standalone`. Fix: keep the six-field core; isolate adapter metadata outside frontmatter. Codex tolerating a Claude-only key is not evidence of any effect there. | BLOCK actually-rejected target; CAUTION unverified effect |
| U08 | Every claimed tool/interpreter+version/OS/network/filesystem prerequisite is declared and actually available to start. Fix: add the declaration or bundle/remove the dependency; preserve offline capability where claimed. | BLOCK cannot start; CAUTION incomplete evidence |
| R08 | Claims agree with actually-delivered behavior, not just the source tree — "runs on Codex" needs **install-cache** evidence, not an in-place directory-marketplace run (different executing path). Fix: correct the claim or the package, then get matching-mode evidence; never cross-infer between runtimes. | BLOCK contradicted claim; CAUTION unverified claim |
| N4 | Reserved-name/XML-tag restrictions apply only to the specific documenting surface. Fix: apply the exact target rule only; don't reject a portable name for an unrelated restriction. | BLOCK documented target rejection; otherwise INFO |
| N5 | Prefer third-person description when the target platform recommends it. Fix: rewrite only if clarity improves. | INFO |
| N6 | Consider (don't mandate) an action/gerund name. Fix: propose a rename only with a concrete ambiguity + migration cost. | INFO |
| N12 | Treat the six shared fields as the portable core; any Claude-only field (`arguments`, `argument-hint`, `disable-model-invocation`, `user-invocable`, `model`, `effort`, `agent`, `background`, `hooks`, `shell`, `when_to_use`, `paths`) is an enhancement with its own cost, not a silent requirement. Fix: keep the six-field core for upload paths; parse mode from free text instead of `arguments` unless the caller has explicitly accepted the tradeoff. | CAUTION extension dependency; BLOCK rejected claimed upload |
| N17 | Date mutable product claims; flag an undated claim contradicted by current behavior. Fix: add a source/access date; replace demonstrated-stale claims. | CAUTION contradicted; INFO not refreshed |
| N18 | Use one stable term per input/mode/outcome/path across body and references. Fix: normalize only where behavior actually differs between the two terms. | CAUTION material ambiguity; otherwise INFO |

## Six-field upload boundary (U05/N12)

Uploading to claude.ai/the Skills API, or packaging with `package_skill.py`,
restricts frontmatter to exactly `name`, `description`, `license`,
`compatibility`, `metadata`, `allowed-tools`. Any other field on that upload
path is BLOCK under U05, not just an N12 CAUTION.
