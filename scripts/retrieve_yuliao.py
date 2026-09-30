# -*- coding: utf-8 -*-
"""retrieve_yuliao.py — 爆款文案语料检索（零依赖，Python 3.8+）

写文案/开头/金句前必跑：取 3-5 条同分类爆款全文做仿写锚点。
数据源：语料库/爆款文案.jsonl（552 条唯一实战爆款全文，五类三平台，跨表重复已合并多分类标签）

用法：
  python scripts/retrieve_yuliao.py "主题词" [更多词...]          # 关键词检索（多词AND加成）
  python scripts/retrieve_yuliao.py "配得感" --sheet 情感         # 按分类过滤（情感/搞钱/AI/人设/营销，模糊匹配，含合并标签）
  python scripts/retrieve_yuliao.py "吸金" --platform 抖音        # 按平台过滤
  python scripts/retrieve_yuliao.py "搞钱" --top 5                # 召回条数（默认5）
  python scripts/retrieve_yuliao.py "爱自己" --json               # 输出完整记录（给AI仿写用）
  python scripts/retrieve_yuliao.py --id 123                     # 按锚点ID直取
  python scripts/retrieve_yuliao.py "来时路" --random             # 高分候选中随机取（避免每次同一批）
  python scripts/retrieve_yuliao.py --stats                      # 语料分布概览

评分：选题命中x8 + 标题命中x4 + 金句命中x3 + 全文命中x2（只命中全文的封顶3分）；多词全命中+5；有互动数据+3
红线：借网感、句式、结构，不借题材；禁止照抄原文发给学员
"""
import argparse
import json
import random
import re
import sys
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "语料库" / "爆款文案.jsonl"


def load():
    if not DB.exists():
        print(f"[语料库缺失] {DB}", file=sys.stderr)
        print("请确认技能包完整（语料库/爆款文案.jsonl 必须和 scripts/ 同级）", file=sys.stderr)
        sys.exit(1)
    records = []
    with DB.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def count_term(text, term):
    if not text or not term:
        return 0
    return text.count(term)


def score_record(record, terms):
    """返回 (总分, 是否有精准命中)。只命中全文的长文案封顶，避免大文件靠篇幅蹭分。"""
    if not terms:
        return 1, True
    score = 0
    hit_terms = 0
    focused_hit = False
    for term in terms:
        topic_score = count_term(" ".join(record.get("topics", [])), term) * 8
        title_score = count_term(record.get("title", ""), term) * 4
        opening_score = count_term(record.get("opening", ""), term) * 3
        copy_score = min(count_term(record.get("copy", ""), term), 3) * 2
        term_score = topic_score + title_score + opening_score + copy_score
        if topic_score or title_score or opening_score:
            focused_hit = True
        if term_score > 0:
            hit_terms += 1
        score += term_score
    if not focused_hit:
        score = min(score, 3)
    if hit_terms == len(terms) and len(terms) > 1:
        score += 5
    if record.get("engagement_value", 0) > 0:
        score += 3
    return score, focused_hit


def match_filter(record, args):
    categories = [record.get("sheet", ""), record.get("category", "")] + record.get("alt_categories", [])
    if args.sheet and not any(args.sheet in category for category in categories):
        return False
    if args.platform and args.platform not in record.get("platform", ""):
        return False
    if args.tier and record.get("tier") != args.tier:
        return False
    return True


def show_stats(records):
    from collections import Counter
    category_count = Counter(r["category"] for r in records)
    platform_count = Counter(r["platform"] for r in records)
    tier_count = Counter(r.get("tier", "无数据") for r in records)
    multi = sum(1 for r in records if r.get("alt_categories"))
    lengths = [r["length"] for r in records]
    print(f"共 {len(records)} 条唯一全文语料（跨分类合并 {multi} 条）")
    print("主分类：", dict(category_count))
    print("平台：", dict(platform_count))
    print("互动分档：", dict(tier_count))
    print(f"长度：最短 {min(lengths)} 字 / 中位 {sorted(lengths)[len(lengths)//2]} 字 / 最长 {max(lengths)} 字")


def print_result(record, as_json=False):
    if as_json:
        print(json.dumps(record, ensure_ascii=False))
        return
    engagement = record.get("engagement_value", 0)
    engagement_text = f"{engagement:,}" if engagement else "精选"
    alt = f"（兼:{'、'.join(record['alt_categories'])}）" if record.get("alt_categories") else ""
    topics = "、".join(record.get("topics", [])[:4]) or "-"
    title = record.get("title") or "-"
    copy = record.get("copy", "")
    preview = re.sub(r"\s+", " ", copy)[:160]
    suffix = "..." if len(copy) > 160 else ""
    print(f"语料#{record['id']} [{record['category']}{alt}|{record['platform']}|{record.get('tier','无数据')}|{record['length']}字|互动{engagement_text}]")
    print(f"  选题：{topics}")
    print(f"  标题：{title[:80]}")
    opening = re.sub(r"\s+", " ", record.get("opening") or "-")[:60]
    print(f"  金句：{opening}")
    print(f"  前文：{preview}{suffix}")
    print()


def main():
    parser = argparse.ArgumentParser(description="爆款文案语料检索")
    parser.add_argument("terms", nargs="*", help="关键词（空格分隔多个词，AND加成）")
    parser.add_argument("--sheet", help="分类过滤：情感/搞钱/AI/人设/营销（含合并标签，模糊匹配）")
    parser.add_argument("--platform", help="平台过滤：抖音/小红书/视频号")
    parser.add_argument("--tier", help="互动分档过滤：高/中/低")
    parser.add_argument("--top", type=int, default=5, help="召回条数，默认5")
    parser.add_argument("--id", type=int, help="按锚点ID直取")
    parser.add_argument("--random", action="store_true", help="高分候选中随机取")
    parser.add_argument("--json", action="store_true", help="输出完整JSON记录")
    parser.add_argument("--stats", action="store_true", help="语料分布概览")
    args = parser.parse_args()

    # 带引号的多词输入自动拆分：'女人 中年 焦虑' -> ['女人','中年','焦虑']
    terms = [term for arg in args.terms for term in re.split(r"[\s,，、]+", arg) if term]
    args.terms = terms

    records = load()
    if args.stats:
        show_stats(records)
        return
    if args.id:
        found = [r for r in records if r["id"] == args.id]
        if not found:
            print(f"[未找到] 语料#{args.id}", file=sys.stderr)
            sys.exit(1)
        print_result(found[0], args.json)
        return

    candidates = [r for r in records if match_filter(r, args)]
    if not candidates:
        print("[无命中] 换个主题词，或去掉 --sheet/--platform 过滤再试", file=sys.stderr)
        sys.exit(2)

    scored = []
    for record in candidates:
        score, focused = score_record(record, args.terms)
        if args.terms and score <= 0:
            continue
        scored.append((score, record))
    if not scored:
        print("[无命中] 语料里没有同时命中这些关键词的条目，减少关键词或换主题词", file=sys.stderr)
        sys.exit(2)

    scored.sort(key=lambda pair: (-pair[0], -pair[1].get("engagement_value", 0)))
    top_score = scored[0][0]
    pool = [r for score, r in scored if score >= max(top_score * 0.6, 1)][:30]
    if args.random:
        random.shuffle(pool)
        results = pool[: args.top]
    else:
        results = [r for _, r in scored[: args.top]]

    for record in results:
        print_result(record, args.json)


if __name__ == "__main__":
    main()