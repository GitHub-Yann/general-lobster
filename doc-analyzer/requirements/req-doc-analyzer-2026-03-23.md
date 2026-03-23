# 需求文档：文档智能分析系统 (doc-analyzer)

> **状态**: 🟢 需求确认  
> **创建日期**: 2026-03-23  
> **版本**: v1.0

---

## 1. 项目背景

需要一个能够从各类文档（PDF、Word、TXT、文章链接）中提取关键词和关键内容（结论/摘要）的Web应用系统。

---

## 2. 功能需求

### 2.1 核心功能

| 功能模块 | 描述 | 优先级 |
|---------|------|--------|
| 文档上传 | 支持 PDF、DOCX、TXT 文件上传，以及 URL 链接输入 | P0 |
| 文档解析 | 将各类文档解析为纯文本 | P0 |
| 智能分段 | 长文档自动分段处理 | P0 |
| 关键词提取 | 提取中英文关键词及权重 | P0 |
| 摘要生成 | 生成文档核心结论/摘要 | P0 |
| 结果展示 | Web界面展示分析结果 | P0 |
| 历史记录 | 保存任务历史，支持查看 | P1 |
| 节点重试 | 失败节点可从断点恢复 | P1 |

### 2.2 支持的文档类型

| 类型 | 扩展名 | 处理方式 |
|------|--------|---------|
| PDF | .pdf | pdfplumber 提取 |
| Word | .docx | python-docx 读取 |
| 文本 | .txt | 直接读取 |
| 网页 | URL | requests + BeautifulSoup 爬取 |

### 2.3 节点化工作流

```
文档上传(upload) → 文档解析(parse) → 智能分段(segment) 
                                                ↓
结果输出(output) ← 摘要生成(summary) ← 关键词提取(keyword)
```

**节点状态**: ⏳ pending / 🔄 running / ✅ completed / ❌ failed

### 2.4 节点配置（根据文档类型选择流程）

| 配置名称 | 适用类型 | 节点流程 |
|---------|---------|---------|
| default | PDF/DOCX | upload → parse → segment → keyword → summary → output |
| txt_only | TXT | upload → segment → keyword → summary → output |
| keyword_only | 快速模式 | upload → parse → keyword → output |

---

## 3. 技术方案

### 3.1 技术栈

| 层级 | 技术选型 |
|------|---------|
| 前端 | Vue3 + Element Plus |
| 后端 | FastAPI |
| 任务队列 | Celery + Redis |
| 数据库 | SQLite |
| 文档解析 | pdfplumber, python-docx, textract |
| NLP处理 | jieba, KeyBERT, transformers |

