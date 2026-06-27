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
    progress_area = st.sidebar.empty()

    progress_area.info("正在抓取最新文章...")
    n = fetch_all()
    progress_area.success(f"抓取完成，新增 {n} 篇文章")

    if n > 0:
        progress_area.info(f"正在生成摘要... 0/{n}")
        progress_bar = st.sidebar.progress(0, text="等待中...")
        status_text = st.sidebar.empty()

        def on_progress(idx, total, title, status):
            pct = idx / total
            progress_bar.progress(pct, text=f"{idx}/{total}")
            status_text.caption(f"{status}: {title[:50]}")

        m = summarize_all_pending(model=OLLAMA_MODEL, progress_callback=on_progress)
        progress_bar.progress(1.0, text=f"{m}/{n}")
        progress_area.success(f"新增 {n} 篇文章，生成 {m} 篇摘要")
        status_text.empty()
    else:
        progress_area.info("没有新文章")
        m = 0

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

    st.markdown("同一篇文章的 **TextRank 抽取式** 与 **LLM 生成式** 摘要并排对比。")

    # --- 加载全部可对比文章 ---
    conn = get_connection()
    all_dates = get_available_dates(conn)

    if not all_dates:
        st.warning("暂无数据，请先抓取文章。", icon="⚠️")
        conn.close()
    else:
        # 日期选择
        selected_date = st.selectbox(
            "📅 选择日期",
            ["全部"] + all_dates,
            format_func=lambda d: f"全部日期（{len(all_dates)} 天）" if d == "全部" else d,
        )

        if selected_date == "全部":
            articles = []
            for d in all_dates:
                articles.extend(get_articles_by_date(conn, d))
        else:
            articles = get_articles_by_date(conn, selected_date)

        # 只保留同时有 TextRank 和 LLM 摘要的
        comparable = [a for a in articles if a.get("textrank") and a.get("short")]

        if not comparable:
            st.warning("该日期内暂无同时包含 TextRank 和 LLM 摘要的文章。", icon="⚠️")
        else:
            # 统计
            st.metric("可对比文章", f"{len(comparable)} 篇")

            # --- 分类筛选 ---
            cat_filter = st.radio(
                "🏷️ 分类筛选",
                ["全部"] + CATEGORIES,
                horizontal=True,
            )
            if cat_filter != "全部":
                comparable = [a for a in comparable if a.get("category") == cat_filter]

            st.markdown("---")

            # --- 文章选择（卡片式，2 列） ---
            st.subheader("选择文章")
            category_colors = {
                "AI/科技": "🔵", "创业/商业": "🟢",
                "编程/技术": "🟡", "其他": "⚪",
            }

            # 分页：每页 10 篇
            page_size = 10
            total_pages = max(1, (len(comparable) + page_size - 1) // page_size)
            if total_pages > 1:
                page_num = st.selectbox("页码", range(1, total_pages + 1), format_func=lambda p: f"第 {p}/{total_pages} 页")
            else:
                page_num = 1

            start = (page_num - 1) * page_size
            page_articles = comparable[start:start + page_size]

            # 卡片网格
            cols = st.columns(2)
            selected_id = st.session_state.get("compare_selected_id", None)

            for i, art in enumerate(page_articles):
                with cols[i % 2]:
                    icon = category_colors.get(art.get("category", "其他"), "⚪")
                    card_label = f"{icon} **[{art['id']}] {art['title'][:55]}**  \n{art['source']} · {art.get('category', '')}"
                    if st.button(card_label, key=f"cmp_{art['id']}", use_container_width=True):
                        st.session_state["compare_selected_id"] = art["id"]
                        st.rerun()

            st.markdown("---")

            # --- 对比展示 ---
            if selected_id:
                selected_art = next((a for a in comparable if a["id"] == selected_id), None)
            elif comparable:
                selected_art = comparable[0]  # 默认选第一篇
            else:
                selected_art = None

            if selected_art:
                st.subheader(f"📄 {selected_art['title']}")
                st.caption(f"来源：{selected_art['source']} | 分类：{selected_art.get('category', '-')} | [原文链接]({selected_art.get('url', '#')})")

                # 四种摘要并排
                tab1, tab2, tab3, tab4 = st.tabs([
                    "📋 TextRank", "🤖 LLM 一句话", "🤖 LLM 100字", "🤖 LLM 200字"
                ])

                with tab1:
                    st.markdown(selected_art.get("textrank", "暂无") or "暂无")
                with tab2:
                    st.markdown(selected_art.get("one_sentence", "暂无") or "暂无")
                with tab3:
                    st.markdown(selected_art.get("short", "暂无") or "暂无")
                with tab4:
                    st.markdown(selected_art.get("long", "暂无") or "暂无")

                st.markdown("---")

                # --- ROUGE 评估 ---
                st.subheader("📏 ROUGE-L 评估")

                # 尝试加载预计算参考摘要
                import json, os
                ref_map = {}
                ref_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reference_summaries_template.json")
                if os.path.exists(ref_path):
                    try:
                        with open(ref_path, "r", encoding="utf-8") as f:
                            ref_data = json.load(f)
                        ref_map = {str(r["article_id"]): r for r in ref_data}
                    except Exception:
                        pass

                # 检查是否有预计算参考
                aid_str = str(selected_art["id"])
                if aid_str in ref_map and (ref_map[aid_str].get("reference_short") or ref_map[aid_str].get("reference_long")):
                    ref = ref_map[aid_str]
                    st.success("✅ 该文章已有人工参考摘要，以下为预计算 ROUGE-L 分数")

                    from news_summary.evaluation.rouge_eval import compute_rouge_l

                    ref_short = ref.get("reference_short", "")
                    ref_long = ref.get("reference_long", "")

                    r1 = compute_rouge_l(ref_short, selected_art.get("textrank", "")) if ref_short else None
                    r2 = compute_rouge_l(ref_short, selected_art.get("short", "")) if ref_short else None
                    r3 = compute_rouge_l(ref_long, selected_art.get("long", "")) if ref_long else None

                    mc1, mc2, mc3 = st.columns(3)
                    with mc1:
                        if r1:
                            st.metric("TextRank ROUGE-L F1", f"{r1['rougeL_f1']:.4f}")
                    with mc2:
                        if r2:
                            st.metric("LLM 100字 ROUGE-L F1", f"{r2['rougeL_f1']:.4f}")
                    with mc3:
                        if r3:
                            st.metric("LLM 200字 ROUGE-L F1", f"{r3['rougeL_f1']:.4f}")

                    # 胜出方
                    f1s = []
                    if r1: f1s.append(("TextRank", r1["rougeL_f1"]))
                    if r2: f1s.append(("LLM 100字", r2["rougeL_f1"]))
                    if r3: f1s.append(("LLM 200字", r3["rougeL_f1"]))
                    if f1s:
                        best = max(f1s, key=lambda x: x[1])
                        st.info(f"🏆 ROUGE-L 胜出方：**{best[0]}**（F1 = {best[1]:.4f}）")

                else:
                    st.info("该文章暂无预计算参考摘要。你可以粘贴人工参考摘要进行实时计算。")

                    ref_input = st.text_area(
                        "粘贴人工参考摘要",
                        placeholder="在此粘贴人工撰写的参考摘要...",
                        height=80,
                    )

                    if ref_input:
                        from news_summary.evaluation.rouge_eval import compute_rouge_l

                        col_t, col_l = st.columns(2)
                        tr_scores = compute_rouge_l(ref_input, selected_art.get("textrank", ""))
                        llm_scores = compute_rouge_l(ref_input, selected_art.get("short", ""))

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
            progress_bar = st.progress(0, text="检查待处理文章...")
            status_text = st.empty()

            def on_progress(idx, total, title, status):
                pct = idx / total
                progress_bar.progress(pct, text=f"{idx}/{total}")
                status_text.caption(f"{status}: {title[:50]}")

            m = summarize_all_pending(model=OLLAMA_MODEL, progress_callback=on_progress)
            if m > 0:
                progress_bar.progress(1.0, text=f"完成 {m} 篇")
                st.success(f"摘要生成完成，处理 {m} 篇")
            else:
                progress_bar.empty()
                st.info("没有待处理的文章")

    st.markdown("---")
    st.markdown("### 设置")

    st.markdown(f"- **LLM 模型**：`{OLLAMA_MODEL}`（通过 Ollama 本地运行）")
    st.markdown(f"- **分类标签**：{' / '.join(CATEGORIES)}")
    st.markdown(f"- **数据库**：`news_summary.db`（SQLite）")

    st.caption("信息源和模型配置在 `news_summary/config.py` 中修改。")
