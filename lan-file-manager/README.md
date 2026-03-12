# LAN File Manager

局域网文件管理器项目

## 项目结构

```
lan-file-manager/
├── README.md           # 本文件
├── requirements/       # 需求文档
│   └── prd.md
├── backend/           # 后端代码
│   ├── main.py
│   ├── auth.py
│   ├── config.py
│   ├── ftp_client.py
│   ├── ftp_server.py
│   └── requirements.txt
└── frontend/          # 前端代码
    ├── index.html
    ├── package.json
    ├── vite.config.js
    └── src/
```

## 简介

这是一个局域网文件管理器，支持 FTP 协议，提供 Web 界面管理文件。

## 技术栈

- **后端**: Python (FTP 服务器)
- **前端**: Vue 3 + Vite
