# 共享剪切板（Clipboard）

一个基于 Flask + Flask‑SocketIO 的轻量级“共享剪切板”小工具。通过浏览器访问即可在多个设备之间实时同步文本内容，数据持久化存储到本地 SQLite。

## 用途
- 在同一局域网或通过端口映射的环境中，快速在多设备间共享文本。
- 团队临时协作、跨设备拷贝片段、记录临时笔记。

## 功能
- 实时同步：网页端内容变更后自动广播到所有在线客户端（Socket.IO）。
- 自动保存：停止输入 3 秒后自动提交并保存到 SQLite。
- 持久化：剪切板内容保存在 `clipboard.db`，断开后仍可读取。
- 简单易用：单页界面，开箱即用；支持 Docker 运行。

## 快速开始

### 本地运行
1. 安装依赖
   ```bash
   pip install -r requirements.txt
   ```
2. 启动服务
   ```bash
   python clipboard.py
   ```
3. 在浏览器访问 `http://localhost:8000`

说明：停止输入约 3 秒后，页面会自动提交更新；其他已打开页面会即时收到更新并刷新文本。

### Docker 运行
```bash
# 构建镜像（在项目根目录）
docker build -t clipboard .

# 运行容器（映射 8000 端口，并挂载数据文件可选）
docker run --name clipboard -p 8000:8000 clipboard
```
然后访问 `http://localhost:8000`。

## 项目结构
```
.
├─ clipboard.py           # 后端服务入口（Flask + SocketIO + SQLite）
├─ templates/
│  └─ clipboard.html      # 前端页面（Textarea + 自动提交 + Socket.IO 客户端）
├─ requirements.txt       # 依赖
└─ dockerfile             # 容器构建脚本
```

## 关键实现
- 路由与保存：`clipboard.py:34`（`/` GET/POST）读取与更新内容，并在更新后广播 `content_updated` 事件。
- 实时推送：`clipboard.py:59`、`clipboard.py:71` Socket.IO 连接生命周期；首次连接会推送当前内容。
- 前端同步：`templates/clipboard.html:10` 连接 Socket.IO，监听 `content_updated` 并更新文本；`templates/clipboard.html:55` 在停止输入 3 秒后自动提交表单。

## 注意事项
- 默认监听 `0.0.0.0:8000`，可按需在源码中调整端口。
- 数据文件 `clipboard.db` 会在首次运行时自动创建于工作目录。
- 页面引用了 Socket.IO CDN，如需离线运行请自行替换为本地资源。
