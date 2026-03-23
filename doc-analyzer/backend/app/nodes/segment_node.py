"""
智能分段节点
长文档自动分段处理
"""
import re
from typing import List, Dict, Any


def segment_text(text: str, max_segment_length: int = 2000, overlap: int = 200) -> Dict[str, Any]:
    """
    将长文本分段处理
    
    Args:
        text: 输入文本
        max_segment_length: 每段最大字符数
        overlap: 段之间重叠字符数（保持上下文连贯）
    
    Returns:
        {
            "segments": ["段落1", "段落2", ...],
            "segment_count": 段落数量,
            "total_length": 总长度,
            "avg_length": 平均段落长度
        }
    """
    if not text or not text.strip():
        return {
            "segments": [],
            "segment_count": 0,
            "total_length": 0,
            "avg_length": 0
        }
    
    # 先按自然段落分割
    paragraphs = _split_paragraphs(text)
    
    # 如果文本较短，不需要分段
    if len(text) <= max_segment_length:
        return {
            "segments": [text],
            "segment_count": 1,
            "total_length": len(text),
            "avg_length": len(text)
        }
    
    # 合并段落为固定长度的段
    segments = []
    current_segment = []
    current_length = 0
    
    for para in paragraphs:
        para_length = len(para)
        
        # 如果当前段落本身超过最大长度，需要进一步分割
        if para_length > max_segment_length:
            # 先保存之前的段落
            if current_segment:
                segments.append('\n'.join(current_segment))
                current_segment = []
                current_length = 0
            
            # 分割长段落
            sub_segments = _split_long_paragraph(para, max_segment_length, overlap)
            segments.extend(sub_segments)
            continue
        
        # 检查加入当前段落后是否超过限制
        if current_length + para_length + 1 > max_segment_length:
            # 保存当前段
            if current_segment:
                segments.append('\n'.join(current_segment))
            
            # 新段开始（带重叠）
            if overlap > 0 and current_segment:
                overlap_text = _get_overlap_text(current_segment, overlap)
                current_segment = [overlap_text, para] if overlap_text else [para]
                current_length = len(overlap_text) + para_length + 1 if overlap_text else para_length
            else:
                current_segment = [para]
                current_length = para_length
        else:
            current_segment.append(para)
            current_length += para_length + 1
    
    # 保存最后一段
    if current_segment:
        segments.append('\n'.join(current_segment))
    
    # 统计
    total_length = sum(len(s) for s in segments)
    avg_length = total_length // len(segments) if segments else 0
    
    return {
        "segments": segments,
        "segment_count": len(segments),
        "total_length": total_length,
        "avg_length": avg_length
    }


def _split_paragraphs(text: str) -> List[str]:
    """按自然段落分割文本"""
    # 统一换行符
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    # 按多个换行符分割段落
    paragraphs = re.split(r'\n\s*\n', text)
    
    # 清理每个段落
    result = []
    for para in paragraphs:
        para = para.strip()
        if para:
            # 移除段落内的多余换行
            para = re.sub(r'\n+', ' ', para)
            para = re.sub(r' +', ' ', para)
            result.append(para)
    
    return result


def _split_long_paragraph(para: str, max_length: int, overlap: int) -> List[str]:
    """分割长段落"""
    segments = []
    start = 0
    
    while start < len(para):
        end = start + max_length
        
        if end >= len(para):
            segments.append(para[start:])
            break
        
        # 尝试在句子边界分割
        segment = para[start:end]
        
        # 查找最后一个句号、问号、感叹号
        for delim in ['。', '？', '！', '. ', '? ', '! ', '；', '; ']:
            last_delim = segment.rfind(delim)
            if last_delim > max_length * 0.5:  # 至少保留一半内容
                end = start + last_delim + 1
                segment = para[start:end]
                break
        
        segments.append(segment)
        start = end - overlap  # 重叠部分
    
    return segments


def _get_overlap_text(paragraphs: List[str], overlap: int) -> str:
    """获取重叠文本"""
    # 从最后几个段落获取重叠文本
    overlap_text = ""
    for para in reversed(paragraphs):
        if len(overlap_text) + len(para) <= overlap:
            overlap_text = para + '\n' + overlap_text
        else:
            remaining = overlap - len(overlap_text)
            if remaining > 0:
                overlap_text = para[-remaining:] + '\n' + overlap_text
            break
    
    return overlap_text.strip()
