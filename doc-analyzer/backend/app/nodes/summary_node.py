"""
摘要生成节点
使用 TextRank 或 Transformers 生成摘要，支持领域词和噪音词过滤
"""
import re
from typing import List, Dict, Any, Optional


def generate_summary(text: str, max_length: int = 500, min_length: int = 100,
                     ratio: float = 0.2,
                     domain_keywords: Optional[List[str]] = None,
                     noise_words: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    生成文本摘要

    Args:
        text: 输入文本
        max_length: 摘要最大长度（字符数）
        min_length: 摘要最小长度（字符数）
        ratio: 摘要占原文比例
        domain_keywords: 领域关键词，优先选择包含这些词的句子
        noise_words: 噪音词，过滤包含这些词的句子

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

    # 初始化配置
    domain_keywords = domain_keywords or []
    noise_words = noise_words or []
    default_noise = {'http://', 'https://', 'api/v', '/svc', '.com', '.cn', '.html'}
    noise_set = set(noise_words) | default_noise

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

    # 优先使用结构化摘要（按标题/章节组织，更适合文档介绍类场景）
    try:
        summary = _structured_summary(text, max_length, min_length, domain_keywords, noise_set)
        method = "structured"
    except Exception:
        summary = ""

    # 结构化摘要不足时，回退到 TextRank
    if len(summary.strip()) < max(60, min_length // 2):
        try:
            summary = _textrank_summary(text, ratio, domain_keywords, noise_set)
            method = "textrank"
        except Exception:
            # 备选：基于位置的摘要
            summary = _position_based_summary(text, max_length, domain_keywords, noise_set)
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


def _is_noise_sentence(sentence: str, noise_set: set) -> bool:
    """判断句子是否包含太多噪音"""
    sentence_lower = sentence.lower()
    # 如果句子中噪音词占比过高，认为是噪音句
    noise_count = sum(1 for noise in noise_set if noise in sentence_lower)
    # 同时检查是否包含URL模式
    has_url = 'http' in sentence_lower or 'https' in sentence_lower
    has_path = '/' in sentence and ('api' in sentence_lower or 'svc' in sentence_lower)
    is_checklist = _is_checklist_sentence(sentence)
    # 过滤策略不要过激：避免因为命中单个噪音词误删有效句
    return has_url or has_path or noise_count >= 2 or is_checklist


def _score_sentence_by_domain(sentence: str, domain_keywords: List[str]) -> float:
    """根据领域关键词给句子打分"""
    if not domain_keywords:
        return 0.0
    sentence_lower = sentence.lower()
    score = sum(1 for kw in domain_keywords if kw.lower() in sentence_lower)
    return score / len(domain_keywords)


def _textrank_summary(text: str, ratio: float = 0.2,
                      domain_keywords: List[str] = None,
                      noise_set: set = None) -> str:
    """
    使用 TextRank 算法提取关键句，支持领域词加权和噪音过滤
    """
    try:
        import jieba
        import networkx as nx
        from sklearn.feature_extraction.text import TfidfVectorizer
    except ImportError:
        raise ImportError("请安装 jieba, networkx, scikit-learn")

    domain_keywords = domain_keywords or []
    noise_set = noise_set or set()

    # 分割句子
    sentences = _split_sentences(text)

    if len(sentences) <= 3:
        return ' '.join(sentences)

    # 过滤噪音句
    filtered_sentences = [(i, s) for i, s in enumerate(sentences)
                          if not _is_noise_sentence(s, noise_set)]

    if not filtered_sentences:
        # 如果全部过滤了，回退到原始句子
        filtered_sentences = list(enumerate(sentences))

    # 计算句子数量
    num_sentences = max(1, int(len(filtered_sentences) * ratio))
    num_sentences = min(num_sentences, 10)  # 最多10句

    # 分词
    sentence_words = [' '.join(jieba.lcut(s)) for _, s in filtered_sentences]

    # 计算 TF-IDF 相似度矩阵
    try:
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform(sentence_words)
        similarity_matrix = (tfidf_matrix * tfidf_matrix.T).toarray()
    except Exception:
        similarity_matrix = _simple_similarity(sentence_words)

    # 构建图并计算 TextRank
    nx_graph = nx.from_numpy_array(similarity_matrix)
    scores = nx.pagerank(nx_graph)

    # 结合领域词权重调整得分
    adjusted_scores = []
    for idx, (orig_idx, sentence) in enumerate(filtered_sentences):
        domain_score = _score_sentence_by_domain(sentence, domain_keywords)
        # TextRank得分 + 领域词加权（最多提升30%）
        final_score = scores[idx] * (1 + domain_score * 0.3)
        adjusted_scores.append((final_score, orig_idx, sentence))

    # 按得分排序
    adjusted_scores.sort(reverse=True)

    # 选择得分最高的句子，但保持原始顺序
    top_indices = sorted([
        orig_idx for _, orig_idx, _ in adjusted_scores[:num_sentences]
    ])

    summary_sentences = [sentences[i] for i in top_indices]

    return ' '.join(summary_sentences)


def _structured_summary(text: str, max_length: int, min_length: int,
                        domain_keywords: List[str] = None,
                        noise_set: set = None) -> str:
    """
    结构化摘要：基于标题和章节首要点构建“文档简介”风格摘要。
    """
    domain_keywords = domain_keywords or []
    noise_set = noise_set or set()

    lines = [line.strip() for line in text.splitlines() if line and line.strip()]
    if not lines:
        return ""

    title = lines[0]
    sections = _extract_sections(lines)
    if not sections:
        # 没有明确章节时回退为空，由上层继续回退 TextRank
        return ""

    heading_names = []
    point_sentences = []

    for heading, body in sections[:4]:
        normalized_heading = re.sub(r'^[一二三四五六七八九十]+、\s*', '', heading)
        if normalized_heading:
            heading_names.append(normalized_heading)

        candidate = _pick_representative_sentence(body, domain_keywords, noise_set)
        if candidate:
            point_sentences.append(candidate)

    # 生成导语
    intro_subject = '、'.join(heading_names[:3]) if heading_names else _normalize_title(title)
    intro = f"该文档围绕{intro_subject}进行说明，"
    intro += "重点概述核心内容、执行流程与关键注意事项。"

    parts = [intro]
    parts.extend(point_sentences[:3])
    summary = ' '.join(parts)

    # 控制长度
    if len(summary) > max_length:
        summary = summary[:max_length].rsplit('。', 1)[0] + '。'

    # 过短时补充一条章节概览
    if len(summary) < min_length and len(heading_names) > 1:
        extra = f"同时覆盖{ '、'.join(heading_names[1:4]) }等内容。"
        if len(summary) + len(extra) <= max_length:
            summary += extra

    return summary


def _position_based_summary(text: str, max_length: int,
                            domain_keywords: List[str] = None,
                            noise_set: set = None) -> str:
    """
    基于位置的摘要（开头 + 结尾 + 关键段落），支持领域词和噪音过滤
    """
    domain_keywords = domain_keywords or []
    noise_set = noise_set or set()

    sentences = _split_sentences(text)

    # 过滤噪音句
    sentences = [s for s in sentences if not _is_noise_sentence(s, noise_set)]

    if len(sentences) <= 5:
        return ' '.join(sentences)

    # 优先选择包含领域词的句子
    domain_sentences = [(i, s) for i, s in enumerate(sentences)
                        if _score_sentence_by_domain(s, domain_keywords) > 0]

    # 取前 30%、后 20% 的句子
    start_count = max(1, len(sentences) // 3)
    end_count = max(1, len(sentences) // 5)

    selected_indices = set()
    selected_indices.update(range(start_count))
    selected_indices.update(range(len(sentences) - end_count, len(sentences)))

    # 加入包含领域词的句子
    for idx, _ in domain_sentences[:3]:  # 最多加3句
        selected_indices.add(idx)

    selected = [sentences[i] for i in sorted(selected_indices)]

    summary = ' '.join(selected)

    if len(summary) > max_length:
        summary = summary[:max_length].rsplit('。', 1)[0] + '。'

    return summary


def _split_sentences(text: str) -> List[str]:
    """分割句子"""
    # 中文句子分隔符
    delimiters = r'[。！？；;\n]+'
    sentences = re.split(delimiters, text)
    
    # 清理并过滤
    result = []
    seen = set()
    for s in sentences:
        s = s.strip()
        if len(s) > 10:  # 过滤太短的句子
            normalized = re.sub(r'\s+', '', s)
            if normalized in seen:
                continue
            seen.add(normalized)
            result.append(s)
    
    return result


def _extract_sections(lines: List[str]) -> List[tuple]:
    """提取章节（标题 + 内容）。"""
    heading_pattern = re.compile(
        r'^([一二三四五六七八九十]+、|\d+(?:\.\d+)*[\.、]?\s+|[IVXivx]+[\.、]\s+)'
    )
    sections = []
    current_heading = None
    current_lines = []

    for line in lines:
        if heading_pattern.match(line):
            if current_heading and current_lines:
                sections.append((current_heading, current_lines))
            current_heading = line
            current_lines = []
        else:
            if current_heading:
                current_lines.append(line)

    if current_heading and current_lines:
        sections.append((current_heading, current_lines))

    return sections


def _pick_representative_sentence(lines: List[str], domain_keywords: List[str], noise_set: set) -> str:
    """从章节内容中挑一条代表句，用于构建简介。"""
    text = ' '.join(lines)
    candidates = _split_sentences(text)
    if not candidates:
        return ""

    scored = []
    for s in candidates:
        s = re.sub(r'^[（(]?[a-zA-Z0-9一二三四五六七八九十]+[)）\.、]\s*', '', s).strip()
        s = re.sub(r'^\d+(?:\.\d+)*\s*', '', s).strip()
        if len(s) < 16 or len(s) > 100:
            continue
        if _is_noise_sentence(s, noise_set):
            continue
        # 避免把章节细节编号句（如 1.1 / 2.3）当作摘要主句
        if re.search(r'\d+\.\d+', s):
            continue
        score = _score_sentence_by_domain(s, domain_keywords)
        # 偏好“说明/流程/配置/规范/路由”等介绍型句子
        if any(token in s for token in ['流程', '说明', '机制', '配置', '规范', '路由', '转发', '部署', '权限']):
            score += 0.2
        scored.append((score, s))

    if not scored:
        return ""

    scored.sort(key=lambda x: x[0], reverse=True)
    sentence = _shrink_clause(scored[0][1])
    if not sentence.endswith('。'):
        sentence += '。'
    return sentence


def _is_checklist_sentence(sentence: str) -> bool:
    """过滤问答清单、样例清单、表单项等结构化噪音句。"""
    s = sentence.strip().lower()
    patterns = [
        r'^[（(]?[a-z0-9]+[)）]',   # (a) / (1)
        r'^情况[0-9一二三四五六七八九十]',
        r'^答案[0-9一二三四五六七八九十]',
        r'^[（(]?[ivx]+[)）]',      # (i) / (iv)
        r'^\d+[\.\)、]\s*',         # 1. / 1) / 1、
    ]
    if any(re.search(p, s) for p in patterns):
        return True
    if '可忽略' in s or '⚠' in s:
        return True
    if re.search(r'（[a-z]）', s):
        return True
    # 通用清单特征：示例/表单式语言 + 多冒号/分号
    checklist_tokens = ['例如', '示例', '请提供', '备注', '填写', '选项', '格式如下', '如下']
    token_hits = sum(1 for token in checklist_tokens if token in s)
    punctuation_hits = s.count('：') + s.count(':') + s.count('；') + s.count(';')
    return token_hits >= 2 or (token_hits >= 1 and punctuation_hits >= 2)


def _shrink_clause(sentence: str) -> str:
    """对过长句进行温和裁剪，保留前半句核心信息。"""
    s = sentence.strip()
    if len(s) <= 56:
        return s
    for sep in ['，', ',', '；', ';']:
        idx = s.find(sep)
        if 18 <= idx <= 56:
            return s[:idx]
    return s


def _normalize_title(title: str) -> str:
    """清理标题前缀，得到更通用的摘要主语。"""
    t = (title or '').strip()
    if not t:
        return "文档主题"
    t = re.sub(r'^[一二三四五六七八九十]+、\s*', '', t)
    t = re.sub(r'^\d+(?:\.\d+)*\s*', '', t)
    return t[:24] if len(t) > 24 else t


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
