# -*- coding: utf-8 -*-
"""构建包含教学资源的本地技能包，不覆盖已有文件，不包含用户资料和历史记录。"""
import argparse
import json
import os
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", "__pycache__", "学员", "config", "_素材资源", "历史资料", "evals", "node_modules"}
SKIP_NAMES = {"设置.md", "文件清单.json", "文件清单_本地候选.json"}
SKIP_SUFFIXES = {".pyc", ".pyo", ".bak", ".tmp", ".log"}

def collect_files(root=ROOT):
    result = []
    for current, directories, names in os.walk(root):
        keep = []
        for directory in directories:
            if directory in SKIP_DIRS or directory.startswith("_打包临时") or directory.startswith("dp-jf_backup_"):
                continue
            path = Path(current) / directory
            if path.is_symlink():
                raise ValueError(f"技能包中含目录链接，无法安全打包：{path}")
            keep.append(directory)
        directories[:] = keep
        for name in names:
            if name in SKIP_NAMES or Path(name).suffix.lower() in SKIP_SUFFIXES:
                continue
            path = Path(current) / name
            if path.is_symlink():
                raise ValueError(f"技能包中含文件链接，无法安全打包：{path}")
            result.append(path)
    return sorted(result, key=lambda p: p.relative_to(root).as_posix())

def validate_required(files, root=ROOT):
    present = {p.relative_to(root).as_posix() for p in files}
    required = {
        "version.json", "skills/dpjf/SKILL.md", "skills/dpjf/scripts/list-skills.py",
        "skills/dpjf/references/catalog.json", "共享资源/规则/共同规则.md",
        "共享资源/规则/来源与取用.md", "共享资源/00_短视频内容创作72变.md",
        "共享资源/语料库/爆款文案.jsonl", "共享资源/要素定义库/06_72变要素.md",
        "共享资源/templates/每日作业模板.md", "scripts/retrieve_yuliao.py",
    }
    catalog = json.loads((root / "skills/dpjf/references/catalog.json").read_text(encoding="utf-8"))
    names = catalog["skills"]
    actual = {p.name for p in (root / "skills").iterdir() if p.is_dir() and p.name.startswith("dpjf-")}
    if not isinstance(names, list) or not names or any(not isinstance(n, str) for n in names) or len(names) != len(set(names)) or set(names) != actual:
        raise ValueError("子技能登记与目录不一致")
    for name in names:
        if not isinstance(name, str) or not name.startswith("dpjf-") or "/" in name or "\\" in name or ".." in name:
            raise ValueError("子技能目录名称不合法")
        required.add(f"skills/{name}/SKILL.md")
        required.add(f"skills/{name}/references/资源调用.md")
    missing = sorted(required - present)
    if missing:
        raise ValueError("安装包缺少必需文件：" + "、".join(missing))
    if not any(x.startswith("共享资源/知识卡片库/PNG截图/") for x in present):
        raise ValueError("安装包缺少 PNG 教学卡片")
    if not any(x.startswith("共享资源/知识卡片库/HTML知识卡片/") for x in present):
        raise ValueError("安装包缺少 HTML 教学卡片")

def write_archive(fileobj, files, root=ROOT):
    validate_required(files, root)
    with zipfile.ZipFile(fileobj, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, "dp-jf/" + path.relative_to(root).as_posix())

def main():
    parser = argparse.ArgumentParser(description="生成 dpjf 本地安装包")
    parser.add_argument("--output", help="目标 zip；默认放在技能包同级，不覆盖已有文件")
    args = parser.parse_args()
    try:
        metadata = json.loads((ROOT / "version.json").read_text(encoding="utf-8"))
        version = str(metadata.get("version", ""))
        if metadata.get("name") != "dpjf" or not version or any(c not in "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ.-_" for c in version):
            raise ValueError("版本元数据无效")
        files = collect_files()
        validate_required(files)
        target = Path(args.output) if args.output else ROOT.parent / f"dpjf_{version}_安装包.zip"
        with target.open("xb") as handle:
            write_archive(handle, files)
        print(f"打包完成：{target}；文件 {len(files)}；含PNG教学卡片，排除学员数据、私有素材和历史资料")
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"[失败] {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
