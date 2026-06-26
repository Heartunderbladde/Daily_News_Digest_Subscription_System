"""ROUGE 评估：对比 TextRank vs LLM 摘要 vs 人工参考摘要"""

import json
import re
import numpy as np

# rouge-score 的 ROUGE-L 基于英文空格分词，中文需先用 jieba 分词再计算
import jieba
from rouge_score import rouge_scorer

from news_summary.storage.db import get_connection, get_all_articles_with_summaries


def _tokenize_chinese(text: str) -> str:
    """将中文文本分词后用空格连接，适配 rouge-score 的英文分词逻辑"""
    return " ".join(jieba.cut(text))


def compute_rouge_l(reference: str, candidate: str) -> dict:
    """计算 ROUGE-L F1 / Precision / Recall"""
    scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=False)
    ref_tokenized = _tokenize_chinese(reference)
    cand_tokenized = _tokenize_chinese(candidate)
    scores = scorer.score(ref_tokenized, cand_tokenized)
    return {
        "rougeL_precision": round(scores["rougeL"].precision, 4),
        "rougeL_recall": round(scores["rougeL"].recall, 4),
        "rougeL_f1": round(scores["rougeL"].fmeasure, 4),
    }


def evaluate_from_db(reference_file: str = None) -> dict:
    """
    从数据库读取所有已生成摘要的文章，进行评估。

    reference_file: JSON 文件，格式 {"article_id": {"short": "...", "long": "..."}, ...}
    如果为 None，则在 LLM 摘要之间做内部对比。
    """
    conn = get_connection()
    articles = get_all_articles_with_summaries(conn)
    conn.close()

    references = {}
    if reference_file:
        with open(reference_file, "r", encoding="utf-8") as f:
            references = json.load(f)

    results = {
        "textrank_vs_llm_short": [],
        "textrank_vs_llm_long": [],
    }

    for art in articles:
        aid = str(art["id"])
        textrank = art.get("textrank", "")
        llm_short = art.get("short", "")
        llm_long = art.get("long", "")

        # TextRank vs LLM short（用 LLM short 作为近似参考）
        if textrank and llm_short:
            scores = compute_rouge_l(llm_short, textrank)
            results["textrank_vs_llm_short"].append({
                "article_id": art["id"],
                "title": art["title"],
                **scores,
            })

        # LLM short vs LLM long（长度对 ROUGE 的影响）
        if llm_short and llm_long:
            scores = compute_rouge_l(llm_long, llm_short)
            results["textrank_vs_llm_long"].append(scores)

    # 汇总统计
    summary = {}
    for key, vals in results.items():
        if vals:
            f1s = [v.get("rougeL_f1", 0) for v in vals]
            summary[key] = {
                "count": len(f1s),
                "mean_f1": round(np.mean(f1s), 4),
                "std_f1": round(np.std(f1s), 4),
            }

    results["summary"] = summary
    return results


def evaluate_with_references(reference_file: str) -> dict:
    """
    用人工参考摘要评估 TextRank 和 LLM。

    reference_file 格式：
    [
        {
            "article_id": 1,
            "title": "...",
            "reference_short": "人工撰写100字摘要",
            "reference_long": "人工撰写200字摘要"
        },
        ...
    ]
    """
    with open(reference_file, "r", encoding="utf-8") as f:
        refs = json.load(f)

    ref_map = {str(r["article_id"]): r for r in refs}

    conn = get_connection()
    articles = get_all_articles_with_summaries(conn)
    conn.close()

    results = []
    for art in articles:
        aid = str(art["id"])
        if aid not in ref_map:
            continue

        ref = ref_map[aid]
        textrank = art.get("textrank", "")
        llm_short = art.get("short", "")
        llm_long = art.get("long", "")

        entry = {
            "article_id": art["id"],
            "title": art["title"],
            "source": art["source"],
        }

        # TextRank vs 人工参考
        if textrank and ref.get("reference_short"):
            entry["textrank_rougeL"] = compute_rouge_l(ref["reference_short"], textrank)

        # LLM short vs 人工参考
        if llm_short and ref.get("reference_short"):
            entry["llm_short_rougeL"] = compute_rouge_l(ref["reference_short"], llm_short)

        # LLM long vs 人工参考
        if llm_long and ref.get("reference_long"):
            entry["llm_long_rougeL"] = compute_rouge_l(ref["reference_long"], llm_long)

        results.append(entry)

    # 汇总
    textrank_f1s = [r["textrank_rougeL"]["rougeL_f1"] for r in results if "textrank_rougeL" in r]
    llm_short_f1s = [r["llm_short_rougeL"]["rougeL_f1"] for r in results if "llm_short_rougeL" in r]
    llm_long_f1s = [r["llm_long_rougeL"]["rougeL_f1"] for r in results if "llm_long_rougeL" in r]

    summary = {
        "textrank": {"count": len(textrank_f1s), "mean_rougeL_f1": round(np.mean(textrank_f1s), 4)} if textrank_f1s else None,
        "llm_short": {"count": len(llm_short_f1s), "mean_rougeL_f1": round(np.mean(llm_short_f1s), 4)} if llm_short_f1s else None,
        "llm_long": {"count": len(llm_long_f1s), "mean_rougeL_f1": round(np.mean(llm_long_f1s), 4)} if llm_long_f1s else None,
    }

    return {"details": results, "summary": summary}


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        result = evaluate_with_references(sys.argv[1])
    else:
        result = evaluate_from_db()
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
