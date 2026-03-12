# LAN File Manager

基于 Python + FastAPI + Vue3 的局域网文件传输系统

## 功能特性

- 🔐 Token 认证
- 📁 目录浏览
- ⬆️ 大文件分片上传（支持断点续传）
- ⬇️ 文件/目录下载
- 📊 实时传输进度
- 🛡️ 路径安全校验

## 项目结构

```
lan-file-manager/
├── backend/              # FastAPI 后端
│   ├── main.py          # 主入口
│   ├── ftp_client.py    # FTP 客户端封装
│   ├── auth.py          # 认证模块
│   └── requirements.txt
├── frontend/            # Vue3 前端
│   ├── src/
│   ├── package.json
│   └── vite.config.js
└── ftp_server.py        # 内嵌 FTP 服务器
```

## 快速启动

### 1. 安装依赖

```bash
# 后端
cd backend
pip install -r requirements.txt

# 前端
cd frontend
npm install
```

### 2. 启动服务

```bash
# 终端1：启动 FTP 服务器
python ftp_server.py

# 终端2：启动后端 API
cd backend
python main.py

# 终端3：启动前端开发服务器
cd frontend
npm run dev
```

### 3. 访问

打开浏览器访问 `http://localhost:5173`

默认账号：admin / admin123

## 配置

编辑 `backend/config.py`：

```python
FTP_HOST = "127.0.0.1"
FTP_PORT = 2121
FTP_USER = "admin"
FTP_PASS = "admin123"
FTP_ROOT = "/data/ftp"  # FTP 根目录
SECRET_KEY = "your-secret-key"  # JWT 密钥
```
