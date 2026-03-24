"""
关键词提取节点
使用 KeyBERT 进行关键词提取，支持用户自定义领域词和噪音词
"""
import json
import re
from typing import List, Dict, Any


def extract_keywords(text: str, top_n: int = 15, min_length: int = 2,
                     use_mmr: bool = True, diversity: float = 0.7,
                     domain_keywords: List[str] = None,
                     noise_words: List[str] = None) -> Dict[str, Any]:
    """
    从文本中提取关键词

    Args:
        text: 输入文本
        top_n: 提取关键词数量
        min_length: 关键词最小长度
        use_mmr: 是否使用 MMR (Maximal Marginal Relevance) 增加多样性
        diversity: MMR 多样性参数 (0-1)
        domain_keywords: 用户提供的领域关键词列表，这些词会被优先提取
        noise_words: 用户提供的噪音词列表，这些词会被过滤

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

    # 初始化默认列表
    domain_keywords = _normalize_terms(domain_keywords or [])
    noise_words = _normalize_terms(noise_words or [])
    # 添加默认噪音词
    default_noise = {'http', 'https', 'www', 'com', 'cn', 'org', 'net', 'html', 'htm'}
    noise_words_set = set(noise_words) | default_noise

    try:
        from keybert import KeyBERT
    except ImportError:
        raise ImportError("请安装 keybert: pip install keybert")

    # 初始化 KeyBERT
    try:
        kw_model = KeyBERT(model='paraphrase-multilingual-MiniLM-L12-v2')
    except Exception:
        kw_model = KeyBERT()

    # 文本预处理：去掉 URL/IP 等强噪音，减少无意义短语
    text = _clean_text_for_keywords(text)
    max_text_length = 10000
    if len(text) > max_text_length:
        text = text[:max_text_length]

    # 提取关键词
    try:
        if use_mmr:
            keywords = kw_model.extract_keywords(
                text,
                keyphrase_ngram_range=(1, 3),  # 支持1-3个词
                stop_words=None,
                top_n=top_n * 3,  # 多提取一些，后续过滤和加权
                use_mmr=True,
                diversity=diversity
            )
        else:
            keywords = kw_model.extract_keywords(
                text,
                keyphrase_ngram_range=(1, 3),
                stop_words=None,
                top_n=top_n * 3
            )
    except Exception as e:
        return _fallback_keyword_extraction(text, top_n, min_length, domain_keywords, noise_words_set)

    # 处理结果
    result = []
    seen = set()

    # 第一步：检查领域关键词是否在原文中，如果在则优先加入
    text_lower = text.lower()
    for domain_kw in domain_keywords:
        if domain_kw.lower() in text_lower and domain_kw.lower() not in seen:
            seen.add(domain_kw.lower())
            result.append({
                "word": domain_kw,
                "weight": 1.0  # 领域词给最高权重
            })

    # 第二步：处理 KeyBERT 提取的关键词
    for keyword, score in keywords:
        keyword_clean = keyword.strip()
        keyword_lower = keyword_clean.lower()

        # 过滤噪音词（支持部分匹配）
        is_noise = False
        for noise in noise_words_set:
            # 噪音词在关键词中，或关键词在噪音词中（且噪音词较长）
            if noise in keyword_lower:
                is_noise = True
                break
        if is_noise:
            continue
        # 限制关键词长度，避免提取完整句子（最多15个字符）
        if len(keyword_clean) > 15:
            continue
        if len(keyword_clean) < min_length:
            continue
        if keyword_lower in seen:
            continue
        if keyword_clean.isdigit() or not any(c.isalnum() for c in keyword_clean):
            continue
        # 过滤模板句式关键词
        if _is_template_keyword(keyword_clean):
            continue

        # 检查是否是领域关键词的变体
        is_domain = any(domain_kw.lower() in keyword_lower or keyword_lower in domain_kw.lower()
                       for domain_kw in domain_keywords)

        # 领域词加权
        final_score = float(score)
        if is_domain:
            final_score = min(1.0, final_score * 1.5)  # 提升50%权重

        seen.add(keyword_lower)
        result.append({
            "word": keyword_clean,
            "weight": round(final_score, 4)
        })

        if len(result) >= top_n:
            break

    # 按权重排序
    result.sort(key=lambda x: x["weight"], reverse=True)

    return {
        "keywords": result[:top_n],
        "total_keywords": len(result[:top_n])
    }


def _normalize_terms(terms: List[str]) -> List[str]:
    """对用户传入的词表做二次拆分与去重，避免单元素长串漏切分。"""
    result = []
    seen = set()

    for term in terms:
        if term is None:
            continue
        for chunk in re.split(r"[,，;；、\n\r\t]+", str(term)):
            item = chunk.strip().strip("\"'[](){}")
            if not item:
                continue
            key = item.lower()
            if key in seen:
                continue
            seen.add(key)
            result.append(item)

    return result


def _clean_text_for_keywords(text: str) -> str:
    """去掉 URL、IP:PORT、多余空白，降低地址模板对关键词的干扰。"""
    cleaned = re.sub(r"https?://\S+", " ", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b\d{1,3}(?:\.\d{1,3}){3}:\d+\b", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _is_template_keyword(keyword: str) -> bool:
    """过滤流程模板类短语，避免整句被当作关键词。"""
    template_tokens = ['如果', '例如', '情况', '答案', '调用方', '请提供', '是否需要', '比如']
    return any(token in keyword for token in template_tokens)


def _fallback_keyword_extraction(text: str, top_n: int, min_length: int,
                                 domain_keywords: List[str] = None,
                                 noise_words: set = None) -> Dict[str, Any]:
    """
    备选关键词提取方案（基于 TF-IDF）
    """
    try:
        import jieba
        from sklearn.feature_extraction.text import TfidfVectorizer
    except ImportError:
        raise ImportError("请安装 jieba 和 scikit-learn")

    domain_keywords = domain_keywords or []
    noise_words = noise_words or set()

    # 中文分词
    words = jieba.lcut(text)

    # 过滤停用词和短词
    stop_words = set(['的', '了', '在', '是', '我', '有', '和', '就', '不', '人',
                      '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去',
                      '你', '会', '着', '没有', '看', '好', '自己', '这', '那'])
    stop_words.update(noise_words)

    filtered_words = [w for w in words if len(w) >= min_length and w not in stop_words]

    # 优先添加领域关键词
    result = []
    seen = set()
    text_lower = text.lower()

    for domain_kw in domain_keywords:
        if domain_kw.lower() in text_lower and domain_kw.lower() not in seen:
            seen.add(domain_kw.lower())
            result.append({"word": domain_kw, "weight": 1.0})

    if not filtered_words:
        return {"keywords": result[:top_n], "total_keywords": len(result[:top_n])}

    # 使用 TF-IDF
    try:
        vectorizer = TfidfVectorizer(max_features=100, ngram_range=(1, 2))
        tfidf_matrix = vectorizer.fit_transform([' '.join(filtered_words)])

        feature_names = vectorizer.get_feature_names_out()
        scores = tfidf_matrix.toarray()[0]

        # 排序并取前 N
        word_scores = list(zip(feature_names, scores))
        word_scores.sort(key=lambda x: x[1], reverse=True)

        for word, score in word_scores:
            if word.lower() in seen:
                continue
            if any(noise in word.lower() for noise in noise_words):
                continue
            seen.add(word.lower())
            result.append({"word": word, "weight": round(float(score), 4)})

            if len(result) >= top_n:
                break

        return {
            "keywords": result[:top_n],
            "total_keywords": len(result[:top_n])
        }
    except Exception:
        # 如果 TF-IDF 也失败，使用简单词频
        from collections import Counter
        word_counts = Counter(filtered_words)
        most_common = word_counts.most_common(top_n)

        # 归一化权重
        max_count = most_common[0][1] if most_common else 1
        for word, count in most_common:
            if word.lower() not in seen:
                result.append({"word": word, "weight": round(count / max_count, 4)})

        return {
            "keywords": result[:top_n],
            "total_keywords": len(result[:top_n])
        }
