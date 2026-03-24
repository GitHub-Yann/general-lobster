"""
任务模型
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer
from app.db.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class Task(Base):
    __tablename__ = "tasks"

    task_id = Column(String(36), primary_key=True, default=generate_uuid)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(20))  # pdf, docx, txt, url
    config_name = Column(String(50), default="default")
    status = Column(String(20), default="pending")  # pending, running, completed, failed
    current_node = Column(String(50), default="upload")
    result_data = Column(Text)  # JSON 格式存储最终结果
    # 用户自定义关键词配置
    domain_keywords = Column(Text)  # JSON 格式存储领域关键词列表
    noise_words = Column(Text)  # JSON 格式存储噪音词列表
    # 可选 LLM 精修配置
    use_llm_refine = Column(Boolean, default=False)
    llm_config_id = Column(Integer)
    prompt_template_id = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "task_id": self.task_id,
            "filename": self.filename,
            "file_type": self.file_type,
            "config_name": self.config_name,
            "status": self.status,
            "current_node": self.current_node,
            "result_data": self.result_data,
            "domain_keywords": self.domain_keywords,
            "noise_words": self.noise_words,
            "use_llm_refine": self.use_llm_refine,
            "llm_config_id": self.llm_config_id,
            "prompt_template_id": self.prompt_template_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
