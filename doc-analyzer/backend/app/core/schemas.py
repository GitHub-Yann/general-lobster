"""
Pydantic 数据模型
"""
from typing import List, Optional, Any
from datetime import datetime
from pydantic import BaseModel


class TaskCreate(BaseModel):
    """创建任务请求"""
    config_name: str = "default"
    domain_keywords: Optional[str] = None  # 逗号分隔的领域关键词
    noise_words: Optional[str] = None  # 逗号分隔的噪音词


class TaskResponse(BaseModel):
    """任务响应"""
    task_id: str
    status: str
    message: Optional[str] = None
    filename: Optional[str] = None
    file_type: Optional[str] = None
    current_node: Optional[str] = None
    use_llm_refine: Optional[bool] = None
    llm_config_id: Optional[int] = None
    prompt_template_id: Optional[int] = None
    nodes: Optional[List[dict]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class TaskList(BaseModel):
    """任务列表响应"""
    total: int
    items: List[dict]


class TaskResult(BaseModel):
    """任务结果响应"""
    task_id: str
    keywords: List[dict]
    summary: str
    full_text: Optional[str] = None
    completed_at: Optional[str] = None


class RetryRequest(BaseModel):
    """重试请求"""
    from_node: str
