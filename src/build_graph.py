#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从三张源表构建知识图谱（节点 + 关系）。

6 类实体：症状 / 证型 / 方剂 / 药材 / 功效 / 归经
8 类关系：
  证型 --表现--> 症状
  证型 --主治--> 方剂
  方剂 --组成--> 药材
  药材 --功效--> 功效
  药材 --归经--> 归经
  药材 --性味--> 字面值
  证型 --治法--> 字面值
  药材 --禁忌--> 字面值

用法：
    python src/build_graph.py                 # 只打印统计
    python src/build_graph.py --out data/graph # 写出 nodes.csv 与 relations.csv
"""

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"

REL_CN = {
    "SYNDROME_SYMPTOM": "表现",
    "SYNDROME_FORMULA": "主治",
    "FORMULA_HERB": "组成",
    "HERB_EFFECT": "功效",
    "HERB_MERIDIAN": "归经",
    "HERB_NATURE": "性味",
    "SYNDROME_PRINCIPLE": "治法",
    "HERB_CAUTION": "禁忌",
}


def load(name):
    with open(DATA / name, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def split(field):
    return [x.strip() for x in (field or "").split(";") if x.strip()]


def build():
    herbs = load("herbs.csv")
    formulas = load("formulas.csv")
    syndromes = load("syndromes.csv")

    nodes = {}          # id -> (type, name)
    edges = []          # (head, rel, tail)

    def node(nid, ntype, name):
        nodes[nid] = (ntype, name)

    for s in syndromes:
        node(f"syn:{s['sid']}", "证型", s["name"])
        if s["principle"]:
            edges.append((f"syn:{s['sid']}", "SYNDROME_PRINCIPLE", s["principle"]))
        for sym in split(s["symptoms"]):
            node(f"sym:{sym}", "症状", sym)
            edges.append((f"syn:{s['sid']}", "SYNDROME_SYMPTOM", f"sym:{sym}"))
        if s["formula_id"]:
            edges.append((f"syn:{s['sid']}", "SYNDROME_FORMULA", f"for:{s['formula_id']}"))

    for f in formulas:
        node(f"for:{f['fid']}", "方剂", f["name"])
        for h in split(f["composition"]):
            node(f"herb:{h}", "药材", h)
            edges.append((f"for:{f['fid']}", "FORMULA_HERB", f"herb:{h}"))

    for h in herbs:
        hid = f"herb:{h['name']}"
        node(hid, "药材", h["name"])
        for eff in split(h["effects"]):
            node(f"eff:{eff}", "功效", eff)
            edges.append((hid, "HERB_EFFECT", f"eff:{eff}"))
        for mer in split(h["meridians"]):
            node(f"mer:{mer}", "归经", mer)
            edges.append((hid, "HERB_MERIDIAN", f"mer:{mer}"))
        if h["nature"]:
            edges.append((hid, "HERB_NATURE", h["nature"]))
        if h["caution"]:
            edges.append((hid, "HERB_CAUTION", h["caution"]))

    return nodes, edges


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None, help="输出前缀，如 data/graph")
    args = ap.parse_args()

    nodes, edges = build()
    type_count = Counter(t for t, _ in nodes.values())
    rel_count = Counter(r for _, r, _ in edges)

    print("== 实体 ==")
    for t, n in type_count.most_common():
        print(f"  {t:<4} {n:>4}")
    print(f"  合计   {len(nodes):>4}")

    print("\n== 关系 ==")
    for r, n in rel_count.most_common():
        print(f"  {REL_CN.get(r, r):<4} {n:>4}")
    print(f"  合计   {len(edges):>4}")

    # 引用完整性：关系末端若指向实体前缀，必须在 nodes 中
    missing = [e for e in edges if e[2].split(":")[0] in ("syn", "for", "herb", "sym", "eff", "mer")
               and e[2] not in nodes]
    if missing:
        print(f"\n[错误] {len(missing)} 条关系指向不存在的实体，例如：{missing[:3]}")
        sys.exit(1)
    print("\n引用完整性：通过")

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(f"{out}_nodes.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["id", "type", "name"])
            for nid, (t, name) in nodes.items():
                w.writerow([nid, t, name])
        with open(f"{out}_relations.csv", "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["head", "relation", "relation_cn", "tail"])
            for h, r, t in edges:
                w.writerow([h, r, REL_CN.get(r, r), t])
        print(f"\n已写出 {out}_nodes.csv（{len(nodes)} 行）与 {out}_relations.csv（{len(edges)} 行）")


if __name__ == "__main__":
    main()
