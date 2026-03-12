from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # FTP 配置
    ftp_host: str = "127.0.0.1"
    ftp_port: int = 2121
    ftp_user: str = "admin"
    ftp_pass: str = "admin123"
    ftp_root: str = "/data/ftp"
    
    # API 配置
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # 安全
    secret_key: str = "lan-file-manager-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24小时
    
    # 上传配置
    max_file_size: int = 1024 * 1024 * 1024 * 10  # 10GB
    chunk_size: int = 1024 * 1024 * 5  # 5MB 分片
    upload_temp_dir: str = "/tmp/lan-file-uploads"
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()
