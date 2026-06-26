"""自实现 TextRank 抽取式摘要算法

算法流程：
1. 分句 → 2. 分词 → 3. 构建 TF-IDF 句子向量
4. 计算余弦相似度矩阵 → 5. PageRank 迭代 → 6. 选取 Top-N 句（保持原序）
"""

import re
import numpy as np
from collections import Counter
import jieba


def split_sentences(text: str) -> list[str]:
    """按中英文标点分句"""
    text = text.replace("\n", "。")
    # 在句末标点处切分，保留标点
    sentences = re.split(r"(?<=[。！？.!?；;])", text)
    return [s.strip() for s in sentences if len(s.strip()) >= 10]


def tokenize(sentence: str) -> list[str]:
    """jieba 分词，过滤停用词和标点"""
    stopwords = {
        "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一",
        "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着",
        "没有", "看", "好", "自己", "这", "他", "她", "它", "们", "那", "些",
        "所", "为", "所以", "因为", "但是", "然而", "虽然", "如果", "可以",
        "还是", "这个", "那个", "什么", "怎么", "如何", "为什么", "被", "把",
        "从", "对", "与", "及", "或", "等", "其", "之", "而", "且", "但",
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "can", "shall", "to", "of", "in", "for",
        "on", "with", "at", "by", "from", "as", "into", "through", "during",
        "before", "after", "above", "below", "between", "under", "again",
        "further", "then", "once", "here", "there", "when", "where", "why",
        "how", "all", "both", "each", "few", "more", "most", "other", "some",
        "such", "no", "nor", "not", "only", "own", "same", "so", "than",
        "too", "very", "just", "because", "but", "however", "although",
    }
    words = list(jieba.cut(sentence))
    return [w.strip() for w in words if w.strip() and w.strip() not in stopwords]


def build_tfidf_matrix(sentences: list[str]) -> np.ndarray:
    """构建句子 TF-IDF 矩阵"""
    tokenized = [tokenize(s) for s in sentences]

    # 计算 IDF
    N = len(sentences)
    df = Counter()
    for tokens in tokenized:
        for word in set(tokens):
            df[word] += 1

    vocab = list(df.keys())
    idf = {w: np.log((N + 1) / (df[w] + 1)) + 1 for w in vocab}
    word_to_idx = {w: i for i, w in enumerate(vocab)}

    # 构建 TF-IDF 矩阵
    V = len(vocab)
    tfidf = np.zeros((N, V))
    for i, tokens in enumerate(tokenized):
        if not tokens:
            continue
        tf = Counter(tokens)
        for word, count in tf.items():
            if word in word_to_idx:
                tfidf[i, word_to_idx[word]] = (count / len(tokens)) * idf[word]

    return tfidf


def cosine_similarity_matrix(tfidf: np.ndarray) -> np.ndarray:
    """计算句子间的余弦相似度矩阵"""
    norms = np.linalg.norm(tfidf, axis=1, keepdims=True)
    norms[norms == 0] = 1  # 避免除零
    normalized = tfidf / norms
    sim = normalized @ normalized.T
    np.fill_diagonal(sim, 0)  # 自相似度置零
    return sim


def pagerank(sim_matrix: np.ndarray, d: float = 0.85, max_iter: int = 100,
             tol: float = 1e-6) -> np.ndarray:
    """PageRank 迭代"""
    N = sim_matrix.shape[0]
    # 转移矩阵：按列归一化
    col_sums = sim_matrix.sum(axis=0)
    col_sums[col_sums == 0] = 1
    M = sim_matrix / col_sums

    # 初始分数均匀分布
    scores = np.ones(N) / N

    for _ in range(max_iter):
        prev = scores.copy()
        scores = (1 - d) / N + d * (M @ scores)
        if np.abs(scores - prev).sum() < tol:
            break

    return scores


def textrank_summarize(text: str, num_sentences: int = 3) -> str:
    """TextRank 抽取式摘要主函数"""
    sentences = split_sentences(text)
    if len(sentences) <= num_sentences:
        return "".join(sentences)

    tfidf = build_tfidf_matrix(sentences)
    sim = cosine_similarity_matrix(tfidf)
    scores = pagerank(sim)

    # 选 Top-N，保持原文顺序
    ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
    top_indices = sorted(i for i, _ in ranked[:num_sentences])

    return "".join(sentences[i] for i in top_indices)
