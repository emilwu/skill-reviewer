#!/usr/bin/env python3
"""Read-only resolver: find Skill(s) by logical name across standard
discovery roots on both runtimes, plus any caller-supplied root.

Reports every match found; never auto-picks when ambiguous. No writes,
no mutation, no execution of anything discovered.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any, Iterable


def parse_name(skill_md: Path) -> str | None:
    try:
        lines = skill_md.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return None
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        stripped = line.strip()
        if stripped == "---":
            break
        if stripped.startswith("name:"):
            value = stripped.split(":", 1)[1].strip()
            return value.strip("'\"")
    return None


def standard_roots() -> list[tuple[str, Path]]:
    home = Path.home()
    cwd = Path.cwd()
    roots: list[tuple[str, Path]] = [
        ("claude-project", cwd / ".claude" / "skills"),
        ("claude-user", home / ".claude" / "skills"),
        ("codex-project-agents", cwd / ".agents" / "skills"),
        ("codex-project-agents-parent", cwd.parent / ".agents" / "skills"),
        ("codex-user-agents", home / ".agents" / "skills"),
        ("codex-user-legacy", home / ".codex" / "skills"),
    ]
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        roots.append(("codex-home-skills", Path(codex_home) / "skills"))
        roots.append(("codex-home-plugin-cache", Path(codex_home) / "plugins" / "cache"))
    claude_config_dir = os.environ.get("CLAUDE_CONFIG_DIR")
    if claude_config_dir:
        roots.append(("claude-config-dir-plugin-cache", Path(claude_config_dir) / "plugins" / "cache"))
    roots.append(("claude-user-plugin-cache", home / ".claude" / "plugins" / "cache"))
    return roots


def walk_entries(root: Path) -> Iterable[Path]:
    """Yield every entry under root without following symlinked directories.

    Interpreter-independent (os.walk followlinks=False): a symlinked
    directory is yielded as an entry but never descended into, so a
    symlink cycle cannot loop on any supported Python version.
    """
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        for name in dirnames + filenames:
            yield Path(dirpath) / name


def find_matches(name: str, roots: list[tuple[str, Path]]) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for label, root in roots:
        if not root.exists() or not root.is_dir():
            continue
        for skill_md in (p for p in walk_entries(root) if p.name == "SKILL.md"):
            found_name = parse_name(skill_md)
            if found_name == name:
                matches.append({
                    "root_label": label,
                    "root": root.as_posix(),
                    "skill_md": skill_md.absolute().as_posix(),
                    "skill_dir": skill_md.parent.absolute().as_posix(),
                })
    return matches


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--name", required=True, help="Logical Skill name to resolve")
    ap.add_argument("--root", action="append", default=[], help="Additional caller-supplied root; repeatable")
    args = ap.parse_args()

    roots = standard_roots()
    for i, raw in enumerate(args.root):
        roots.append((f"caller-supplied-{i}", Path(raw).expanduser().absolute()))

    matches = find_matches(args.name, roots)
    result = {
        "schema_version": "1",
        "requested_name": args.name,
        "searched_roots": [{"label": l, "path": r.as_posix(), "existed": r.exists()} for l, r in roots],
        "matches": matches,
        "ambiguous": len(matches) > 1,
    }
    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    if not matches:
        print(f"locate_skill: no match for name={args.name!r} in searched roots", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
