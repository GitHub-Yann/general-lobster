"""
Celery 异步任务定义
优化版本：支持更细粒度的节点重试和错误处理
"""
import json
import os
import sys
import traceback
import re
from datetime import datetime
from celery import Celery
from celery.exceptions import MaxRetriesExceededError
import logging

# 配置 Celery 日志
logger = logging.getLogger(__name__)

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
    # Redis 连接稳定性配置（LLM 场景下任务更长，适当放宽超时并启用保活）
    broker_transport_options={
        "socket_connect_timeout": 30,
        "socket_timeout": 30,
        "socket_keepalive": True,
        "retry_on_timeout": True,
        "health_check_interval": 30,
    },
    result_backend_transport_options={
        "socket_connect_timeout": 30,
        "socket_timeout": 30,
        "socket_keepalive": True,
        "retry_on_timeout": True,
        "health_check_interval": 30,
    },
)

from app.db.database import SessionLocal
from app.models.task import Task
from app.models.node_data import NodeData
from app.models.node_config import NodeConfig
from app.models.llm_config import LLMConfig
from app.models.llm_prompt_template import LLMPromptTemplate
from app.models.llm_call_log import LLMCallLog

from app.nodes.parse_node import parse_document
from app.nodes.segment_node import segment_text
from app.nodes.keyword_node import extract_keywords
from app.nodes.summary_node import generate_summary
from app.nodes.output_node import generate_output
from app.core.llm_service import LLMService, DEFAULT_SYSTEM_PROMPT, DEFAULT_USER_TEMPLATE


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
        # 可选：在摘要之后插入 LLM 精修节点
        if task.use_llm_refine:
            if "summary" in node_list and "output" in node_list and "llm_refine" not in node_list:
                output_index = node_list.index("output")
                node_list.insert(output_index, "llm_refine")
        else:
            node_list = [n for n in node_list if n != "llm_refine"]

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
        logger.info(f"[Task {task_id}] 节点 [{node_name}] 已缓存，跳过执行")
        return {
            "status": "completed",
            "output": json.loads(node_data.output_data)
        }

    # 更新为运行中
    node_data.status = "running"
    node_data.started_at = datetime.utcnow()
    node_data.input_data = json.dumps(context, ensure_ascii=False, default=str)
    db.commit()
    logger.info(f"[Task {task_id}] 节点 [{node_name}] 开始执行...")

    try:
        # 根据节点类型执行
        output = _run_node_logic(node_name, db, task_id, context)

        # 更新节点完成状态
        node_data.status = "completed"
        node_data.output_data = json.dumps(output, ensure_ascii=False, default=str)
        node_data.completed_at = datetime.utcnow()
        db.commit()

        logger.info(f"[Task {task_id}] 节点 [{node_name}] 执行完成 ✓")
        return {
            "status": "completed",
            "output": output
        }

    except Exception as e:
        # 更新节点失败状态
        node_data.status = "failed"
        node_data.error_msg = f"{str(e)}\n{traceback.format_exc()}"
        db.commit()

        logger.error(f"[Task {task_id}] 节点 [{node_name}] 执行失败 ✗: {str(e)}")
        raise


