# LAN File Manager - 产品需求文档 (PRD)

## 1. 项目概述

### 1.1 项目背景
需要一个基于 Python 的局域网文件传输系统，用于在局域网内快速、安全地进行文件和目录的传输。

### 1.2 项目目标
构建一个前后端分离的 Web 文件管理器，支持文件/目录的上传、下载、浏览和管理功能。

### 1.3 目标用户
局域网内的用户，需要在多台设备间传输文件。

---

## 2. 功能需求

### 2.1 核心功能

| 功能模块 | 需求描述 | 优先级 |
|---------|---------|--------|
| FTP 服务 | 内嵌 FTP 服务器，提供底层文件传输能力 | P0 |
| 目录浏览 | 展示服务端指定目录及其子目录内容 | P0 |
| 文件上传 | 支持本地文件上传到服务器指定目录 | P0 |
| 目录上传 | 支持本地目录（含子目录）上传到服务器 | P0 |
| 文件下载 | 支持服务器文件下载到本地 | P0 |
| 目录下载 | 支持服务器目录（打包）下载到本地 | P0 |

### 2.2 管理功能

| 功能模块 | 需求描述 | 优先级 |
|---------|---------|--------|
| 用户认证 | JWT Token 认证，确保只有授权用户可访问 | P0 |
| 新建文件夹 | 在服务器创建新目录 | P1 |
| 文件重命名 | 支持文件/目录重命名 | P1 |
| 文件删除 | 支持文件/目录删除（递归删除目录） | P1 |
| 路径导航 | 面包屑导航，支持返回上级目录 | P1 |

### 2.3 高级功能

| 功能模块 | 需求描述 | 优先级 |
|---------|---------|--------|
| 大文件支持 | 分片上传，支持断点续传 | P2 |
| 传输进度 | 实时显示上传/下载进度 | P2 |
| 批量操作 | 支持多文件同时上传/下载 | P2 |

---

## 3. 技术架构

### 3.1 部署架构
```
┌─────────────────────────────────────────┐
│              浏览器 (前端)               │
│    - Vue3 单页应用                       │
│    - Element Plus UI 组件库              │
└─────────────┬───────────────────────────┘
              │ HTTP/WebSocket
┌─────────────▼───────────────────────────┐
│           FastAPI (后端 API)            │
│    - RESTful API                        │
│    - JWT 认证                           │
│    - FTP 客户端封装                      │
└─────────────┬───────────────────────────┘
              │ (本地连接)
┌─────────────▼───────────────────────────┐
│         pyftpdlib (FTP 服务器)          │
│    - 实际文件存储                        │
│    - 被动模式，限速保护                   │
└─────────────────────────────────────────┘
```

### 3.2 技术栈

**后端:**
- 语言: Python 3.10+
- 框架: FastAPI
- FTP 库: pyftpdlib
- 认证: JWT (python-jose)

**前端:**
- 框架: Vue 3
- UI 库: Element Plus
- 构建工具: Vite
- HTTP 客户端: Axios

---

## 4. 安全需求

### 4.1 认证授权
- 用户登录使用 JWT Token 认证
- Token 有效期: 24 小时
- 默认账号: admin / admin123

### 4.2 路径安全
- 路径规范化处理，防止目录遍历攻击 (../)
- 所有路径必须在 FTP 根目录范围内
- 禁止访问系统敏感目录

### 4.3 传输安全
- FTP 被动模式，限制端口范围
- 上传/下载限速（默认 10MB/s）
- 最大并发连接数限制

---

## 5. 接口规范

### 5.1 认证接口

**POST /api/auth/login**
- 功能: 用户登录
- 请求: `{ username, password }`
- 响应: `{ access_token, token_type }`

### 5.2 文件管理接口

**GET /api/files**
- 功能: 列出目录内容
- 参数: `path` (目录路径)
- 响应: `[{ name, path, size, is_dir, permissions }]`

**POST /api/files/upload**
- 功能: 上传文件
- 参数: `path` (目标目录), `file` (文件)
- 响应: `{ success, path }`

