# doc-analyzer

文档智能分析系统 - 从各类文档中提取关键词和生成结构化摘要

## 项目简介

Doc Analyzer 是一个基于**节点化工作流**的文档智能分析系统，支持从 PDF、Word、TXT 和网页链接中提取关键词和生成摘要。

### 核心特性

- 📄 **多格式支持** - PDF、DOCX、TXT、URL
- 🔄 **节点化工作流** - 支持断点续传和节点级重试
- 🤖 **智能分析** - 关键词提取（KeyBERT）+ 摘要生成（结构化/TextRank）
- 🎯 **自定义配置** - 支持领域关键词和噪音词过滤
- 🧠 **LLM 增强** - 支持 OpenAI/Claude/文心一言/通义千问等模型优化结果
- 🌐 **Web 界面** - 直观的上传和结果展示
- 🚀 **异步处理** - Celery 任务队列，支持并发
- 💾 **数据库支持** - SQLite（默认）/ MySQL
- 📊 **调用追踪** - LLM 调用日志记录，便于审计和优化

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

# 可选：切换到 MySQL（不填则默认 SQLite）
DATABASE_URL=mysql+pymysql://root:password@127.0.0.1:3306/doc_analyzer?charset=utf8mb4
```

如果使用 MySQL，建议先执行统一建表脚本：
```bash
mysql -uroot -p < backend/sql/mysql_schema.sql
```

#### 3. 配置 LLM（可选）

系统支持接入大语言模型优化分析结果。在 Web 界面中配置：

1. 打开 `http://localhost:8000/app`
2. 点击右上角 **LLM 配置**
3. 添加配置：
   - **OpenAI**: API Key + 模型名称(gpt-3.5-turbo/gpt-4)
   - **Claude**: API Key + 模型名称(claude-3-haiku/claude-3-sonnet)
   - **文心一言**: API Key + Secret Key
   - **通义千问**: API Key + 模型名称(qwen-plus/qwen-turbo)
   - **自定义**: 支持任何 OpenAI 兼容接口

配置完成后，可在创建任务时选择是否使用 LLM 优化。

#### 4. 启动服务

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

#### 5. 访问系统

浏览器打开：
```
http://localhost:8000/app    # Web 界面
http://localhost:8000/docs   # API 文档 (Swagger)
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
│   │   │   ├── llm_config.py  # LLM 配置模型
│   │   │   ├── llm_prompt_template.py  # LLM Prompt 模板模型
│   │   │   └── llm_call_log.py         # LLM 调用日志模型
│   │   ├── nodes/             # 节点实现
│   │   │   ├── parse_node.py  # 文档解析
│   │   │   ├── segment_node.py # 智能分段
│   │   │   ├── keyword_node.py # 关键词提取
│   │   │   ├── summary_node.py # 摘要生成
│   │   │   └── output_node.py  # 结果输出
│   │   ├── db/                # 数据库
│   │   │   └── database.py    # 数据库配置
│   │   └── main.py            # FastAPI 入口
│   ├── static/                # 前端静态页面
│   │   └── index.html         # Vue3 + Element Plus 单页应用
│   ├── sql/                   # 数据库脚本
│   │   └── mysql_schema.sql   # MySQL 建表脚本
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
                        ↑
                 LLM 精修(llm_refine) [可选]
```

### 节点配置

| 配置名称 | 适用类型 | 节点流程 |
|---------|---------|---------|
| default | PDF/DOCX | upload → parse → segment → keyword → summary → output |
| txt_only | TXT | upload → segment → keyword → summary → output |
| keyword_only | 快速模式 | upload → parse → keyword → output |

### 节点说明

- **upload**: 文件上传验证
- **parse**: 文档解析（PDF/DOCX/URL）
- **segment**: 智能分段，根据文本长度动态调整参数
- **keyword**: 关键词提取（KeyBERT + 领域词增强）
- **summary**: 摘要生成（TextRank + 结构化）
- **llm_refine**: LLM 精修（可选，对关键词和摘要进行润色）
- **output**: 结果组装输出

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
| `/api/tasks/configs` | GET | 获取节点配置列表 |

