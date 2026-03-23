# Projects

本目录包含所有开发项目

## 项目列表

| 项目名称 | 描述 | 状态 |
|---------|------|------|
| lan-file-manager | 局域网文件管理器 | 🟢 活跃 |
| doc-analyzer | 文档智能分析系统 | 🟢 已完成 |

### doc-analyzer

文档智能分析系统 - 从 PDF、Word、TXT 和网页中提取关键词和摘要

- **功能**: 文档解析、智能分段、关键词提取、摘要生成
- **技术栈**: FastAPI + Vue3 + Celery + SQLite
- **特点**: 节点化工作流、断点续传、Web 界面
- **路径**: [./doc-analyzer](./doc-analyzer/)

### lan-file-manager

局域网文件管理器 - 通过 FTP 管理局域网文件

- **功能**: 文件上传下载、目录管理
- **技术栈**: Python + FTP
- **路径**: [./lan-file-manager](./lan-file-manager/)

## 目录规范

```
/root/projects
├── README.md                    # 本文件
└── {project-name}/              # 单个项目目录
    ├── README.md               # 项目说明
    ├── requirements/           # 需求文档
    ├── backend/               # 后端代码
    └── frontend/              # 前端代码
```

## Git 仓库

- **远程地址**: `git@github.com:GitHub-Yann/general-lobster.git`
- **本地路径**: `/root/projects/`
- **访问**: https://github.com/GitHub-Yann/general-lobster
