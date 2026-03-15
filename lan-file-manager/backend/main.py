from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, WebSocket, WebSocketDisconnect, Query, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import io
import asyncio
import json
from datetime import timedelta
from urllib.parse import quote

from config import get_settings
from auth import authenticate_user, create_access_token, verify_token
from ftp_client import FTPClient, FileInfo

settings = get_settings()
app = FastAPI(title="LAN File Manager API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()
ftp_client = FTPClient()

# WebSocket 连接管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
    
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
    
    async def send_progress(self, client_id: str, uploaded: int, total: int):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json({
                "type": "progress",
                "uploaded": uploaded,
                "total": total,
                "percent": round(uploaded / total * 100, 2) if total > 0 else 0
            })

manager = ConnectionManager()

# 依赖：获取当前用户
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    username = verify_token(token)
    return username

# ============ 认证接口 ============

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str

@app.post("/api/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    user = authenticate_user(request.username, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# ============ 文件管理接口 ============

class FileListResponse(BaseModel):
    name: str
    path: str
    size: int
    is_dir: bool
    permissions: str

@app.get("/api/files", response_model=List[FileListResponse])
async def list_files(path: str = "", username: str = Depends(get_current_user)):
    """列出目录内容"""
    try:
        print(f"[DEBUG] list_files called with path='{path}'")
        files = ftp_client.list_directory(path)
        print(f"[DEBUG] list_files returned {len(files)} files")
        return [
            {
                "name": f.name,
                "path": f.path,
                "size": f.size,
                "is_dir": f.is_dir,
                "permissions": f.permissions
            }
            for f in files
        ]
    except Exception as e:
        print(f"[ERROR] list_files failed: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取文件列表失败: {str(e)}")

@app.post("/api/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    path: str = Form(default=""),
    username: str = Depends(get_current_user)
):
    """上传文件"""
    try:
        # 读取文件内容
        content = await file.read()
        file_obj = io.BytesIO(content)
        
        # 构建远程路径
        remote_path = os.path.join(path, file.filename).replace("\\", "/")
        
        # 上传
        ftp_client.upload_file(remote_path, file_obj)
        
        return {"success": True, "path": remote_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")

@app.get("/api/files/download")
async def download_file(
    path: str,
    username: str = Depends(get_current_user)
):
    """下载文件"""
    try:
        print(f"[DEBUG] download_file called with path='{path}'")
        buffer = ftp_client.download_file(path)
        filename = os.path.basename(path)
        print(f"[DEBUG] download_file success, filename='{filename}'")
        
        # 对中文文件名进行 RFC 5987 编码
        encoded_filename = quote(filename, safe='')
        
        return StreamingResponse(
            buffer,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"}
        )
    except Exception as e:
        print(f"[ERROR] download_file failed: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"下载失败: {str(e)}")

@app.delete("/api/files")
async def delete_file(
    path: str,
    is_dir: bool = False,
    username: str = Depends(get_current_user)
):
    """删除文件或目录"""
    try:
        if is_dir:
            ftp_client.delete_directory(path)
        else:
            ftp_client.delete_file(path)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")

@app.post("/api/files/mkdir")
async def create_directory(
    path: str,
    username: str = Depends(get_current_user)
):
    """创建目录"""
    try:
        ftp_client.create_directory(path)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建目录失败: {str(e)}")

@app.post("/api/files/rename")
async def rename_file(
    old_path: str,
    new_path: str,
    username: str = Depends(get_current_user)
):
    """重命名文件/目录"""
    try:
        ftp_client.rename(old_path, new_path)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重命名失败: {str(e)}")

# ============ WebSocket 接口（实时进度） ============

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        while True:
            # 保持连接
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
                
    except WebSocketDisconnect:
        manager.disconnect(client_id)

# ============ 分片上传接口 ============

import hashlib
from pathlib import Path

# 临时上传目录
UPLOAD_TEMP_DIR = Path(settings.upload_temp_dir)
UPLOAD_TEMP_DIR.mkdir(parents=True, exist_ok=True)

class ChunkUploadRequest(BaseModel):
    filename: str
    chunk_index: int
    total_chunks: int
    path: str = ""

@app.post("/api/files/upload/chunk")
async def upload_chunk(
    file: UploadFile = File(...),
    filename: str = Query(...),
    chunk_index: int = Query(...),
    total_chunks: int = Query(...),
    upload_id: str = Query(...),
    path: str = Query(default=""),
    username: str = Depends(get_current_user)
):
    """分片上传"""
    try:
        # 保存分片到临时目录
        chunk_dir = UPLOAD_TEMP_DIR / upload_id
        chunk_dir.mkdir(exist_ok=True)
        
        chunk_path = chunk_dir / f"chunk_{chunk_index}"
        content = await file.read()
        with open(chunk_path, "wb") as f:
            f.write(content)
        
        # 检查是否所有分片都已上传
        uploaded_chunks = len(list(chunk_dir.glob("chunk_*")))
        
        if uploaded_chunks == total_chunks:
            # 合并分片
            remote_path = os.path.join(path, filename).replace("\\", "/")
            
            # 按顺序合并
            merged = io.BytesIO()
            for i in range(total_chunks):
                chunk_file = chunk_dir / f"chunk_{i}"
                with open(chunk_file, "rb") as f:
                    merged.write(f.read())
            
            merged.seek(0)
            ftp_client.upload_file(remote_path, merged)
            
            # 清理临时文件
            for chunk_file in chunk_dir.glob("chunk_*"):
                chunk_file.unlink()
            chunk_dir.rmdir()
            
            return {"success": True, "completed": True, "path": remote_path}
        
        return {"success": True, "completed": False, "uploaded": uploaded_chunks, "total": total_chunks}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分片上传失败: {str(e)}")

# ============ 启动 ============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)
