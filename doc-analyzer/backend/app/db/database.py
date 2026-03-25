"""
数据库配置和连接
"""
import os
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 数据库路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

# 支持通过环境变量切换数据库（MySQL/SQLite）
# 示例：
#   mysql+pymysql://user:password@127.0.0.1:3306/doc_analyzer?charset=utf8mb4
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{os.path.join(DATA_DIR, 'doc_analyzer.db')}"
)

if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=3600
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """初始化数据库表"""
    from app.models import task, node_data, node_config, llm_config, llm_prompt_template, llm_call_log
    Base.metadata.create_all(bind=engine)
    _run_lightweight_migrations()


def _run_lightweight_migrations():
    """轻量迁移：确保关键新增列存在（兼容已有库）。"""
    inspector = inspect(engine)
    if "tasks" not in inspector.get_table_names():
        return

    existing_cols = {col["name"] for col in inspector.get_columns("tasks")}
    statements = []
    if "use_llm_refine" not in existing_cols:
        statements.append("ALTER TABLE tasks ADD COLUMN use_llm_refine BOOLEAN DEFAULT 0")
    if "llm_config_id" not in existing_cols:
        statements.append("ALTER TABLE tasks ADD COLUMN llm_config_id INTEGER")
    if "prompt_template_id" not in existing_cols:
        statements.append("ALTER TABLE tasks ADD COLUMN prompt_template_id INTEGER")
    if "keywords_data" not in existing_cols:
        statements.append("ALTER TABLE tasks ADD COLUMN keywords_data TEXT")
    if "summary_text" not in existing_cols:
        statements.append("ALTER TABLE tasks ADD COLUMN summary_text TEXT")

    if not statements:
        return

    with engine.begin() as conn:
        for sql in statements:
            conn.execute(text(sql))
