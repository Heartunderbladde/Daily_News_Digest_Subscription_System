"""每日流水线：抓取 → 摘要 → 入库"""

from datetime import date

from news_summary.fetcher.hackernews import HackerNewsFetcher
from news_summary.fetcher.rss_36kr import RSS36krFetcher
from news_summary.summarizer.textrank import textrank_summarize
from news_summary.summarizer.llm_summarizer import summarize_article
from news_summary.storage.db import (
    init_db, get_connection, insert_article,
    get_articles_without_summary, upsert_summary,
)


def fetch_all() -> int:
    """抓取所有信息源，存入数据库。返回新增文章数。"""
    fetchers = [
        HackerNewsFetcher(),
        RSS36krFetcher(),
    ]

    conn = get_connection()
    inserted = 0
    today = str(date.today())

    for fetcher in fetchers:
        articles = fetcher.fetch()
        for art in articles:
            aid = insert_article(
                conn, art.source, art.title, art.url,
                content=art.content, raw_summary=art.raw_summary,
                fetch_date=today,
            )
            if aid:
                inserted += 1

    conn.commit()
    conn.close()
    print(f"[Pipeline] 抓取完成，新增 {inserted} 篇文章")
    return inserted


def summarize_all_pending(model: str = None) -> int:
    """对所有未生成摘要的文章，运行 TextRank + LLM 摘要。返回处理数。"""
    conn = get_connection()
    articles = get_articles_without_summary(conn)
    processed = 0

    for art in articles:
        content = art.get("content") or art.get("raw_summary") or ""
        title = art.get("title", "")

        if not content or len(content) < 50:
            continue

        # TextRank 抽取式
        textrank_result = textrank_summarize(content)

        # LLM 生成式（分类 + 三种长度摘要）
        llm_result = summarize_article(title, content, model=model)

        if llm_result is None:
            continue

        upsert_summary(
            conn,
            article_id=art["id"],
            category=llm_result.get("category", "其他"),
            one_sentence=llm_result.get("one_sentence", ""),
            short=llm_result.get("short", ""),
            long=llm_result.get("long", ""),
            textrank=textrank_result,
        )
        processed += 1

    conn.commit()
    conn.close()
    print(f"[Pipeline] 摘要生成完成，处理 {processed} 篇")
    return processed


def daily_run(model: str = None):
    """每日完整流程"""
    init_db()
    n = fetch_all()
    if n > 0:
        summarize_all_pending(model=model)
    print(f"[Pipeline] 每日任务完成")
