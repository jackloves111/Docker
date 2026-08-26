# DockerPilot

Docker 可视化管理平台 - 通过 Web UI 管理 Docker 镜像加载和容器启动。

## 功能特性

- **镜像管理**
  - 从 Docker Hub 或私有仓库 Pull 镜像
  - 从 URL 下载 tar 包并 Load 到 Docker
  - 多镜像源支持（可配置认证信息）

- **项目管理**
  - 保存 `docker run` 命令为项目
  - 保存 `docker compose` 配置为项目
  - 支持路径变量 `${VAR_NAME}`

- **批量组合**
  - 将多个镜像拉取和项目执行组合
  - 一键无人值守执行
  - 可配置失败时是否继续

- **容器管理**
  - 查看运行中的容器
  - 启动/停止/删除容器
  - 查看容器日志

- **路径变量方案**
  - 预设多套路径变量（如本地/NAS/云）
  - 执行前选择方案并确认
  - 支持临时覆盖变量值

## 快速开始

### Docker 运行

```bash
docker run -d \
  --name dockerpilot \
  -p 3000:3000 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v ./data:/config \
  dockerpilot:latest
```

访问 http://localhost:3000

### Docker Compose

```bash
docker compose up -d
```

### 本地开发

```bash
# 后端
pip install -r requirements.txt
python -m app.main

# 前端
cd web
npm install
npm run dev
```

## 技术栈

- **后端**: Python, FastAPI, SQLite, Docker SDK
- **前端**: Vue 3, Ant Design Vue 4, Vite

## 目录结构

```
DockerPilot/
├── app/                # 后端
│   ├── api/           # API 路由
│   ├── core/          # 核心逻辑
│   ├── db/            # 数据库
│   └── models/        # 数据模型
├── web/               # 前端
│   └── src/
│       ├── views/     # 页面组件
│       └── api/       # API 调用
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## License

MIT
