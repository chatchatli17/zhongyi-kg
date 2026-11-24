#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Streamlit 检索界面：症状反查证型 / 药材速查。

    streamlit run app.py
"""

from pathlib import Path

import pandas as pd
import streamlit as st

DATA = Path(__file__).resolve().parent / "data"


@st.cache_data
def load():
    herbs = pd.read_csv(DATA / "herbs.csv", encoding="utf-8-sig")
    formulas = pd.read_csv(DATA / "formulas.csv", encoding="utf-8-sig")
    syndromes = pd.read_csv(DATA / "syndromes.csv", encoding="utf-8-sig")
    return herbs, formulas, syndromes


def split(field):
    return [x.strip() for x in str(field).split(";") if x.strip()]


st.set_page_config(page_title="中医药知识图谱检索", page_icon="🌿", layout="wide")
herbs, formulas, syndromes = load()

st.title("🌿 中医药知识图谱检索")
st.caption(
    f"药材 {len(herbs)} 味 · 方剂 {len(formulas)} 首 · 证型 {len(syndromes)} 个　"
    "｜　数据摘编自《中药学》教材与药典公开条目，仅供数据工程练习，勿作诊疗依据"
)

mode = st.sidebar.radio("模式", ["症状 → 证型 → 方剂", "药材速查"])

if mode == "症状 → 证型 → 方剂":
    query = st.text_input(
        "输入症状，用空格分隔",
        value="恶寒 无汗 脉浮紧",
        help="例如：恶寒 无汗 脉浮紧 / 食少 便溏 乏力 / 失眠 心悸",
    )
    keys = [k for k in query.replace("，", " ").replace(",", " ").split() if k]

    if not keys:
        st.info("至少输入一个症状关键词。")
        st.stop()

    rows = []
    for _, s in syndromes.iterrows():
        symptoms = split(s["symptoms"])
        hit = [k for k in keys if any(k in sym for sym in symptoms)]
        if hit:
            rows.append({**s.to_dict(), "命中症状": len(hit), "对应": "、".join(hit)})

    if not rows:
        st.warning("没有证型命中这些症状，试试减少关键词或换个说法（如「乏力」「纳差」）。")
        st.stop()

    df = pd.DataFrame(rows).sort_values("命中症状", ascending=False)
    st.subheader(f"候选证型：{len(df)} 个")
    st.dataframe(
        df[["sid", "name", "principle", "formula_id", "命中症状", "对应"]].rename(
            columns={"sid": "编号", "name": "证型", "principle": "治法",
                     "formula_id": "方剂", "对应": "命中"}
        ),
        hide_index=True,
        use_container_width=True,
    )

    picked = st.selectbox("展开证型", df["name"].tolist())
    row = df[df["name"] == picked].iloc[0]
    f = formulas[formulas["fid"] == row["formula_id"]]

    left, right = st.columns([1, 2])
    with left:
        st.markdown(f"**证型**：{row['name']}")
        st.markdown(f"**治法**：{row['principle']}")
        st.markdown("**症状**：")
        for sym in split(row["symptoms"]):
            st.markdown(f"- {sym}")
    with right:
        if f.empty:
            st.warning("该证型未关联方剂。")
        else:
            f = f.iloc[0]
            st.markdown(f"**主治方剂**：{f['name']}（{f['fid']}）　{f['note']}")
            comp = split(f["composition"])
            detail = herbs[herbs["name"].isin(comp)].copy()
            detail["组内位置"] = detail["name"].apply(lambda x: comp.index(x))
            detail = detail.sort_values("组内位置")[
                ["name", "nature", "meridians", "effects", "caution"]
            ].rename(
                columns={"name": "药材", "nature": "性味", "meridians": "归经",
                         "effects": "功效", "caution": "禁忌"}
            )
            st.dataframe(detail, hide_index=True, use_container_width=True)
            st.caption(f"共 {len(comp)} 味组成，其中 {len(detail)} 味已收录属性。")

else:
    name = st.selectbox("选择药材", sorted(herbs["name"].tolist()))
    h = herbs[herbs["name"] == name].iloc[0]

    c1, c2, c3 = st.columns(3)
    c1.metric("性味", h["nature"])
    c2.metric("归经", h["meridians"].replace(";", "、"))
    c3.metric("分类", h["category"])

    st.markdown("**功效**")
    st.markdown("　·　".join(split(h["effects"])))
    if isinstance(h["caution"], str) and h["caution"].strip():
        st.error(f"禁忌与注意：{h['caution']}")

    used = formulas[formulas["composition"].apply(lambda c: name in split(c))]
    st.markdown(f"**出现在 {len(used)} 首方剂中**")
    if used.empty:
        st.caption("未被本项目收录的方剂使用（多为单味应用）。")
    else:
        st.dataframe(
            used[["fid", "name", "note"]].rename(columns={"fid": "编号", "name": "方剂", "note": "定位"}),
            hide_index=True,
            use_container_width=True,
        )
