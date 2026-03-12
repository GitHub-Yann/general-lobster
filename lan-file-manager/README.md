# LAN File Manager 🦐

> 基于 Python + FastAPI + Vue3 的局域网文件传输系统

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-009688.svg)](https://fastapi.tiangolo.com/)
[![Vue.js](https://img.shields.io/badge/Vue.js-3.4-4FC08D.svg)](https://vuejs.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📖 项目简介

LAN File Manager 是一个专为局域网环境设计的 Web 文件管理系统。它采用前后端分离架构，内嵌 FTP 服务器提供底层文件传输能力，通过现代化的 Web 界面让用户能够方便地浏览、上传、下载和管理文件。

### 核心特性

- 🔐 **JWT 认证** - 安全的 Token 认证机制，保护您的文件安全
- 📁 **目录浏览** - 直观的文件浏览器，支持面包屑导航
- ⬆️ **大文件上传** - 支持分片上传，断点续传，最大支持 10GB 文件
- ⬇️ **文件下载** - 支持单文件和整个目录打包下载
- 📊 **实时进度** - WebSocket 实时推送上传/下载进度
- 🛡️ **安全防护** - 路径规范化处理，防止目录遍历攻击
- 🚀 **高性能** - 异步处理，支持高并发文件传输

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────┐
│              浏览器 (前端)               │
│    - Vue3 单页应用                       │
│    - Element Plus UI 组件库              │
└─────────────┬───────────────────────────┘
              │ HTTP / WebSocket
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

### 技术栈

| 层级 | 技术 | 版本 |
|------|------|------|
| 前端 | Vue 3 + Element Plus + Vite | ^3.4.15 |
| 后端 | FastAPI + Uvicorn | ^0.109.0 |
| FTP | pyftpdlib | ^1.5.9 |
| 认证 | JWT (python-jose) | ^3.3.0 |

---

## 📁 项目结构

```
lan-file-manager/
├── README.md                 # 本文件
├── requirements/             # 需求文档
│   └── prd.md               # 产品需求文档
├── backend/                  # 后端代码 (FastAPI)
│   ├── main.py              # FastAPI 主入口
│   ├── ftp_client.py        # FTP 客户端封装
│   ├── ftp_server.py        # FTP 服务器
│   ├── auth.py              # JWT 认证模块
│   ├── config.py            # 配置文件
│   ├── requirements.txt     # Python 依赖
│   └── README.md            # 后端说明
└── frontend/                 # 前端代码 (Vue3)
    ├── index.html           # HTML 入口
    ├── package.json         # Node 依赖
    ├── vite.config.js       # Vite 配置
    ├── src/
    │   ├── main.js          # 应用入口
    │   ├── App.vue          # 根组件
    │   ├── api/             # API 接口封装
    │   ├── router/          # 路由配置
    │   └── views/           # 页面视图
    │       ├── Login.vue    # 登录页
    │       └── FileManager.vue  # 文件管理页
    └── README.md            # 前端说明
```

---

## 🚀 快速开始

### 环境要求

- **Python**: 3.10 或更高版本
- **Node.js**: 18 或更高版本
- **操作系统**: Linux / macOS / Windows (推荐 Linux)

### 1️⃣ 克隆项目

```bash
git clone git@github.com:GitHub-Yann/general-lobster.git
cd general-lobster/lan-file-manager
```

### 2️⃣ 配置环境

#### 创建 FTP 根目录

```bash
# 创建 FTP 文件存储目录 (可自定义)
mkdir -p /data/ftp
# 或者使用当前目录
mkdir -p ./ftp-data
```

#### 配置后端

编辑 `backend/config.py` 或在项目根目录创建 `.env` 文件：

```bash
# .env 文件示例
FTP_HOST=127.0.0.1
FTP_PORT=2121
FTP_USER=admin
FTP_PASS=your-secure-password
FTP_ROOT=/data/ftp
API_HOST=0.0.0.0
API_PORT=8000
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

### 3️⃣ 安装依赖

#### 后端依赖

```bash
cd backend

# 创建虚拟环境 (推荐)
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或: venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

#### 前端依赖

```bash
cd frontend
npm install
```

### 4️⃣ 启动服务

需要同时启动三个服务，建议在不同的终端窗口中运行：

#### 终端 1: 启动 FTP 服务器

```bash
cd backend
python ftp_server.py
```

输出示例：
```
Starting FTP server on 127.0.0.1:2121
FTP root: /data/ftp
User: admin
FTP server started!
```

#### 终端 2: 启动后端 API

```bash
cd backend
python main.py
```

输出示例：
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

API 文档地址: http://localhost:8000/docs

#### 终端 3: 启动前端开发服务器

```bash
cd frontend
npm run dev
```

输出示例：
```
  VITE v5.0.12  ready in 300 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: http://192.168.x.x:5173/
```

### 5️⃣ 访问系统

打开浏览器访问: http://localhost:5173

**默认登录账号:**
- 用户名: `admin`
- 密码: `admin123` (或在配置中自定义)

---

## ⚙️ 详细配置

### FTP 服务器配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `FTP_HOST` | 127.0.0.1 | FTP 服务器监听地址 |
| `FTP_PORT` | 2121 | FTP 服务器端口 |
| `FTP_USER` | admin | FTP 用户名 |
| `FTP_PASS` | admin123 | FTP 密码 |
| `FTP_ROOT` | /data/ftp | FTP 根目录路径 |
| `MAX_CONS` | 256 | 最大并发连接数 |
| `MAX_CONS_PER_IP` | 5 | 每 IP 最大连接数 |
| `PASSIVE_PORTS` | 60000-60100 | 被动模式端口范围 |

### API 服务器配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `API_HOST` | 0.0.0.0 | API 监听地址 |
| `API_PORT` | 8000 | API 端口 |
| `SECRET_KEY` | lan-file-manager-secret-key | JWT 密钥 (生产环境请修改) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 1440 | Token 有效期 (分钟) |

### 上传配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `MAX_FILE_SIZE` | 10GB | 单个文件最大大小 |
| `CHUNK_SIZE` | 5MB | 分片上传大小 |
| `UPLOAD_TEMP_DIR` | /tmp/lan-file-uploads | 上传临时目录 |

---

## 📝 使用指南

### 文件管理

1. **浏览文件** - 登录后进入文件管理页面，可查看 FTP 根目录下的所有文件和文件夹
2. **路径导航** - 点击面包屑导航可快速返回上级目录
3. **新建文件夹** - 点击工具栏的"新建文件夹"按钮创建目录
4. **刷新列表** - 点击刷新按钮重新加载当前目录内容

### 文件上传

1. 点击工具栏的"上传"按钮
2. 在弹出的对话框中选择文件 (支持拖拽上传)
3. 大文件会自动分片上传，支持断点续传
4. 上传进度会实时显示

### 文件下载

1. 点击文件行右侧的"下载"按钮下载单个文件
2. 点击文件夹的"下载"按钮会将整个目录打包为 zip 下载
3. 下载进度通过 WebSocket 实时推送

### 文件操作

- **重命名** - 点击文件行的"重命名"按钮
- **删除** - 点击"删除"按钮，会弹出确认对话框
- **进入目录** - 点击文件夹名称进入该目录

---

## 🔒 安全说明

### 当前版本安全特性

- ✅ JWT Token 认证
- ✅ 路径规范化，防止目录遍历攻击
- ✅ FTP 被动模式，限制端口范围
- ✅ 上传/下载限速保护
- ✅ 最大并发连接数限制

### 安全建议

⚠️ **重要提示**: 当前版本 FTP 使用明文传输，建议仅在**受信任的局域网环境**中使用。

如需在公网或不安全网络中使用，建议：
1. 使用 VPN 或 SSH 隧道保护传输
2. 配置 FTPS/TLS 加密 (后续版本支持)
3. 定期更换管理员密码
4. 限制 FTP 服务器的访问 IP 范围

---

## 🐛 故障排除

### 常见问题

#### 1. FTP 服务器启动失败

**问题**: `Address already in use`

**解决**: 
```bash
# 查找占用 2121 端口的进程
lsof -i :2121
# 结束进程
kill -9 <PID>
```

#### 2. 前端无法连接后端

**问题**: 浏览器控制台显示 CORS 错误或连接失败

**解决**:
- 确认后端服务已启动 (http://localhost:8000)
- 检查 `frontend/vite.config.js` 中的代理配置
- 确认防火墙未拦截 8000 端口

#### 3. 上传大文件失败

**问题**: 上传过程中断或超时

**解决**:
- 检查 `MAX_FILE_SIZE` 配置是否足够大
- 检查磁盘空间是否充足
- 检查 `/tmp` 目录权限

#### 4. 无法登录

**问题**: 提示用户名或密码错误

**解决**:
- 确认使用的是 FTP 配置的账号密码
- 检查 `backend/config.py` 或 `.env` 中的配置
- 确认 FTP 服务器已正常启动

### 日志查看

```bash
# 后端日志
# 默认输出到控制台，可通过环境变量配置
LOG_LEVEL=debug python main.py

# FTP 服务器日志
# 直接查看终端输出
```

---

## 🛠️ 开发指南

### 后端开发

```bash
cd backend

# 安装开发依赖
pip install -r requirements.txt

# 运行开发服务器 (带热重载)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 运行测试
pytest
```

### 前端开发

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build

# 预览生产构建
npm run preview
```

### API 文档

启动后端后访问: http://localhost:8000/docs

---

## 📦 部署生产环境

### 使用 Docker (推荐)

```dockerfile
# Dockerfile 示例 (待补充)
FROM python:3.11-slim

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt

COPY backend/ .

EXPOSE 8000 2121

CMD ["python", "main.py"]
```

### 手动部署

1. 按照【快速开始】步骤安装依赖
2. 使用生产级 WSGI 服务器 (如 Gunicorn) 运行后端
3. 使用 Nginx 反向代理前端静态文件
4. 配置 systemd 服务确保进程常驻

---

## 📋 功能清单

### 已实现功能

- [x] JWT 用户认证
- [x] 目录浏览与导航
- [x] 文件上传 (支持拖拽)
- [x] 大文件分片上传
- [x] 断点续传
- [x] 文件下载
- [x] 目录打包下载
- [x] 新建文件夹
- [x] 文件重命名
- [x] 文件删除
- [x] 实时传输进度
- [x] 路径安全校验

### 计划功能

- [ ] FTPS/TLS 加密传输
- [ ] 多用户权限管理
- [ ] 文件预览 (图片、文本、PDF)
- [ ] 文件搜索
- [ ] 回收站功能
- [ ] 操作日志
- [ ] WebDAV 支持

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

---

## 📄 许可证

本项目采用 [MIT](LICENSE) 许可证开源。

---

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 高性能 Python Web 框架
- [Vue.js](https://vuejs.org/) - 渐进式 JavaScript 框架
- [Element Plus](https://element-plus.org/) - Vue 3 组件库
- [pyftpdlib](https://github.com/giampaolo/pyftpdlib) - Python FTP 服务器库

---

## 📞 联系方式

如有问题或建议，欢迎通过以下方式联系：

- 提交 [GitHub Issue](https://github.com/GitHub-Yann/general-lobster/issues)
- 发送邮件至: 350714953@qq.com

---

**Made with ❤️ by 虾将大人 🦐**
