# doc-analyzer

文档智能分析系统 - 从各类文档中提取关键词和关键内容

## 项目结构

```
doc-analyzer/
├── requirements/               # 需求文档
├── backend/                    # 后端代码 (FastAPI)
│   ├── app/
│   │   ├── api/               # API 路由
│   │   ├── core/              # 核心逻辑
│   │   ├── models/            # 数据模型
│   │   ├── nodes/             # 节点实现
│   │   └── db/                # 数据库
│   ├── celery_worker.py       # Celery worker
│   └── requirements.txt
├── frontend/                   # 前端代码 (Vue3)
├── uploads/                    # 上传文件存储
└── data/                       # SQLite 数据库
```

## 快速开始

### 后端启动

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 启动服务
uvicorn app.main:app --reload

# 启动 Celery worker
celery -A celery_worker worker --loglevel=info
```

### 前端启动

```bash
cd frontend
npm install
npm run dev
```

## 技术栈

- **后端**: FastAPI + Celery + SQLite
- **前端**: Vue3 + Element Plus
- **任务队列**: Celery + Redis
- **NLP**: KeyBERT + Transformers

## 功能特性

- 支持 PDF、DOCX、TXT、URL 文档分析
- 节点化工作流，支持断点续传
- 关键词提取 + 智能摘要
- Web 界面管理任务

## License

MIT