**POST /api/files/upload/chunk**
- 功能: 分片上传
- 参数: `filename, chunk_index, total_chunks, upload_id, path`
- 响应: `{ success, completed, uploaded, total }`

**GET /api/files/download**
- 功能: 下载文件
- 参数: `path` (文件路径)
- 响应: 文件流 (blob)

**POST /api/files/mkdir**
- 功能: 创建目录
- 参数: `path` (目录路径)
- 响应: `{ success }`

**POST /api/files/rename**
- 功能: 重命名
- 参数: `old_path, new_path`
- 响应: `{ success }`

**DELETE /api/files**
- 功能: 删除文件/目录
- 参数: `path, is_dir`
- 响应: `{ success }`

### 5.3 WebSocket 接口

**WS /ws/{client_id}**
- 功能: 实时传输进度推送
- 消息格式: `{ type: "progress", uploaded, total, percent }`

---

## 6. 界面设计

### 6.1 登录页
- 用户名/密码输入框
- 登录按钮
- 背景渐变样式

### 6.2 文件管理页
- 顶部工具栏: 返回、面包屑导航、上传、新建文件夹、刷新、退出
- 文件列表表格: 图标、文件名、大小、权限、操作按钮
- 空状态提示

### 6.3 对话框
- 上传对话框: 拖拽上传区域
- 新建文件夹对话框: 名称输入
- 重命名对话框: 新名称输入
- 删除确认对话框

---

## 7. 配置参数

### 7.1 FTP 配置
```python
FTP_HOST = "127.0.0.1"
FTP_PORT = 2121
FTP_USER = "admin"
FTP_PASS = "admin123"
FTP_ROOT = "/data/ftp"
MAX_CONS = 256
MAX_CONS_PER_IP = 5
PASSIVE_PORTS = 60000-60100
```

### 7.2 API 配置
```python
API_HOST = "0.0.0.0"
API_PORT = 8000
SECRET_KEY = "lan-file-manager-secret-key"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24小时
```

### 7.3 上传配置
```python
MAX_FILE_SIZE = 10GB
CHUNK_SIZE = 5MB
UPLOAD_TEMP_DIR = "/tmp/lan-file-uploads"
```

---

## 8. 部署说明

### 8.1 环境要求
- Python 3.10+
- Node.js 18+
- 端口: 2121 (FTP), 8000 (API), 5173 (前端开发)

### 8.2 启动步骤
```bash
# 1. 启动 FTP 服务器
python ftp_server.py

# 2. 启动后端 API
cd backend
pip install -r requirements.txt
python main.py

# 3. 启动前端
cd frontend
npm install
npm run dev
```

### 8.3 访问地址
- 前端: http://localhost:5173
- API 文档: http://localhost:8000/docs

---

## 9. 项目目录结构

```
/root/projects/
├── requirement/lan-file-manager/
│   └── prd.md                    # 本文件
├── backend/lan-file-manager/
│   ├── ftp_server.py            # FTP 服务器
│   ├── main.py                  # FastAPI 主入口
│   ├── ftp_client.py            # FTP 客户端封装
│   ├── auth.py                  # JWT 认证
│   ├── config.py                # 配置
│   └── requirements.txt         # Python 依赖
└── frontend/lan-file-manager/
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── main.js
        ├── App.vue
        ├── router/
        ├── api/
        └── views/
            ├── Login.vue
            └── FileManager.vue
```

---

## 10. 风险与限制

### 10.1 已知限制
- 当前版本 FTP 明文传输，建议局域网内使用
- 大文件分片上传需要进一步优化断点续传
- 目录下载暂时打包为 zip，大目录可能耗时较长

### 10.2 后续优化方向
- 添加 FTPS/TLS 加密传输
- 完善分片上传的断点续传机制
- 添加文件预览功能
- 支持多用户权限管理

---

**文档版本:** v1.0  
**创建日期:** 2026-03-11  
**作者:** 虾将大人 🦐
