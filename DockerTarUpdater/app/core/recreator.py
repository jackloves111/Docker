import logging
import json

logger = logging.getLogger(__name__)

class Recreater:
    def __init__(self):
        import docker
        import os
        socket_path = os.environ.get('DOCKER_SOCKET', '/var/run/docker.sock')
        self.docker_client = docker.DockerClient(base_url=f'unix://{socket_path}')

    def recreate(self, container_name: str, new_image_tag: str) -> tuple:
        logger.info(f"[重建器] 开始重建容器: {container_name} -> {new_image_tag}")

        try:
            logger.debug(f"[重建器] 获取容器配置: {container_name}")
            config = self._get_container_config(container_name)
            if not config:
                logger.error(f"[重建器] 容器 {container_name} 未找到")
                return False, f"容器 {container_name} 未找到"

            logger.debug(f"[重建器] 容器配置: {json.dumps(config, indent=2)}")

            logger.info(f"[重建器] 停止容器: {container_name}")
            container = self.docker_client.containers.get(container_name)
            container.stop()
            logger.debug(f"[重建器] 容器已停止")

            logger.info(f"[重建器] 删除容器: {container_name}")
            container.remove()
            logger.debug(f"[重建器] 容器已删除")

            logger.info(f"[重建器] 使用新镜像创建容器: {new_image_tag}")
            new_container = self._create_container(config, new_image_tag, container_name)
            if not new_container:
                return False, "创建容器失败"

            logger.info(f"[重建器] 启动容器: {container_name}")
            new_container.start()
            logger.debug(f"[重建器] 容器已启动")

            logger.info(f"[重建器] 容器升级成功: {container_name} -> {new_image_tag}")
            return True, f"容器已升级到 {new_image_tag}"

        except Exception as e:
            logger.error(f"[重建器] 重建异常: {e}")
            return False, f"重建异常: {e}"

    def _get_container_config(self, container_name: str) -> dict:
        try:
            logger.debug(f"[重建器] 获取容器: {container_name}")
            container = self.docker_client.containers.get(container_name)
            info = container.attrs
            logger.debug(f"[重建器] 成功获取容器配置")

            return {
                'image': info['Config']['Image'],
                'env': info['Config']['Env'] or [],
                'cmd': info['Config']['Cmd'],
                'entrypoint': info['Config']['Entrypoint'],
                'working_dir': info['Config']['WorkingDir'],
                'mounts': info['Mounts'] or [],
                'exposed_ports': info['Config'].get('ExposedPorts', {}),
                'host_config': info['HostConfig'],
                'networking': info['NetworkSettings']['Networks']
            }
        except Exception as e:
            logger.error(f"[重建器] 获取容器配置失败: {e}")
            return None

    def _create_container(self, config: dict, new_image: str, container_name: str):
        try:
            logger.debug(f"[重建器] 构建容器创建参数...")

            host_config = config.get('host_config', {})
            port_bindings = host_config.get('PortBindings', {})
            logger.debug(f"[重建器] 端口绑定: {port_bindings}")

            port_map = {}
            for container_port, host_ports in port_bindings.items():
                if host_ports:
                    port_map[container_port] = [{'HostPort': hp.get('HostPort', '')} for hp in host_ports]

            restart_policy = host_config.get('RestartPolicy', {})
            restart_policy_name = restart_policy.get('Name', 'no')
            logger.debug(f"[重建器] 重启策略: {restart_policy_name}")

            binds = []
            for mount in config.get('mounts', []):
                mtype = mount.get('Type', 'bind')
                source = mount.get('Source', '')
                target = mount.get('Destination', '')
                mode = 'ro' if not mount.get('RW', True) else 'rw'
                binds.append(f'{source}:{target}:{mode}')
                logger.debug(f"[重建器] 挂载: {source} -> {target} ({mode})")

            networking_config = {}
            for net_name, net_info in config.get('networking', {}).items():
                networking_config[net_name] = None
            logger.debug(f"[重建器] 网络: {list(networking_config.keys())}")

            memory = host_config.get('Memory', 0)
            cpu_period = host_config.get('CpuPeriod')
            cpu_quota = host_config.get('CpuQuota')

            create_params = {
                'name': container_name,
                'image': new_image,
                'environment': config.get('env', []),
                'command': config.get('cmd'),
                'entrypoint': config.get('entrypoint'),
                'working_dir': config.get('working_dir'),
                'ports': list(port_map.keys()) if port_map else None,
                'volumes': [m['Destination'] for m in config.get('mounts', [])],
                'host_config': {
                    'PortBindings': port_map,
                    'Binds': binds,
                    'RestartPolicy': {'Name': restart_policy_name},
                    'Memory': memory if memory else None,
                    'CpuPeriod': cpu_period,
                    'CpuQuota': cpu_quota,
                },
                'networking_config': networking_config if networking_config else None,
            }

            logger.info(f"[重建器] 创建容器...")
            container = self.docker_client.containers.create(**create_params)
            logger.debug(f"[重建器] 容器创建成功: {container.id}")
            return container

        except Exception as e:
            logger.error(f"[重建器] 创建容器失败: {e}")
            return None
