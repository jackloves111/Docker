# DockerTarUpdater

一个 Docker 容器自动升级工具，支持从自定义 URL 下载 tar 镜像并自动升级运行中的容器。

## 功能特性

- 支持从自定义 URL 下载 tar 镜像（不限于 Docker 官方仓库）
- 自动重建容器，保留原有配置（端口、卷、环境变量）
- 支持 Cron 表达式和间隔分钟两种调度方式
- Web UI 管理界面
- Web 实时通知
- 预留通知扩展（钉钉、飞书、邮件等）

## 工作流程

```
[定时/触发] → [下载 tar] → [docker load 新镜像] → [获取目标容器配置] → [停止旧容器] → [用新镜像重建容器] → [清理旧镜像]
```

## 快速开始

### 使用 Docker 运行

```bash
docker run -d \
  --name dockertarupdater \
  -p 5000:5000 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /config:/config \
  nobody114/dockertarupdater:latest
```

访问 Web UI: http://localhost:5000

### 从源码构建

```bash
# 进入项目目录
cd DockerTarUpdater

# 构建镜像
docker build -t dockertarupdater:latest .

# 运行
docker run -d \
  --name dockertarupdater \
  -p 5000:5000 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /config:/config \
  dockertarupdater:latest
```

### 本地开发启动

```bash
# 进入项目目录
cd DockerTarUpdater

# 安装后端依赖
pip install -r requirements.txt

# 修改 config.yaml 中的路径配置（开发环境）
# 将 data_dir、log_file、socket_path 等改为本地路径

# 启动后端（Flask）
python -m app.main

# 新开终端，启动前端
cd web
npm install
npm run dev
```

## 目录结构

```
DockerTarUpdater/
├── app/                    # Flask 后端
│   ├── api/               # API 路由
│   ├── core/              # 核心引擎
│   ├── db/                # 数据库
│   ├── models/            # 数据模型
│   └── utils/             # 工具函数
├── web/                   # Vue.js 前端
│   └── src/
│       ├── views/         # 页面组件
│       ├── api/           # API 调用
│       └── router/         # 路由配置
├── Dockerfile             # 容器构建文件
├── config.yaml            # 配置文件
├── requirements.txt       # Python 依赖
└── README.md
```

## 配置说明

### config.yaml

```yaml
app:
  host: "0.0.0.0"
  port: 5000
  debug: false
  data_dir: "/config"
  log_level: "INFO"
  log_file: "/config/updater.log"

docker:
  socket_path: "/var/run/docker.sock"

scheduler:
  default_interval: 60
  default_enabled: true

download:
  temp_dir: "/tmp/dockertarupdater/downloads"
  timeout: 300
  max_retries: 3

notifications:
  web_enabled: true
```

## 使用方法

### 添加升级目标

1. 打开 Web UI → Targets → Add Target
2. 填写表单：
   - **Container Name**: 要升级的容器名称
   - **Tar URL**: tar 镜像下载地址
   - **Image Tag**: 加载后的镜像标签（如 `myrepo/myapp:latest`）
   - **Schedule Type**: `interval`（间隔分钟）或 `cron`（Cron 表达式）
   - **Schedule Value**: 如 `360`（分钟）或 `0 2 * * *`（每天凌晨2点）

### 手动触发

在目标列表点击 **Trigger** 按钮手动触发升级。

### Web 通知

通过 WebSocket 实时推送通知。可在 Settings 中配置钉钉、飞书、邮件等通知渠道。

## API 接口

### 目标管理

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/targets` | 获取所有目标 |
| GET | `/api/targets/<id>` | 获取单个目标 |
| POST | `/api/targets` | 创建目标 |
| PUT | `/api/targets/<id>` | 更新目标 |
| DELETE | `/api/targets/<id>` | 删除目标 |
| POST | `/api/targets/<id>/trigger` | 手动触发升级 |
| GET | `/api/targets/<id>/info` | 获取容器信息 |

### 任务日志

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/tasks` | 获取任务日志列表 |
| GET | `/api/tasks/latest` | 获取最新任务 |
| GET | `/api/tasks/stats` | 获取统计信息 |

### 调度器

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/scheduler/status` | 获取调度器状态 |
| POST | `/api/scheduler/start` | 启动调度器 |
| POST | `/api/scheduler/stop` | 停止调度器 |
| POST | `/api/scheduler/sync` | 同步任务 |

### 通知配置

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/notifications` | 获取通知配置列表 |
| POST | `/api/notifications` | 创建通知配置 |
| GET | `/api/notifications/web/list` | 获取 Web 通知列表 |
| PUT | `/api/notifications/web/read` | 标记已读 |

## 系统架构

```
┌─────────────────────────────────────────────────┐
│                  Web UI (Vue.js)                │
│   Dashboard │ Targets │ Logs │ Settings         │
└─────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│               Flask API Server                   │
│   Targets API │ Tasks API │ Scheduler API       │
└─────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│                  Core Engine                     │
│  Scheduler │ Downloader │ Loader │ Recreator     │
│  Cleanup │ Notifier                           │
└─────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│              Docker Socket                       │
└─────────────────────────────────────────────────┘
```

## 技术栈

- **后端**: Flask, SQLite, APScheduler, docker-py
- **前端**: Vue.js 3, Element Plus, Axios
- **实时通信**: Flask-SocketIO

## License

MIT
