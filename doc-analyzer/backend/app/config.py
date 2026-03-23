"""
配置管理
支持从 .env 文件加载配置
"""
import os
from pathlib import Path

# 加载 .env 文件
def load_env_file():
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key, value)

# 加载环境变量
load_env_file()

# 配置项
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "52428800"))
CELERY_WORKERS = int(os.getenv("CELERY_WORKERS", "4"))
RELOAD = os.getenv("RELOAD", "true").lower() == "true")
