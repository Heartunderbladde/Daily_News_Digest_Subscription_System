"""独立定时任务脚本 — 可配 Windows 任务计划或 cron"""

import sys
import os

# 确保项目根目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from news_summary.pipeline import daily_run
from news_summary.config import OLLAMA_MODEL


if __name__ == "__main__":
    daily_run(model=OLLAMA_MODEL)
