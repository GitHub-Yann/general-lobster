"""
Celery 异步任务定义
优化版本：支持更细粒度的节点重试和错误处理
"""
import json
import os
import traceback
from datetime import datetime
from celery import Celery
from celery.exceptions import MaxRetriesExceededError

# 从 .env 加载配置
from pathlib import Path
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                key, value = line.split("=", 1)
                os.environ.setdefault(key, value)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# 创建 Celery 实例
celery_app = Celery(
    "doc_analyzer",
    broker=REDIS_URL,
    backend=REDIS_URL
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
    worker_prefetch_multiplier=1,
    # Windows 兼容配置
    broker_connection_retry_on_startup=True,
    worker_concurrency=1,
)

from app.db.database import SessionLocal
from app.models.task import Task
from app.models.node_data import NodeData
from app.models.node_config import NodeConfig

from app.nodes.parse_node import parse_document
from app.nodes.segment_node import segment_text
from app.nodes.keyword_node import extract_keywords
from app.nodes.summary_node import generate_summary
from app.nodes.output_node import generate_output


class NodeExecutionError(Exception):
    """节点执行错误"""
    def __init__(self, node_name: str, message: str, original_error: Exception = None):
        self.node_name = node_name
        self.message = message
        self.original_error = original_error
        super().__init__(f"节点 [{node_name}] 执行失败: {message}")


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def process_task(self, task_id: str, start_from_node: str = None):
    """
    处理文档分析任务的主流程
    
    Args:
        task_id: 任务ID
        start_from_node: 从指定节点开始执行（用于重试）
    """
    db = SessionLocal()
    
    try:
        # 获取任务信息
        task = db.query(Task).filter(Task.task_id == task_id).first()
        if not task:
            raise ValueError(f"任务不存在: {task_id}")
        
        # 获取节点配置
        config = db.query(NodeConfig).filter(
            NodeConfig.config_name == task.config_name
        ).first()
        
        if not config:
            raise ValueError(f"节点配置不存在: {task.config_name}")
        
        node_list = json.loads(config.nodes)
        
        # 如果指定了起始节点，找到该节点位置
        if start_from_node and start_from_node in node_list:
            start_index = node_list.index(start_from_node)
            node_list = node_list[start_index:]
            
            # 重置该节点及后续节点的状态
            for node_name in node_list:
                node_data = db.query(NodeData).filter(
                    NodeData.task_id == task_id,
                    NodeData.node_name == node_name
                ).first()
                if node_data:
                    node_data.status = "pending"
                    node_data.error_msg = None
                    db.commit()
        
        # 更新任务状态
        task.status = "running"
        db.commit()
        
        # 执行节点流程
        context = _load_context(db, task_id, node_list)
        
        for node_name in node_list:
            # 更新当前节点
            task.current_node = node_name
            db.commit()
            
            # 执行节点
            try:
                result = execute_node_with_retry(db, task_id, node_name, context)
            except NodeExecutionError as e:
                # 节点执行失败，更新任务状态
                task.status = "failed"
                db.commit()
                
                return {
                    "task_id": task_id,
                    "status": "failed",
                    "failed_node": node_name,
                    "error": e.message,
                    "traceback": traceback.format_exc()
                }
            
            # 保存节点输出到上下文
            context[node_name] = result.get("output", {})
        
        # 所有节点执行成功
        task.status = "completed"
        task.completed_at = datetime.utcnow()
        
        # 保存最终结果
        final_result = context.get("output", {})
        task.result_data = json.dumps(final_result, ensure_ascii=False)
        
        db.commit()
        
        return {
            "task_id": task_id,
            "status": "completed",
            "result": final_result
        }
        
    except Exception as exc:
        # 更新任务失败状态
        try:
            task = db.query(Task).filter(Task.task_id == task_id).first()
            if task:
                task.status = "failed"
                db.commit()
        except:
            pass
        
        # 重试逻辑
        try:
            self.retry(exc=exc)
        except MaxRetriesExceededError:
            return {
                "task_id": task_id,
                "status": "failed",
                "error": str(exc),
                "traceback": traceback.format_exc()
            }
    finally:
        db.close()


