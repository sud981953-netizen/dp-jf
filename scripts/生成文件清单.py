# -*- coding: utf-8 -*-
"""生成受管理技能文件的哈希清单；当前本地候选仅允许 --local。"""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", "__pycache__", "学员", "config", "_素材资源", "历史资料", "evals", "node_modules"}
SKIP_NAMES = {"设置.md", "文件清单.json", "文件清单_本地候选.json"}
SKIP_SUFFIXES = {".pyc", ".pyo", ".bak", ".tmp", ".log"}

def collect_files(root):
    files = []
    for current, directories, names in os.walk(root):
        keep = []
        for directory in directories:
            if directory in SKIP_DIRS or directory.startswith("_打包临时") or directory.startswith("dp-jf_backup_"):
                continue
            path = Path(current) / directory
            if path.is_symlink():
                raise ValueError(f"拒绝将目录链接写入清单：{path}")
            keep.append(directory)
        directories[:] = keep
        for name in names:
            if name in SKIP_NAMES or Path(name).suffix.lower() in SKIP_SUFFIXES:
                continue
            path = Path(current) / name
            if path.is_symlink():
                raise ValueError(f"拒绝将链接写入清单：{path}")
            files.append(path)
    return sorted(files, key=lambda p: p.relative_to(root).as_posix())

def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def main():
    parser = argparse.ArgumentParser(description="生成 dpjf 技能包清单")
    parser.add_argument("--local", action="store_true", help="生成本地候选清单")
    parser.add_argument("--output", help="输出位置；默认维护目录")
    args = parser.parse_args()
    try:
        version = json.loads((ROOT / "version.json").read_text(encoding="utf-8"))
        if not version.get("version") or version.get("name") != "dpjf":
            raise ValueError("version.json 缺版本或名称不匹配")
        if not args.local and version.get("status") != "released":
            raise ValueError("当前是本地候选；请使用 --local，不能生成发布清单")
        if not args.local and not version.get("remote_source"):
            raise ValueError("未配置确认的发布来源")
        paths = collect_files(ROOT)
        entries = [{"path": p.relative_to(ROOT).as_posix(), "size": p.stat().st_size, "sha256": digest(p)} for p in paths]
        fingerprint = hashlib.sha256("\n".join(x["path"] + ":" + x["sha256"] for x in entries).encode("utf-8")).hexdigest()
        data = {"skill": "dpjf", "version": version["version"], "source_state": "local-candidate" if args.local else "released", "remote_source": version.get("remote_source"), "generated_at": datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds"), "file_count": len(entries), "fingerprint": fingerprint, "excluded": ["学员", "config", "_素材资源", "历史资料", "evals", "缓存"], "notes": (["本地候选清单不证明远端发布。"] if args.local else ["发布前需核对实际来源及内容。 "]) + ["不以清单缺失为由删除用户文件。"], "files": entries}
        default = ROOT / "维护" / ("文件清单_本地候选.json" if args.local else "文件清单.json")
        target = Path(args.output) if args.output else default
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"文件清单已生成：{target}；文件 {len(entries)}；指纹 {fingerprint}")
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"[失败] {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
