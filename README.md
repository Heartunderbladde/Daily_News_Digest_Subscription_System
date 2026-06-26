# 每日资讯摘要订阅系统

深度学习与自然语言处理 — 课程设计（题目 4）

## 功能

- 🔄 自动从 **Hacker News API** 和 **36氪 RSS** 抓取每日资讯
- 📝 **TextRank 抽取式摘要**（自实现）与 **LLM 生成式摘要**（Qwen2.5）双方案
- 🏷️ 自动分类（AI/科技、创业/商业、编程/技术、其他）
- 📏 三种摘要长度：一句话 / 100字 / 200字
- 📊 ROUGE-L 评估对比 + 实验对比页面
- 💾 SQLite 持久化，支持历史回顾

## 环境要求

- Python 3.10+
- [Ollama](https://ollama.com) + qwen2.5 模型
- Windows / Mac / Linux

## 安装

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 拉取模型（二选一）
ollama pull qwen2.5:7b    # 推荐，效果好
ollama pull qwen2.5:1.5b  # 备用，速度快

# 3. 确保 Ollama 在后台运行
ollama serve
```

## 运行

```bash
cd news_summary
streamlit run main.py
```

浏览器打开 `http://localhost:8501`。

## 项目结构

```
news_summary/
├── main.py                  # Streamlit Web 入口
├── config.py                # 全局配置
├── pipeline.py              # 每日流水线（抓取→摘要→入库）
├── fetcher/
│   ├── base.py              # 抓取器基类
│   ├── hackernews.py        # HN API 抓取
│   └── rss_36kr.py          # 36氪 RSS 抓取
├── summarizer/
│   ├── textrank.py          # 自实现 TextRank 抽取式
│   └── llm_summarizer.py    # LLM 生成式摘要
├── storage/
│   └── db.py                # SQLite 持久化
├── scheduler/
│   └── daily.py             # 独立定时任务脚本
└── evaluation/
    └── rouge_eval.py        # ROUGE 评估工具
```

## 定时抓取

Windows 任务计划程序 / cron：

```bash
python news_summary/scheduler/daily.py
```

## 技术栈

| 组件 | 技术 |
|------|------|
| 前端 | Streamlit |
| 模型 | Ollama + Qwen2.5:7b |
| 数据库 | SQLite |
| 正文提取 | trafilatura |
| RSS 解析 | lxml |
| 中文分词 | jieba |
| RSS 解析 | feedparser |
| 评估 | rouge-score |

涉及课程知识：词向量、TF-IDF、TextRank、Prompt Engineering、结构化输出
