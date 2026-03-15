# REQ: 文件夹下载功能

> **状态**: 🔵 需求完成
> **创建日期**: 2026-03-15
> **更新日期**: 2026-03-15

## 1. 需求背景

当前系统支持单个文件的上传和下载，但用户需要下载整个文件夹时，只能逐个文件下载，操作繁琐。需要支持一键下载整个文件夹，将文件夹内容打包成压缩包（ZIP）后下载。

## 2. 功能需求

### 2.1 核心功能
- [ ] 在文件管理器界面，文件夹行显示"下载"按钮
- [ ] 点击文件夹下载按钮，将文件夹及其所有内容打包为 ZIP 文件
- [ ] ZIP 文件保留原文件夹的目录结构
- [ ] 下载完成后，浏览器自动保存 ZIP 文件

### 2.2 交互细节
- [ ] 下载大文件夹时显示进度提示（可选）
- [ ] 文件夹名称作为 ZIP 文件的默认文件名
- [ ] 如果文件夹为空，下载空 ZIP 文件或提示用户

### 2.3 边界情况
- [ ] 处理文件夹中包含大量文件的情况
- [ ] 处理文件夹嵌套层级很深的情况
- [ ] 处理文件名包含特殊字符的情况

## 3. 技术方案

### 3.1 大文件处理策略

**问题**: 10GB+ 的大文件夹如果先压缩再下载，会带来以下问题：
1. 压缩耗时很长，用户等待时间久
2. 临时 ZIP 文件占用大量磁盘空间
3. 压缩完成后才能开始下载，效率低

**解决方案**: 流式 ZIP 生成 + 边压缩边下载

```
用户点击下载
    ↓
后端开始遍历文件夹
    ↓
逐个文件从FTP读取 → 实时写入ZIP流 → 浏览器接收
    ↓
所有文件处理完毕，ZIP流结束
```

**优势**:
- 无需等待全部压缩完成，用户立即开始下载
- 不生成临时文件，节省磁盘空间
- 内存占用低（一次只处理一个文件）

### 3.2 技术实现细节

**后端实现**:
- 使用 `zipstream` 或 `zipfile` + `Generator` 实现流式 ZIP
- 通过 `StreamingResponse` 流式返回
- 逐个文件从 FTP 读取，实时写入 ZIP 流
- 不存储临时文件，内存中只保留当前处理的数据块

**代码示例**:
```python
from fastapi.responses import StreamingResponse
import zipfile
import io

def generate_zip_stream(folder_path):
    """流式生成 ZIP 文件"""
    # 使用内存中的缓冲区，但数据会立即发送给客户端
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file_info in walk_ftp_directory(folder_path):
            # 从 FTP 读取文件数据
            file_data = ftp_client.download_file(file_info.path)
            # 写入 ZIP
            zf.writestr(file_info.relative_path, file_data.getvalue())
            # 刷新缓冲区，让数据流式发送
            buffer.seek(0)
            yield buffer.read()
            buffer.seek(0)
            buffer.truncate()

@app.get("/api/files/download-folder")
async def download_folder(path: str):
    return StreamingResponse(
        generate_zip_stream(path),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(folder_name)}.zip"}
    )
```

### 3.3 前端实现
- 在文件夹行的操作按钮中添加"下载"按钮
- 调用新的 API 端点 `/api/files/download-folder`
- 大文件下载时显示"正在打包下载..."提示

### 3.4 API 设计
```
GET /api/files/download-folder?path={folder_path}
Response: ZIP 文件流（流式传输）
```

## 4. 验收标准

- [ ] 在文件管理器中，文件夹行显示下载按钮
- [ ] 点击下载按钮，浏览器下载一个 ZIP 文件
- [ ] ZIP 文件内容与原文件夹结构一致
- [ ] ZIP 文件可以正常解压，文件内容完整
- [ ] 支持中文文件夹名和文件名
- [ ] 支持嵌套文件夹结构
- [ ] 大文件夹（10GB+）也能正常下载，不占用大量磁盘空间
- [ ] 下载开始后用户立即收到响应，无需等待全部压缩完成

## 5. 变更记录

| 日期 | 版本 | 变更内容 | 作者 |
|------|------|---------|------|
| 2026-03-15 | v1.0 | 初始需求文档 | AI |
| 2026-03-15 | v1.1 | 添加大文件流式处理方案 | AI |
| 2026-03-15 | v1.2 | 需求完成，测试通过 | 用户 |
