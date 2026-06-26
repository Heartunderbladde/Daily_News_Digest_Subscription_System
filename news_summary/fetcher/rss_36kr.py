"""36氪 RSS 抓取器 — 直接解析 XML，不依赖 feedparser"""

import re
import requests
from lxml import etree
import trafilatura

from news_summary.config import SOURCES, REQUEST_TIMEOUT, USER_AGENT
from news_summary.fetcher.base import BaseFetcher, Article


HEADERS = {"User-Agent": USER_AGENT}

# RSS 2.0 / Atom 的命名空间
NS_MAP = {
    "atom": "http://www.w3.org/2005/Atom",
    "dc": "http://purl.org/dc/elements/1.1/",
    "content": "http://purl.org/rss/1.0/modules/content/",
}


class RSS36krFetcher(BaseFetcher):

    def __init__(self):
        cfg = SOURCES["36kr"]
        self.feed_url = cfg["url"]
        self.max_articles = cfg["max_articles"]
        self.source_name = cfg["name"]

    def fetch(self) -> list[Article]:
        articles = []

        # 1. 获取并解析 RSS XML
        try:
            resp = requests.get(
                self.feed_url,
                timeout=REQUEST_TIMEOUT,
                headers=HEADERS,
            )
            resp.raise_for_status()
            root = etree.fromstring(resp.content)
        except requests.RequestException as e:
            print(f"[36kr] RSS 获取失败: {e}")
            return articles
        except etree.XMLSyntaxError as e:
            print(f"[36kr] XML 解析失败: {e}")
            return articles

        # 2. 检测 feed 类型并提取条目
        items = self._extract_items(root)[:self.max_articles]

        for item in items:
            title, link, raw_summary = item
            if not title or not link:
                continue

            # 3. 用 trafilatura 抓取正文
            content = self._extract_content(link)
            if not content:
                if len(raw_summary) >= 100:
                    content = raw_summary
                else:
                    continue

            articles.append(Article(
                source=self.source_name,
                title=title,
                url=link,
                content=content,
                raw_summary=raw_summary if raw_summary != content else None,
            ))

        print(f"[36kr] 成功抓取 {len(articles)}/{self.max_articles} 篇文章")
        return articles

    def _extract_items(self, root) -> list[tuple]:
        """从 RSS/Atom feed 中提取 (title, link, summary) 三元组"""
        items = []

        # RSS 2.0: <channel><item>...</item></channel>
        for item in root.findall(".//item"):
            title = self._text(item, "title")
            link = self._text(item, "link")
            summary = (
                self._text(item, "description") or
                self._text(item, "summary") or
                self._text(item, "{http://purl.org/rss/1.0/modules/content/}encoded") or
                ""
            )
            summary = re.sub(r"<[^>]+>", "", summary).strip()
            items.append((title, link, summary))

        # Atom: <feed><entry>...</entry></feed>
        if not items:
            for entry in root.findall(".//{http://www.w3.org/2005/Atom}entry"):
                title = self._text(entry, "{http://www.w3.org/2005/Atom}title")
                link_el = entry.find("{http://www.w3.org/2005/Atom}link")
                link = link_el.get("href", "") if link_el is not None else ""
                summary = (
                    self._text(entry, "{http://www.w3.org/2005/Atom}summary") or
                    self._text(entry, "{http://www.w3.org/2005/Atom}content") or
                    ""
                )
                summary = re.sub(r"<[^>]+>", "", summary).strip()
                items.append((title, link, summary))

        return items

    @staticmethod
    def _text(el, tag) -> str:
        """安全获取元素文本"""
        child = el.find(tag)
        if child is not None:
            return (child.text or "").strip()
        return ""

    def _extract_content(self, url: str) -> str | None:
        """用 trafilatura 提取正文"""
        try:
            downloaded = trafilatura.fetch_url(url)
            if downloaded:
                text = trafilatura.extract(downloaded, include_links=False,
                                           include_images=False, include_tables=False)
                if text and len(text.strip()) >= 50:
                    return text.strip()
        except Exception:
            pass
        return None
