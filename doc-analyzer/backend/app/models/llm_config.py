"""
LLM 配置模型
预留大模型接口
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from app.db.database import Base


class LLMConfig(Base):
    __tablename__ = "llm_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    provider = Column(String(50), nullable=False)  # openai, claude, wenxin, tongyi
    name = Column(String(100), nullable=False)  # 配置名称
    api_key = Column(Text)  # API Key（加密存储）
    api_base = Column(String(500))  # API 基础地址
    model = Column(String(100))  # 模型名称
    enabled = Column(Boolean, default=False)  # 是否启用
    config = Column(Text)  # 额外配置 JSON
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "provider": self.provider,
            "name": self.name,
            "api_base": self.api_base,
            "model": self.model,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
