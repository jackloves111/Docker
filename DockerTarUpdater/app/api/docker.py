from flask import Blueprint
from app.utils.response import success
import docker
import os
import logging
import time

logger = logging.getLogger(__name__)

bp = Blueprint('docker', __name__, url_prefix='/api/docker')

_docker_status = {
    'connected': None,
    'socket': None,
    'error': None,
    'last_check': None
}

def get_docker_socket():
    return os.environ.get('DOCKER_SOCKET', '/var/run/docker.sock')

def _update_docker_status():
    global _docker_status
    socket_path = get_docker_socket()
    try:
        client = docker.DockerClient(base_url=f'unix://{socket_path}')
        client.ping()
        _docker_status = {
            'connected': True,
            'socket': socket_path,
            'error': None,
            'last_check': time.time()
        }
        logger.info("[Docker健康检查] Docker 连接正常")
    except docker.errors.DockerException as e:
        _docker_status = {
            'connected': False,
            'socket': socket_path,
            'error': '无法连接到 Docker daemon，请检查是否正确映射了 /var/run/docker.sock',
            'last_check': time.time()
        }
        logger.warning(f"[Docker健康检查] Docker 连接失败: {e}")
    except Exception as e:
        _docker_status = {
            'connected': False,
            'socket': socket_path,
            'error': str(e),
            'last_check': time.time()
        }
        logger.error(f"[Docker健康检查] Docker 连接异常: {e}")

def init_health_checker(app):
    _update_docker_status()

@bp.route('/health', methods=['GET'])
def health_check():
    return success(_docker_status)