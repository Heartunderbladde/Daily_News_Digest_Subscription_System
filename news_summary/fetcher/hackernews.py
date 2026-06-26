"""Hacker News API 抓取器"""

import requests
import trafilatura

from news_summary.config import SOURCES, REQUEST_TIMEOUT, USER_AGENT
from news_summary.fetcher.base import BaseFetcher, Article


HEADERS = {"User-Agent": USER_AGENT}


class HackerNewsFetcher(BaseFetcher):

    def __init__(self):
        cfg = SOURCES["hackernews"]
        self.base_url = cfg["url"]
        self.max_articles = cfg["max_articles"]
        self.source_name = cfg["name"]

    def fetch(self) -> list[Article]:
        articles = []

        # 1. 获取 Top Stories ID 列表
        try:
            resp = requests.get(
                f"{self.base_url}/topstories.json",
                timeout=REQUEST_TIMEOUT,
                headers=HEADERS,
            )
            resp.raise_for_status()
            story_ids = resp.json()[:self.max_articles]
        except requests.RequestException as e:
            print(f"[HN] 获取 story IDs 失败: {e}")
            return articles

        # 2. 逐个获取详情
        for sid in story_ids:
            try:
                resp = requests.get(
                    f"{self.base_url}/item/{sid}.json",
                    timeout=REQUEST_TIMEOUT,
                    headers=HEADERS,
                )
                resp.raise_for_status()
                item = resp.json()
            except requests.RequestException:
                continue

            title = item.get("title", "")
            url = item.get("url", "")
            if not title or not url:
                continue

            # 3. 抓取正文
            content = self._extract_content(url)
            if not content:
                continue

            articles.append(Article(
                source=self.source_name,
                title=title,
                url=url,
                content=content,
            ))

        print(f"[HN] 成功抓取 {len(articles)}/{self.max_articles} 篇文章")
        return articles

    def _extract_content(self, url: str) -> str | None:
        """用 trafilatura 提取正文"""
        try:
            downloaded = trafilatura.fetch_url(url)
            if downloaded:
                text = trafilatura.extract(downloaded, include_links=False,
                                           include_images=False, include_tables=False)
                if text and len(text.strip()) >= 100:
                    return text.strip()
        except Exception:
            pass
        return None
