# CONTEXT.md — 每日资讯摘要订阅系统

## 项目概述

自动抓取多源资讯 → 抽取式/生成式摘要 → 自动分类 → Web 展示的端到端系统。

## 术语表

| 术语 | 定义 |
|------|------|
| **信息源 (Source)** | 文章获取渠道，支持 RSS 订阅和 HTTP API 两种协议 |
| **抓取 (Fetch)** | 从信息源获取文章元信息（标题、URL、简介）的过程 |
| **正文提取 (Article Extraction)** | 从文章 URL 下载 HTML 并用 newspaper3k 提取正文文本 |
| **抽取式摘要 (Extractive Summary)** | 基于 TextRank 算法从原文选取关键句，不生成新文本 |
| **生成式摘要 (Abstractive Summary)** | 由 LLM (Qwen2.5) 重新组织语言生成的摘要 |
| **分类 (Category)** | 文章主题标签，固定为：AI/科技、创业/商业、编程/技术、其他 |
| **长度档位 (Length Tier)** | 一句话 / 100字 / 200字 三档，用户可切换 |
| **参考摘要 (Reference Summary)** | 人工撰写的摘要，作为 ROUGE 评估的 ground truth |

## 技术选型决策

| 决策点 | 选择 | 依据 |
|--------|------|------|
| 信息源 | HN API + 36kr RSS | 稳定、免费、中英互补 |
| 模型 | Ollama qwen2.5:7b | 本地免费，8GB 显存可流畅运行 |
| Web 框架 | Streamlit | 适合内容展示型应用 |
| 持久化 | SQLite | 结构查询需求，单文件零配置 |
| 正文提取 | trafilatura | 现代内容提取库，Python 3.13 兼容 |
| RSS 解析 | lxml.etree | 直接解析 XML，避免 feedparser 3.13 兼容问题 |
| 分类方案 | LLM Prompt 分类 | 一次调用完成分类+摘要，类别稳定 |
| TextRank | 自己实现 | 体现技术深度，答辩有内容可讲 |
| 参考摘要 | 人工撰写 20 篇 | 真正的 ground truth，答辩方法论站得住 |
