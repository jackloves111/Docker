import subprocess
import logging
import json
import re

logger = logging.getLogger(__name__)

class Recreater:
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
            stop_result = subprocess.run(['docker', 'stop', container_name], capture_output=True, text=True)
            logger.debug(f"[重建器] stop 返回码: {stop_result.returncode}, stdout: {stop_result.stdout}, stderr: {stop_result.stderr}")

            logger.info(f"[重建器] 删除容器: {container_name}")
            rm_result = subprocess.run(['docker', 'rm', container_name], capture_output=True, text=True)
            logger.debug(f"[重建器] rm 返回码: {rm_result.returncode}, stdout: {rm_result.stdout}, stderr: {rm_result.stderr}")

            cmd = self._build_create_command(config, new_image_tag, container_name)
            logger.info(f"[重建器] 构建创建命令: {' '.join(cmd)}")
            logger.debug(f"[重建器] 完整命令: {cmd}")

            result = subprocess.run(cmd, capture_output=True, text=True)
            logger.debug(f"[重建器] create 返回码: {result.returncode}")
            logger.debug(f"[重建器] create stdout: {result.stdout}")
            logger.debug(f"[重建器] create stderr: {result.stderr}")

            if result.returncode != 0:
                logger.error(f"[重建器] 创建容器失败: {result.stderr}")
                return False, f"创建容器失败: {result.stderr}"

            logger.info(f"[重建器] 启动容器: {container_name}")
            start_result = subprocess.run(['docker', 'start', container_name], capture_output=True, text=True)
            logger.debug(f"[重建器] start 返回码: {start_result.returncode}, stdout: {start_result.stdout}, stderr: {start_result.stderr}")

            logger.info(f"[重建器] 容器升级成功: {container_name} -> {new_image_tag}")
            return True, f"容器已升级到 {new_image_tag}"

        except subprocess.CalledProcessError as e:
            logger.error(f"[重建器] 操作失败: {e}")
            return False, f"操作失败: {e}"
        except Exception as e:
            logger.error(f"[重建器] 重建异常: {e}")
            return False, f"重建异常: {e}"

    def _get_container_config(self, container_name: str) -> dict:
        try:
            logger.debug(f"[重建器] 执行 docker inspect {container_name}")
            result = subprocess.run(
                ['docker', 'inspect', container_name],
                capture_output=True,
                text=True
            )
            logger.debug(f"[重建器] inspect 返回码: {result.returncode}")

            if result.returncode != 0:
                logger.error(f"[重建器] docker inspect 失败: {result.stderr}")
                return None

            info = json.loads(result.stdout)[0]
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

    def _build_create_command(self, config: dict, new_image: str, container_name: str) -> list:
        logger.debug(f"[重建器] 构建 docker create 命令...")
        cmd = ['docker', 'create', '--name', container_name]

        for env in config.get('env', []):
            cmd.extend(['-e', env])
        logger.debug(f"[重建器] 环境变量数量: {len(config.get('env', []))}")

        for mount in config.get('mounts', []):
            mtype = mount.get('Type', 'bind')
            source = mount.get('Source', '')
            target = mount.get('Destination', '')
            mode = 'ro' if not mount.get('RW', True) else 'rw'
            cmd.extend(['--mount', f'type={mtype},source={source},target={target},{mode}'])
        logger.debug(f"[重建器] 挂载点数量: {len(config.get('mounts', []))}")

        host_config = config.get('host_config', {})
        port_bindings = host_config.get('PortBindings', {})
        logger.debug(f"[重建器] 端口绑定: {port_bindings}")

        for container_port, host_ports in port_bindings.items():
            if host_ports:
                for hp in host_ports:
                    host_port = hp.get('HostPort', '')
                    cmd.extend(['-p', f'{host_port}:{container_port}'])

        for net_name in config.get('networking', {}).keys():
            cmd.extend(['--network', net_name])
        logger.debug(f"[重建器] 网络: {list(config.get('networking', {}).keys())}")

        memory = host_config.get('Memory', 0)
        if memory and memory > 0:
            cmd.extend(['-m', str(memory)])
            logger.debug(f"[重建器] 内存限制: {memory}")

        cpu_period = host_config.get('CpuPeriod')
        cpu_quota = host_config.get('CpuQuota')
        if cpu_period and cpu_quota:
            cmd.extend(['--cpu-period', str(cpu_period), '--cpu-quota', str(cpu_quota)])
            logger.debug(f"[重建器] CPU 配置: period={cpu_period}, quota={cpu_quota}")

        restart_policy = host_config.get('RestartPolicy', {})
        if restart_policy.get('Name') and restart_policy['Name'] != 'no':
            cmd.extend(['--restart', restart_policy['Name']])
            logger.debug(f"[重建器] 重启策略: {restart_policy['Name']}")

        if config.get('entrypoint'):
            cmd.extend(['--entrypoint', json.dumps(config['entrypoint'])])
            logger.debug(f"[重建器] 入口点: {config['entrypoint']}")

        if config.get('working_dir'):
            cmd.extend(['-w', config['working_dir']])
            logger.debug(f"[重建器] 工作目录: {config['working_dir']}")

        cmd.append(new_image)
        logger.debug(f"[重建器] 最终镜像: {new_image}")

        if config.get('cmd'):
            if isinstance(config['cmd'], list):
                cmd.extend(config['cmd'])
            else:
                cmd.append(config['cmd'])
            logger.debug(f"[重建器] 启动命令: {config['cmd']}")

        logger.debug(f"[重建器] 最终命令构建完成，共 {len(cmd)} 个参数")
        return cmd
