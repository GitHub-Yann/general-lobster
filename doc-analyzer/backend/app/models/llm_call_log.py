"""
LLM 调用日志模型
"""
from datetime import datetime
from sqlalchemy import Column, BigInteger, String, Integer, Boolean, DateTime, Text
from app.db.database import Base


class LLMCallLog(Base):
    __tablename__ = "llm_call_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_id = Column(String(36))
    provider = Column(String(50), nullable=False)
    model = Column(String(100))
    prompt_template_id = Column(Integer)
    request_payload = Column(Text)
    response_payload = Column(Text)
    success = Column(Boolean, default=False)
    error_message = Column(Text)
    latency_ms = Column(Integer)
    token_in = Column(Integer)
    token_out = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
