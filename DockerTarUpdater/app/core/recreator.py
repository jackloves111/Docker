import subprocess
import logging
import json
import re

logger = logging.getLogger(__name__)

class Recreater:
    def recreate(self, container_name: str, new_image_tag: str) -> tuple:
        try:
            config = self._get_container_config(container_name)
            if not config:
                return False, f"Container {container_name} not found"

            logger.info(f"Stopping container {container_name}")
            subprocess.run(['docker', 'stop', container_name], check=True, capture_output=True)

            logger.info(f"Removing container {container_name}")
            subprocess.run(['docker', 'rm', container_name], check=True, capture_output=True)

            cmd = self._build_create_command(config, new_image_tag, container_name)
            logger.info(f"Creating container: {' '.join(cmd)}")

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"Create failed: {result.stderr}")
                return False, f"Create container failed: {result.stderr}"

            logger.info(f"Starting container {container_name}")
            subprocess.run(['docker', 'start', container_name], check=True, capture_output=True)

            return True, f"Container upgraded to {new_image_tag}"

        except subprocess.CalledProcessError as e:
            return False, f"Operation failed: {e}"
        except Exception as e:
            return False, f"Recreate error: {e}"

    def _get_container_config(self, container_name: str) -> dict:
        try:
            result = subprocess.run(
                ['docker', 'inspect', container_name],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                return None

            info = json.loads(result.stdout)[0]
            return {
                'image': info['Config']['Image'],
                'env': info['Config']['Env'] or [],
                'cmd': info['Config']['Cmd'],
                'entrypoint': info['Config']['Entrypoint'],
                'working_dir': info['Config']['WorkingDir'],
                ' mounts': info['Mounts'] or [],
                'exposed_ports': info['Config'].get('ExposedPorts', {}),
                'host_config': info['HostConfig'],
                'networking': info['NetworkSettings']['Networks']
            }
        except Exception as e:
            logger.error(f"Failed to get container config: {e}")
            return None

    def _build_create_command(self, config: dict, new_image: str, container_name: str) -> list:
        cmd = ['docker', 'create', '--name', container_name]

        for env in config.get('env', []):
            cmd.extend(['-e', env])

        for mount in config.get('mounts', []):
            mtype = mount.get('Type', 'bind')
            source = mount.get('Source', '')
            target = mount.get('Destination', '')
            mode = 'ro' if not mount.get('RW', True) else 'rw'
            cmd.extend(['--mount', f'type={mtype},source={source},target={target},{mode}'])

        host_config = config.get('host_config', {})
        port_bindings = host_config.get('PortBindings', {})

        for container_port, host_ports in port_bindings.items():
            if host_ports:
                for hp in host_ports:
                    host_port = hp.get('HostPort', '')
                    cmd.extend(['-p', f'{host_port}:{container_port}'])

        for net_name in config.get('networking', {}).keys():
            cmd.extend(['--network', net_name])

        memory = host_config.get('Memory', 0)
        if memory and memory > 0:
            cmd.extend(['-m', str(memory)])

        cpu_period = host_config.get('CpuPeriod')
        cpu_quota = host_config.get('CpuQuota')
        if cpu_period and cpu_quota:
            cmd.extend(['--cpu-period', str(cpu_period), '--cpu-quota', str(cpu_quota)])

        restart_policy = host_config.get('RestartPolicy', {})
        if restart_policy.get('Name') and restart_policy['Name'] != 'no':
            cmd.extend(['--restart', restart_policy['Name']])

        if config.get('entrypoint'):
            cmd.extend(['--entrypoint', json.dumps(config['entrypoint'])])

        if config.get('working_dir'):
            cmd.extend(['-w', config['working_dir']])

        cmd.append(new_image)

        if config.get('cmd'):
            if isinstance(config['cmd'], list):
                cmd.extend(config['cmd'])
            else:
                cmd.append(config['cmd'])

        return cmd