def _run_node_logic(node_name: str, db, task_id: str, context: dict) -> dict:
    """运行节点逻辑"""
    node_executors = {
        "upload": execute_upload_node,
        "parse": execute_parse_node,
        "segment": execute_segment_node,
        "keyword": execute_keyword_node,
        "summary": execute_summary_node,
        "llm_refine": execute_llm_refine,
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
    # 获取任务信息（用于读取用户自定义关键词配置）
    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise ValueError("任务不存在")

    # 解析用户自定义配置（兼容 JSON / 中英文逗号 / 分号 / 顿号 / 换行）
    domain_keywords = _parse_user_terms(task.domain_keywords)
    noise_words = _parse_user_terms(task.noise_words)

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

    logger.info(f"[Task {task_id}] 关键词提取 - 领域词: {domain_keywords}, 噪音词: {noise_words}")

    try:
        result = extract_keywords(
            text,
            top_n=15,
            use_mmr=True,
            diversity=0.3,
            domain_keywords=domain_keywords,
            noise_words=noise_words
        )
        return result
    except Exception as e:
        logger.error(f"[Task {task_id}] 关键词提取失败: {e}")
        # 如果 KeyBERT 失败，使用备选方案
        result = extract_keywords(
            text,
            top_n=15,
            use_mmr=False,
            domain_keywords=domain_keywords,
            noise_words=noise_words
        )
        result["method"] = "fallback"
        return result


def execute_summary_node(db, task_id: str, context: dict) -> dict:
    """摘要生成节点"""
    # 获取任务信息
    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise ValueError("任务不存在")

    # 解析用户自定义配置（兼容 JSON / 中英文逗号 / 分号 / 顿号 / 换行）
    domain_keywords = _parse_user_terms(task.domain_keywords)
    noise_words = _parse_user_terms(task.noise_words)

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

    logger.info(f"[Task {task_id}] 摘要生成 - 领域词: {domain_keywords}, 噪音词: {noise_words}")

    result = generate_summary(
        text,
        max_length=max_length,
        min_length=min_length,
        domain_keywords=domain_keywords,
        noise_words=noise_words
    )
    return result


def _parse_user_terms(raw_value: str) -> list:
    """
    解析用户输入的关键词配置，兼容以下格式：
    1) JSON 数组：["a", "b"]
    2) 逗号/分号/顿号/换行分隔：a,b 或 a，b 或 a；b 或 a、b
    """
    if not raw_value or not str(raw_value).strip():
        return []

    parsed = raw_value
    try:
        parsed = json.loads(raw_value)
    except Exception:
        parsed = raw_value

    items = []
    if isinstance(parsed, list):
        for item in parsed:
            if item is None:
                continue
            items.append(str(item))
    else:
        items.append(str(parsed))

    result = []
    seen = set()
    for item in items:
        # 进一步拆分，避免 ["a，b，c"] 这种单元素列表漏切分
        chunks = re.split(r"[,，;；、\n\r\t]+", item)
        for chunk in chunks:
            term = chunk.strip().strip("\"'[](){}")
            if not term:
                continue
            key = term.lower()
            if key in seen:
                continue
            seen.add(key)
            result.append(term)

    return result


def execute_output_node(db, task_id: str, context: dict) -> dict:
    """输出节点 - 组装最终结果"""
    parse_output = context.get("parse", {})
    segment_output = context.get("segment", {})
    keyword_output = context.get("keyword", {})
    summary_output = context.get("summary", {})
    llm_refine_output = context.get("llm_refine", {})

    # 默认使用抽取结果；LLM 精修成功时覆盖
    final_keyword_output = keyword_output
    final_summary_output = summary_output
    if llm_refine_output.get("used"):
        if llm_refine_output.get("keywords"):
            final_keyword_output = {
                **keyword_output,
                "keywords": llm_refine_output.get("keywords", []),
                "total_keywords": len(llm_refine_output.get("keywords", [])),
                "method": "llm_refine"
            }
        if llm_refine_output.get("summary"):
            final_summary_output = {
                **summary_output,
                "summary": llm_refine_output.get("summary", ""),
                "method": "llm_refine"
            }

    result = generate_output(
        task_id=task_id,
        parse_result=parse_output,
        segment_result=segment_output,
        keyword_result=final_keyword_output,
        summary_result=final_summary_output
    )

    # 添加处理统计信息
    result["processing_info"] = {
        "completed_at": datetime.utcnow().isoformat(),
        "segment_count": segment_output.get("segment_count", 0),
        "keyword_method": final_keyword_output.get("method", "keybert"),
        "summary_method": final_summary_output.get("method", "textrank"),
        "llm_refine_used": bool(llm_refine_output.get("used")),
        "llm_refine_reason": llm_refine_output.get("reason", ""),
        "llm_provider": llm_refine_output.get("provider", ""),
        "llm_model": llm_refine_output.get("model", ""),
    }

    return result


def execute_llm_refine_node(db, task_id: str, context: dict) -> dict:
    """兼容命名（防止旧引用）"""
    return execute_llm_refine(db, task_id, context)


def execute_llm_refine(db, task_id: str, context: dict) -> dict:
    """LLM 精修节点：对关键词+摘要进行重写整合，可选执行"""
    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise ValueError("任务不存在")

    if not task.use_llm_refine:
        return {"used": False, "reason": "disabled"}

    parse_output = context.get("parse", {})
    keyword_output = context.get("keyword", {})
    summary_output = context.get("summary", {})
    text = parse_output.get("text", "")
    if not text:
        return {"used": False, "reason": "empty_text"}

    llm_config = _resolve_llm_config(db, task.llm_config_id)
    if not llm_config:
        return {"used": False, "reason": "llm_config_not_found"}

    prompt_template = _resolve_prompt_template(db, task.prompt_template_id)
    system_prompt = prompt_template.system_prompt if prompt_template else DEFAULT_SYSTEM_PROMPT
    user_template = prompt_template.user_prompt_template if prompt_template else DEFAULT_USER_TEMPLATE

    payload = _build_llm_payload(
        parse_output=parse_output,
        keyword_output=keyword_output,
        summary_output=summary_output,
        domain_keywords=_parse_user_terms(task.domain_keywords),
        noise_words=_parse_user_terms(task.noise_words),
    )

    logger.info(f"[Task {task_id}] LLM payload==============>: {payload}")

    call_started = datetime.utcnow()
    request_payload_text = json.dumps(payload, ensure_ascii=False)
    prompt_template_id = prompt_template.id if prompt_template else None
    try:
        llm_result = LLMService.refine_keywords_and_summary(
            provider_name=llm_config.provider,
            api_key=llm_config.api_key or "",
            api_base=llm_config.api_base,
            model=llm_config.model,
            payload=payload,
            system_prompt=system_prompt,
            user_prompt_template=user_template,
            timeout=60
        )
        latency_ms = int((datetime.utcnow() - call_started).total_seconds() * 1000)

        logger.info(f"[Task {task_id}] LLM result==============>: {llm_result}")
        
        _save_llm_call_log(
            db=db,
            task_id=task_id,
            provider=llm_config.provider,
            model=llm_config.model,
            prompt_template_id=prompt_template_id,
            request_payload=request_payload_text,
            response_payload=json.dumps(llm_result, ensure_ascii=False),
            success=True,
            error_message=None,
            latency_ms=latency_ms,
        )
    except Exception as e:
        latency_ms = int((datetime.utcnow() - call_started).total_seconds() * 1000)
        _save_llm_call_log(
            db=db,
            task_id=task_id,
            provider=llm_config.provider,
            model=llm_config.model,
            prompt_template_id=prompt_template_id,
            request_payload=request_payload_text,
            response_payload=None,
            success=False,
            error_message=str(e),
            latency_ms=latency_ms,
        )
        logger.warning(f"[Task {task_id}] LLM 精修失败，回退抽取版: {e}")
        return {"used": False, "reason": f"llm_call_failed: {str(e)}"}

    guard = _guard_llm_result(
        llm_result=llm_result,
        keyword_output=keyword_output,
        summary_output=summary_output
    )
    if not guard["passed"]:
        return {"used": False, "reason": f"guard_rejected: {guard['reason']}"}

    return {
        "used": True,
        "reason": "ok",
        "keywords": llm_result.get("keywords", []),
        "summary": llm_result.get("summary", ""),
        "provider": llm_config.provider,
        "model": llm_config.model,
        "prompt_template_id": prompt_template.id if prompt_template else None,
        "prompt_version": prompt_template.version if prompt_template else None,
    }


def _resolve_llm_config(db, llm_config_id: int = None):
    if llm_config_id:
        cfg = db.query(LLMConfig).filter(LLMConfig.id == llm_config_id).first()
        if cfg and cfg.enabled:
            return cfg
    return db.query(LLMConfig).filter(LLMConfig.enabled == True).order_by(LLMConfig.updated_at.desc()).first()


def _resolve_prompt_template(db, prompt_template_id: int = None):
    if prompt_template_id:
        tpl = db.query(LLMPromptTemplate).filter(LLMPromptTemplate.id == prompt_template_id).first()
        if tpl and tpl.enabled:
            return tpl
    return db.query(LLMPromptTemplate).filter(
        LLMPromptTemplate.scene == "doc_refine",
        LLMPromptTemplate.enabled == True
    ).order_by(LLMPromptTemplate.updated_at.desc()).first()


def _build_llm_payload(parse_output: dict, keyword_output: dict, summary_output: dict,
                       domain_keywords: list, noise_words: list) -> dict:
    text = parse_output.get("text", "") or ""
    sentences = re.split(r"[。！？；;\n]+", text)
    sentences = [s.strip() for s in sentences if len(s.strip()) >= 12]

    keyword_words = [k.get("word", "") for k in keyword_output.get("keywords", []) if isinstance(k, dict)]
    candidate_sentences = []
    for s in sentences:
        score = 0
        for kw in keyword_words[:10]:
            if kw and kw in s:
                score += 1
        for kw in domain_keywords[:10]:
            if kw and kw in s:
                score += 1
        if score > 0:
            candidate_sentences.append((score, s))
    candidate_sentences.sort(key=lambda x: x[0], reverse=True)

    return {
        "title": parse_output.get("title", ""),
        "original_summary": summary_output.get("summary", ""),
        "keywords": keyword_output.get("keywords", [])[:15],
        "candidate_sentences": [s for _, s in candidate_sentences[:12]],
        "domain_keywords": domain_keywords[:20],
        "noise_words": noise_words[:20],
        "constraints": {
            "max_keywords": 15,
            "summary_style": "简介",
            "forbid_hallucination": True
        }
    }


def _guard_llm_result(llm_result: dict, keyword_output: dict, summary_output: dict) -> dict:
    keywords = llm_result.get("keywords", [])
    summary = (llm_result.get("summary") or "").strip()
    if not summary:
        return {"passed": False, "reason": "empty_summary"}
    if len(summary) < 40:
        return {"passed": False, "reason": "summary_too_short"}
    if len(summary) > 800:
        return {"passed": False, "reason": "summary_too_long"}
    if not isinstance(keywords, list) or len(keywords) == 0:
        return {"passed": False, "reason": "empty_keywords"}

    # 术语保留率：原 Top10 在「摘要 + LLM关键词」联合文本中至少命中 30%
    # 说明：只看 summary 会误杀（LLM 可能把术语放在 keywords 而非摘要正文）
    old_words = [k.get("word", "") for k in keyword_output.get("keywords", []) if isinstance(k, dict)][:10]
    old_words = [w for w in old_words if w]
    if old_words:
        llm_words = []
        for item in keywords:
            if isinstance(item, dict):
                word = str(item.get("word", "")).strip()
            else:
                word = str(item).strip()
            if word:
                llm_words.append(word)

        merged_text = summary + " " + " ".join(llm_words)

        def _norm(s: str) -> str:
            return re.sub(r"[\s\-_，,。；;：:（）()\[\]【】]", "", (s or "").lower())

        merged_norm = _norm(merged_text)
        hits = 0
        hit_words = []
        miss_words = []
        for w in old_words:
            wn = _norm(w)
            matched = False
            if wn and wn in merged_norm:
                matched = True
            # 弱匹配：短语差异时允许包含关系（长度>=3才启用）
            if not matched and len(wn) >= 3:
                for lw in llm_words:
                    lwn = _norm(lw)
                    if not lwn:
                        continue
                    if wn in lwn or lwn in wn:
                        matched = True
                        break
            if matched:
                hits += 1
                hit_words.append(w)
            else:
                miss_words.append(w)

        recall = hits / len(old_words)
        logger.info(
            f"[LLM Guard] term recall={recall:.2f}, hits={hit_words}, miss={miss_words}"
        )
        if recall < 0.3:
            return {"passed": False, "reason": f"term_recall_low({hits}/{len(old_words)})"}

    return {"passed": True, "reason": "ok"}


def _save_llm_call_log(db, task_id: str, provider: str, model: str, prompt_template_id: int,
                       request_payload: str, response_payload: str, success: bool,
                       error_message: str, latency_ms: int):
    """记录 LLM 调用日志（失败不影响主流程）。"""
    try:
        row = LLMCallLog(
            task_id=task_id,
            provider=provider or "",
            model=model,
            prompt_template_id=prompt_template_id,
            request_payload=request_payload,
            response_payload=response_payload,
            success=bool(success),
            error_message=error_message,
            latency_ms=latency_ms
        )
        db.add(row)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning(f"[Task {task_id}] 写 llm_call_logs 失败: {e}")