### 3.2 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    前端 (Vue3)                          │
│  文件上传 │ 任务列表 │ 进度查看 │ 结果展示 │ 历史记录    │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│                  FastAPI 后端服务                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ 任务管理  │  │ 节点执行  │  │ 结果接口  │              │
│  │  - 创建   │  │  - 调度   │  │  - 查询   │              │
│  │  - 状态   │  │  - 重试   │  │  - 导出   │              │
│  └──────────┘  └──────────┘  └──────────┘              │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│              Celery Worker (异步任务)                    │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐           │
│  │ parse  │ │segment │ │keyword │ │summary │           │
│  │ 节点   │ │ 节点   │ │ 节点   │ │ 节点   │           │
│  └────────┘ └────────┘ └────────┘ └────────┘           │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│              SQLite 数据库                              │
│  tasks 表 │ node_data 表 │ node_configs 表              │
└─────────────────────────────────────────────────────────┘
```

### 3.3 数据库设计

#### tasks 表（任务主表）
```sql
CREATE TABLE tasks (
    task_id TEXT PRIMARY KEY,           -- UUID
    filename TEXT NOT NULL,             -- 原始文件名
    file_path TEXT NOT NULL,            -- 文件存储路径
    file_type TEXT,                     -- pdf/docx/txt/url
    config_name TEXT DEFAULT 'default', -- 节点配置名称
    status TEXT DEFAULT 'pending',      -- pending/running/completed/failed
    current_node TEXT DEFAULT 'upload', -- 当前执行节点
    result_data TEXT,                   -- 最终结果JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### node_data 表（节点中间数据）
```sql
CREATE TABLE node_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT REFERENCES tasks(task_id),
    node_name TEXT NOT NULL,            -- 节点名称
    status TEXT DEFAULT 'pending',      -- pending/running/completed/failed
    input_data TEXT,                    -- 输入数据JSON
    output_data TEXT,                   -- 输出数据JSON（中间结果）
    error_msg TEXT,                     -- 错误信息
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(task_id, node_name)
);
```

#### node_configs 表（节点配置）
```sql
CREATE TABLE node_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_name TEXT UNIQUE,            -- 配置名称
    nodes TEXT NOT NULL,                -- 节点列表JSON
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 4. API 接口设计

### 4.1 任务管理接口

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/tasks` | POST | 创建任务（上传文件） |
| `/api/tasks` | GET | 获取任务列表 |
| `/api/tasks/{task_id}` | GET | 获取任务详情 |
| `/api/tasks/{task_id}/retry` | POST | 从指定节点重试 |
| `/api/tasks/{task_id}/result` | GET | 获取分析结果 |

### 4.2 关键接口详情

#### 创建任务
```http
POST /api/tasks
Content-Type: multipart/form-data

file: <文件>
config_name: "default"  # 可选
```

响应：
```json
{
  "task_id": "uuid",
  "status": "pending",
  "message": "任务创建成功"
}
```

#### 获取任务详情
```http
GET /api/tasks/{task_id}
```

响应：
```json
{
  "task_id": "uuid",
  "filename": "document.pdf",
  "status": "running",
  "current_node": "keyword",
  "nodes": [
    {"name": "upload", "status": "completed"},
    {"name": "parse", "status": "completed"},
    {"name": "segment", "status": "completed"},
    {"name": "keyword", "status": "running"},
    {"name": "summary", "status": "pending"},
    {"name": "output", "status": "pending"}
  ],
  "created_at": "2026-03-23T13:00:00",
  "updated_at": "2026-03-23T13:05:00"
}
```

#### 节点重试
```http
POST /api/tasks/{task_id}/retry
Content-Type: application/json

{
  "from_node": "parse"  # 从哪个节点开始重试
}
```

#### 获取结果
```http
GET /api/tasks/{task_id}/result
```

响应：
```json
{
  "task_id": "uuid",
  "keywords": [
    {"word": "人工智能", "weight": 0.95},
    {"word": "machine learning", "weight": 0.88}
  ],
  "summary": "本文主要讨论了...",
  "full_text": "...",
  "completed_at": "2026-03-23T13:10:00"
}
```

---

## 5. 预留扩展

### 5.1 大模型API接口（Phase 2）
预留接口配置，支持接入：
- OpenAI GPT
- Claude
- 文心一言
- 通义千问

配置表：
```sql
CREATE TABLE llm_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT,          -- openai/claude/wenxin
    api_key TEXT,
    api_base TEXT,
    model TEXT,
    enabled BOOLEAN DEFAULT 0
);
```

### 5.2 高级功能（Future）
- 批量文档处理
- 自定义提取模板
- 结果导出（PDF/Word）
- 多语言支持优化

---

## 6. 验收标准

### 6.1 功能验收

| 验收项 | 标准 |
|--------|------|
| 文件上传 | 支持 PDF/DOCX/TXT/URL，单文件最大 50MB |
| 文档解析 | 正确提取文本内容，保留段落结构 |
| 关键词提取 | 提取 10-20 个关键词，按权重排序 |
| 摘要生成 | 生成 200-500 字摘要，覆盖核心结论 |
| 节点状态 | 每个节点状态可追踪，失败可重试 |
| 并发处理 | 支持 5 个任务并发执行 |
| 历史记录 | 任务结果持久化，可查询历史 |

### 6.2 性能指标

| 指标 | 目标 |
|------|------|
| 单文档处理时间 | < 30 秒（< 10MB 文档） |
| 并发稳定性 | 5 并发无错误 |
| 接口响应 | < 500ms（非计算接口） |

### 6.3 质量指标

| 指标 | 目标 |
|------|------|
| 关键词准确率 | > 80%（人工评估） |
| 摘要相关性 | > 75%（人工评估） |

---

## 7. 项目结构

```
doc-analyzer/
├── requirements/               # 需求文档
│   └── req-doc-analyzer-2026-03-23.md
├── backend/                    # 后端代码
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py            # FastAPI 入口
│   │   ├── api/               # API 路由
│   │   ├── core/              # 核心逻辑
│   │   ├── models/            # 数据模型
│   │   ├── nodes/             # 节点实现
│   │   └── db/                # 数据库
│   ├── celery_worker.py       # Celery  worker
│   ├── requirements.txt
│   └── config.py
├── frontend/                   # 前端代码
│   ├── src/
│   ├── package.json
│   └── vite.config.js
├── uploads/                    # 上传文件存储
├── data/                       # SQLite 数据库
└── README.md
```

---

## 8. 开发计划

### Phase 1: 基础框架（Week 1）
- [x] 项目初始化，目录结构
- [x] FastAPI + SQLite 搭建
- [x] 基础 API 接口
- [x] Celery 异步任务框架

### Phase 2: 节点实现（Week 2）
- [x] 文档解析节点（PDF/DOCX/TXT/URL）
- [x] 智能分段节点
- [x] 关键词提取节点（KeyBERT + TF-IDF 备选）
- [x] 摘要生成节点（TextRank）
- [x] Celery 任务编排
- [x] 节点中间数据落库
- [x] URL 输入支持

### Phase 3: Web界面（Week 3）
- [ ] Vue3 项目搭建
- [ ] 文件上传组件
- [ ] 任务列表/详情页面
- [ ] 结果展示页面

### Phase 4: 优化完善（Week 4）
- [ ] 节点重试功能
- [ ] 错误处理优化
- [ ] 性能优化
- [ ] 预留大模型接口

---

## 9. 风险评估

| 风险 | 影响 | 应对措施 |
|------|------|---------|
| 长文档处理慢 | 中 | 分段处理 + 异步执行 |
| 复杂PDF解析失败 | 中 | 多库备选 + 错误提示 |
| 关键词质量不高 | 中 | 可调参数 + 预留大模型接口 |
| 并发资源占用 | 低 | 限制5并发 + 队列控制 |

---

## 10. 附录

### 10.1 参考库版本
- FastAPI: ^0.104.0
- Celery: ^5.3.0
- SQLAlchemy: ^2.0.0
- pdfplumber: ^0.10.0
- python-docx: ^1.1.0
- KeyBERT: ^0.8.0
- transformers: ^4.35.0
- Vue3: ^3.3.0
- Element Plus: ^2.4.0

### 10.2 命名规范
- 任务ID: UUID v4
- 数据库表: 小写下划线
- API路径: RESTful风格，小写中划线
- 代码变量: 小写下划线（Python）/ 驼峰（JS）

---

**文档维护记录**
| 日期 | 版本 | 修改内容 | 修改人 |
|------|------|---------|--------|
| 2026-03-23 | v1.0 | 初稿 | 虾将大人 |
