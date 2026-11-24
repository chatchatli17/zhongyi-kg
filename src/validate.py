#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据校验：字段完整性、唯一性、引用完整性、逻辑自洽。

用法：python src/validate.py    # 有错误时退出码为 1
"""

import csv
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"


def load(name):
    with open(DATA / name, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def split(field):
    return [x.strip() for x in (field or "").split(";") if x.strip()]


def main():
    errors, warns = [], []
    herbs = load("herbs.csv")
    formulas = load("formulas.csv")
    syndromes = load("syndromes.csv")

    # 1. 必填与非空
    for h in herbs:
        for col in ("name", "nature", "meridians", "effects", "category"):
            if not (h.get(col) or "").strip():
                errors.append(f"药材 [{h.get('name','?')}] 缺少字段 {col}")
    for f in formulas:
        for col in ("fid", "name", "composition", "syndrome_id"):
            if not (f.get(col) or "").strip():
                errors.append(f"方剂 [{f.get('name','?')}] 缺少字段 {col}")
    for s in syndromes:
        for col in ("sid", "name", "symptoms", "principle", "formula_id"):
            if not (s.get(col) or "").strip():
                errors.append(f"证型 [{s.get('name','?')}] 缺少字段 {col}")

    # 2. 唯一性
    for label, items, key in (("药材", herbs, "name"), ("方剂", formulas, "fid"), ("证型", syndromes, "sid")):
        names = [i[key] for i in items]
        dup = {n for n in names if names.count(n) > 1}
        if dup:
            errors.append(f"{label}主键重复：{sorted(dup)}")

    herb_names = {h["name"] for h in herbs}
    formula_ids = {f["fid"] for f in formulas}
    syndrome_ids = {s["sid"] for s in syndromes}
    formula_by_sid = {f["syndrome_id"]: f["fid"] for f in formulas}

    # 3. 引用完整性
    for f in formulas:
        if f["syndrome_id"] not in syndrome_ids:
            errors.append(f"方剂 [{f['name']}] 的证型 {f['syndrome_id']} 不存在")
        for h in split(f["composition"]):
            if h not in herb_names:
                errors.append(f"方剂 [{f['name']}] 含未收录药材 [{h}]")
    for s in syndromes:
        if s["formula_id"] not in formula_ids:
            errors.append(f"证型 [{s['name']}] 的方剂 {s['formula_id']} 不存在")
        f = next((x for x in formulas if x["fid"] == s["formula_id"]), None)
        if f and f["syndrome_id"] != s["sid"]:
            errors.append(f"证型 [{s['name']}] 与方剂 [{f['name']}] 的主治证型不一致")

    # 4. 逻辑自洽
    for s in syndromes:
        if len(split(s["symptoms"])) < 3:
            warns.append(f"证型 [{s['name']}] 症状少于 3 条，可能不足以支撑辨证")
        if f := formula_by_sid.get(s["sid"]):
            if f != s["formula_id"]:
                errors.append(f"证型 [{s['name']}] 与方剂表映射不一致")
    for f in formulas:
        if len(split(f["composition"])) < 2:
            errors.append(f"方剂 [{f['name']}] 组成少于 2 味，不像方剂")

    herb_used = set()
    for f in formulas:
        herb_used.update(split(f["composition"]))
    unused = sorted(herb_names - herb_used)

    print(f"药材 {len(herbs)} 味 / 方剂 {len(formulas)} 首 / 证型 {len(syndromes)} 个")
    print(f"错误 {len(errors)} 条，警告 {len(warns)} 条")
    if unused:
        print(f"未被任何方剂使用的药材 {len(unused)} 味：{', '.join(unused[:8])}{'...' if len(unused) > 8 else ''}")
    for e in errors:
        print("  [错误]", e)
    for w in warns:
        print("  [警告]", w)
    if errors:
        sys.exit(1)
    print("校验通过")


if __name__ == "__main__":
    main()
