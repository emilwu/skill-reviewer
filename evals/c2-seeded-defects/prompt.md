---
max_turns: 15
allowed_tools: [Read, Glob, Grep, Bash(python3:*), Skill]
runs: 3
---

Review the Skill named `seeded-defect-skill`, provided in the eval fixtures at
`{{FIXTURES_DIR}}/seeded-defect-skill/`. Report
every defect you find with its rule ID and exact evidence (path/line).
