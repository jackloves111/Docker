import docker
import os
import logging

logger = logging.getLogger(__name__)

_client = None

def get_client():
    global _client
    if _client is None:
        socket_path = os.environ.get('DOCKER_SOCKET', '/var/run/docker.sock')
        logger.info(f"[Docker客户端] 初始化 Docker 客户端，Socket: {socket_path}")
        _client = docker.DockerClient(base_url=f'unix://{socket_path}')
    return _client

def get_container_info(container_name):
    logger.debug(f"[Docker客户端] 获取容器信息: {container_name}")
    client = get_client()
    try:
        container = client.containers.get(container_name)
        info = container.attrs
        result = {
            'id': container.id,
            'short_id': container.short_id,
            'name': container.name,
            'image': info['Config']['Image'],
            'image_id': info['Image'],
            'status': container.status,
            'created': info['Created'],
            'env': info['Config']['Env'],
            'cmd': info['Config']['Cmd'],
            'mounts': info['Mounts'],
            'exposed_ports': info['Config'].get('ExposedPorts', {}),
            'host_config': info['HostConfig'],
            'networking': info['NetworkSettings']['Networks']
        }
        logger.debug(f"[Docker客户端] 容器信息获取成功: {container_name}, 状态: {container.status}")
        return result
    except docker.errors.NotFound:
        logger.warning(f"[Docker客户端] 容器未找到: {container_name}")
        return None
    except Exception as e:
        logger.error(f"[Docker客户端] 获取容器信息失败: {container_name}, 错误: {e}")
        raise Exception(f"获取容器信息失败: {e}")

def get_container_config(container_name):
    logger.debug(f"[Docker客户端] 获取容器配置: {container_name}")
    info = get_container_info(container_name)
    if not info:
        logger.warning(f"[Docker客户端] 容器配置获取失败，容器不存在: {container_name}")
        return None

    config = {
        'image': info['image'],
        'env': info['env'] or [],
        'cmd': info['cmd'],
        'mounts': info['mounts'] or [],
        'exposed_ports': info['exposed_ports'],
        'host_config': info['host_config'],
        'networking': info['networking']
    }
    logger.debug(f"[Docker客户端] 容器配置获取成功: {container_name}")
    return config

def list_containers():
    logger.debug("[Docker客户端] 列出所有容器")
    client = get_client()
    containers = []
    for container in client.containers.list(all=True):
        info = container.attrs
        containers.append({
            'id': container.id,
            'short_id': container.short_id,
            'name': container.name,
            'image': info['Config']['Image'],
            'status': container.status,
            'created': info['Created']
        })
    logger.info(f"[Docker客户端] 共找到 {len(containers)} 个容器")
    return containers
