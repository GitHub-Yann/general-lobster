"""
doc-analyzer 后端主入口
FastAPI 应用
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from app.db.database import init_db
from app.api import tasks, llm


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化数据库
    init_db()
    yield
    # 关闭时清理资源


app = FastAPI(
    title="Doc Analyzer API",
    description="文档智能分析系统 API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境需要限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册 API 路由
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(llm.router, prefix="/api/llm", tags=["llm"])

# 静态文件服务（前端）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
print(f"[DEBUG] BASE_DIR: {BASE_DIR}")
print(f"[DEBUG] FRONTEND_DIR: {FRONTEND_DIR}")
print(f"[DEBUG] FRONTEND_DIR exists: {os.path.exists(FRONTEND_DIR)}")
if os.path.exists(FRONTEND_DIR):
    print(f"[DEBUG] FRONTEND_DIR contents: {os.listdir(FRONTEND_DIR)}")
    app.mount("/app", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
    print("[DEBUG] Static files mounted at /app")
else:
    print("[WARNING] Frontend directory not found!")


@app.get("/")
async def root():
    return {
        "message": "Doc Analyzer API",
        "version": "1.0.0",
        "docs": "/docs",
        "frontend": "/app"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
