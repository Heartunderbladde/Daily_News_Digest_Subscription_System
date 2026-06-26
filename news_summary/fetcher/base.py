"""抓取器基类"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date


@dataclass
class Article:
    """标准化文章数据结构"""
    source: str
    title: str
    url: str
    content: str | None = None       # 正文（抓取后填充）
    raw_summary: str | None = None   # RSS 原始简介
    fetch_date: str = field(default_factory=lambda: str(date.today()))


class BaseFetcher(ABC):
    """抓取器抽象基类"""

    @abstractmethod
    def fetch(self) -> list[Article]:
        """从信息源获取文章列表（含正文）"""
        ...
