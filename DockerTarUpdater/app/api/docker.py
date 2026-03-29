from flask import Blueprint
from app.utils.response import success, error
import docker
import os
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('docker', __name__, url_prefix='/api/docker')

def get_docker_socket():
    return os.environ.get('DOCKER_SOCKET', '/var/run/docker.sock')

@bp.route('/health', methods=['GET'])
def health_check():
    socket_path = get_docker_socket()
    logger.info(f"[Docker健康检查] 检查 Docker 连接，Socket: {socket_path}")
    try:
        client = docker.DockerClient(base_url=f'unix://{socket_path}')
        client.ping()
        logger.info("[Docker健康检查] Docker 连接正常")
        return success({
            'connected': True,
            'socket': socket_path
        })
    except docker.errors.DockerException as e:
        logger.warning(f"[Docker健康检查] Docker 连接失败: {e}")
        return success({
            'connected': False,
            'socket': socket_path,
            'error': '无法连接到 Docker daemon，请检查是否正确映射了 /var/run/docker.sock'
        })
    except Exception as e:
        logger.error(f"[Docker健康检查] Docker 连接异常: {e}")
        return success({
            'connected': False,
            'socket': socket_path,
            'error': str(e)
        })