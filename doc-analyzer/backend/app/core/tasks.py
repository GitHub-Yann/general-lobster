"""
Celery 异步任务定义
"""
import json
from datetime import datetime
from celery import shared_task
from celery.exceptions import MaxRetriesExceededError

from app.db.database import SessionLocal
from app.models.task import Task
from app.models.node_data import NodeData
from app.models.node_config import NodeConfig

from app.nodes.parse_node import parse_document
from app.nodes.segment_node import segment_text
from app.nodes.keyword_node import extract_keywords
from app.nodes.summary_node import generate_summary
from app.nodes.output_node import generate_output


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def process_task(self, task_id: str):
    """
    处理文档分析任务的主流程
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
        
        # 更新任务状态
        task.status = "running"
        db.commit()
        
        # 执行节点流程
        context = {}  # 节点间传递的数据
        
        for node_name in node_list:
            # 更新当前节点
            task.current_node = node_name
            db.commit()
            
            # 执行节点
            result = execute_node(self, db, task_id, node_name, context)
            
            if result.get("status") == "failed":
                task.status = "failed"
                db.commit()
                return {
                    "task_id": task_id,
                    "status": "failed",
                    "failed_node": node_name,
                    "error": result.get("error")
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
                "error": str(exc)
            }
    finally:
        db.close()


def execute_node(task_instance, db, task_id: str, node_name: str, context: dict) -> dict:
    """
    执行单个节点
    """
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
    node_data.input_data = json.dumps(context, ensure_ascii=False)
    db.commit()
    
    try:
        # 根据节点类型执行
        if node_name == "upload":
            output = execute_upload_node(db, task_id, context)
        elif node_name == "parse":
            output = execute_parse_node(db, task_id, context)
        elif node_name == "segment":
            output = execute_segment_node(db, task_id, context)
        elif node_name == "keyword":
            output = execute_keyword_node(db, task_id, context)
        elif node_name == "summary":
            output = execute_summary_node(db, task_id, context)
        elif node_name == "output":
            output = execute_output_node(db, task_id, context)
        else:
            raise ValueError(f"未知节点类型: {node_name}")
        
        # 更新节点完成状态
        node_data.status = "completed"
        node_data.output_data = json.dumps(output, ensure_ascii=False)
        node_data.completed_at = datetime.utcnow()
        db.commit()
        
        return {
            "status": "completed",
            "output": output
        }
        
    except Exception as e:
        # 更新节点失败状态
        node_data.status = "failed"
        node_data.error_msg = str(e)
        db.commit()
        
        raise


def execute_upload_node(db, task_id: str, context: dict) -> dict:
    """上传节点 - 主要是验证文件"""
    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise ValueError("任务不存在")
    
    import os
    if not os.path.exists(task.file_path):
        raise ValueError(f"文件不存在: {task.file_path}")
    
    return {
        "file_path": task.file_path,
        "filename": task.filename,
        "file_type": task.file_type
    }


def execute_parse_node(db, task_id: str, context: dict) -> dict:
    """解析节点"""
    upload_output = context.get("upload", {})
    file_path = upload_output.get("file_path")
    file_type = upload_output.get("file_type")
    
    if not file_path or not file_type:
        raise ValueError("缺少文件信息")
    
    result = parse_document(file_path, file_type)
    return result


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
    
    result = segment_text(text)
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
    
    result = extract_keywords(text)
    return result


def execute_summary_node(db, task_id: str, context: dict) -> dict:
    """摘要生成节点"""
    # 获取文本
    parse_output = context.get("parse", {})
    text = parse_output.get("text", "")
    
    if not text:
        raise ValueError("没有可总结的文本")
    
    result = generate_summary(text)
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
    
    return result
