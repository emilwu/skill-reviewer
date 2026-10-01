---
name: seeded-defect-skill
description: Fixture Skill with deliberately seeded defects, used only by this reviewer's C2 eval case. Not a real tool.
allowed-tools: [Read, Write, Bash]
---

# seeded-defect-skill

This body intentionally references `references/missing-file.md`, which does
not exist.

It also hardcodes `${CLAUDE_PROJECT_DIR}/scripts/run.sh` as an absolute,
runtime-specific path. A support file sits alongside this one on disk that
this body never names or links anywhere.

The frontmatter above grants `Write` and `Bash` with no bound on target,
purpose, or failure behavior.

Below is a long inline procedure that should be extracted to a script
instead of living in the always-loaded body:

```
step 1: list files
step 2: for each file, read contents
step 3: for each file, compute a hash
step 4: for each file, compare the hash to the previous run
step 5: for each file, if the hash changed, mark it dirty
step 6: for each file, if dirty, append it to the changed-set
step 7: for each file, if not dirty, append it to the unchanged-set
step 8: once all files are processed, print both sets
```

The exact same eight-step block appears a second time immediately below:

```
step 1: list files
step 2: for each file, read contents
step 3: for each file, compute a hash
step 4: for each file, compare the hash to the previous run
step 5: for each file, if the hash changed, mark it dirty
step 6: for each file, if dirty, append it to the changed-set
step 7: for each file, if not dirty, append it to the unchanged-set
step 8: once all files are processed, print both sets
```
