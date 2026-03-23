"""
节点配置模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from app.db.database import Base


class NodeConfig(Base):
    __tablename__ = "node_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    config_name = Column(String(50), unique=True, nullable=False)
    nodes = Column(Text, nullable=False)  # JSON 格式节点列表
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "config_name": self.config_name,
            "nodes": self.nodes,
            "description": self.description,
        }
