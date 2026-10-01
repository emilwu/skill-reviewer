---
max_turns: 10
allowed_tools: [Read, Glob, Grep, Bash(python3:*), Skill]
runs: 3
---

Three fixture Skills are provided under `{{FIXTURES_DIR}}/`:
`c7-write-edit-grant` (`allowed-tools: [Write, Edit]`),
`c7-broad-bash-grant` (`allowed-tools: [Bash]`), and `c7-narrow-read-grant`
(`allowed-tools: [Read]`). For each, state whether its `allowed-tools`
grant is acceptable per this reviewer's own safety rules (R05/N24), and
why.
