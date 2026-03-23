"""
节点数据模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint
from app.db.database import Base


class NodeData(Base):
    __tablename__ = "node_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(36), ForeignKey("tasks.task_id"), nullable=False)
    node_name = Column(String(50), nullable=False)  # upload, parse, segment, keyword, summary, output
    status = Column(String(20), default="pending")  # pending, running, completed, failed
    input_data = Column(Text)  # JSON 格式
    output_data = Column(Text)  # JSON 格式 - 中间结果
    error_msg = Column(Text)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("task_id", "node_name", name="uix_task_node"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "node_name": self.node_name,
            "status": self.status,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "error_msg": self.error_msg,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
