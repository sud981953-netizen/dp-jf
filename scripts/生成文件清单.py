# -*- coding: utf-8 -*-
"""
生成 文件清单.json

用途：发布前运行，产出本版本权威文件清单，供使用者侧 AI 自动更新时比对使用。
      清单记录了每个文件的路径、大小、sha256，以及整体内容指纹。
      使用者侧 AI 据此可以：删除本地多余文件（旧版残留）、下载缺失/更新文件，
      从而做到「只保留最新版的项目文件」。

用法：
    python scripts/生成文件清单.py
    python scripts/生成文件清单.py --output 文件清单.json

排除：.git、__pycache__、_打包临时、备份目录、*.pyc/*.bak/*.tmp、
      学员数据（不进仓库）、config/设置.md（本机私有）、清单自身。
"""

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

REPO = "sud981953-netizen/dp-jf"
BRANCH = "master"
RAW_BASE = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/"

MANIFEST_NAME = "文件清单.json"
SKILL_NAME = "dp-jf"

# 不进清单的目录（数据目录/缓存/版本控制）
EXCLUDE_DIRS = {".git", "__pycache__", "_打包临时", "学员", "node_modules"}
# 不进清单的后缀
EXCLUDE_SUFFIXES = (".pyc", ".pyo", ".bak", ".tmp", ".log")
# 不进清单的具体文件（本机私有运行设置）
EXCLUDE_FILES = {"设置.md"}

CST = timezone(timedelta(hours=8))


def read_version(skill_root):
    """从 version.md 提取版本号。"""
    version_path = os.path.join(skill_root, "version.md")
    if not os.path.exists(version_path):
        print("[失败] 找不到 version.md，无法确定版本号", file=sys.stderr)
        sys.exit(1)
    with open(version_path, "r", encoding="utf-8") as f:
        content = f.read()
    match = re.search(r"当前版本[：:]\s*v?([0-9]+\.[0-9]+\.[0-9]+)", content)
    if not match:
        print("[失败] version.md 里没找到「当前版本：x.y.z」", file=sys.stderr)
        sys.exit(1)
    return match.group(1)


def sha256_of(path):
    """算文件 sha256。"""
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collect_files(skill_root):
    """遍历技能目录，返回 [(相对路径, 绝对路径)]，已按排除规则过滤。"""
    collected = []
    for current_dir, dir_names, file_names in os.walk(skill_root):
        # 原地过滤目录，os.walk 就不会往下走
        dir_names[:] = [
            d for d in dir_names
            if d not in EXCLUDE_DIRS and not d.startswith("dp-jf_backup_")
        ]
        for name in file_names:
            if name in EXCLUDE_FILES:
                continue
            if name == MANIFEST_NAME:
                continue  # 清单不描述自己，避免自指
            if name.lower().endswith(EXCLUDE_SUFFIXES):
                continue
            abs_path = os.path.join(current_dir, name)
            rel_path = os.path.relpath(abs_path, skill_root).replace(os.sep, "/")
            collected.append((rel_path, abs_path))
    collected.sort(key=lambda item: item[0])
    return collected


def main():
    parser = argparse.ArgumentParser(description="生成 dp-jf 文件清单.json")
    parser.add_argument("--output", default=None, help="输出路径，默认技能根目录下 文件清单.json")
    args = parser.parse_args()

    skill_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_path = args.output or os.path.join(skill_root, MANIFEST_NAME)

    version = read_version(skill_root)
    pairs = collect_files(skill_root)

    files = []
    fingerprint_input = []
    total_bytes = 0
    for rel_path, abs_path in pairs:
        size = os.path.getsize(abs_path)
        digest = sha256_of(abs_path)
        total_bytes += size
        files.append({
            "path": rel_path,
            # url_path 已做百分号编码，使用者侧 AI 直接拼 RAW_BASE 即可下载，无需自己处理中文
            "url_path": "/".join(quote(seg, safe="") for seg in rel_path.split("/")),
            "size": size,
            "sha256": digest,
        })
        fingerprint_input.append(f"{rel_path}:{digest}")

    fingerprint = hashlib.sha256("\n".join(fingerprint_input).encode("utf-8")).hexdigest()

    manifest = {
        "skill": SKILL_NAME,
        "version": version,
        "repo": REPO,
        "branch": BRANCH,
        "raw_base": RAW_BASE,
        "generated_at": datetime.now(CST).strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "fingerprint": fingerprint,
        "file_count": len(files),
        "total_bytes": total_bytes,
        # 更新时必须保留的本地文件/目录（不进仓库，不能删）
        "preserve": [
            "config/设置.md",
            "学员/**",
        ],
        "notes": [
            "本清单描述的是仓库 master 分支的完整内容。",
            "本地存在但不在本清单、也不在 preserve 里的文件 = 旧版残留，更新时应删除。",
            "preserve 里的路径是本机数据/设置，任何时候都不许删。",
        ],
        "files": files,
    }

    # 写盘前先自检：version.md 的「文件数」表格行必须与实际一致
    # （不自动改，避免静默篡改维护者文件；不一致就不生成清单，防止发出对不上的版本）
    version_path = os.path.join(skill_root, "version.md")
    with open(version_path, "r", encoding="utf-8") as f:
        version_text = f.read()
    declared = re.search(r"\|\s*文件数\s*\|\s*(\d+)\s*\|", version_text)
    if declared and int(declared.group(1)) != len(files):
        print(
            f"[失败] version.md 里写的文件数是 {declared.group(1)}，实际是 {len(files)}。\n"
            f"       请把 version.md 的「| 文件数 | N |」改成 {len(files)} 后重新运行，未生成清单。",
            file=sys.stderr,
        )
        sys.exit(2)

    with open(output_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"文件清单已生成：{output_path}")
    print(f"版本：v{version}｜文件数：{len(files)}｜总体积：{round(total_bytes / 1048576, 2)} MB")
    print(f"内容指纹：{fingerprint}")
    if not declared:
        print("[提示] version.md 里没找到「| 文件数 | N |」表格行，跳过一次核对。", file=sys.stderr)


if __name__ == "__main__":
    main()