def _load_context(db, task_id: str, node_list: list) -> dict:
    """加载已完成的节点数据到上下文"""
    context = {}
    
    for node_name in node_list:
        node_data = db.query(NodeData).filter(
            NodeData.task_id == task_id,
            NodeData.node_name == node_name,
            NodeData.status == "completed"
        ).first()
        
        if node_data and node_data.output_data:
            try:
                context[node_name] = json.loads(node_data.output_data)
            except json.JSONDecodeError:
                pass
    
    return context


def execute_node_with_retry(db, task_id: str, node_name: str, context: dict, 
                            max_retries: int = 2) -> dict:
    """
    执行单个节点（带重试）
    """
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            return _execute_node_internal(db, task_id, node_name, context)
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                # 等待后重试
                import time
                time.sleep(2 ** attempt)  # 指数退避
                continue
    
    # 所有重试都失败
    raise NodeExecutionError(
        node_name=node_name,
        message=str(last_error),
        original_error=last_error
    )


def _execute_node_internal(db, task_id: str, node_name: str, context: dict) -> dict:
    """执行单个节点（内部实现）"""
    # 获取或创建节点数据记录
    node_data = db.query(NodeData).filter(
        NodeData.task_id == task_id,
        NodeData.node_name == node_name
    ).first()
    
    if not node_data:
        node_data = NodeData(
            task_id=task_id,
            node_name=node_name,
            status="pending"
        )
        db.add(node_data)
        db.commit()
    
    # 如果节点已完成，直接返回缓存结果
    if node_data.status == "completed" and node_data.output_data:
        return {
            "status": "completed",
            "output": json.loads(node_data.output_data)
        }
    
    # 更新为运行中
    node_data.status = "running"
    node_data.started_at = datetime.utcnow()
    node_data.input_data = json.dumps(context, ensure_ascii=False, default=str)
    db.commit()
    
    try:
        # 根据节点类型执行
        output = _run_node_logic(node_name, db, task_id, context)
        
        # 更新节点完成状态
        node_data.status = "completed"
        node_data.output_data = json.dumps(output, ensure_ascii=False, default=str)
        node_data.completed_at = datetime.utcnow()
        db.commit()
        
        return {
            "status": "completed",
            "output": output
        }
        
    except Exception as e:
        # 更新节点失败状态
        node_data.status = "failed"
        node_data.error_msg = f"{str(e)}\n{traceback.format_exc()}"
        db.commit()
        
        raise


def _run_node_logic(node_name: str, db, task_id: str, context: dict) -> dict:
    """运行节点逻辑"""
    node_executors = {
        "upload": execute_upload_node,
        "parse": execute_parse_node,
        "segment": execute_segment_node,
        "keyword": execute_keyword_node,
        "summary": execute_summary_node,
        "output": execute_output_node,
    }
    
    executor = node_executors.get(node_name)
    if not executor:
        raise ValueError(f"未知节点类型: {node_name}")
    
    return executor(db, task_id, context)


def execute_upload_node(db, task_id: str, context: dict) -> dict:
    """上传节点 - 主要是验证文件"""
    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise ValueError("任务不存在")
    
    import os
    if task.file_type == 'url':
        # URL 类型不需要本地文件
        return {
            "file_path": task.file_path,
            "filename": task.filename,
            "file_type": task.file_type
        }
    
    if not os.path.exists(task.file_path):
        raise ValueError(f"文件不存在: {task.file_path}")
    
    # 检查文件大小
    file_size = os.path.getsize(task.file_path)
    max_size = 50 * 1024 * 1024  # 50MB
    if file_size > max_size:
        raise ValueError(f"文件过大: {file_size / 1024 / 1024:.1f}MB > 50MB")
    
    return {
        "file_path": task.file_path,
        "filename": task.filename,
        "file_type": task.file_type,
        "file_size": file_size
    }


