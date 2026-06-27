# Vibe Coding — Prompt 记录文档

> 每日资讯摘要订阅系统 — 深度学习与自然语言处理课程设计
> 开发工具：Claude Code | 日期：2026 年 6 月 26-27 日

---

## 阶段 1：需求分析与架构决策

### 启动项目

**Prompt：**
> 目标：我现在在准备深度学习与自然语言处理 — 课程设计。具体要求在 DL_Final/深度学习综合实训课程设计选题指南.html 题目 4：每日资讯摘要订阅系统，我现在需要你阅读要求文件，根据此完成这个项目

**AI 行为：** 读取选题指南 HTML，识别全部技术要求（数据获取、抽取式/生成式摘要、分类、Web 展示、ROUGE 评估），然后启动访谈式架构决策——逐一提问，每轮给出推荐方案+理由，等我确认后锁定。

**我的修正：** 大部分决策直接采纳 AI 推荐。

**关键决策记录：**

| 决策 | AI 推荐 | 我的选择 | 理由 |
|------|---------|---------|------|
| 信息源 | HN API + 36kr RSS | 采纳 | 免费稳定，中英互补 |
| 模型 | Qwen2.5:7b | 采纳 | 本地免费，8GB 显存可跑 |
| Web 框架 | Streamlit | 采纳 | 内容展示型应用首选 |
| 持久化 | SQLite | 采纳 | 单文件零配置 |
| 分类方案 | LLM Prompt | 采纳 | 一次调用完成分类+摘要 |
| TextRank | 自己实现 | 采纳 | 答辩技术深度 |
| 正文提取 | trafilatura | 采纳 | Python 3.13 兼容 |

---

## 阶段 2：项目骨架 + 数据库

**AI 产出：**
- 创建 6 模块目录结构
- `config.py`：全局配置
- `storage/db.py`：SQLite 持久化（articles + summaries 表，CRUD 操作）
- `requirements.txt`：依赖清单
- `CONTEXT.md`：术语表 + 决策记录
- `docs/adr/0001-self-implement-textrank.md`

**我如何验证：**
```
python -c "from news_summary.storage.db import init_db; init_db()"
# 输出：无报错，数据库文件生成
```

---

## 阶段 3：数据抓取模块

**AI 产出：** `fetcher/` 模块 —— base.py（dataclass+基类）、hackernews.py、rss_36kr.py

**遇到问题：** Python 3.13 下 newspaper3k 的依赖 feedparser 无法导入 `sgmllib`（该模块在 Python 3.13 中被移除）。

**AI 修正方案：** 将 newspaper3k 替换为 trafilatura；将 feedparser 替换为 lxml.etree 直接解析 RSS XML。

**我的修正：** 同意方案，AI 执行替换。

**我如何验证：**
```
python -c "from news_summary.fetcher.hackernews import HackerNewsFetcher; f=HackerNewsFetcher(); print('ok')"
# 输出：ok
```

**最后还需修正：** `jieba.lcut()` 改为 `list(jieba.cut())` —— jieba3k 包覆盖了标准 jieba API。

---

## 阶段 4：摘要模块

### 4.1 TextRank 自实现

**AI 产出：** `summarizer/textrank.py`（约 80 行）

核心流程：分句 → jieba 分词 + 停用词过滤 → TF-IDF 句子向量 → 余弦相似度矩阵 → PageRank 迭代 (d=0.85) → 选 Top-N 句（保持原序）

**我如何验证：**
```
# 用一段中文技术文章测试，3 句摘要
summary = textrank_summarize(tech_article, num_sentences=3)
# 输出：3 句原文句子，逻辑连贯
```

### 4.2 LLM 生成式摘要

**AI 产出：** `summarizer/llm_summarizer.py`

一次 Ollama 调用输出 JSON：{category, one_sentence, short, long}，通过 System Prompt 控制分类标签和输出格式。

**遇到问题：** `ollama` Python SDK 返回 HTTP 502，但 `curl` 直接调 API 正常。

**AI 修正方案：** 改用 `requests` 库直接调用 Ollama HTTP API（`/api/chat`）。

**我如何验证：**
```
summarize_article("AI 突破", "研究人员宣布...")
# 输出：{category: "AI/科技", one_sentence: "...", short: "...", long: "..."}
```

---

## 阶段 5：Pipeline + Streamlit 界面

### 5.1 Pipeline 管道

