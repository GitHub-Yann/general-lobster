"""
任务相关 API 路由
"""
import os
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.task import Task
from app.models.node_data import NodeData
from app.models.node_config import NodeConfig
from app.core.schemas import TaskCreate, TaskResponse, TaskList, TaskResult, RetryRequest

router = APIRouter()

# 上传目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 默认节点配置
DEFAULT_CONFIGS = [
    {
        "config_name": "default",
        "nodes": '["upload", "parse", "segment", "keyword", "summary", "output"]',
        "description": "默认完整流程，适用于 PDF/DOCX"
    },
    {
        "config_name": "txt_only",
        "nodes": '["upload", "segment", "keyword", "summary", "output"]',
        "description": "TXT 文件流程，跳过解析节点"
    },
    {
        "config_name": "keyword_only",
        "nodes": '["upload", "parse", "keyword", "output"]',
        "description": "仅提取关键词，快速模式"
    }
]


def init_default_configs(db: Session):
    """初始化默认节点配置"""
    for config in DEFAULT_CONFIGS:
        existing = db.query(NodeConfig).filter(
            NodeConfig.config_name == config["config_name"]
        ).first()
        if not existing:
            db.add(NodeConfig(**config))
    db.commit()


def get_file_type(filename: str) -> str:
    """根据文件名获取文件类型"""
    ext = filename.lower().split('.')[-1] if '.' in filename else ''
    if ext in ['pdf']:
        return 'pdf'
    elif ext in ['docx', 'doc']:
        return 'docx'
    elif ext in ['txt']:
        return 'txt'
    return 'unknown'


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    file: UploadFile = File(...),
    config_name: Optional[str] = Form("default"),
    db: Session = Depends(get_db)
):
    """
    创建新任务（上传文件）
    """
    # 初始化默认配置
    init_default_configs(db)
    
    # 生成任务ID和文件路径
    task_id = str(uuid.uuid4())
    file_ext = file.filename.split('.')[-1] if '.' in file.filename else ''
    safe_filename = f"{task_id}.{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)
    
    # 保存文件
    try:
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文件保存失败: {str(e)}"
        )
    
    # 创建任务记录
    file_type = get_file_type(file.filename)
    
    # 根据文件类型自动选择配置
    if file_type == 'txt' and config_name == 'default':
        config_name = 'txt_only'
    
    task = Task(
        task_id=task_id,
        filename=file.filename,
        file_path=file_path,
        file_type=file_type,
        config_name=config_name,
        status="pending",
        current_node="upload"
    )
    
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # TODO: 启动异步任务处理
    # from app.core.tasks import process_task
    # process_task.delay(task_id)
    
    return {
        "task_id": task.task_id,
        "status": task.status,
        "message": "任务创建成功"
    }


@router.get("", response_model=TaskList)
async def list_tasks(
    skip: int = 0,
    limit: int = 20,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    获取任务列表
    """
    query = db.query(Task)
    if status:
        query = query.filter(Task.status == status)
    
    total = query.count()
    tasks = query.order_by(Task.created_at.desc()).offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "items": [task.to_dict() for task in tasks]
    }


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, db: Session = Depends(get_db)):
    """
    获取任务详情
    """
    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在"
        )
    
    # 获取节点状态
    nodes = db.query(NodeData).filter(NodeData.task_id == task_id).all()
    
    # 获取配置节点列表
    config = db.query(NodeConfig).filter(
        NodeConfig.config_name == task.config_name
    ).first()
    
    import json
    node_list = json.loads(config.nodes) if config else []
    
    # 构建节点状态列表
    node_statuses = []
    for node_name in node_list:
        node = next((n for n in nodes if n.node_name == node_name), None)
        node_statuses.append({
            "name": node_name,
            "status": node.status if node else "pending"
        })
    
    result = task.to_dict()
    result["nodes"] = node_statuses
    
    return result


@router.post("/{task_id}/retry")
async def retry_task(
    task_id: str,
    retry_req: RetryRequest,
    db: Session = Depends(get_db)
):
    """
    从指定节点重试任务
    """
    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在"
        )
    
    # 重置从指定节点开始的状态
    nodes = db.query(NodeData).filter(
        NodeData.task_id == task_id,
        NodeData.node_name == retry_req.from_node
    ).first()
    
    if not nodes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"节点 {retry_req.from_node} 不存在"
        )
    
    # TODO: 重新启动任务处理
    
    return {
        "task_id": task_id,
        "from_node": retry_req.from_node,
        "message": "任务重试已启动"
    }


@router.get("/{task_id}/result", response_model=TaskResult)
async def get_task_result(task_id: str, db: Session = Depends(get_db)):
    """
    获取任务分析结果
    """
    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在"
        )
    
    if task.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"任务尚未完成，当前状态: {task.status}"
        )
    
    import json
    result_data = json.loads(task.result_data) if task.result_data else {}
    
    return {
        "task_id": task_id,
        "keywords": result_data.get("keywords", []),
        "summary": result_data.get("summary", ""),
        "full_text": result_data.get("full_text", ""),
        "completed_at": task.completed_at.isoformat() if task.completed_at else None
    }
