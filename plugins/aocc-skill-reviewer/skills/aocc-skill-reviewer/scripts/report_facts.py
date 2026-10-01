#!/usr/bin/env python3
"""Report structural facts for one logical Skill without making policy judgments.

Facts only: no verdict, severity, remediation, or threshold comparison.
Exit code means "report produced" (0) or "could not run" (2) — never
"skill conforms" or "skill violates". Extends the skill-audit v1.0.0
reporter with the fact families required by aocc-skill-reviewer Policy
v1.0 S6.1: ToC/heading candidates, code-fence spans and repeated-block
hashes, table row/byte counts, directive-token spans, exec-bit and
symlink metadata, and an optional caller-supplied token estimate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import threading
from typing import Any, Iterable

SCHEMA_VERSION = "3"
REPORTER_VERSION = "2.1.0"
SKIP_NAMES = {".git", "__pycache__", ".DS_Store"}
DIRECTIVE_RE = re.compile(r"\b(NEVER|MUST NOT|ALWAYS|DO NOT)\b")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
FENCE_RE = re.compile(r"^```")
TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$")
BOM = b"\xef\xbb\xbf"

# F1: never recurse into a directory candidate that resolves outside the
# unit root, and cap even an in-scope walk — unbounded recursive globbing on an
# ancestor/sibling mount (e.g. a backtick-quoted `/mnt/d` or `/`) hangs.
MAX_WALK_FILES = 5000

# F6: a backtick/markdown-link candidate is a reference only if it resolves
# to an existing in-scope path, or looks file-like on its own text (no
# whitespace/$/quotes, has an extension or trailing slash, and is not a
# single-segment slash-command like `/exit`). Everything else is an
# unverified_mention, not a dangling/present reference.
_FORBIDDEN_CANDIDATE_CHARS_RE = re.compile(r"[\s$\"']")
_FILE_EXT_RE = re.compile(r"\.[A-Za-z0-9]{1,10}$")
_PLACEHOLDER_RE = re.compile(r"[<>{}*]")

# F11: env-var/runtime-path tokens are tracked as their own fact family,
# independent of reference extraction, so they never need to masquerade as
# a dangling file reference.
_ENV_VAR_PATH_RE = re.compile(
    r"(\$\{[A-Za-z_][A-Za-z0-9_]*\}|\$[A-Za-z_][A-Za-z0-9_]*|%[A-Za-z_][A-Za-z0-9_]*%)[/\\][^\s`\"']*"
)


def sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return ""
    if value[0:1] in {'"', "'"} and value[-1:] == value[0]:
        return value[1:-1]
    if value.startswith("[") and value.endswith("]"):
        try:
            return json.loads(value.replace("'", '"'))
        except (json.JSONDecodeError, TypeError):
            return value
    if value in {"true", "false"}:
        return value == "true"
    if value in {"null", "~"}:
        return None
    return value


def parse_frontmatter(text: str) -> tuple[str, dict[str, Any], str | None]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return "absent", {}, None
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        return "unavailable", {}, "opening delimiter has no closing delimiter"

    values: dict[str, Any] = {}
    parent: str | None = None
    list_key: str | None = None
    try:
        for lineno, raw in enumerate(lines[1:end], start=2):
            if not raw.strip() or raw.lstrip().startswith("#"):
                continue
            indent = len(raw) - len(raw.lstrip(" "))
            body = raw.strip()
            if body.startswith("- "):
                if list_key is None:
                    raise ValueError(f"line {lineno}: list item has no key")
                current = values[list_key]
                if not isinstance(current, list):
                    raise ValueError(f"line {lineno}: mixed scalar and list")
                current.append(scalar(body[2:]))
                continue
            if ":" not in body:
                raise ValueError(f"line {lineno}: unsupported YAML construct")
            key, raw_value = body.split(":", 1)
            key = key.strip()
            if not key:
                raise ValueError(f"line {lineno}: empty key")
            if indent:
                if parent is None or not isinstance(values.get(parent), dict):
                    raise ValueError(f"line {lineno}: nested key has no map parent")
                values[parent][key] = scalar(raw_value)
                list_key = None
            elif raw_value.strip():
                values[key] = scalar(raw_value)
                parent = None
                list_key = None
            else:
                next_body = lines[lineno].strip() if lineno < end else ""
                if next_body.startswith("- "):
                    values[key] = []
                    list_key = key
                    parent = None
                else:
                    values[key] = {}
                    parent = key
                    list_key = None
    except ValueError as exc:
        return "unavailable", {}, str(exc)
    return "parsed", values, None


def walk_entries(root: Path) -> Iterable[Path]:
    """Yield every entry under root without following symlinked directories.

    Interpreter-independent (os.walk followlinks=False): a symlinked
    directory is yielded as an entry but never descended into, so a
    symlink cycle cannot loop on any supported Python version.
    """
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        for name in dirnames + filenames:
            yield Path(dirpath) / name


def regular_files(root: Path) -> list[Path]:
    found: list[Path] = []
    for path in walk_entries(root):
        if any(part in SKIP_NAMES for part in path.parts):
            continue
        if path.is_file() or path.is_symlink():
            found.append(path)
    return sorted(found, key=lambda p: p.as_posix())


def bounded_regular_files(root: Path, cap: int) -> tuple[list[Path], bool]:
    """Like regular_files, but stops after `cap` files and reports truncation.

    Only ever called on a candidate already proven in-scope and non-symlink
    (see F1) — this bound exists so an in-scope but very large directory
    still returns, not as the primary DoS guard.
    """
    found: list[Path] = []
    hit_cap = False
    for path in walk_entries(root):
        if any(part in SKIP_NAMES for part in path.parts):
            continue
        if path.is_file() or path.is_symlink():
            found.append(path)
            if len(found) >= cap:
                hit_cap = True
                break
    return sorted(found, key=lambda p: p.as_posix()), hit_cap


def normalize_master(raw: str) -> Path:
    path = Path(raw).expanduser().absolute()
    return path / "SKILL.md" if path.is_dir() else path


def candidate_copies(
    skill_id: str,
    roots: Iterable[Path],
    master: Path,
    unavailable: list[dict[str, str]],
) -> list[Path]:
    copies: set[Path] = set()
    for root in roots:
        if not root.exists() or not root.is_dir():
            unavailable.append({
                "fact": f"copy_search_root:{root}",
                "reason": "search root does not exist or is not a directory",
            })
            continue
        for path in (p for p in walk_entries(root) if p.name == "SKILL.md"):
            if path.absolute() == master.absolute():
                continue
            try:
                status, values, reason = parse_frontmatter(path.read_text(encoding="utf-8-sig"))
            except (OSError, UnicodeError) as exc:
                unavailable.append({
                    "fact": f"candidate_frontmatter:{path.absolute()}",
                    "reason": f"candidate could not be read as UTF-8: {exc}",
                })
                continue
            if status == "unavailable":
                unavailable.append({
                    "fact": f"candidate_frontmatter:{path.absolute()}",
                    "reason": reason or "candidate frontmatter could not be parsed",
                })
            if status == "parsed" and values.get("name") == skill_id:
                copies.add(path.absolute())
    return sorted(copies, key=lambda p: p.as_posix())


def _looks_file_like(candidate: str) -> bool:
    """Extension-based file-likeness only. Trailing-slash directory
    mentions are handled separately in referenced_paths() by existence,
    not guessed here — a nonexistent `.../<placeholder>/` prose mention is
    not evidence of a missing bundled file (F6).
    """
    if not candidate or _FORBIDDEN_CANDIDATE_CHARS_RE.search(candidate):
        return False
    if "://" in candidate or _PLACEHOLDER_RE.search(candidate):
        return False
    if candidate.endswith("/"):
        return False
    if candidate.count("/") == 1 and candidate.startswith("/"):
        rest = candidate[1:]
        if rest and "." not in rest:
            return False  # single-segment slash-command, e.g. `/exit`
    return bool(_FILE_EXT_RE.search(candidate))


def _extract_reference_candidates(text: str) -> set[str]:
    candidates: set[str] = set()
    for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
        candidates.add(target.split("#", 1)[0])
    for target in re.findall(r"`([^`\n]+)`", text):
        if "/" in target or target in {"README.md", "lineage.yaml"}:
            candidates.add(target.split("#", 1)[0])
    return candidates


def referenced_paths(text: str, unit_root: Path, unavailable: list[dict[str, str]]) -> dict[str, Any]:
    unit_root_resolved = unit_root.resolve()
    refs: set[str] = set()
    unverified: set[str] = set()
    out_of_scope: list[dict[str, Any]] = []
    truncated = False

    for raw in _extract_reference_candidates(text):
        candidate = raw.strip()
        if not candidate or "://" in candidate or candidate.startswith("#"):
            continue
        path = Path(candidate)
        resolved = path if path.is_absolute() else unit_root / path
        resolved = resolved.resolve()
        exists = resolved.exists()
        try:
            in_scope = resolved.is_relative_to(unit_root_resolved)
        except ValueError:
            in_scope = False

        if exists and resolved.is_dir():
            if not in_scope or resolved.is_symlink():
                out_of_scope.append({
                    "candidate": candidate,
                    "path": resolved.as_posix(),
                    "status": "not-walked: outside unit root" if not in_scope else "not-walked: symlinked directory",
                })
                continue
            found, hit_cap = bounded_regular_files(resolved, MAX_WALK_FILES)
            if hit_cap:
                truncated = True
            refs.update(item.resolve().as_posix() for item in found)
            continue

        if candidate.endswith("/"):
            # A nonexistent directory-style mention is not evidence of a
            # missing bundled *file* — file-reachability facts (dangling)
            # are file-level; record it as an unverified mention instead.
            unverified.add(candidate)
            continue

        if exists and in_scope:
            refs.add(resolved.as_posix())
            continue

        if _looks_file_like(candidate) and not path.is_absolute():
            # A relative file-like candidate is only a plausible *bundled*
            # reference if its own first path segment exists under the
            # unit root at all (e.g. a real `references/` or `scripts/`
            # dir) — a deep cross-repo path mention (`agent-GM/state/...`)
            # under a Skill with no such top-level directory is prose
            # documentation of another system, not a dangling bundled file.
            first_segment = path.parts[0] if path.parts else None
            if first_segment and (unit_root / first_segment).exists():
                refs.add(resolved.as_posix())
            else:
                unverified.add(candidate)
        elif _looks_file_like(candidate):
            refs.add(resolved.as_posix())
        else:
            unverified.add(candidate)

    if truncated:
        unavailable.append({
            "fact": "references.from_skill_md",
            "reason": f"one or more in-scope directory walks truncated at {MAX_WALK_FILES} files",
        })

    return {
        "refs": sorted(refs),
        "unverified_mentions": sorted(unverified),
        "out_of_scope_directories": sorted(out_of_scope, key=lambda d: d["candidate"]),
        "truncated": truncated,
    }


def reference_depth(unit_root: Path, ref_path: str) -> int | str:
    """Count path components between unit_root and ref_path; 1 = direct child dir level."""
    try:
        rel = Path(ref_path).resolve().relative_to(unit_root.resolve())
    except ValueError:
        return "outside-unit"
    return max(len(rel.parts) - 1, 0)


def env_var_path_candidates(text: str) -> list[dict[str, Any]]:
    out = []
    for i, line in enumerate(text.splitlines(), start=1):
        for m in _ENV_VAR_PATH_RE.finditer(line):
            out.append({"line": i, "token": m.group(0)})
    return out


def heading_candidates(lines: list[str]) -> list[dict[str, Any]]:
    out = []
    for i, line in enumerate(lines, start=1):
        m = HEADING_RE.match(line)
        if m:
            out.append({"line": i, "level": len(m.group(1)), "text": m.group(2).strip()})
    return out


def code_fence_spans(lines: list[str]) -> list[dict[str, Any]]:
    spans = []
    start = None
    for i, line in enumerate(lines, start=1):
        if FENCE_RE.match(line.strip()):
            if start is None:
                start = i
            else:
                spans.append({"start_line": start, "end_line": i, "line_count": i - start + 1})
                start = None
    if start is not None:
        spans.append({"start_line": start, "end_line": None, "line_count": "unavailable: unterminated fence"})
    return spans


def repeated_block_hashes(lines: list[str], spans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: dict[str, list[int]] = {}
    for span in spans:
        end = span.get("end_line")
        if not isinstance(end, int):
            continue
        block_lines = lines[span["start_line"]:end - 1]
        normalized = "\n".join(l.strip() for l in block_lines if l.strip())
        if len(block_lines) < 8 or not normalized:
            continue
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        seen.setdefault(digest, []).append(span["start_line"])
    return [
        {"hash": f"sha256:{h}", "occurrences": len(starts), "start_lines": starts}
        for h, starts in seen.items()
        if len(starts) >= 2
    ]


def table_candidates(lines: list[str]) -> list[dict[str, Any]]:
    tables = []
    start = None
    rows = 0
    byte_count = 0
    for i, line in enumerate(lines, start=1):
        if TABLE_ROW_RE.match(line):
            if start is None:
                start = i
                rows = 0
                byte_count = 0
            rows += 1
            byte_count += len(line.encode("utf-8"))
        else:
            if start is not None:
                tables.append({"start_line": start, "end_line": i - 1, "rows": rows, "bytes": byte_count})
                start = None
    if start is not None:
        tables.append({"start_line": start, "end_line": len(lines), "rows": rows, "bytes": byte_count})
    return tables


def _backtick_spans(line: str) -> list[tuple[int, int]]:
    positions = [i for i, ch in enumerate(line) if ch == "`"]
    return list(zip(positions[0::2], positions[1::2]))


def directive_candidates(lines: list[str]) -> list[dict[str, Any]]:
    """F7: a directive token is "quoted" only when its own offset falls
    inside a paired-backtick span on that line, or the line is a
    blockquote — not merely "the line contains a backtick somewhere".
    """
    out = []
    in_fence = False
    for i, line in enumerate(lines, start=1):
        if FENCE_RE.match(line.strip()):
            in_fence = not in_fence
            continue
        is_quote_line = line.strip().startswith(">")
        spans = _backtick_spans(line)
        for m in DIRECTIVE_RE.finditer(line):
            token_start = m.start(1)
            in_span = any(start < token_start < end for start, end in spans)
            out.append({
                "line": i,
                "token": m.group(1),
                "in_code_fence": in_fence,
                "in_inline_code_or_quote": in_span or is_quote_line,
            })
    return out


def exec_and_symlink_facts(path: Path) -> dict[str, Any]:
    try:
        st = path.lstat()
    except OSError as exc:
        return {"status": "unavailable", "reason": str(exc)}
    is_link = path.is_symlink()
    link_target = os.readlink(path) if is_link else None
    mode = stat.S_IMODE(st.st_mode)
    return {
        "status": "available",
        "mode_octal": oct(mode),
        "executable": bool(mode & stat.S_IXUSR),
        "is_symlink": is_link,
        "link_target_text": link_target,
    }


def entrypoint_case_fact(master: Path, unavailable: list[dict[str, str]]) -> dict[str, Any]:
    """F8: report the entrypoint's actual on-disk filename case, derived
    from a directory listing (not from the caller-supplied path string),
    so a case-insensitive filesystem cannot mask a mismatch.
    """
    parent = master.parent
    try:
        names = os.listdir(parent)
    except OSError as exc:
        unavailable.append({"fact": "entrypoint_case", "reason": str(exc)})
        return {"status": "unavailable"}
    on_disk = next((n for n in names if n == master.name), None)
    if on_disk is None:
        on_disk = next((n for n in names if n.lower() == master.name.lower()), None)
    if on_disk is None:
        unavailable.append({
            "fact": "entrypoint_case",
            "reason": "entrypoint filename not found via directory listing of its parent",
        })
        return {"status": "unavailable"}
    return {"status": "available", "filename": on_disk, "exact_case_match": on_disk == "SKILL.md"}


def file_record(
    path: Path,
    role: str,
    master_bytes: bytes,
    unit_root: Path,
    unavailable: list[dict[str, str]],
    ref_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    display = path.absolute().as_posix()
    try:
        data = path.read_bytes()
    except OSError as exc:
        reason = f"cannot read file: {exc}"
        unavailable.append({"fact": f"file:{display}", "reason": reason})
        return {
            "path": display,
            "role": role,
            "lines": "unavailable",
            "bytes": "unavailable",
            "frontmatter": {"status": "unavailable", "values": {}},
            "storage": {"kind": "unavailable", "target": "unavailable", "inode_or_sha256": "unavailable"},
            "identical_to_master": "unavailable",
        }

    bom_present = data.startswith(BOM)
    text = None
    if path.suffix.lower() == ".md":
        try:
            text = data.decode("utf-8-sig")
            fm_status, fm_values, fm_reason = parse_frontmatter(text)
        except UnicodeDecodeError as exc:
            fm_status, fm_values, fm_reason = "unavailable", {}, f"not UTF-8: {exc}"
    else:
        fm_status, fm_values, fm_reason = "absent", {}, None
    if fm_reason:
        unavailable.append({"fact": f"frontmatter:{display}", "reason": fm_reason})

    exec_facts = exec_and_symlink_facts(path)

    identity: bool | str
    if role in {"skill-md", "copy"}:
        identity = data == master_bytes
    else:
        identity = "unavailable"
        unavailable.append({
            "fact": f"identical_to_master:{display}",
            "reason": "not applicable: support files are not declared copies",
        })

    record: dict[str, Any] = {
        "path": display,
        "role": role,
        "lines": len(data.splitlines()),
        "bytes": len(data),
        "bom_present": bom_present,
        "frontmatter": {"status": fm_status, "values": fm_values},
        "storage": {
            "kind": "symlink" if exec_facts.get("is_symlink") else "real",
            "target": exec_facts.get("link_target_text"),
            "inode_or_sha256": sha256(data),
        },
        "exec": exec_facts,
        "identical_to_master": identity,
    }

    if text is not None and path.suffix.lower() == ".md":
        lines = text.splitlines()
        record["headings"] = heading_candidates(lines)
        record["toc_present"] = any(
            "table of contents" in h["text"].lower() or h["text"].lower() in {"toc", "contents"}
            for h in record["headings"]
        )
        fences = code_fence_spans(lines)
        record["code_fence_spans"] = fences
        record["repeated_block_hashes"] = repeated_block_hashes(lines, fences)
        record["table_candidates"] = table_candidates(lines)
        record["directive_candidates"] = directive_candidates(lines)
        if role == "skill-md" and ref_result is not None:
            record["reference_depth"] = {r: reference_depth(unit_root, r) for r in ref_result["refs"]}
            record["unverified_mentions"] = ref_result["unverified_mentions"]
            record["out_of_scope_directories"] = ref_result["out_of_scope_directories"]

    return record


def run_skills_ref(unit_root: Path, unavailable: list[dict[str, str]]) -> dict[str, Any]:
    executable = shutil.which("skills-ref")
    if executable is None:
        reason = "SKIP: skills-ref is not installed or not on PATH"
        unavailable.append({"fact": "skills_ref_validation", "reason": reason})
        return {"status": "skipped", "reason": reason}
    try:
        completed = subprocess.run(
            [executable, "validate", str(unit_root)],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        reason = f"skills-ref could not complete: {exc}"
        unavailable.append({"fact": "skills_ref_validation", "reason": reason})
        return {"status": "unavailable", "reason": reason}
    return {
        "status": "ran",
        "command": [executable, "validate", str(unit_root)],
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def run_plugin_validate(target: str | None, unavailable: list[dict[str, str]]) -> dict[str, Any]:
    """F2/N15: wrap `claude plugin validate --strict` as a fact, never a verdict.

    Only runs when the caller explicitly passes --plugin-validate; the
    reporter never guesses a plugin directory on its own.
    """
    if not target:
        return {"status": "not-requested"}
    executable = shutil.which("claude")
    if executable is None:
        reason = "SKIP: claude is not installed or not on PATH"
        unavailable.append({"fact": "plugin_validate", "reason": reason})
        return {"status": "skipped", "reason": reason}
    try:
        completed = subprocess.run(
            [executable, "plugin", "validate", "--strict", target],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        reason = f"claude plugin validate could not complete: {exc}"
        unavailable.append({"fact": "plugin_validate", "reason": reason})
        return {"status": "unavailable", "reason": reason}
    return {
        "status": "ran",
        "command": [executable, "plugin", "validate", "--strict", target],
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def eval_dir_facts(eval_dir_arg: str | None, unavailable: list[dict[str, str]]) -> dict[str, Any]:
    """F10: inventory an eval dir (case/prompt/grader presence, latest raw
    result path if one exists already) — never launches a model run.
    """
    if not eval_dir_arg:
        return {"status": "not-requested"}
    base = Path(eval_dir_arg).expanduser().resolve()
    if not base.is_dir():
        unavailable.append({"fact": f"eval_dir:{base}", "reason": "eval dir does not exist or is not a directory"})
        return {"status": "unavailable", "path": base.as_posix()}
    cases = []
    for case_dir in sorted(p for p in base.iterdir() if p.is_dir() and p.name != "results"):
        prompt = case_dir / "prompt.md"
        graders_dir = case_dir / "graders"
        grader_files = sorted(p.name for p in graders_dir.glob("*.md")) if graders_dir.is_dir() else []
        results_dir = case_dir / "results"
        latest_result = None
        if results_dir.is_dir():
            result_files = sorted(results_dir.glob("*.json"), key=lambda p: p.stat().st_mtime)
            if result_files:
                latest_result = result_files[-1].as_posix()
        cases.append({
            "case": case_dir.name,
            "prompt_present": prompt.is_file(),
            "grader_files": grader_files,
            "latest_raw_result_path": latest_result,
        })
    return {"status": "available", "path": base.as_posix(), "cases": cases}


def token_estimate_fact(args: argparse.Namespace, unavailable: list[dict[str, str]]) -> dict[str, Any]:
    if args.token_estimate is None:
        unavailable.append({
            "fact": "token_estimate",
            "reason": "no estimator supplied; do not use bytes/4 as an authoritative counter "
                      "(Policy S4.1) — pass --token-estimate with --token-estimator-label if one is available",
        })
        return {"status": "unavailable"}
    return {
        "status": "supplied",
        "value": args.token_estimate,
        "estimator_label": args.token_estimator_label or "unlabeled",
    }


def manifest_facts(paths: list[str], unavailable: list[dict[str, str]]) -> list[dict[str, Any]]:
    out = []
    for raw in paths:
        p = Path(raw).expanduser().absolute()
        if not p.exists():
            unavailable.append({"fact": f"manifest:{p}", "reason": "manifest path does not exist"})
            out.append({"path": p.as_posix(), "status": "unavailable"})
            continue
        try:
            parsed = json.loads(p.read_text(encoding="utf-8-sig"))
            out.append({"path": p.as_posix(), "status": "parsed", "values": parsed})
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            unavailable.append({"fact": f"manifest:{p}", "reason": str(exc)})
            out.append({"path": p.as_posix(), "status": "unavailable", "reason": str(exc)})
    return out


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    unavailable: list[dict[str, str]] = []
    raw_master = args.master or os.environ.get("SKILL_AUDIT_TARGET")
    if not raw_master:
        raise ValueError("provide --master PATH or set SKILL_AUDIT_TARGET")
    master = normalize_master(raw_master)
    if not master.exists() or not master.is_file():
        raise ValueError(f"master does not exist or is not a file: {master}")
    try:
        master_bytes = master.read_bytes()
        master_text = master_bytes.decode("utf-8-sig")
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"master is unreadable UTF-8: {exc}") from exc

    unit_root = master.parent
    explicit_copies = [normalize_master(value) for value in args.copy]
    search_roots = [Path(value).expanduser().resolve() for value in args.search_root]
    copies = {path.absolute() for path in explicit_copies}
    copies.update(candidate_copies(args.skill_id, search_roots, master, unavailable))

    support = [path for path in regular_files(unit_root) if path.resolve() != master.resolve()]
    copy_resolved = {path.resolve() for path in copies if path.exists()}
    support = [path for path in support if path.resolve() not in copy_resolved]

    ref_result = referenced_paths(master_text, unit_root, unavailable)

    files = [file_record(master, "skill-md", master_bytes, unit_root, unavailable, ref_result)]
    files.extend(file_record(path, "support", master_bytes, unit_root, unavailable) for path in support)
    for path in sorted(copies, key=lambda p: p.as_posix()):
        files.append(file_record(path, "copy", master_bytes, unit_root, unavailable))

    present_support = [path.absolute().as_posix() for path in support]
    present_set = {Path(path).resolve().as_posix() for path in present_support}
    referenced_set = {Path(path).resolve().as_posix() for path in ref_result["refs"]}

    report = {
        "schema_version": SCHEMA_VERSION,
        "reporter_version": REPORTER_VERSION,
        "skill_id": args.skill_id,
        "master": {"path": master.absolute().as_posix(), "status": "available"},
        "entrypoint": entrypoint_case_fact(master, unavailable),
        "files": files,
        "references": {
            "from_skill_md": ref_result["refs"],
            "present_support_files": present_support,
            "dangling": sorted(referenced_set - present_set),
            "unreferenced": sorted(present_set - referenced_set),
            "unverified_mentions": ref_result["unverified_mentions"],
            "out_of_scope_directories": ref_result["out_of_scope_directories"],
            "truncated": ref_result["truncated"],
            "max_depth_from_skill_md": max(
                (d for d in (reference_depth(unit_root, r) for r in ref_result["refs"]) if isinstance(d, int)),
                default=0,
            ),
        },
        "env_var_path_candidates": env_var_path_candidates(master_text),
        "token_estimate": token_estimate_fact(args, unavailable),
        "manifests": manifest_facts(args.manifest, unavailable),
        "eval_dir": eval_dir_facts(args.eval_dir, unavailable),
        "validators": {
            "skills_ref": run_skills_ref(unit_root, unavailable),
            "plugin_validate": run_plugin_validate(args.plugin_validate, unavailable),
        },
        "unavailable": unavailable,
    }
    return report


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--skill-id", required=True, help="Logical Skill name")
    result.add_argument("--master", help="Master SKILL.md or its directory; alternatively set SKILL_AUDIT_TARGET")
    result.add_argument("--copy", action="append", default=[], help="Declared copy SKILL.md or directory; repeatable")
    result.add_argument("--search-root", action="append", default=[], help="Explicit root to search for same-name copies; repeatable")
    result.add_argument("--manifest", action="append", default=[], help="plugin.json/marketplace.json path to parse for N23; repeatable")
    result.add_argument("--eval-dir", default=None, help="Eval cases directory to inventory (case/prompt/grader presence only; never launches a run)")
    result.add_argument("--plugin-validate", default=None, help="Plugin directory to run `claude plugin validate --strict` against, for the N15 fact")
    result.add_argument("--deadline-sec", type=float, default=60.0, help="Wall-clock bound for the whole report (default 60); on expiry emit an all-UNAVAILABLE report and exit 0")
    result.add_argument("--token-estimate", type=int, default=None, help="Caller-supplied token estimate for the body; omit to report unavailable")
    result.add_argument("--token-estimator-label", default=None, help="Model/tokenizer/version label for --token-estimate")
    return result


def main() -> int:
    args = parser().parse_args()
    box: dict[str, Any] = {}

    def work() -> None:
        try:
            box["report"] = build_report(args)
        except (ValueError, OSError) as exc:
            box["error"] = exc

    worker = threading.Thread(target=work, daemon=True)
    worker.start()
    worker.join(args.deadline_sec if args.deadline_sec > 0 else None)
    if worker.is_alive():
        report = {
            "schema_version": SCHEMA_VERSION,
            "reporter_version": REPORTER_VERSION,
            "skill_id": args.skill_id,
            "deadline_exceeded": True,
            "unavailable": [{
                "fact": "all_script_facts",
                "reason": f"reporter exceeded its {args.deadline_sec:g}s deadline; "
                          "treat the whole script-sourced fact family as UNAVAILABLE",
            }],
        }
        json.dump(report, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        sys.stdout.flush()
        os._exit(0)
    if "error" in box:
        print(f"fact reporter failed: {box['error']}", file=sys.stderr)
        return 2
    json.dump(box["report"], sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
