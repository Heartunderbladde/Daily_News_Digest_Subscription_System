"""全局配置"""

import os

# --- 路径 ---
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(_BASE_DIR, "news_summary.db")

# --- 模型 ---
OLLAMA_MODEL = "qwen2.5:7b"
OLLAMA_HOST = "http://localhost:11434"

# --- 信息源 ---
SOURCES = {
    "hackernews": {
        "name": "Hacker News",
        "type": "api",
        "url": "https://hacker-news.firebaseio.com/v0",
        "max_articles": 30,
    },
    "36kr": {
        "name": "36氪",
        "type": "rss",
        "url": "https://36kr.com/feed",
        "max_articles": 20,
    },
}

# --- 分类标签 ---
CATEGORIES = ["AI/科技", "创业/商业", "编程/技术", "其他"]

# --- 摘要长度档位 ---
SUMMARY_TIERS = {
    "one_sentence": "用一句话（不超过50字）概括核心信息",
    "short": "生成约100字的短摘要",
    "long": "生成约200字的详细摘要",
}

# --- 数据库 ---

# --- 抓取 ---
REQUEST_TIMEOUT = 15  # 秒
USER_AGENT = "NewsSummaryBot/1.0 (Course Project)"
