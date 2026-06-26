"""每日资讯摘要订阅系统 — Streamlit Web 入口"""

import sys
import os
from datetime import date, timedelta

import streamlit as st

# 确保项目根目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from news_summary.config import CATEGORIES, SUMMARY_TIERS, OLLAMA_MODEL, SOURCES
from news_summary.storage.db import (
    init_db, get_connection,
    get_articles_by_date, get_articles_by_category,
    get_available_dates, get_articles_without_summary,
)
from news_summary.pipeline import fetch_all, summarize_all_pending


st.set_page_config(
    page_title="每日资讯摘要",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --- 初始化 ---
init_db()


# --- 侧边栏 ---
st.sidebar.title("📰 每日资讯摘要")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "导航",
    ["📰 今日摘要", "📅 历史回顾", "📊 实验对比", "⚙️ 订阅管理"],
    label_visibility="collapsed",
)

st.sidebar.markdown("---")

# 摘要长度档位选择
tier_key = st.sidebar.selectbox(
    "摘要长度",
    list(SUMMARY_TIERS.keys()),
    format_func=lambda x: {
        "one_sentence": "一句话",
        "short": "约100字",
        "long": "约200字",
    }[x],
    key="summary_tier",
)

st.sidebar.markdown("---")

# 数据刷新
if st.sidebar.button("🔄 刷新数据", use_container_width=True):
    with st.spinner("正在抓取最新文章..."):
        n = fetch_all()
    with st.spinner("正在生成摘要..."):
        m = summarize_all_pending(model=OLLAMA_MODEL)
    st.sidebar.success(f"新增 {n} 篇文章，生成 {m} 篇摘要")
    st.rerun()


# --- 辅助函数 ---
def render_summary_card(article: dict, tier: str):
    """渲染单篇文章摘要卡片"""
    summary_text = article.get(tier, "") or article.get("short", "") or "暂无摘要"
    category = article.get("category", "其他")
    source = article.get("source", "未知来源")
    title = article.get("title", "无标题")
    url = article.get("url", "#")

    # 分类颜色标记
    category_colors = {
        "AI/科技": "🔵",
        "创业/商业": "🟢",
        "编程/技术": "🟡",
        "其他": "⚪",
    }
    icon = category_colors.get(category, "⚪")

    with st.container(border=True):
        st.markdown(f"{icon} **{category}** | *{source}*")
        st.markdown(f"### [{title}]({url})")
        st.markdown(summary_text)


# --- 页面 1: 今日摘要 ---
if page == "📰 今日摘要":

    st.title("📰 今日摘要")
    today = str(date.today())

    # 检查今天是否有数据
    conn = get_connection()
    articles = get_articles_by_date(conn, today)
    conn.close()

    if not articles:
        st.info("今日暂无数据。点击左侧「🔄 刷新数据」开始抓取。", icon="ℹ️")
    else:
        # 按分类统计
        category_counts = {}
        for a in articles:
            cat = a.get("category", "其他")
            category_counts[cat] = category_counts.get(cat, 0) + 1

        cols = st.columns(len(CATEGORIES) + 1)
        for i, cat in enumerate(CATEGORIES):
            with cols[i]:
                count = category_counts.get(cat, 0)
                st.metric(label=cat, value=f"{count} 篇")
        with cols[-1]:
            st.metric(label="总计", value=f"{len(articles)} 篇")

        st.markdown("---")

        # 分类筛选
        selected_cat = st.selectbox(
            "筛选分类",
            ["全部"] + CATEGORIES,
            key="filter_category",
        )

        if selected_cat != "全部":
            articles = [a for a in articles if a.get("category") == selected_cat]

        # 渲染摘要列表
        for art in articles:
            render_summary_card(art, st.session_state.summary_tier)


# --- 页面 2: 历史回顾 ---
elif page == "📅 历史回顾":

    st.title("📅 历史回顾")

    conn = get_connection()
    dates = get_available_dates(conn)
    conn.close()

    if not dates:
        st.info("暂无历史数据。", icon="ℹ️")
    else:
        selected_date = st.selectbox("选择日期", dates)

        conn = get_connection()
        articles = get_articles_by_date(conn, selected_date)
        conn.close()

        if not articles:
            st.info(f"{selected_date} 无数据", icon="ℹ️")
        else:
            st.markdown(f"**{selected_date}** 共收录 **{len(articles)}** 篇文章")

            selected_cat = st.selectbox(
                "筛选分类",
                ["全部"] + CATEGORIES,
                key="history_category",
            )
            if selected_cat != "全部":
                articles = [a for a in articles if a.get("category") == selected_cat]

            for art in articles:
                render_summary_card(art, st.session_state.summary_tier)


