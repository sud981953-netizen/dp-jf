# -*- coding: utf-8 -*-
"""构建语料库：从 365条爆款文案 xlsx 解析出全量文案 JSONL（带互动数据与平台内分档）

用法：
  python scripts/构建语料库.py --source "F:\素材库\00_365爆款文案\source\365条爆款文案(1).xlsx" --output "语料库\爆款文案.jsonl"

依赖：openpyxl（仅构建时需要；检索脚本 retrieve_yuliao.py 零依赖）

清洗规则：
1. 文案为空或为分享垃圾（小红书分享串/链接码）时，用「内容」列兜底；仍不足10字则跳过
2. 去包裹引号；按全文md5跨表去重——同一文案出现在多个sheet时合并为一条：
   categories 记录全部分类；主分类取更具体的一个（情感为泛分类，排在末位；专题sheet优先）
3. 合并去重时：topics 取并集；title/opening/link/date 取首个非空；互动取最大值
分档规则：同平台内按互动量排序，前20%=高，20%-50%=中，其余=低；无互动数据=无数据
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

import openpyxl

SHEET_ORDER = ["情感（泛流量）", "搞钱（干货）", "自媒体+AI", "人设", "营销"]
SHEET_COLS = {
    "情感（泛流量）": dict(platform=2, title=3, topics=5, link=6, copy=7, content=None, date=8, likes_saves=9, opening=10),
    "搞钱（干货）":    dict(platform=2, title=3, topics=4, link=None, copy=6, content=5, date=7, likes_saves=8, opening=9),
    "自媒体+AI":       dict(platform=2, title=5, topics=3, link=4, copy=6, content=None, date=8, likes=9, comments=10, collects=11, followers=12, opening=7),
    "人设":            dict(platform=2, title=3, topics=4, link=None, copy=6, content=5, date=7, likes_saves=8, opening=9),
    "营销":            dict(platform=2, title=3, topics=4, link=None, copy=6, content=5, date=7, likes_saves=8, opening=9),
}
CATEGORY_SHORT = {"情感（泛流量）": "情感", "搞钱（干货）": "搞钱", "自媒体+AI": "AI", "人设": "人设", "营销": "营销"}
# 泛分类排最后：同一文案跨表重复时，主分类取更具体的专题sheet
CATEGORY_PRIORITY = {"营销": 0, "人设": 1, "AI": 2, "搞钱": 3, "情感": 4}

NUM_RE = re.compile(r"([\d.]+)\s*(万|w|W)?")
JUNK_MARKERS = ("你的生活兴趣社区", "😆", "| 小红书", "复制链接", "打开小红书")


def cell(row, idx):
    if idx is None:
        return None
    return row[idx - 1] if idx - 1 < len(row) else None


def to_int(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip()
    if not text or text in {"无", "-", "—", "/"}:
        return None
    match = NUM_RE.search(text)
    if not match:
        return None
    number = float(match.group(1))
    if match.group(2):
        number *= 10000
    return int(number)


def clean_text(text):
    if text is None:
        return ""
    text = str(text).replace("\r\n", "\n").replace("\r", "\n").strip()
    for left, right in [("\"", "\""), ("“", "”"), ("‘", "’"), ("「", "」")]:
        if text.startswith(left) and text.endswith(right) and len(text) >= 2:
            text = text[1:-1].strip()
    return text


def is_share_junk(text):
    """识别「11 【标题 - 作者 | 小红书 - 你的生活兴趣社区】 😆 code 😆」式分享串。"""
    if not text:
        return False
    if any(marker in text for marker in JUNK_MARKERS):
        return True
    if re.match(r"^\d+\s*【", text) and len(text) < 200:
        return True
    stripped = re.sub(r"[\s\d【】|｜:：,，.。!！?？~～\-—_a-zA-Z]", "", text)
    return len(stripped) < max(10, len(text) * 0.3)


def clean_fallback_content(text):
    """「内容」列兜底：去掉链接、话题标签，只留正文。"""
    text = clean_text(text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"#[^#\n]{1,30}#", "", text)
    text = re.sub(r"[\w.]+:/", "", text)
    return text.strip()


def normalize_date(value):
    if value is None:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    text = str(value).strip()
    match = re.match(r"^(\d{2,4})[.\-/](\d{1,2})[.\-/](\d{1,2})", text)
    if match:
        year, month, day = match.groups()
        year = int(year)
        year = year + 2000 if year < 100 else year
        return f"{year:04d}-{int(month):02d}-{int(day):02d}"
    match = re.match(r"^(\d{1,2})[.\-/](\d{1,2})$", text)
    if match:
        month, day = match.groups()
        return f"2026-{int(month):02d}-{int(day):02d}"
    return text


def split_topics(value):
    if value is None:
        return []
    parts = re.split(r"[\n,，、;；/|\s]+", str(value).strip())
    return [part.strip() for part in parts if part.strip() and part.strip() != "-"]


def build_record(sheet_name, cols, row):
    copy = clean_text(cell(row, cols["copy"]))
    if len(copy) < 10 or is_share_junk(copy):
        if cols.get("content"):
            copy = clean_fallback_content(cell(row, cols["content"]))
        if len(copy) < 10 or is_share_junk(copy):
            return None

    engagement = {}
    if cols.get("likes_saves"):
        engagement["likes_saves"] = to_int(cell(row, cols["likes_saves"]))
    if cols.get("likes"):
        engagement["likes"] = to_int(cell(row, cols["likes"]))
        engagement["comments"] = to_int(cell(row, cols["comments"]))
        engagement["collects"] = to_int(cell(row, cols["collects"]))
        engagement["followers"] = to_int(cell(row, cols["followers"]))
    engagement_value = 0
    if engagement.get("likes_saves"):
        engagement_value = engagement["likes_saves"]
    else:
        engagement_value = sum(v for k, v in engagement.items() if k != "followers" and v) or 0

    return {
        "sheet": sheet_name,
        "category": CATEGORY_SHORT[sheet_name],
        "platform": clean_text(cell(row, cols["platform"])),
        "topics": split_topics(cell(row, cols["topics"])),
        "title": clean_text(cell(row, cols["title"])),
        "copy": copy,
        "opening": clean_text(cell(row, cols["opening"])),
        "date": normalize_date(cell(row, cols["date"])),
        "engagement": {k: v for k, v in engagement.items() if v is not None},
        "engagement_value": engagement_value,
        "link": clean_text(cell(row, cols["link"])),
        "length": len(copy),
        "alt_categories": [],
    }


def merge_duplicate(existing, incoming):
    """同一全文跨表重复：合并元数据，主分类取更具体的sheet。"""
    if CATEGORY_PRIORITY[incoming["category"]] < CATEGORY_PRIORITY[existing["category"]]:
        primary = dict(incoming)
        primary["alt_categories"] = sorted(set(existing["alt_categories"]) | {existing["category"]} | set(incoming["alt_categories"]) - {incoming["category"]})
        secondary = existing
    else:
        primary = dict(existing)
        primary["alt_categories"] = sorted(set(existing["alt_categories"]) | {incoming["category"]} | set(incoming["alt_categories"]) - {incoming["category"]})
        secondary = incoming
    primary["topics"] = sorted(set(primary["topics"]) | set(secondary["topics"]))
    for field in ("title", "opening", "link", "date", "platform"):
        if not primary.get(field) and secondary.get(field):
            primary[field] = secondary[field]
    primary["engagement_value"] = max(primary["engagement_value"], secondary["engagement_value"])
    merged_engagement = dict(primary["engagement"])
    for key, value in secondary["engagement"].items():
        if key not in merged_engagement or (value or 0) > (merged_engagement.get(key) or 0):
            merged_engagement[key] = value
    primary["engagement"] = merged_engagement
    return primary


def parse(source: Path, output: Path):
    workbook = openpyxl.load_workbook(source, read_only=True)
    dedup = {}
    stats = {}
    for sheet_name in SHEET_ORDER:
        cols = SHEET_COLS[sheet_name]
        worksheet = workbook[sheet_name]
        sheet_total = sheet_kept = 0
        for row in worksheet.iter_rows(min_row=2, values_only=True):
            if not any(cell(row, i) for i in range(1, worksheet.max_column + 1)):
                continue
            sheet_total += 1
            record = build_record(sheet_name, cols, row)
            if record is None:
                continue
            sheet_kept += 1
            digest = hashlib.md5(record["copy"].encode("utf-8")).hexdigest()
            if digest in dedup:
                dedup[digest] = merge_duplicate(dedup[digest], record)
            else:
                dedup[digest] = record
        stats[sheet_name] = (sheet_total, sheet_kept)
    workbook.close()

    records = sorted(dedup.values(), key=lambda r: (CATEGORY_PRIORITY[r["category"]], -r["engagement_value"]))

    by_platform = {}
    for record in records:
        if record["engagement_value"] > 0:
            by_platform.setdefault(record["platform"], []).append(record)
    for platform_rows in by_platform.values():
        platform_rows.sort(key=lambda r: -r["engagement_value"])
        total = len(platform_rows)
        for index, record in enumerate(platform_rows):
            percentile = index / total
            record["tier"] = "高" if percentile < 0.2 else ("中" if percentile < 0.5 else "低")
    for record in records:
        record.setdefault("tier", "无数据")

    final_records = []
    for index, record in enumerate(records, start=1):
        final_records.append({"id": index, **record})

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for record in final_records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"输出：{output}")
    print(f"总计：{len(final_records)} 条唯一全文")
    for sheet_name, (total, kept) in stats.items():
        print(f"  {sheet_name}: 数据行 {total} -> 有效 {kept}")
    from collections import Counter
    category_count = Counter(r["category"] for r in final_records)
    platform_count = Counter(r["platform"] for r in final_records)
    tier_count = Counter(r["tier"] for r in final_records)
    multi_category = sum(1 for r in final_records if r["alt_categories"])
    print(f"主分类分布：{dict(category_count)}（跨表重复合并 {multi_category} 条）")
    print(f"平台分布：{dict(platform_count)}")
    print(f"互动分档：{dict(tier_count)}")


def main():
    parser = argparse.ArgumentParser(description="从 xlsx 构建爆款文案语料 JSONL")
    parser.add_argument("--source", required=True, help="xlsx 路径")
    parser.add_argument("--output", required=True, help="输出 jsonl 路径")
    args = parser.parse_args()
    parse(Path(args.source), Path(args.output))


if __name__ == "__main__":
    main()