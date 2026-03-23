"""
关键词提取节点
使用 KeyBERT 进行关键词提取
"""
import json
from typing import List, Dict, Any


def extract_keywords(text: str, top_n: int = 15, min_length: int = 2, 
                     use_mmr: bool = True, diversity: float = 0.7) -> Dict[str, Any]:
    """
    从文本中提取关键词
    
    Args:
        text: 输入文本
        top_n: 提取关键词数量
        min_length: 关键词最小长度
        use_mmr: 是否使用 MMR (Maximal Marginal Relevance) 增加多样性
        diversity: MMR 多样性参数 (0-1)
    
    Returns:
        {
            "keywords": [
                {"word": "关键词1", "weight": 0.95},
                {"word": "关键词2", "weight": 0.88},
                ...
            ],
            "total_keywords": 提取的关键词总数
        }
    """
    if not text or not text.strip():
        return {
            "keywords": [],
            "total_keywords": 0
        }
    
    try:
        from keybert import KeyBERT
    except ImportError:
        raise ImportError("请安装 keybert: pip install keybert")
    
    # 初始化 KeyBERT
    # 使用轻量级中文模型
    try:
        kw_model = KeyBERT(model='paraphrase-multilingual-MiniLM-L12-v2')
    except Exception:
        # 如果模型下载失败，使用默认模型
        kw_model = KeyBERT()
    
    # 文本预处理
    # 如果文本太长，分段处理
    max_text_length = 10000
    if len(text) > max_text_length:
        text = text[:max_text_length]
    
    # 提取关键词
    try:
        if use_mmr:
            keywords = kw_model.extract_keywords(
                text,
                keyphrase_ngram_range=(1, 2),  # 支持单个词和双词词组
                stop_words='english',  # 停用词
                top_n=top_n * 2,  # 多提取一些，后续过滤
                use_mmr=True,
                diversity=diversity
            )
        else:
            keywords = kw_model.extract_keywords(
                text,
                keyphrase_ngram_range=(1, 2),
                stop_words='english',
                top_n=top_n * 2
            )
    except Exception as e:
        # 如果 KeyBERT 失败，使用备选方案
        return _fallback_keyword_extraction(text, top_n, min_length)
    
    # 处理结果
    result = []
    seen = set()
    
    for keyword, score in keywords:
        # 清理关键词
        keyword = keyword.strip().lower()
        
        # 过滤条件
        if len(keyword) < min_length:
            continue
        if keyword in seen:
            continue
        
        # 过滤纯数字和纯符号
        if keyword.isdigit() or not any(c.isalnum() for c in keyword):
            continue
        
        seen.add(keyword)
        result.append({
            "word": keyword,
            "weight": round(float(score), 4)
        })
        
        if len(result) >= top_n:
            break
    
    return {
        "keywords": result,
        "total_keywords": len(result)
    }


def _fallback_keyword_extraction(text: str, top_n: int, min_length: int) -> Dict[str, Any]:
    """
    备选关键词提取方案（基于 TF-IDF）
    """
    try:
        import jieba
        from sklearn.feature_extraction.text import TfidfVectorizer
    except ImportError:
        raise ImportError("请安装 jieba 和 scikit-learn")
    
    # 中文分词
    words = jieba.lcut(text)
    
    # 过滤停用词和短词
    stop_words = set(['的', '了', '在', '是', '我', '有', '和', '就', '不', '人', 
                      '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去',
                      '你', '会', '着', '没有', '看', '好', '自己', '这', '那'])
    
    filtered_words = [w for w in words if len(w) >= min_length and w not in stop_words]
    
    if not filtered_words:
        return {"keywords": [], "total_keywords": 0}
    
    # 使用 TF-IDF
    try:
        vectorizer = TfidfVectorizer(max_features=100, ngram_range=(1, 2))
        tfidf_matrix = vectorizer.fit_transform([' '.join(filtered_words)])
        
        feature_names = vectorizer.get_feature_names_out()
        scores = tfidf_matrix.toarray()[0]
        
        # 排序并取前 N
        word_scores = list(zip(feature_names, scores))
        word_scores.sort(key=lambda x: x[1], reverse=True)
        
        result = [
            {"word": word, "weight": round(float(score), 4)}
            for word, score in word_scores[:top_n]
            if score > 0
        ]
        
        return {
            "keywords": result,
            "total_keywords": len(result)
        }
    except Exception:
        # 如果 TF-IDF 也失败，使用简单词频
        from collections import Counter
        word_counts = Counter(filtered_words)
        most_common = word_counts.most_common(top_n)
        
        # 归一化权重
        max_count = most_common[0][1] if most_common else 1
        result = [
            {"word": word, "weight": round(count / max_count, 4)}
            for word, count in most_common
        ]
        
        return {
            "keywords": result,
            "total_keywords": len(result)
        }