# --- 页面 3: 实验对比 ---
elif page == "📊 实验对比":

    st.title("📊 摘要方案对比")

    st.markdown("""
    同一篇文章的**抽取式摘要（TextRank）**与**生成式摘要（LLM）**并排对比。
    评估指标：ROUGE-L（衡量摘要与参考摘要的重叠度）。
    """)

    conn = get_connection()
    articles = get_articles_by_date(conn, str(date.today()))
    conn.close()

    # 如果没有今日数据，尝试历史日期
    if not articles:
        conn = get_connection()
        archives = get_available_dates(conn)
        conn.close()
        if archives:
            conn = get_connection()
            articles = get_articles_by_date(conn, archives[0])
            conn.close()

    if not articles:
        st.warning("暂无数据，请先抓取文章。", icon="⚠️")
    else:
        # 筛选有 TextRank 和 LLM 摘要的文章
        comparable = [a for a in articles if a.get("textrank") and a.get("short")]

        if not comparable:
            st.warning("暂无同时包含 TextRank 和 LLM 摘要的文章。", icon="⚠️")
        else:
            titles = [f"[{a.get('id')}] {a.get('title', '')[:60]}" for a in comparable]
            selected_idx = st.selectbox(
                "选择文章",
                range(len(titles)),
                format_func=lambda i: titles[i],
            )

            art = comparable[selected_idx]

            col1, col2 = st.columns(2)

            with col1:
                st.subheader("📋 TextRank 抽取式")
                st.markdown(art.get("textrank", "暂无") or "暂无")

            with col2:
                st.subheader("🤖 LLM 生成式")
                st.markdown(art.get("short", "暂无") or "暂无")

            st.markdown("---")

            # ROUGE 评估模块（如果有参考摘要）
            st.subheader("📏 ROUGE-L 评估")

            from news_summary.evaluation.rouge_eval import compute_rouge_l

            ref_input = st.text_area(
                "粘贴人工参考摘要（用于计算 ROUGE-L）",
                placeholder="在此粘贴人工撰写的参考摘要...",
                height=100,
            )

            if ref_input:
                col_t, col_l = st.columns(2)
                tr_scores = compute_rouge_l(ref_input, art.get("textrank", ""))
                llm_scores = compute_rouge_l(ref_input, art.get("short", ""))

                with col_t:
                    st.metric("TextRank ROUGE-L F1", f"{tr_scores['rougeL_f1']:.4f}")
                with col_l:
                    st.metric("LLM ROUGE-L F1", f"{llm_scores['rougeL_f1']:.4f}")

                better = "TextRank" if tr_scores["rougeL_f1"] > llm_scores["rougeL_f1"] else "LLM 生成式"
                st.info(f"🏆 当前文章 ROUGE-L 胜出方：**{better}**")


# --- 页面 4: 订阅管理 ---
elif page == "⚙️ 订阅管理":

    st.title("⚙️ 订阅管理")

    st.markdown("### 当前信息源")

    for key, cfg in SOURCES.items():
        with st.container(border=True):
            col1, col2, col3 = st.columns([1, 2, 1])
            with col1:
                st.markdown(f"**{cfg['name']}**")
            with col2:
                st.markdown(f"类型：{cfg['type'].upper()} | 地址：`{cfg['url']}`")
            with col3:
                st.markdown(f"每次最多 {cfg['max_articles']} 篇")

    st.markdown("---")
    st.markdown("### 操作")

    col_a, col_b = st.columns(2)

    with col_a:
        if st.button("🔄 立即抓取所有信息源", use_container_width=True):
            with st.spinner("正在抓取..."):
                n = fetch_all()
            st.success(f"抓取完成，新增 {n} 篇文章")

    with col_b:
        if st.button("🤖 为未处理文章生成摘要", use_container_width=True):
            with st.spinner("正在生成摘要...（可能需要几分钟）"):
                m = summarize_all_pending(model=OLLAMA_MODEL)
            st.success(f"摘要生成完成，处理 {m} 篇")

    st.markdown("---")
    st.markdown("### 设置")

    st.markdown(f"- **LLM 模型**：`{OLLAMA_MODEL}`（通过 Ollama 本地运行）")
    st.markdown(f"- **分类标签**：{' / '.join(CATEGORIES)}")
    st.markdown(f"- **数据库**：`news_summary.db`（SQLite）")

    st.caption("信息源和模型配置在 `news_summary/config.py` 中修改。")
