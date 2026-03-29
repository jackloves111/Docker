import logging

logger = logging.getLogger(__name__)

class Recreater:
    def __init__(self):
        import docker
        import os
        socket_path = os.environ.get('DOCKER_SOCKET', '/var/run/docker.sock')
        self.docker_client = docker.DockerClient(base_url=f'unix://{socket_path}')

    def recreate(self, container_name: str, new_image_tag: str) -> tuple:
        import docker
        logger.info(f"[重建器] 开始重建容器: {container_name} -> {new_image_tag}")
        old_container_name = f"{container_name}_old"

        try:
            logger.debug(f"[重建器] 获取容器配置: {container_name}")
            try:
                container = self.docker_client.containers.get(container_name)
            except docker.errors.NotFound:
                logger.error(f"[重建器] 容器 {container_name} 未找到")
                return False, f"容器 {container_name} 未找到"

            # 提取创建参数
            create_kwargs = self._extract_create_kwargs(container)
            create_kwargs['image'] = new_image_tag
            create_kwargs['name'] = container_name

            logger.info(f"[重建器] 停止容器: {container_name}")
            container.stop()
            logger.debug(f"[重建器] 容器已停止")

            logger.info(f"[重建器] 重命名旧容器: {container_name} -> {old_container_name}")
            # 清理可能存在的遗留同名旧容器
            try:
                old = self.docker_client.containers.get(old_container_name)
                old.remove(force=True)
            except docker.errors.NotFound:
                pass
            container.rename(old_container_name)

            logger.info(f"[重建器] 使用新镜像创建容器: {new_image_tag}")
            try:
                new_container = self.docker_client.containers.create(**create_kwargs)
            except Exception as e:
                logger.error(f"[重建器] 创建容器失败，开始回滚: {e}")
                container.rename(container_name)
                container.start()
                return False, f"创建容器失败，已回滚: {e}"

            logger.info(f"[重建器] 启动容器: {container_name}")
            try:
                new_container.start()
                logger.debug(f"[重建器] 容器已启动")
            except Exception as e:
                logger.error(f"[重建器] 启动容器失败，开始回滚: {e}")
                new_container.remove(force=True)
                container.rename(container_name)
                container.start()
                return False, f"启动容器失败，已回滚: {e}"

            # 重新连接多余的网络
            networks = container.attrs.get('NetworkSettings', {}).get('Networks', {})
            primary_network = create_kwargs.get('network')
            for net_name, net_config in networks.items():
                if net_name != primary_network and primary_network is not None:
                    try:
                        logger.debug(f"[重建器] 连接额外网络: {net_name}")
                        net = self.docker_client.networks.get(net_name)
                        net.connect(
                            new_container,
                            ipv4_address=net_config.get('IPAddress'),
                            ipv6_address=net_config.get('GlobalIPv6Address'),
                            aliases=net_config.get('Aliases'),
                            links=net_config.get('Links')
                        )
                    except Exception as e:
                        logger.warning(f"[重建器] 无法连接网络 {net_name}: {e}")

            logger.info(f"[重建器] 删除旧容器: {old_container_name}")
            container.remove(v=False) # 保留 volume
            logger.debug(f"[重建器] 旧容器已删除")

            logger.info(f"[重建器] 容器升级成功: {container_name} -> {new_image_tag}")
            return True, f"容器已升级到 {new_image_tag}"

        except Exception as e:
            logger.error(f"[重建器] 重建异常: {e}")
            import traceback
            logger.error(f"[重建器] 详细错误: {traceback.format_exc()}")
            return False, f"重建异常: {e}"

    def _extract_create_kwargs(self, container) -> dict:
        """从现有容器提取用于创建新容器的全量配置参数，排除应由新镜像决定的配置项"""
        attrs = container.attrs
        config = attrs.get('Config', {})
        host_config = attrs.get('HostConfig', {})
        network_settings = attrs.get('NetworkSettings', {})

        # 注意：此处不提取 command(Cmd), user(User), working_dir(WorkingDir), labels(Labels)
        # 让这些参数在创建新容器时，自然继承新版镜像的默认值
        kwargs = {
            'environment': config.get('Env'),
            'hostname': config.get('Hostname'),
            'tty': config.get('Tty'),
            'stdin_open': config.get('OpenStdin'),
            'detach': True,
        }

        # 端口映射
        port_bindings = host_config.get('PortBindings') or {}
        ports = {}
        for container_port, bindings in port_bindings.items():
            if bindings:
                bind_list = []
                for b in bindings:
                    host_ip = b.get('HostIp')
                    host_port = b.get('HostPort')
                    if host_ip:
                        bind_list.append((host_ip, host_port))
                    else:
                        bind_list.append(host_port)
                ports[container_port] = bind_list
        if ports:
            kwargs['ports'] = ports

        # 挂载 (Mounts)
        mounts_info = attrs.get('Mounts') or []
        if mounts_info:
            import docker
            mounts = []
            for m in mounts_info:
                m_type = m.get('Type', 'bind')
                source = m.get('Source') or m.get('Name')
                target = m.get('Destination')
                if not source or not target:
                    continue
                read_only = not m.get('RW', True)
                
                mount_kwargs = {
                    'target': target,
                    'source': source,
                    'type': m_type,
                    'read_only': read_only
                }
                
                # tmpfs 的 source 为空
                if m_type == 'tmpfs':
                    mount_kwargs['source'] = ''
                
                mounts.append(docker.types.Mount(**mount_kwargs))
            if mounts:
                kwargs['mounts'] = mounts

        # 提取网络模式
        network_mode = host_config.get('NetworkMode')
        if network_mode and network_mode != 'default':
            kwargs['network_mode'] = network_mode
            if network_mode not in ['bridge', 'host', 'none'] and not network_mode.startswith('container:'):
                kwargs['network'] = network_mode
        else:
            networks = network_settings.get('Networks', {})
            if networks:
                kwargs['network'] = list(networks.keys())[0]

        # 重启策略
        restart_policy = host_config.get('RestartPolicy')
        if restart_policy and restart_policy.get('Name') and restart_policy.get('Name') != 'no':
            kwargs['restart_policy'] = restart_policy

        # 高级权限与设备
        if host_config.get('Privileged'):
            kwargs['privileged'] = True
        if host_config.get('CapAdd'):
            kwargs['cap_add'] = host_config.get('CapAdd')
        if host_config.get('CapDrop'):
            kwargs['cap_drop'] = host_config.get('CapDrop')
        
        # 设备映射
        devices = []
        for dev in host_config.get('Devices') or []:
            host_path = dev.get('PathOnHost', '')
            container_path = dev.get('PathInContainer', '')
            perms = dev.get('CgroupPermissions', '')
            if host_path and container_path:
                devices.append(f"{host_path}:{container_path}:{perms}")
        if devices:
            kwargs['devices'] = devices

        # 资源限制
        if host_config.get('Memory'):
            kwargs['mem_limit'] = host_config.get('Memory')
        if host_config.get('MemorySwap'):
            kwargs['memswap_limit'] = host_config.get('MemorySwap')
        if host_config.get('CpuPeriod'):
            kwargs['cpu_period'] = host_config.get('CpuPeriod')
        if host_config.get('CpuQuota'):
            kwargs['cpu_quota'] = host_config.get('CpuQuota')
        if host_config.get('CpuShares'):
            kwargs['cpu_shares'] = host_config.get('CpuShares')
        if host_config.get('CpusetCpus'):
            kwargs['cpuset_cpus'] = host_config.get('CpusetCpus')

        # 其他
        if host_config.get('IpcMode'):
            kwargs['ipc_mode'] = host_config.get('IpcMode')
        if host_config.get('PidMode'):
            kwargs['pid_mode'] = host_config.get('PidMode')
        if host_config.get('Sysctls'):
            kwargs['sysctls'] = host_config.get('Sysctls')
        if host_config.get('ExtraHosts'):
            kwargs['extra_hosts'] = host_config.get('ExtraHosts')

        # 清理 None 值
        return {k: v for k, v in kwargs.items() if v is not None}
