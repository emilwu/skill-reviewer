# Rules — Context, Size, JIT, Extraction

Load for every full review, and for a revise fix touching architecture,
size, JIT, or script extraction.

## Rules

| ID | Statement + fix | severity |
|---|---|---|
| U06 | Required support is directly reachable from SKILL.md, one explicit trigger each; a reference-must-require-reference chain defeats JIT. Fix: direct link+trigger per file; flatten chains (optional cross-links between references are fine). | CAUTION depth; BLOCK if required material is actually missing |
| U07 | Apply the size ladder below; measure body and reference cost separately. Fix: split out coherent detail, dedupe, remeasure. | BLOCK ladder breach; CAUTION token guidance breach |
| R06 | Split references by coherent topic, loaded only on an explicit trigger — splitting alone isn't JIT if everything still loads together. Fix: add a direct load-trigger map; dedupe body/reference text. | CAUTION; BLOCK if a required rule is unreachable |
| R09 | The trigger (name+description) stays discoverable without duplicating the body in an always-loaded surface (identity file, router list). Fix: shorten the trigger; point, don't inline. | CAUTION; BLOCK on demonstrated unreachability |
| R11 | A "must fire"/exact-enforcement claim needs an executable carrier, not prose. Contextual/subjective classification stays prose. Fix: extract the deterministic part to `scripts/`, keep a short invocation note; the script stays facts-only — you assign the verdict. | BLOCK false must-fire claim; CAUTION extraction opportunity |
| R19 | Reach is justified per runtime (Claude `disable-model-invocation`/`user-invocable`; Codex `agents/openai.yaml` `allow_implicit_invocation`). One skill = one reach for both modes. Fix: document the choice/cost; a router claiming full coverage needs a set-equality check. | CAUTION; BLOCK on proven unreachability |
| R20 | Classify every `NEVER`/`MUST NOT`/all-caps directive as hard guardrail, redundant twin, or positive-rewrite candidate before touching it; never delete a guardrail mechanically. Fix: keep the boundary + positive rationale; remove only a confirmed twin. | CAUTION; BLOCK on weakened safety |
| N2 | Every independently-needed reference links directly from SKILL.md; no reference is the *sole* route to another. Fix: add the missing direct link. | CAUTION |
| N3 | References >~100 lines should get a heading ToC (advisory — platform says >100, skill-creator >300; neither is a hard upstream rule). Fix: add a ToC; don't cite either number as a limit. | INFO; CAUTION if far past both |
| N7 | Match rigidity to fragility: script exact/fragile sequences, keep judgment where real choices matter. Fix: extract the bounded part; keep rationale for the rest. | CAUTION; BLOCK if a claimed exact gate has no carrier |
| N8 | Scripts handle expected errors explicitly (no silent wrong-default fallback); explain non-obvious constants. Fix: explicit unavailable/error output; name constants. | CAUTION; BLOCK on silent false success |
| N11 | Report three numbers separately: Claude listing (always-on), SKILL.md-body (on-invoke, via `claude plugin details`), and actual reference bytes/lines — `details` is body-only by design. Fix: capture `details` + per-reference byte/line count; compare before/after on both axes. | INFO missing estimator; CAUTION measured bloat |
| N16 | Codex's listing budget (≤2% context or 8,000 chars) is an aggregate across all installed skills, not a per-skill quota. Fix: shorten this skill's own trigger; report observed truncation if supplied. | CAUTION measured truncation; INFO unavailable |
| N19 | Classify every edit: keep / delete / move-to-reference / move-to-asset / extract-to-script, each with its own rationale. | INFO |
| N20 | Near a size limit, reduce by relevance/loading-stage first, not mechanical splitting. Fix: apply the ladder; keep coherent topics and any mandatory safety entrypoint intact. | CAUTION eager bloat; BLOCK only on inherited size breach |

## Size and JIT ladder

| Surface | Ceiling | Outcome |
|---|---|---|
| SKILL.md | 0–199 ideal; 200–299 acceptable; ≥300 | BLOCK ≥300 for standalone release |
| Each reference file | <500 lines | BLOCK ≥500 |
| Total skill-dir text | ≥1,500 lines | CAUTION after assessing loaded portions, not a file failure |
| Description | 1–1,024 chars | BLOCK missing/oversize |
| compatibility | 1–500 chars if present | BLOCK malformed |
| Claude listing (description+when_to_use) | 1,536-char truncation | front-load the trigger; not license to exceed the description limit |
| Codex listing | ≤2%/8,000 chars, aggregate | shorten own trigger; never a per-skill quota |
| Activated instruction tokens | <5,000 recommended | CAUTION when measured over; no invented hard BLOCK |
| Reference depth | one direct level from SKILL.md | see U06/N2 |

## Script-extraction signals (operationalize R11 — CAUTION triggers, not automatic verdicts)

| Signal | Heuristic | Decision |
|---|---|---|
| Deterministic mandatory validation | inline schema/count/hash/set comparison, or "must fire" claim | MUST script if claimed exact |
| Repeated computation | same ≥8-line block in ≥2 places | SHOULD extract to one parameterized script |
| Fragile exact sequence | ≥3 dependent parse/escape/normalize steps | SHOULD script; MUST if sold as a must-fire gate |
| Long inline program | fenced block ≥20 lines, or ≥40 combined lines in the entrypoint | SHOULD inspect for extraction |
| Long table as data | ≥20 rows or ≥2,000 bytes AND exact lookup use | SHOULD move to asset + scripted query |
| Parsing/validation recipe | regex/YAML/JSON parse, path normalize, checksum, set-diff in prose | Try an official tool first (R10, `rules-core.md`), then custom code for the named gap |
| Boilerplate template | repeated output template with substitutions | SHOULD move to `assets/` |
| Lookup-only knowledge | definitions/examples used in one branch | MOVE to references |
| Redundant basic explanation | adds no task-specific decision value | consider DELETE, with explicit approval |

`report_facts.py` emits code-block spans/hashes, table counts, and directive
candidates as raw facts only — you classify.
