import docker
import os

_client = None

def get_client():
    global _client
    if _client is None:
        socket_path = os.environ.get('DOCKER_SOCKET', '/var/run/docker.sock')
        _client = docker.DockerClient(base_url=f'unix://{socket_path}')
    return _client

def get_container_info(container_name):
    client = get_client()
    try:
        container = client.containers.get(container_name)
        info = container.attrs
        return {
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
    except docker.errors.NotFound:
        return None
    except Exception as e:
        raise Exception(f"Failed to get container info: {e}")

def get_container_config(container_name):
    info = get_container_info(container_name)
    if not info:
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
    return config

def list_containers():
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
    return containers
