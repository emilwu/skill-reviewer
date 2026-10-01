# Rules — Portability (install/runtime evidence)

Load for every review claiming cross-runtime portability, every self-review
of this package, and a revise fix touching packaging/paths.

| ID | Statement + fix | severity |
|---|---|---|
| R12 | State tested coverage per runtime/mode separately (Claude interactive, Claude headless, Codex CLI); install ≠ listing ≠ execution — never infer one from another. Fix: add a runtime/version/transport/workdir matrix; test the actually-installed path or narrow the claim. | BLOCK broken claimed mode; CAUTION untested mode |
| R14 | Declare one master; each copy is byte-identical (hash-verified) or a declared fork with owner/rationale/update policy. A symlink is not a survivable "copy": Claude drops an escaping link (or keeps it dangling under `git-subdir`); Codex drops **every** symlink at install, in-package ones included. Fix: use physical byte-copies, never symlinks, for anything that must survive install on both runtimes. | BLOCK undeclared drift or missing required copy |
| N1 | Every bundled path is anchored to SKILL_DIR (self-located, provider-neutral prose) or the correct runtime variable — a body claiming Codex support must not depend on `${CLAUDE_*}` substitution (Codex doesn't substitute; the literal leaks). Fix: use the "paths are relative to this SKILL.md's directory" anchor sentence; quote paths. | BLOCK unresolved required path; CAUTION untested |
| N13 | Package hygiene: no top-level `bin/` (refused by claude.ai/Cowork); forward-slash paths; **no symlinks anywhere**; `name` set explicitly (else a marketplace install may name it after the cache dir); no mutable state under a plugin-cache path. Fix: physical files only; explicit `name`; write outputs to the caller's workspace, never plugin storage. | BLOCK missing/escaping dependency; CAUTION packaging risk |
| N14 | State one version/release policy; bump the manifest version when shipped content changes. Fix: matched explicit versions in both manifests, or a deliberate SHA-derived scheme. | CAUTION; BLOCK conflicting identities across manifests |
| N21 | Use provider-neutral language ("the model"); name a product only where behavior genuinely differs by product. Fix: replace product-specific instructions with neutral language; keep runtime evidence in a clearly scoped branch. | CAUTION wording; BLOCK nonportable operative dependency if dual-runtime is claimed |
| N22 | A portability claim needs resolution tested from an **install cache**, clean environment, unrelated cwd, on each claimed runtime — not an in-place directory-marketplace source and not a project-local run alone. Fix: capture the actual loaded SKILL.md path + output facts from a real install. | BLOCK failed required resolution; CAUTION unverified claim |
| N23 | Dual manifests (`.claude-plugin/` + `.codex-plugin/`) and both marketplace files must agree on name/version/resolved-source; omit a root `plugin.json` unless its precedence vs the two has actually been tested for this package. Fix: keep both manifests in sync (CI check); don't add a root manifest speculatively. | BLOCK inconsistent identity across manifests |

## Known runtime asymmetries (facts — cite, don't re-derive)

- Claude: a directory-marketplace install **executes from the source dir**
  (in place, re-read each session); a git/`git-subdir` source install
  **executes from the cache copy**. These are different properties.
- Claude prepends `Base directory for this skill: <abs dir>` to the loaded
  body (SKILL_DIR signal). Codex's listing gives the model the SKILL.md's
  absolute path (`plugin:skill` namespaced) — its own SKILL_DIR signal.
  Codex has no `${CLAUDE_*}`-style body substitution.
- Exec bits are preserved on every tested install path on both runtimes.
  Windows has no exec bit; archive/zip-source mode handling is untested —
  invoke scripts via explicit `python3 <path>` anyway, as portability
  insurance, not because the bit is known to be lost.
- Both CLIs reject `file://`/`git://` marketplace sources; localhost
  smart-http (Claude) / dumb-http (Codex) works, as does the documented
  hosted `owner/repo`/HTTPS path. A root-as-plugin (`source: "./"`) install
  copies the **whole** repo root into the cache on both runtimes — why
  Layout A scopes the marketplace entry to `./plugins/aocc-skill-reviewer`.
