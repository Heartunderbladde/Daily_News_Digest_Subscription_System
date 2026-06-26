"""SQLite 持久化层"""

import sqlite3
from datetime import date
from contextlib import contextmanager
from news_summary.config import DB_PATH


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


@contextmanager
def transaction():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """初始化数据库表"""
    with transaction() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                content TEXT,
                raw_summary TEXT,
                fetch_date DATE NOT NULL,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(source, url)
            );

            CREATE TABLE IF NOT EXISTS summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id INTEGER NOT NULL UNIQUE,
                category TEXT,
                one_sentence TEXT,
                short TEXT,
                long TEXT,
                textrank TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (article_id) REFERENCES articles(id)
            );

            CREATE INDEX IF NOT EXISTS idx_articles_fetch_date ON articles(fetch_date);
            CREATE INDEX IF NOT EXISTS idx_summaries_category ON summaries(category);
        """)


# --- Article CRUD ---

def insert_article(conn, source: str, title: str, url: str,
                   content: str = None, raw_summary: str = None,
                   fetch_date: str = None) -> int | None:
    """插入文章，已存在则跳过。返回 article id 或 None"""
    fetch_date = fetch_date or str(date.today())
    try:
        cur = conn.execute(
            """INSERT OR IGNORE INTO articles (source, title, url, content, raw_summary, fetch_date)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (source, title, url, content, raw_summary, fetch_date),
        )
        if cur.rowcount == 0:
            return None
        return cur.lastrowid
    except sqlite3.IntegrityError:
        return None


def get_articles_by_date(conn, fetch_date: str = None):
    """获取指定日期的文章（含摘要），按分类排序"""
    fetch_date = fetch_date or str(date.today())
    rows = conn.execute(
        """SELECT a.*, s.category, s.one_sentence, s.short, s.long, s.textrank
           FROM articles a
           LEFT JOIN summaries s ON a.id = s.article_id
           WHERE a.fetch_date = ?
           ORDER BY s.category, a.id""",
        (fetch_date,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_articles_by_category(conn, category: str, fetch_date: str = None):
    """按分类获取文章"""
    fetch_date = fetch_date or str(date.today())
    rows = conn.execute(
        """SELECT a.*, s.category, s.one_sentence, s.short, s.long, s.textrank
           FROM articles a
           JOIN summaries s ON a.id = s.article_id
           WHERE s.category = ? AND a.fetch_date = ?
           ORDER BY a.id""",
        (category, fetch_date),
    ).fetchall()
    return [dict(r) for r in rows]


def get_available_dates(conn) -> list[str]:
    """返回有数据的所有日期"""
    rows = conn.execute(
        "SELECT DISTINCT fetch_date FROM articles ORDER BY fetch_date DESC"
    ).fetchall()
    return [r["fetch_date"] for r in rows]


def get_articles_without_summary(conn) -> list[dict]:
    """获取尚未生成摘要的文章"""
    rows = conn.execute(
        """SELECT a.* FROM articles a
           LEFT JOIN summaries s ON a.id = s.article_id
           WHERE s.id IS NULL"""
    ).fetchall()
    return [dict(r) for r in rows]


def get_all_articles_with_summaries(conn) -> list[dict]:
    """获取所有已生成摘要的文章（用于评估）"""
    rows = conn.execute(
        """SELECT a.*, s.category, s.one_sentence, s.short, s.long, s.textrank
           FROM articles a
           JOIN summaries s ON a.id = s.article_id
           ORDER BY a.fetch_date, a.id"""
    ).fetchall()
    return [dict(r) for r in rows]


# --- Summary CRUD ---

def upsert_summary(conn, article_id: int, category: str = None,
                   one_sentence: str = None, short: str = None,
                   long: str = None, textrank: str = None):
    """插入或更新摘要"""
    conn.execute(
        """INSERT INTO summaries (article_id, category, one_sentence, short, long, textrank)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(article_id) DO UPDATE SET
               category=excluded.category,
               one_sentence=excluded.one_sentence,
               short=excluded.short,
               long=excluded.long,
               textrank=excluded.textrank,
               created_at=CURRENT_TIMESTAMP""",
        (article_id, category, one_sentence, short, long, textrank),
    )
