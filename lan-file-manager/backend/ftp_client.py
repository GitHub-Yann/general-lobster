import ftplib
import os
import io
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
from config import get_settings

settings = get_settings()

@dataclass
class FileInfo:
    name: str
    path: str
    size: int
    is_dir: bool
    modified_time: Optional[datetime] = None
    permissions: str = ""

class FTPClient:
    def __init__(self):
        self.host = settings.ftp_host
        self.port = settings.ftp_port
        self.user = settings.ftp_user
        self.password = settings.ftp_pass
        self.root = settings.ftp_root
    
    def _connect(self) -> ftplib.FTP:
        """建立 FTP 连接"""
        ftp = ftplib.FTP()
        ftp.connect(self.host, self.port, timeout=30)
        ftp.login(self.user, self.password)
        ftp.set_pasv(True)
        return ftp
    
    def _safe_path(self, path: str) -> str:
        """安全路径校验，防止目录遍历攻击"""
        # 规范化路径
        normalized = os.path.normpath(path)
        # 确保不以 .. 开头
        if normalized.startswith("..") or "/../" in normalized:
            raise ValueError(f"非法路径: {path}")
        # 移除开头的 /
        normalized = normalized.lstrip("/")
        return normalized
    
    def list_directory(self, path: str = "") -> List[FileInfo]:
        """列出目录内容"""
        safe_path = self._safe_path(path)
        
        with self._connect() as ftp:
            # 切换到目标目录
            if safe_path:
                ftp.cwd(safe_path)
            
            files = []
            
            def parse_line(line: str):
                # 解析 FTP LIST 输出
                # 格式: -rw-r--r-- 1 user group 1234 Jan 01 12:00 filename
                parts = line.split()
                if len(parts) < 9:
                    return
                
                permissions = parts[0]
                size = int(parts[4]) if parts[4].isdigit() else 0
                date_str = " ".join(parts[5:8])
                name = " ".join(parts[8:])
                
                is_dir = permissions.startswith("d")
                
                # 跳过 . 和 ..
                if name in (".", ".."):
                    return
                
                file_path = os.path.join(path, name).replace("\\", "/")
                
                files.append(FileInfo(
                    name=name,
                    path=file_path,
                    size=size,
                    is_dir=is_dir,
                    permissions=permissions
                ))
            
            ftp.retrlines("LIST", parse_line)
            return files
    
    def upload_file(self, remote_path: str, file_obj: io.BytesIO, 
                    progress_callback: Optional[Callable[[int, int], None]] = None) -> bool:
        """上传文件"""
        safe_path = self._safe_path(remote_path)
        
        with self._connect() as ftp:
            # 确保目录存在
            dir_path = os.path.dirname(safe_path)
            if dir_path:
                self._ensure_dir(ftp, dir_path)
            
            # 获取文件大小
            file_obj.seek(0, 2)
            total_size = file_obj.tell()
            file_obj.seek(0)
            
            # 上传
            uploaded = 0
            def callback(chunk):
                nonlocal uploaded
                uploaded += len(chunk)
                if progress_callback:
                    progress_callback(uploaded, total_size)
            
            ftp.storbinary(f"STOR {safe_path}", file_obj, blocksize=8192, callback=callback)
            return True
    
    def download_file(self, remote_path: str, 
                      progress_callback: Optional[Callable[[int, int], None]] = None) -> io.BytesIO:
        """下载文件"""
        safe_path = self._safe_path(remote_path)
        
        with self._connect() as ftp:
            # 切换到二进制模式（Windows FTP 服务器需要）
            ftp.voidcmd('TYPE I')
            # 获取文件大小
            size = ftp.size(safe_path)
            
            buffer = io.BytesIO()
            downloaded = 0
            
            def callback(chunk):
                nonlocal downloaded
                buffer.write(chunk)
                downloaded += len(chunk)
                if progress_callback:
                    progress_callback(downloaded, size)
            
            ftp.retrbinary(f"RETR {safe_path}", callback, blocksize=8192)
            buffer.seek(0)
            return buffer
    
    def delete_file(self, remote_path: str) -> bool:
        """删除文件"""
        safe_path = self._safe_path(remote_path)
        
        with self._connect() as ftp:
            ftp.delete(safe_path)
            return True
    
    def delete_directory(self, remote_path: str) -> bool:
        """删除目录（递归）"""
        safe_path = self._safe_path(remote_path)
        
        with self._connect() as ftp:
            self._rmdir_recursive(ftp, safe_path)
            return True
    
    def create_directory(self, remote_path: str) -> bool:
        """创建目录"""
        safe_path = self._safe_path(remote_path)
        
        with self._connect() as ftp:
            self._ensure_dir(ftp, safe_path)
            return True
    
    def rename(self, old_path: str, new_path: str) -> bool:
        """重命名文件/目录"""
        safe_old = self._safe_path(old_path)
        safe_new = self._safe_path(new_path)
        
        with self._connect() as ftp:
            ftp.rename(safe_old, safe_new)
            return True
    
    def _ensure_dir(self, ftp: ftplib.FTP, path: str):
        """确保目录存在，不存在则创建"""
        parts = path.split("/")
        current = ""
        for part in parts:
            if not part:
                continue
            current = f"{current}/{part}" if current else part
            try:
                ftp.cwd(current)
            except ftplib.error_perm:
                ftp.mkd(current)
                ftp.cwd(current)
        ftp.cwd("/")  # 回到根目录
    
    def _rmdir_recursive(self, ftp: ftplib.FTP, path: str):
        """递归删除目录"""
        try:
            ftp.cwd(path)
        except ftplib.error_perm:
            return
        
        # 列出目录内容
        items = []
        ftp.retrlines("LIST", items.append)
        
        for item in items:
            parts = item.split()
            if len(parts) < 9:
                continue
            name = " ".join(parts[8:])
            if name in (".", ".."):
                continue
            
            full_path = f"{path}/{name}"
            if parts[0].startswith("d"):
                # 目录
                self._rmdir_recursive(ftp, full_path)
            else:
                # 文件
                ftp.delete(full_path)
        
        ftp.cwd("..")
        ftp.rmd(path)
    
    def get_file_size(self, remote_path: str) -> int:
        """获取文件大小"""
        safe_path = self._safe_path(remote_path)
        
        with self._connect() as ftp:
            return ftp.size(safe_path)
