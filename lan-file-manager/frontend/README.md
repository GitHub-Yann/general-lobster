# LAN File Manager - Frontend

局域网文件管理器前端项目

## 技术栈

- Vue 3
- Element Plus
- Vite
- Axios

## 功能特性

- 📁 目录浏览（面包屑导航）
- ⬆️ 文件上传（拖拽上传）
- ⬇️ 文件下载
- 📂 新建文件夹
- ✏️ 文件重命名
- 🗑️ 文件删除
- 🔐 JWT 认证

## 开发环境

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build
```

## 项目结构

```
src/
├── api/           # API 接口
├── router/        # 路由配置
├── views/         # 页面视图
│   ├── Login.vue
│   └── FileManager.vue
├── App.vue
└── main.js
```

## 配置

开发服务器代理配置在 `vite.config.js`：
- `/api` → `http://localhost:8000`
- `/ws` → `ws://localhost:8000`

## 访问地址

开发环境: http://localhost:5173

---

*LAN File Manager 🦐*
