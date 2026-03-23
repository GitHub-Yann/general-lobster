"""
摘要生成节点
使用 TextRank 或 Transformers 生成摘要
"""
import re
from typing import List, Dict, Any


def generate_summary(text: str, max_length: int = 500, min_length: int = 100,
                     ratio: float = 0.2) -> Dict[str, Any]:
    """
    生成文本摘要
    
    Args:
        text: 输入文本
        max_length: 摘要最大长度（字符数）
        min_length: 摘要最小长度（字符数）
        ratio: 摘要占原文比例
    
    Returns:
        {
            "summary": "生成的摘要",
            "method": "使用的方法",
            "original_length": 原文长度,
            "summary_length": 摘要长度,
            "compression_ratio": 压缩比
        }
    """
    if not text or not text.strip():
        return {
            "summary": "",
            "method": "none",
            "original_length": 0,
            "summary_length": 0,
            "compression_ratio": 0
        }
    
    original_length = len(text)
    
    # 如果文本较短，直接返回
    if original_length <= max_length:
        return {
            "summary": text.strip(),
            "method": "original",
            "original_length": original_length,
            "summary_length": original_length,
            "compression_ratio": 1.0
        }
    
    # 尝试使用 TextRank 提取关键句
    try:
        summary = _textrank_summary(text, ratio)
        method = "textrank"
    except Exception:
        # 备选：基于位置的摘要（取开头、结尾和中间）
        summary = _position_based_summary(text, max_length)
        method = "position"
    
    # 控制长度
    if len(summary) > max_length:
        summary = summary[:max_length].rsplit('。', 1)[0] + '。'
    
    summary_length = len(summary)
    compression_ratio = round(summary_length / original_length, 4) if original_length > 0 else 0
    
    return {
        "summary": summary,
        "method": method,
        "original_length": original_length,
        "summary_length": summary_length,
        "compression_ratio": compression_ratio
    }


def _textrank_summary(text: str, ratio: float = 0.2) -> str:
    """
    使用 TextRank 算法提取关键句
    """
    try:
        import jieba
        import networkx as nx
        from sklearn.feature_extraction.text import TfidfVectorizer
    except ImportError:
        raise ImportError("请安装 jieba, networkx, scikit-learn")
    
    # 分割句子
    sentences = _split_sentences(text)
    
    if len(sentences) <= 3:
        return ' '.join(sentences)
    
    # 计算句子数量
    num_sentences = max(1, int(len(sentences) * ratio))
    num_sentences = min(num_sentences, 10)  # 最多10句
    
    # 分词
    sentence_words = [' '.join(jieba.lcut(s)) for s in sentences]
    
    # 计算 TF-IDF 相似度矩阵
    try:
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform(sentence_words)
        similarity_matrix = (tfidf_matrix * tfidf_matrix.T).toarray()
    except Exception:
        # 如果 TF-IDF 失败，使用简单词重叠
        similarity_matrix = _simple_similarity(sentence_words)
    
    # 构建图并计算 TextRank
    nx_graph = nx.from_numpy_array(similarity_matrix)
    scores = nx.pagerank(nx_graph)
    
    # 按得分排序
    ranked_sentences = sorted(
        [(scores[i], s) for i, s in enumerate(sentences)],
        reverse=True
    )
    
    # 选择得分最高的句子，但保持原始顺序
    top_indices = sorted([
        sentences.index(s) for _, s in ranked_sentences[:num_sentences]
    ])
    
    summary_sentences = [sentences[i] for i in top_indices]
    
    return ' '.join(summary_sentences)


def _position_based_summary(text: str, max_length: int) -> str:
    """
    基于位置的摘要（开头 + 结尾 + 关键段落）
    """
    sentences = _split_sentences(text)
    
    if len(sentences) <= 5:
        return ' '.join(sentences)
    
    # 取前 30%、后 20% 的句子
    start_count = max(1, len(sentences) // 3)
    end_count = max(1, len(sentences) // 5)
    
    selected = sentences[:start_count] + sentences[-end_count:]
    
    summary = ' '.join(selected)
    
    # 如果还太长，截断
    if len(summary) > max_length:
        summary = summary[:max_length].rsplit('。', 1)[0] + '。'
    
    return summary


def _split_sentences(text: str) -> List[str]:
    """分割句子"""
    # 中文句子分隔符
    delimiters = r'[。！？\n]+'
    sentences = re.split(delimiters, text)
    
    # 清理并过滤
    result = []
    for s in sentences:
        s = s.strip()
        if len(s) > 10:  # 过滤太短的句子
            result.append(s)
    
    return result


def _simple_similarity(sentence_words: List[str]) -> List[List[float]]:
    """计算简单词重叠相似度"""
    n = len(sentence_words)
    similarity = [[0.0] * n for _ in range(n)]
    
    for i in range(n):
        for j in range(n):
            if i == j:
                similarity[i][j] = 1.0
            else:
                words_i = set(sentence_words[i].split())
                words_j = set(sentence_words[j].split())
                if words_i and words_j:
                    intersection = len(words_i & words_j)
                    union = len(words_i | words_j)
                    similarity[i][j] = intersection / union if union > 0 else 0
    
    return similarity
