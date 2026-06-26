"""LLM 生成式摘要：通过 HTTP API 调用 Ollama，一次完成分类 + 三种长度摘要"""

import json
import re
import requests

from news_summary.config import OLLAMA_MODEL, OLLAMA_HOST, CATEGORIES


CHAT_URL = f"{OLLAMA_HOST}/api/chat"

SYSTEM_PROMPT = """你是一个专业的新闻摘要助手。你的任务：
1. 阅读给定的新闻文章
2. 将文章分类到以下类别之一：{categories}
3. 生成三种长度的摘要

你必须严格按以下 JSON 格式输出，不要输出其他内容：
{{
    "category": "类别名称",
    "one_sentence": "一句话摘要（不超过50字）",
    "short": "约100字的短摘要",
    "long": "约200字的详细摘要"
}}

注意：
- 摘要必须基于原文事实，不要编造信息
- 中文文章用中文摘要，英文文章翻译为中文再摘要
- 一句话摘要必须控制在50字以内
- JSON 必须是合法的，用双引号"""


def _clean_json(text: str) -> str:
    """从 LLM 输出中提取 JSON"""
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if m:
        text = m.group(1)
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        return m.group(0)
    return text


def summarize_article(title: str, content: str, model: str = None) -> dict | None:
    """
    调用 Ollama 生成分类 + 摘要。

    返回:
        {"category": str, "one_sentence": str, "short": str, "long": str}
        或 None（失败时）
    """
    model = model or OLLAMA_MODEL

    # 截断正文（保留前 3000 字符）
    truncated = content[:3000] if len(content) > 3000 else content

    prompt = f"""文章标题：{title}

文章正文：
{truncated}

请按 JSON 格式输出分类和摘要。"""

    try:
        resp = requests.post(
            CHAT_URL,
            json={
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT.format(categories=", ".join(CATEGORIES)),
                    },
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
                "options": {"temperature": 0.3, "num_predict": 800},
            },
            timeout=120,
        )

        if resp.status_code != 200:
            print(f"[LLM] HTTP {resp.status_code}: {resp.text[:200]}")
            return None

        data = resp.json()
        raw = data["message"]["content"].strip()
        json_str = _clean_json(raw)
        result = json.loads(json_str)

        # 验证必要字段
        for field in ["category", "one_sentence", "short", "long"]:
            if field not in result:
                result[field] = ""

        # 规范化分类
        if result["category"] not in CATEGORIES:
            result["category"] = "其他"

        return result

    except json.JSONDecodeError as e:
        print(f"[LLM] JSON 解析失败: {e}\n原始输出: {raw}")
        return None
    except requests.RequestException as e:
        print(f"[LLM] 请求失败: {e}")
        return None
    except Exception as e:
        print(f"[LLM] 调用失败: {e}")
        return None
