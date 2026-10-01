---
type: llm
weight: 1
---

Pass only if the response:

- Names the observed source of `SKILL_DIR` for this invocation (for example
  the "Base directory for this skill" line, or the directory of the active
  `SKILL.md`) and does not assert a hardcoded guess or an absolute path it
  did not observe.
- Contains no host-environment-variable literal presented as a working path:
  no `${CLAUDE_PROJECT_DIR}`, `$CLAUDE_*`, `${CODEX_*}`, `%VAR%` or `$env:`
  form, and no `~/.claude/...` or `~/.codex/...` path offered as universal.
- Resolved `SKILL_DIR` on the first attempt, without being told where its
  own skill directory is.

Fail if any environment-variable literal appears as an instruction, or the
`SKILL_DIR` source is unstated.
