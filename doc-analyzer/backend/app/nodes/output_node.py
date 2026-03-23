"""
输出节点
组装最终结果
"""
from typing import Dict, Any, List


def generate_output(task_id: str, parse_result: Dict, segment_result: Dict,
                   keyword_result: Dict, summary_result: Dict) -> Dict[str, Any]:
    """
    组装最终输出结果
    
    Args:
        task_id: 任务ID
        parse_result: 解析节点结果
        segment_result: 分段节点结果
        keyword_result: 关键词节点结果
        summary_result: 摘要节点结果
    
    Returns:
        {
            "task_id": "任务ID",
            "title": "文档标题",
            "keywords": [...],
            "summary": "摘要",
            "full_text": "完整文本",
            "statistics": {
                "word_count": 字数,
                "segment_count": 段落数,
                "keyword_count": 关键词数
            }
        }
    """
    return {
        "task_id": task_id,
        "title": parse_result.get("title", ""),
        "keywords": keyword_result.get("keywords", []),
        "summary": summary_result.get("summary", ""),
        "full_text": parse_result.get("text", ""),
        "statistics": {
            "word_count": parse_result.get("word_count", 0),
            "segment_count": segment_result.get("segment_count", 0),
            "keyword_count": keyword_result.get("total_keywords", 0),
            "compression_ratio": summary_result.get("compression_ratio", 0)
        }
    }
