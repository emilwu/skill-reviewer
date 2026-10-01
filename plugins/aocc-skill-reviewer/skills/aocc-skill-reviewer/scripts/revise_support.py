#!/usr/bin/env python3
"""Mechanical pieces of the revise-mode consent protocol (Policy S7).

Subcommands:
  snapshot        Hash/mode/type manifest of one or more target roots.
  propose         Build a canonical proposal + sha256 proposal_id from a
                   snapshot and an items JSON file. Never writes the target.
  check-approval  Parse `APPROVE <proposal_id>: <item-id>[, ...]` against a
                   proposal file. Reports grammar/id/item-set facts only —
                   the caller still decides whether the approval text is a
                   durable, independently-establishable consent record.
  drift-check     Re-snapshot the proposal's bound roots and report any
                   path/hash/type/mode difference since the proposal was built.
  verify          Compare a post-apply snapshot against a proposal's expected
                   postconditions.

No subcommand mutates any target file. `propose`/`drift-check`/`verify` only
read.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
from typing import Any, Iterable


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_bytes(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def walk_entries(root: Path) -> Iterable[Path]:
    """Yield every entry under root without following symlinked directories.

    Interpreter-independent (os.walk followlinks=False): a symlinked
    directory is yielded as an entry but never descended into, so a
    symlink cycle cannot loop on any supported Python version.
    """
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        for name in dirnames + filenames:
            yield Path(dirpath) / name


def snapshot_root(root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    if not root.exists():
        return entries
    paths = [root] if root.is_file() else sorted(walk_entries(root))
    for p in paths:
        if any(part in {".git", "__pycache__"} for part in p.parts):
            continue
        rel = p.relative_to(root.parent) if root.is_file() else p.relative_to(root)
        if p.is_symlink():
            entries.append({
                "rel_path": rel.as_posix(),
                "type": "symlink",
                "link_target_text": os.readlink(p),
                "mode_octal": None,
                "sha256": None,
            })
        elif p.is_dir():
            entries.append({"rel_path": rel.as_posix(), "type": "dir", "mode_octal": None, "sha256": None})
        elif p.is_file():
            data = p.read_bytes()
            entries.append({
                "rel_path": rel.as_posix(),
                "type": "file",
                "mode_octal": oct(stat.S_IMODE(p.stat().st_mode)),
                "sha256": sha256_bytes(data),
            })
    return entries


def cmd_snapshot(args: argparse.Namespace) -> int:
    roots = [Path(r).expanduser().absolute() for r in args.root]
    manifest = {r.as_posix(): snapshot_root(r) for r in roots}
    json.dump({"schema_version": "1", "roots": manifest}, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


def cmd_propose(args: argparse.Namespace) -> int:
    roots = [Path(r).expanduser().absolute() for r in args.root]
    manifest = {r.as_posix(): snapshot_root(r) for r in roots}
    items = json.loads(Path(args.items).read_text(encoding="utf-8"))
    if not isinstance(items, list) or not items:
        print("propose failed: --items must be a non-empty JSON array of item objects", file=sys.stderr)
        return 2
    for item in items:
        for required in ("item_id", "rule_ids", "action_kind", "paths"):
            if required not in item:
                print(f"propose failed: item missing required field {required!r}: {item}", file=sys.stderr)
                return 2
    core = {
        "schema_version": "1",
        "policy_version": args.policy_version,
        "target_roots": [r.as_posix() for r in roots],
        "snapshot_manifest": manifest,
        "items": sorted(items, key=lambda it: it["item_id"]),
    }
    proposal_id = sha256_bytes(canonical_bytes(core))
    proposal = {**core, "proposal_id": proposal_id}
    json.dump(proposal, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


APPROVE_GRAMMAR = "APPROVE <proposal_id>: <item-id>[, <item-id>...]"


def parse_approval_text(text: str) -> dict[str, Any]:
    text = text.strip()
    if not text.startswith("APPROVE "):
        return {"grammar_ok": False, "reason": f"text does not start with 'APPROVE '; expected {APPROVE_GRAMMAR!r}"}
    rest = text[len("APPROVE "):]
    if ":" not in rest:
        return {"grammar_ok": False, "reason": "missing ':' separating proposal_id from item-ids"}
    pid, items_text = rest.split(":", 1)
    pid = pid.strip()
    items = [i.strip() for i in items_text.split(",") if i.strip()]
    if not pid or not items:
        return {"grammar_ok": False, "reason": "empty proposal_id or empty item-id list"}
    if any(i.lower() == "all" for i in items):
        return {"grammar_ok": False, "reason": "wildcard 'all' is not accepted — list exact item IDs"}
    return {"grammar_ok": True, "proposal_id": pid, "item_ids": items}


def cmd_check_approval(args: argparse.Namespace) -> int:
    proposal = json.loads(Path(args.proposal).read_text(encoding="utf-8"))
    parsed = parse_approval_text(args.text)
    result: dict[str, Any] = {"schema_version": "1", "parsed_approval": parsed}
    if parsed.get("grammar_ok"):
        known_ids = {it["item_id"] for it in proposal.get("items", [])}
        requested = set(parsed["item_ids"])
        result["proposal_id_matches"] = parsed["proposal_id"] == proposal.get("proposal_id")
        result["unknown_item_ids"] = sorted(requested - known_ids)
        result["known_item_ids_in_proposal"] = sorted(known_ids)
        result["approval_valid"] = (
            result["proposal_id_matches"] and not result["unknown_item_ids"]
        )
    else:
        result["approval_valid"] = False
    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


def cmd_drift_check(args: argparse.Namespace) -> int:
    proposal = json.loads(Path(args.proposal).read_text(encoding="utf-8"))
    current = {root: snapshot_root(Path(root)) for root in proposal["target_roots"]}
    original = proposal["snapshot_manifest"]
    drift: list[dict[str, Any]] = []
    for root, entries in original.items():
        cur_entries = current.get(root, [])
        cur_by_path = {e["rel_path"]: e for e in cur_entries}
        orig_by_path = {e["rel_path"]: e for e in entries}
        for rel, orig_entry in orig_by_path.items():
            cur_entry = cur_by_path.get(rel)
            if cur_entry != orig_entry:
                drift.append({"root": root, "rel_path": rel, "original": orig_entry, "current": cur_entry})
        for rel in cur_by_path.keys() - orig_by_path.keys():
            drift.append({"root": root, "rel_path": rel, "original": None, "current": cur_by_path[rel]})
    json.dump(
        {"schema_version": "1", "drift_detected": bool(drift), "drift": drift},
        sys.stdout, indent=2, ensure_ascii=False,
    )
    sys.stdout.write("\n")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    proposal = json.loads(Path(args.proposal).read_text(encoding="utf-8"))
    post = json.loads(Path(args.post_snapshot).read_text(encoding="utf-8"))["roots"]
    selected_ids = set(args.item.split(",")) if args.item else {it["item_id"] for it in proposal["items"]}
    selected_items = [it for it in proposal["items"] if it["item_id"] in selected_ids]
    expected_changed = {p for it in selected_items for p in it["paths"]}
    pre = proposal["snapshot_manifest"]

    changed_paths: set[str] = set()
    for root, entries in pre.items():
        pre_by_path = {e["rel_path"]: e for e in entries}
        post_by_path = {e["rel_path"]: e for e in post.get(root, [])}
        for rel in set(pre_by_path) | set(post_by_path):
            if pre_by_path.get(rel) != post_by_path.get(rel):
                changed_paths.add(rel)

    result = {
        "schema_version": "1",
        "selected_item_ids": sorted(selected_ids),
        "expected_changed_paths": sorted(expected_changed),
        "actually_changed_paths": sorted(changed_paths),
        "unexpected_changes": sorted(changed_paths - expected_changed),
        "missing_expected_changes": sorted(expected_changed - changed_paths),
        "postconditions_hold": not (changed_paths - expected_changed) and not (expected_changed - changed_paths),
    }
    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)

    s_snap = sub.add_parser("snapshot")
    s_snap.add_argument("--root", action="append", required=True)
    s_snap.set_defaults(func=cmd_snapshot)

    s_prop = sub.add_parser("propose")
    s_prop.add_argument("--root", action="append", required=True)
    s_prop.add_argument("--items", required=True, help="Path to a JSON array of item objects")
    s_prop.add_argument("--policy-version", default="aocc-skill-reviewer-policy-v1.0")
    s_prop.set_defaults(func=cmd_propose)

    s_appr = sub.add_parser("check-approval")
    s_appr.add_argument("--proposal", required=True)
    s_appr.add_argument("--text", required=True)
    s_appr.set_defaults(func=cmd_check_approval)

    s_drift = sub.add_parser("drift-check")
    s_drift.add_argument("--proposal", required=True)
    s_drift.set_defaults(func=cmd_drift_check)

    s_verify = sub.add_parser("verify")
    s_verify.add_argument("--proposal", required=True)
    s_verify.add_argument("--post-snapshot", required=True)
    s_verify.add_argument("--item", default=None, help="Comma-separated subset of item IDs; default = all proposal items")
    s_verify.set_defaults(func=cmd_verify)

    args = ap.parse_args()
    try:
        return args.func(args)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"revise_support {args.command} failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
