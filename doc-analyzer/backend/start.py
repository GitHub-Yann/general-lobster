"""
启动脚本
从 .env 读取配置启动服务
"""
import uvicorn
from app.config import HOST, PORT, RELOAD

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=HOST,
        port=PORT,
        reload=RELOAD
    )
