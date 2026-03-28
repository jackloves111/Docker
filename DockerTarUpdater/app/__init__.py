from flask import Flask, send_from_directory
from flask_socketio import SocketIO
from flask_cors import CORS
import yaml
import os

socketio = SocketIO()

def create_app():
    app = Flask(__name__)

    config_path = os.environ.get('CONFIG_PATH', '/app/config.yaml')
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    else:
        config = {
            'app': {
                'host': '0.0.0.0',
                'port': 5000,
                'debug': False,
                'data_dir': '/data/dockertarupdater',
                'log_level': 'INFO',
                'log_file': '/data/dockertarupdater/updater.log'
            },
            'docker': {
                'socket_path': '/var/run/docker.sock'
            },
            'scheduler': {
                'default_interval': 60,
                'default_enabled': True
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

    os.makedirs(config['app']['data_dir'], exist_ok=True)
    os.makedirs(config['download']['temp_dir'], exist_ok=True)

    app.config['APP_CONFIG'] = config

    frontend_dist = os.environ.get('FRONTEND_DIST', '/app/web/dist')
    if os.path.exists(frontend_dist):
        @app.route('/')
        def serve_index():
            return send_from_directory(frontend_dist, 'index.html')

        @app.route('/<path:path>')
        def serve_static(path):
            file_path = os.path.join(frontend_dist, path)
            if os.path.exists(file_path):
                return send_from_directory(frontend_dist, path)
            return send_from_directory(frontend_dist, 'index.html')

    from app.db.database import db
    db.init(config['app']['data_dir'])

    CORS(app)
    socketio.init_app(app, cors_allowed_origins="*", async_mode='eventlet')

    from app.api import targets, tasks, scheduler as scheduler_api, notifications
    app.register_blueprint(targets.bp)
    app.register_blueprint(tasks.bp)
    app.register_blueprint(scheduler_api.bp)
    app.register_blueprint(notifications.bp)

    from app.core.scheduler import init_scheduler
    init_scheduler(app)

    return app