def execute_parse_node(db, task_id: str, context: dict) -> dict:
    """解析节点"""
    upload_output = context.get("upload", {})
    file_path = upload_output.get("file_path")
    file_type = upload_output.get("file_type")
    
    if not file_path or not file_type:
        raise ValueError("缺少文件信息")
    
    try:
        result = parse_document(file_path, file_type)
        return result
    except Exception as e:
        raise ValueError(f"文档解析失败: {str(e)}")


def execute_segment_node(db, task_id: str, context: dict) -> dict:
    """分段节点"""
    parse_output = context.get("parse", {})
    text = parse_output.get("text", "")
    
    if not text:
        # 尝试从 upload 获取（TXT 文件跳过 parse 节点的情况）
        upload_output = context.get("upload", {})
        file_path = upload_output.get("file_path")
        file_type = upload_output.get("file_type")
        
        if file_type == "txt" and file_path:
            from app.nodes.parse_node import _parse_txt
            result = _parse_txt(file_path)
            text = result.get("text", "")
    
    if not text:
        raise ValueError("没有可分析的文本")
    
    # 根据文本长度动态调整分段参数
    text_length = len(text)
    if text_length < 5000:
        max_length = 2000
    elif text_length < 20000:
        max_length = 3000
    else:
        max_length = 4000
    
    result = segment_text(text, max_segment_length=max_length, overlap=200)
    return result


def execute_keyword_node(db, task_id: str, context: dict) -> dict:
    """关键词提取节点"""
    # 优先使用分段结果
    segment_output = context.get("segment", {})
    segments = segment_output.get("segments", [])
    
    if segments:
        # 合并前几个段落进行关键词提取
        text = " ".join(segments[:5])  # 取前5段
    else:
        # 使用解析结果
        parse_output = context.get("parse", {})
        text = parse_output.get("text", "")
    
    if not text:
        raise ValueError("没有可分析的文本")
    
    # 限制文本长度以提高性能
    max_text_length = 10000
    if len(text) > max_text_length:
        text = text[:max_text_length]
    
    try:
        result = extract_keywords(text, top_n=15, use_mmr=True, diversity=0.7)
        return result
    except Exception as e:
        # 如果 KeyBERT 失败，使用备选方案
        result = extract_keywords(text, top_n=15, use_mmr=False)
        result["method"] = "fallback"
        return result


def execute_summary_node(db, task_id: str, context: dict) -> dict:
    """摘要生成节点"""
    # 获取文本
    parse_output = context.get("parse", {})
    text = parse_output.get("text", "")
    
    if not text:
        raise ValueError("没有可总结的文本")
    
    # 根据文本长度动态调整摘要长度
    text_length = len(text)
    if text_length < 1000:
        max_length = 200
        min_length = 50
    elif text_length < 5000:
        max_length = 400
        min_length = 100
    else:
        max_length = 600
        min_length = 200
    
    result = generate_summary(text, max_length=max_length, min_length=min_length)
    return result


def execute_output_node(db, task_id: str, context: dict) -> dict:
    """输出节点 - 组装最终结果"""
    parse_output = context.get("parse", {})
    segment_output = context.get("segment", {})
    keyword_output = context.get("keyword", {})
    summary_output = context.get("summary", {})
    
    result = generate_output(
        task_id=task_id,
        parse_result=parse_output,
        segment_result=segment_output,
        keyword_result=keyword_output,
        summary_result=summary_output
    )
    
    # 添加处理统计信息
    result["processing_info"] = {
        "completed_at": datetime.utcnow().isoformat(),
        "segment_count": segment_output.get("segment_count", 0),
        "keyword_method": keyword_output.get("method", "keybert"),
        "summary_method": summary_output.get("method", "textrank"),
    }
    
    return result
