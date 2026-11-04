#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

CATEGORIES = {
    "00_对话存档",
    "01_账号策划",
    "02_选题与文案",
    "03_作业与排期",
    "04_视频评价",
    "05_复盘记录",
    "06_素材与作品",
    "07_钉钉证据",
}


def safe_component(value, label):
    if not value or value in {".", ".."} or "/" in value or "\\" in value or "\x00" in value:
        raise ValueError(f"{label}必须是单一路径组件，不能包含路径分隔符")
    if value.strip() != value:
        raise ValueError(f"{label}首尾不能包含空白字符")
    return value


def resolve_target(root, student, category, filename, create_student=False):
    if not root:
        raise ValueError("必须提供学员资料父目录")
    root_path = Path(root).expanduser().resolve()
    if not root_path.is_dir():
        raise ValueError("学员资料父目录不存在或不是文件夹")
    student_name = safe_component(student, "学员名称")
    if category not in CATEGORIES:
        raise ValueError(f"未知产物分类：{category}")
    student_dir = (root_path / student_name).resolve()
    student_dir.relative_to(root_path)
    if not student_dir.is_dir():
        if not create_student:
            raise ValueError("学员文件夹不存在，需要先完成学员建档")
        student_dir.mkdir(parents=True)
    if filename is None:
        return student_dir
    safe_component(filename, "文件名")
    target = (student_dir / category / filename).resolve()
    target.relative_to(student_dir)
    return target


def write_file(root, student, category, filename, content_file, create=False, overwrite=False):
    target = resolve_target(root, student, category, filename, create_student=create)
    if target.exists() and not overwrite:
        raise ValueError("目标文件已存在；未获覆盖授权")
    source = Path(content_file).expanduser().resolve()
    if not source.is_file():
        raise ValueError("内容源文件不存在")
    if source == target:
        raise ValueError("内容源文件与目标文件相同")
    target.parent.mkdir(parents=True, exist_ok=True)
    data = source.read_bytes()
    temporary = target.with_name(target.name + ".dpjf-tmp")
    try:
        with temporary.open("wb") as handle:
            handle.write(data)
        if target.exists() and not overwrite:
            raise ValueError("目标文件已存在；未获覆盖授权")
        temporary.replace(target)
    finally:
        if temporary.exists():
            temporary.unlink()
    if target.read_bytes() != data:
        raise ValueError("写入后回读校验失败")
    return target


def main():
    parser = argparse.ArgumentParser(description="dpjf 学员文件路径闸门")
    sub = parser.add_subparsers(dest="action", required=True)
    for name in ("resolve", "check"):
        command = sub.add_parser(name)
        command.add_argument("--root", required=True)
        command.add_argument("--student", required=True)
        command.add_argument("--category", choices=sorted(CATEGORIES))
        command.add_argument("--filename")
        if name == "check":
            command.add_argument("--path", required=True)
    command = sub.add_parser("write")
    command.add_argument("--root", required=True)
    command.add_argument("--student", required=True)
    command.add_argument("--category", required=True, choices=sorted(CATEGORIES))
    command.add_argument("--filename", required=True)
    command.add_argument("--content-file", required=True)
    command.add_argument("--create", action="store_true")
    command.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    try:
        if args.action == "resolve":
            target = resolve_target(args.root, args.student, args.category, args.filename)
        elif args.action == "check":
            requested = Path(args.path).expanduser().resolve()
            if args.category or args.filename:
                expected = resolve_target(args.root, args.student, args.category, args.filename)
                if requested != expected:
                    raise ValueError("目标路径与学员、分类或文件名不一致")
            else:
                student_dir = resolve_target(args.root, args.student, None, None)
                requested.relative_to(student_dir)
            target = requested
        else:
            target = write_file(args.root, args.student, args.category, args.filename, args.content_file, args.create, args.overwrite)
        print(str(target))
        return 0
    except (ValueError, OSError) as error:
        print(f"DPJF_PATH_REJECTED: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