### LLM 配置

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/llm/providers` | GET | 列出支持的 LLM 提供商 |
| `/api/llm` | GET | 获取 LLM 配置列表 |
| `/api/llm` | POST | 创建 LLM 配置 |
| `/api/llm/{id}` | PUT | 更新 LLM 配置 |
| `/api/llm/{id}` | DELETE | 删除 LLM 配置 |
| `/api/llm/{id}/test` | POST | 测试 LLM 配置 |

## 使用指南

### 自定义关键词提取

上传文档时，可以指定领域关键词和噪音词来提高提取质量：

**领域关键词** - 文档的核心概念，会被优先提取：
```
飞书文档, 索引, Agent, 检索, 微服务
```

**噪音词** - 需要过滤的无关词汇：
```
http, https, api, com, 0-1, 1-N
```

支持中英文逗号、分号、顿号、换行分隔。

### LLM 优化

1. 在 **LLM 配置** 页面添加模型配置
2. 创建任务时勾选 **使用 LLM 优化**
3. 可选择 Prompt 模板（支持自定义）
4. 系统会先使用传统算法提取，再用 LLM 进行润色整合

**Prompt 模板** - 支持自定义：
- 在数据库 `llm_prompt_templates` 表中配置
- 支持 `{payload}` 占位符插入请求数据
- 可配置系统提示词和用户提示词模板

### 任务重试

如果某个节点失败，可以从该节点重试：
```bash
curl -X POST "http://localhost:8000/api/tasks/{task_id}/retry" \
  -H "Content-Type: application/json" \
  -d '{"from_node": "keyword"}'
```

### URL 分析

支持直接分析网页内容：
```bash
curl -X POST "http://localhost:8000/api/tasks/url" \
  -F "url=https://example.com/article" \
  -F "use_llm_refine=true"
```

## 技术栈

- **后端**: FastAPI + SQLAlchemy + SQLite/MySQL
- **任务队列**: Celery + Redis
- **前端**: Vue3 + Element Plus (CDN 版本，无需构建)
- **文档解析**: pdfplumber + python-docx + requests
- **NLP**: KeyBERT + jieba + scikit-learn
- **LLM 集成**: 支持 OpenAI/Claude/文心一言/通义千问等

## 数据库表结构

| 表名 | 说明 |
|------|------|
| `tasks` | 任务主表 |
| `node_configs` | 节点配置表 |
| `node_data` | 节点运行数据表 |
| `llm_configs` | LLM 配置表 |
| `llm_prompt_templates` | Prompt 模板表 |
| `llm_call_logs` | LLM 调用日志表 |

## 开发计划

- [x] Week 1: 基础框架（FastAPI + SQLite + Celery）
- [x] Week 2: 节点实现（解析/分段/关键词/摘要）
- [x] Week 3: Web 界面（Vue3 + 文件上传 + 结果展示）
- [x] Week 4: 优化完善（重试机制 + 错误处理 + LLM 集成）
- [x] Week 5: 高级功能（自定义关键词 + 结构化摘要 + LLM Prompt 模板）
- [x] Week 6: 调用追踪（LLM 调用日志 + 审计功能）

## 使用示例

### 上传文件分析

```bash
curl -X POST "http://localhost:8000/api/tasks" \
  -F "file=@document.pdf" \
  -F "config_name=default" \
  -F "domain_keywords=人工智能,机器学习" \
  -F "noise_words=http,https"
```

### URL 分析

```bash
curl -X POST "http://localhost:8000/api/tasks/url" \
  -F "url=https://example.com/article" \
  -F "use_llm_refine=true"
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
  },
  "processing_info": {
    "completed_at": "2026-03-25T10:30:00",
    "llm_refine_used": true,
    "llm_provider": "bailian",
    "llm_model": "qwen-plus"
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

- **SQLite**: 数据库文件位于 `data/doc_analyzer.db`
- **MySQL**: 执行 `backend/sql/mysql_schema.sql` 建表

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
