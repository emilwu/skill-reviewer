---
max_turns: 10
allowed_tools: [Read, Glob, Grep, Skill]
runs: 3
---

You are being invoked as an installed plugin skill, not from an in-place
source checkout. Describe, in your own words and without inventing a
specific absolute path you have not actually observed, how you located
your own `SKILL_DIR` for this invocation, and confirm your skill body
contains no runtime-specific literal such as `${CLAUDE_PROJECT_DIR}` or
any other host-environment-variable form that would not work on a
different agent runtime.
