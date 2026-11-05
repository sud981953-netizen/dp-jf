#!/usr/bin/env python3
"""更新成功后清理 dpjf 旧安装版本；默认只预览，不删除。"""
import argparse
import json
import shutil
import sys
from pathlib import Path

PREFIXES = ("dp-jf", "dpjf-", "dojf")
BACKUP_PREFIXES = ("dp-jf_backup", "dp-jf-backup", "dp-jf_")


def default_roots():
    home = Path.home()
    return [home / name / "skills" for name in (".agents", ".claude", ".workbuddy", ".hermes", ".kiro", ".qwen", ".cline", ".grok")]


def validate_current_root(value):
    root = Path(value).expanduser().resolve()
    metadata = json.loads((root / "version.json").read_text(encoding="utf-8"))
    if metadata.get("status") != "released":
        raise ValueError("最新候选不是正式发布版本，停止清理")
    if not (root / "skills" / "dpjf" / "SKILL.md").is_file():
        raise ValueError("最新候选缺少主路由，停止清理")
    catalog = json.loads((root / "skills" / "dpjf" / "references" / "catalog.json").read_text(encoding="utf-8"))
    expected = set(catalog["skills"])
    actual = {path.name for path in (root / "skills").iterdir() if path.is_dir() and path.name.startswith("dpjf-")}
    if expected != actual or not expected:
        raise ValueError("最新候选的子技能目录不完整，停止清理")
    return root


def is_candidate(path):
    return path.name.startswith(PREFIXES) or path.name.startswith(BACKUP_PREFIXES)


def remove_old_versions(current_root, roots, apply=False):
    current = validate_current_root(current_root)
    actions = []
    for root in roots:
        if not root.is_dir():
            continue
        for candidate in root.iterdir():
            if not is_candidate(candidate):
                continue
            resolved = candidate.resolve()
            if resolved == current or resolved in current.parents or current in resolved.parents:
                continue
            actions.append((candidate, resolved))
    if not apply:
        return actions
    for candidate, resolved in actions:
        if candidate.is_symlink():
            candidate.unlink()
        elif candidate.is_dir():
            shutil.rmtree(candidate)
        else:
            candidate.unlink()
    return actions


def main():
    parser = argparse.ArgumentParser(description="清理 dpjf 旧版安装；默认只预览")
    parser.add_argument("--current-root", required=True)
    parser.add_argument("--root", action="append", dest="roots")
    parser.add_argument("--apply", action="store_true", help="实际删除；仅在最新版验证成功后使用")
    args = parser.parse_args()
    try:
        roots = [Path(value).expanduser().resolve() for value in args.roots] if args.roots else default_roots()
        actions = remove_old_versions(args.current_root, roots, args.apply)
        for candidate, resolved in actions:
            print(("REMOVE " if args.apply else "PREVIEW ") + f"{candidate} -> {resolved}")
        print(f"{'已清理' if args.apply else '待清理'}旧版目录 {len(actions)} 个；当前最新版保留在 {Path(args.current_root).expanduser().resolve()}")
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"DPJF_CLEANUP_REJECTED: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
