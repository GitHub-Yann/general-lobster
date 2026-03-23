# doc-analyzer

文档智能分析系统 - 从各类文档中提取关键词和核心内容

## 项目简介

Doc Analyzer 是一个基于节点化工作流的文档智能分析系统，支持从 PDF、Word、TXT 和网页链接中提取关键词和生成摘要。

### 核心特性

- 📄 **多格式支持** - PDF、DOCX、TXT、URL
- 🔄 **节点化工作流** - 支持断点续传和节点级重试
- 🤖 **智能分析** - 关键词提取（KeyBERT）+ 摘要生成（TextRank）
- 🌐 **Web 界面** - 直观的上传和结果展示
- 🚀 **异步处理** - Celery 任务队列，支持并发
- 🔌 **大模型预留** - 支持接入 OpenAI/Claude/文心一言

## 快速开始

### 环境要求

- Python 3.8+
- Redis（用于 Celery 任务队列）

### 完整启动步骤

#### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

#### 2. 配置 Redis

复制示例配置文件：
```bash
copy .env.example .env    # Windows
# 或
cp .env.example .env      # Linux/Mac
```

编辑 `backend/.env`，修改 Redis 地址：
```ini
# 如果 Redis 在其他机器
REDIS_URL=redis://192.168.1.100:6379/0

# 如果 Redis 在本机（默认）
REDIS_URL=redis://localhost:6379/0
```

#### 3. 启动服务

需要同时运行三个服务（三个终端窗口）：

**终端 1 - 启动 Redis：**
```bash
redis-server
```

**终端 2 - 启动后端 API：**
```bash
cd backend
python start.py
```

**终端 3 - 启动 Celery Worker：**
```bash
cd backend
celery -A celery_worker worker --loglevel=info
```

所有配置（端口、Redis地址等）都在 `backend/.env` 文件中修改。

#### 4. 访问系统

浏览器打开：
```
http://localhost:8000/app    # Web 界面
```

### 前端说明

前端使用 Vue3 + Element Plus（CDN 版本），是单文件 `backend/static/index.html`，不需要 Node.js 构建。

FastAPI 会自动将 `backend/static/` 目录挂载到 `/app` 路径。

## 项目结构

```
doc-analyzer/
├── requirements/               # 需求文档
│   └── req-doc-analyzer-2026-03-23.md
├── backend/                    # 后端代码 (FastAPI)
│   ├── app/
│   │   ├── api/               # API 路由
│   │   │   ├── tasks.py       # 任务管理接口
│   │   │   └── llm.py         # LLM 配置接口
│   │   ├── core/              # 核心逻辑
│   │   │   ├── tasks.py       # Celery 任务编排
│   │   │   ├── schemas.py     # 数据模型
│   │   │   └── llm_service.py # LLM 服务接口
│   │   ├── models/            # 数据库模型
│   │   │   ├── task.py        # 任务模型
│   │   │   ├── node_data.py   # 节点数据模型
│   │   │   ├── node_config.py # 节点配置模型
│   │   │   └── llm_config.py  # LLM 配置模型
│   │   ├── nodes/             # 节点实现
│   │   │   ├── parse_node.py  # 文档解析
│   │   │   ├── segment_node.py # 智能分段
│   │   │   ├── keyword_node.py # 关键词提取
│   │   │   ├── summary_node.py # 摘要生成
│   │   │   └── output_node.py  # 结果输出
│   │   ├── db/                # 数据库
│   │   │   └── database.py    # SQLite 配置
│   │   └── main.py            # FastAPI 入口
│   ├── static/                # 前端静态页面
│   │   └── index.html         # Vue3 + Element Plus 单页应用
│   ├── celery_worker.py       # Celery worker
│   ├── start.py               # 启动脚本
│   ├── requirements.txt       # Python 依赖
│   └── .env.example           # 配置示例
├── uploads/                    # 上传文件存储
├── data/                       # SQLite 数据库
└── README.md                   # 本文件
```

## 工作流节点

```
文档上传(upload) → 文档解析(parse) → 智能分段(segment) 
                                                ↓
结果输出(output) ← 摘要生成(summary) ← 关键词提取(keyword)
```

### 节点配置

