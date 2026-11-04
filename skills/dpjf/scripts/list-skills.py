#!/usr/bin/env python3
"""列出此包明确登记的子技能；仅本地读取，不搜索学员资料。"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
SKILLS = HERE.parent
CATALOG = HERE / "references" / "catalog.json"

def read_entry(name):
    if not re.fullmatch(r"dpjf-[a-z0-9-]+", name):
        raise ValueError("名称格式无效")
    path = SKILLS / name / "SKILL.md"
    if not path.is_file():
        raise ValueError("SKILL.md 缺失")
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        raise ValueError("frontmatter 不完整")
    header = text.split("\n---\n", 1)[0]
    declared = re.search(r"(?m)^name:\s*(\S+)\s*$", header)
    description = re.search(r"(?m)^description:\s*(.+?)\s*$", header)
    handoff = re.search(r"(?m)^  dpjf-handoff:\s*\|\s*$", header)
    if not declared or declared.group(1) != name or not description or not handoff:
        raise ValueError("名称、描述或接手字段不完整")
    lines = header[handoff.end():].splitlines()
    entries = []
    for line in lines:
        if not line.strip(): continue
        if not line.startswith("    - "): break
        entries.append(line.strip()[2:])
    if not entries or not any(x.startswith("不交出：") for x in entries):
        raise ValueError("接手条件或不交出边界缺失")
    return {"name": name, "description": description.group(1).strip(), "handoff": entries, "source": str(path.resolve())}

def main():
    try:
        names = json.loads(CATALOG.read_text(encoding="utf-8"))["skills"]
        if not isinstance(names, list) or len(set(names)) != len(names):
            raise ValueError("目录为空、格式错误或有重复")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"skills": [], "errors": [str(exc)]}, ensure_ascii=False))
        return 1
    entries, errors = [], []
    for name in names:
        try: entries.append(read_entry(name))
        except (OSError, ValueError, TypeError) as exc: errors.append(f"{name}: {exc}")
    print(json.dumps({"skills": entries, "errors": errors}, ensure_ascii=False, indent=2))
    return 1 if errors or not entries else 0

if __name__ == "__main__":
    raise SystemExit(main())
