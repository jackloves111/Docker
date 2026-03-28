import logging

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

            logger.debug(f"[重建器] 容器配置获取成功")

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

            config = {
                'image': info.get('Config', {}).get('Image', ''),
                'env': self._parse_env(info.get('Config', {}).get('Env', [])),
                'cmd': info.get('Config', {}).get('Cmd', None),
                'entrypoint': info.get('Config', {}).get('Entrypoint', None),
                'working_dir': info.get('Config', {}).get('WorkingDir', None),
                'mounts': info.get('Mounts') or [],
                'exposed_ports': info.get('Config', {}).get('ExposedPorts', {}),
                'host_config': info.get('HostConfig') or {},
                'networking': info.get('NetworkSettings', {}).get('Networks') or {}
            }

            logger.debug(f"[重建器] 成功获取容器配置")
            logger.debug(f"[重建器] 环境变量: {config['env']}")
            logger.debug(f"[重建器] 启动命令: {config['cmd']}")
            logger.debug(f"[重建器] 入口点: {config['entrypoint']}")
            logger.debug(f"[重建器] 工作目录: {config['working_dir']}")
            logger.debug(f"[重建器] 挂载数: {len(config['mounts'])}")
            logger.debug(f"[重建器] 网络数: {len(config['networking'])}")

            return config
        except Exception as e:
            logger.error(f"[重建器] 获取容器配置失败: {e}")
            return None

    def _parse_env(self, env_list):
        if not env_list:
            return []
        result = []
        for env in env_list:
            if env and isinstance(env, str) and '=' in env:
                result.append(env)
            elif env and isinstance(env, str):
                result.append(env)
        return result

    def _create_container(self, config: dict, new_image: str, container_name: str):
        try:
            import docker

            logger.debug(f"[重建器] 构建容器创建参数...")

            host_config = config.get('host_config') or {}
            port_bindings = host_config.get('PortBindings') or {}
            logger.debug(f"[重建器] 端口绑定: {port_bindings}")

            port_map = {}
            for container_port, host_ports in port_bindings.items():
                if host_ports:
                    for hp in host_ports:
                        host_port = hp.get('HostPort', '')
                        if host_port:
                            port_map[container_port] = [{'HostPort': host_port}]

            restart_policy = host_config.get('RestartPolicy') or {}
            restart_policy_name = restart_policy.get('Name', 'no')
            if restart_policy_name == 'no':
                restart_policy_name = 'no'
            logger.debug(f"[重建器] 重启策略: {restart_policy_name}")

            binds = []
            for mount in (config.get('mounts') or []):
                mount_type = mount.get('Type', 'bind')
                source = mount.get('Source', '')
                target = mount.get('Destination', '')
                if not source or not target:
                    continue
                mode = 'ro' if not mount.get('RW', True) else 'rw'
                bind_str = f'{source}:{target}:{mode}'
                binds.append(bind_str)
                logger.debug(f"[重建器] 挂载: {bind_str}")

            networks = list((config.get('networking') or {}).keys())
            logger.debug(f"[重建器] 网络: {networks}")

            memory = host_config.get('Memory')
            cpu_period = host_config.get('CpuPeriod')
            cpu_quota = host_config.get('CpuQuota')

            hc_kwargs = {}
            if binds:
                hc_kwargs['binds'] = binds
            if port_map:
                hc_kwargs['port_bindings'] = port_map
            if restart_policy_name and restart_policy_name != 'no':
                hc_kwargs['restart_policy'] = {'Name': restart_policy_name}
            if memory:
                hc_kwargs['memory'] = memory
            if cpu_period and cpu_quota:
                hc_kwargs['cpu_period'] = cpu_period
                hc_kwargs['cpu_quota'] = cpu_quota

            hc = docker.types.HostConfig(**hc_kwargs) if hc_kwargs else None
            logger.debug(f"[重建器] HostConfig 构建完成")

            create_kwargs = {
                'name': container_name,
                'image': new_image,
            }

            env = config.get('env')
            if env:
                create_kwargs['environment'] = env

            cmd = config.get('cmd')
            if cmd:
                create_kwargs['command'] = cmd

            entrypoint = config.get('entrypoint')
            if entrypoint:
                create_kwargs['entrypoint'] = entrypoint

            working_dir = config.get('working_dir')
            if working_dir:
                create_kwargs['working_dir'] = working_dir

            exposed_ports = config.get('exposed_ports')
            if exposed_ports:
                create_kwargs['ports'] = list(exposed_ports.keys())

            volumes_list = []
            for mount in (config.get('mounts') or []):
                target = mount.get('Destination', '')
                if target:
                    volumes_list.append(target)
            if volumes_list:
                create_kwargs['volumes'] = volumes_list

            if hc:
                create_kwargs['host_config'] = hc

            if networks:
                from docker.types import NetworkingConfig
                endpoints_config = {}
                for net_name in networks:
                    endpoints_config[net_name] = None
                create_kwargs['networking_config'] = NetworkingConfig(endpoints_config)

            logger.info(f"[重建器] 创建容器，参数: name={container_name}, image={new_image}")
            logger.debug(f"[重建器] 完整参数: {create_kwargs}")

            container = self.docker_client.containers.create(**create_kwargs)
            logger.debug(f"[重建器] 容器创建成功: {container.id}")
            return container

        except Exception as e:
            logger.error(f"[重建器] 创建容器失败: {e}")
            import traceback
            logger.error(f"[重建器] 详细错误: {traceback.format_exc()}")
            return None