| 配置名称 | 适用类型 | 节点流程 |
|---------|---------|---------|
| default | PDF/DOCX | upload → parse → segment → keyword → summary → output |
| txt_only | TXT | upload → segment → keyword → summary → output |
| keyword_only | 快速模式 | upload → parse → keyword → output |

## API 接口

### 任务管理

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/tasks` | POST | 创建任务（上传文件） |
| `/api/tasks/url` | POST | 创建 URL 分析任务 |
| `/api/tasks` | GET | 获取任务列表 |
| `/api/tasks/{id}` | GET | 获取任务详情 |
| `/api/tasks/{id}/retry` | POST | 从指定节点重试 |
| `/api/tasks/{id}/result` | GET | 获取分析结果 |

### LLM 配置

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/llm/providers` | GET | 列出支持的 LLM 提供商 |
| `/api/llm` | GET | 获取 LLM 配置列表 |
| `/api/llm` | POST | 创建 LLM 配置 |
| `/api/llm/{id}` | PUT | 更新 LLM 配置 |
| `/api/llm/{id}` | DELETE | 删除 LLM 配置 |

## 技术栈

- **后端**: FastAPI + SQLAlchemy + SQLite
- **任务队列**: Celery + Redis
- **前端**: Vue3 + Element Plus (CDN 版本，无需构建)
- **文档解析**: pdfplumber + python-docx
- **NLP**: KeyBERT + jieba + scikit-learn

## 开发计划

- [x] Week 1: 基础框架（FastAPI + SQLite + Celery）
- [x] Week 2: 节点实现（解析/分段/关键词/摘要）
- [x] Week 3: Web 界面（Vue3 + 文件上传 + 结果展示）
- [x] Week 4: 优化完善（重试机制 + 错误处理 + LLM 预留）

## 使用示例

### 上传文件分析

```bash
curl -X POST "http://localhost:8000/api/tasks" \
  -F "file=@document.pdf" \
  -F "config_name=default"
```

### URL 分析

```bash
curl -X POST "http://localhost:8000/api/tasks/url" \
  -F "url=https://example.com/article"
```

### 获取结果

```bash
curl "http://localhost:8000/api/tasks/{task_id}/result"
```

## 响应示例

```json
{
  "task_id": "uuid",
  "keywords": [
    {"word": "人工智能", "weight": 0.95},
    {"word": "machine learning", "weight": 0.88}
  ],
  "summary": "本文主要讨论了...",
  "full_text": "...",
  "statistics": {
    "word_count": 5000,
    "segment_count": 3,
    "keyword_count": 15,
    "compression_ratio": 0.15
  }
}
```

## 配置说明

### 配置文件

项目使用 `.env` 文件进行配置，位于 `backend/.env`。

**创建配置文件：**
```bash
cd backend
copy .env.example .env    # Windows
# 或
cp .env.example .env      # Linux/Mac
```

**编辑 `backend/.env`：**
```ini
# Redis Configuration
REDIS_URL=redis://192.168.1.100:6379/0

# Server Configuration
HOST=0.0.0.0
PORT=8000

# Development Mode
RELOAD=true

# File Upload Configuration
MAX_FILE_SIZE=52428800

# Celery Configuration
CELERY_WORKERS=4
```

### 配置项说明

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `REDIS_URL` | `redis://localhost:6379/0` | Redis 连接地址 |
| `HOST` | `0.0.0.0` | 服务器监听地址 |
| `PORT` | `8000` | 服务器端口 |
| `RELOAD` | `true` | 开发模式（代码修改自动重启） |
| `MAX_FILE_SIZE` | `52428800` | 最大文件大小（字节） |
| `CELERY_WORKERS` | `4` | Celery Worker 数量 |

### Redis 配置示例

```ini
# 本机 Redis 无密码
REDIS_URL=redis://localhost:6379/0

# 局域网 Redis 无密码
REDIS_URL=redis://192.168.1.100:6379/0

# Redis 有密码（注意冒号位置）
REDIS_URL=redis://:mypassword@192.168.1.100:6379/0
```

### 数据库

SQLite 数据库文件位于 `data/doc_analyzer.db`

## 贡献指南

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/xxx`)
3. 提交更改 (`git commit -am 'Add xxx'`)
4. 推送分支 (`git push origin feature/xxx`)
5. 创建 Pull Request

## 许可证

MIT License

## 作者

🦐 虾将大人
