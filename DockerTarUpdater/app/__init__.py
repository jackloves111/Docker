from flask import Flask, send_from_directory
from flask_socketio import SocketIO
from flask_cors import CORS
import yaml
import os
import logging

socketio = SocketIO()
_app = None

def get_app():
    return _app

def setup_logging(config):
    log_level = config.get('app', {}).get('log_level', 'INFO')
    log_file = config.get('app', {}).get('log_file', '/config/updater.log')
    log_dir = os.path.dirname(log_file)
    os.makedirs(log_dir, exist_ok=True)

    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def create_app():
    global _app

    os.environ.setdefault('TZ', 'Asia/Shanghai')

    import time
    try:
        import zoneinfo
        tz = zoneinfo.ZoneInfo('Asia/Shanghai')
    except ImportError:
        import pytz
        tz = pytz.timezone('Asia/Shanghai')
    time.tzset()

    app = Flask(__name__)
    _app = app

    config_path = os.environ.get('CONFIG_PATH', '/app/config.yaml')
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        print(f"[启动] 配置文件加载成功: {config_path}")
    else:
        config = {
            'app': {
                'host': '0.0.0.0',
                'port': 3006,
                'debug': False,
                'data_dir': '/config',
                'log_level': 'INFO',
                'log_file': '/config/updater.log'
            },
            'docker': {
                'socket_path': '/var/run/docker.sock'
            },
            'download': {
                'temp_dir': '/tmp/dockertarupdater/downloads',
                'timeout': 300,
                'max_retries': 3
            },
            'notifications': {
                'web_enabled': True
            }
        }
        print(f"[启动] 使用默认配置")

    logger = setup_logging(config)
    logger.info("="*50)
    logger.info("[启动] Docker镜像更新器开始启动...")
    logger.info(f"[启动] 日志级别: {config.get('app', {}).get('log_level', 'INFO')}")
    logger.info(f"[启动] Docker Socket: {config.get('docker', {}).get('socket_path', '/var/run/docker.sock')}")
    logger.info(f"[启动] 临时目录: {config.get('download', {}).get('temp_dir', '/tmp/dockertarupdater/downloads')}")
    logger.info("="*50)

    os.makedirs(config['app']['data_dir'], exist_ok=True)
    os.makedirs(config['download']['temp_dir'], exist_ok=True)

    app.config['APP_CONFIG'] = config

    frontend_dist = os.environ.get('FRONTEND_DIST', '/app/web/dist')
    if os.path.exists(frontend_dist):
        logger.info(f"[启动] 前端静态文件目录: {frontend_dist}")
        @app.route('/')
        def serve_index():
            return send_from_directory(frontend_dist, 'index.html')

        @app.route('/<path:path>')
        def serve_static(path):
            file_path = os.path.join(frontend_dist, path)
            if os.path.exists(file_path):
                return send_from_directory(frontend_dist, path)
            return send_from_directory(frontend_dist, 'index.html')
    else:
        logger.warning(f"[启动] 前端静态文件目录不存在: {frontend_dist}，跳过前端服务配置")

    from app.db.database import db
    db.init(config['app']['data_dir'])
    logger.info("[启动] 数据库初始化完成")

    CORS(app)
    socketio.init_app(app, cors_allowed_origins="*", async_mode='eventlet')
    logger.info("[启动] SocketIO 初始化完成")

    from app.api import targets, tasks, scheduler as scheduler_api, notifications, env_editor, docker
    app.register_blueprint(targets.bp)
    app.register_blueprint(tasks.bp)
    app.register_blueprint(scheduler_api.bp)
    app.register_blueprint(notifications.bp)
    app.register_blueprint(env_editor.bp)
    app.register_blueprint(docker.bp)
    logger.info("[启动] API 路由注册完成")

    from app.core.scheduler import init_scheduler
    init_scheduler(app)
    logger.info("[启动] 调度器初始化完成")

    logger.info("[启动] Docker镜像更新器启动成功！")
    return app