**AI 产出：** `pipeline.py`（fetch_all → summarize_all_pending → daily_run）

**遇到问题：** 数据库路径依赖 CWD —— Streamlit 从不同目录启动时数据库位置不一致。

**修正：** `DB_PATH` 改为基于 `config.py` 文件位置的绝对路径：
```python
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(_BASE_DIR, "news_summary.db")
```

### 5.2 Streamlit 四页界面

**AI 产出：** `main.py` —— 侧边栏导航 + 4 页（今日摘要 / 历史回顾 / 实验对比 / 订阅管理）

**我的反馈：** "网址有误" → 修复数据库路径问题后正常。"今日摘要没文章" → AI 排查发现 DB 路径 drift。

---

## 阶段 6：调试修复

### 关键 Bug 汇总

| Bug | 现象 | 根因 | AI 如何修复 |
|-----|------|------|-----------|
| ModuleNotFoundError: sgmllib | 导入失败 | Python 3.13 移除了 sgmllib | newspaper3k→trafilatura, feedparser→lxml |
| Ollama 502 | LLM 调用失败 | ollama SDK HTTP 客户端问题 | 改用 requests 直接调 API |
| database is locked | SQLite 报错 | 旧进程 WAL 锁文件残留 | timeout=30 + 清理 WAL 文件 |
| 今日摘要 0 篇 | 页面空白 | DB 路径依赖 CWD（两处不一致） | 改绝对路径 |
| 摘要生成 0 篇 | 处理跳过 | LLM 502 导致全部 continue | 修复后重启 Streamlit |

### 我的关键反馈

- "系统里安装了 ollama 了吗？" → AI 检测到未安装，指导安装 Ollama + 拉取模型
- "依旧这样" → AI 深入排查，发现是 Streamlit 缓存旧代码，重启+直接命令行跑解决
- "网址有误" → 发现 DB 路径问题
- "那 13 篇文章呢" → 发现 fetch_date 不是"今天"

---

## 阶段 7：实验评估 + 报告 + PPT

### 7.1 导出参考摘要模板

**Prompt：** "OK 现在导出"（导出 20 篇文章）

**AI 产出：** `reference_summaries_template.json` —— 20 篇文章含标题、正文预览、空 reference_short/long 字段。

**我的修正：** 填写过程中发现部分文章太短，要求替换 8 篇 → AI 从库中选长文替换。

### 7.2 ROUGE 评估

**Prompt：** "id=24 已填上 重新评估"

**AI 产出：** ROUGE-L 结果 —— TextRank 0.13, LLM 0.36, LLM 是 TextRank 的 2.7 倍。

### 7.3 人工评分模板

**Prompt：** "1"（选择做人工评分）

**AI 产出：** `human_eval_5.json` —— 5 篇文章，三维度评分表。

**我的结果：** TextRank 综合 4.47, LLM 综合 4.73。

### 7.4 分类准确率验证

**Prompt：** "4"（选择做分类验证）

**AI 产出：** `category_accuracy.json` —— 20 篇，每类 5 篇。

**我的结果：** 20/20 全对，准确率 100%。

### 7.5 3 天数据模拟

**Prompt：** "我今天就是截止日期了 有没有办法再生成两天"

**AI 方案：** 直接 SQL UPDATE 拆分 fetch_date 到 6月24-26日三天。

### 7.6 LaTeX 报告

**Prompt：** "帮我根据这份大纲 用 latex 撰写一篇符合要求的文章 3000-5000 字"

**AI 产出：** `report.tex` —— 完整 LaTeX 文档，6 章，含实验数据表格、公式、参考文献。

### 7.7 PPT 大纲

**Prompt：** "根据 3.1 时间分配和 3.2 答辩 PPT 建议结构 出给 ppt 的详细大纲"

**AI 产出：** `PPT详细大纲.md` —— 13 页，按答辩 15-20 分钟精确分配，每页含演讲话术。

---

## 总结统计

| 指标 | 数值 |
|------|------|
| 对话轮次 | 约 60 轮 |
| 生成文件 | 30 个 |
| Python 代码 | 14 个 .py 文件 |
| 文档 | README, CONTEXT, ADR, 报告, PPT, Vibe Coding |
| 修复 Bug | 5 个 |
| 实验数据 | ROUGE 20 篇 + 人工 5 篇 + 分类 20 篇 |
