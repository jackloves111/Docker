"""
Container Replace - Replace containers with new images
Using WatchTower's difference calculation approach:
  Container Config - Image Default Config = User Overrides
"""

import os
import logging
import docker
from docker.errors import NotFound, APIError

logger = logging.getLogger(__name__)


def get_client():
    socket_path = os.environ.get("DOCKER_SOCKET", "/var/run/docker.sock")
    return docker.DockerClient(base_url=f"unix://{socket_path}")


def find_containers_by_image(image_tag: str) -> list:
    """Find all containers using a specific image tag"""
    try:
        client = get_client()
        containers = client.containers.list(all=True)
        result = []
        for c in containers:
            container_image = c.image.tags[0] if c.image.tags else str(c.image.short_id)
            if container_image == image_tag:
                result.append({
                    'id': c.short_id,
                    'full_id': c.id,
                    'name': c.name,
                    'image': container_image,
                    'state': c.state,
                })
        return result
    except Exception as e:
        logger.error(f"[Replace] Find containers failed: {e}")
        return []


def slice_subtract(container_list, image_list):
    """Remove image defaults from container values (WatchTower approach)"""
    if not container_list or not image_list:
        return container_list or []
    return [x for x in container_list if x not in image_list]


def map_subtract(container_map, image_map):
    """Remove image defaults from container values"""
    if not container_map or not image_map:
        return container_map or {}
    return {k: v for k, v in container_map.items() if k not in image_map}


def extract_container_config(container) -> dict:
    """
    Extract container configuration using WatchTower's difference approach:
    Container Config - Image Default Config = User Overrides
    """
    try:
        attrs = container.attrs
        config = attrs.get('Config', {})
        host_config = attrs.get('HostConfig', {})

        # Get image config for comparison
        try:
            image_inspect = client.api.inspect_image(config.get('Image', ''))
            image_config = image_inspect.get('Config', {})
        except:
            image_config = {}

        create_kwargs = {}

        # --- Config section (WatchTower logic) ---

        # WorkingDir: clear if same as image default
        if config.get('WorkingDir') == image_config.get('WorkingDir'):
            create_kwargs['working_dir'] = ''
        elif config.get('WorkingDir'):
            create_kwargs['working_dir'] = config['WorkingDir']

        # User: clear if same as image default
        if config.get('User') == image_config.get('User'):
            create_kwargs['user'] = ''
        elif config.get('User'):
            create_kwargs['user'] = config['User']

        # Entrypoint: clear if same as image default
        container_entrypoint = config.get('Entrypoint') or []
        image_entrypoint = image_config.get('Entrypoint') or []
        if container_entrypoint == image_entrypoint:
            create_kwargs['entrypoint'] = None
        elif container_entrypoint:
            create_kwargs['entrypoint'] = container_entrypoint

        # Cmd: clear if same as image default (and Entrypoint is also same)
        container_cmd = config.get('Cmd') or []
        image_cmd = image_config.get('Cmd') or []
        if container_entrypoint == image_entrypoint and container_cmd == image_cmd:
            create_kwargs['command'] = None
        elif container_cmd:
            create_kwargs['command'] = container_cmd

        # Env: subtract image env vars (only keep user overrides)
        container_env = config.get('Env') or []
        image_env = image_config.get('Env') or []
        env_overrides = slice_subtract(container_env, image_env)
        if env_overrides:
            create_kwargs['environment'] = env_overrides

        # Labels: subtract image labels (only keep user overrides)
        container_labels = config.get('Labels') or {}
        image_labels = image_config.get('Labels') or {}
        labels_overrides = map_subtract(container_labels, image_labels)
        if labels_overrides:
            create_kwargs['labels'] = labels_overrides

        # --- HostConfig section ---

        # PortBindings
        port_bindings = host_config.get('PortBindings') or {}
        if port_bindings:
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
                create_kwargs['ports'] = ports

        # Mounts
        mounts_info = attrs.get('Mounts') or []
        if mounts_info:
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
                if m_type == 'tmpfs':
                    mount_kwargs['source'] = ''

                mounts.append(docker.types.Mount(**mount_kwargs))
            if mounts:
                create_kwargs['mounts'] = mounts

        # NetworkMode
        network_mode = host_config.get('NetworkMode')
        if network_mode and network_mode != 'default':
            create_kwargs['network_mode'] = network_mode
            if network_mode not in ['bridge', 'host', 'none'] and not network_mode.startswith('container:'):
                create_kwargs['network'] = network_mode
        else:
            networks = attrs.get('NetworkSettings', {}).get('Networks', {})
            if networks:
                create_kwargs['network'] = list(networks.keys())[0]

        # RestartPolicy
        restart_policy = host_config.get('RestartPolicy')
        if restart_policy and restart_policy.get('Name') and restart_policy.get('Name') != 'no':
            create_kwargs['restart_policy'] = restart_policy

        # Privileged
        if host_config.get('Privileged'):
            create_kwargs['privileged'] = True

        # CapAdd / CapDrop
        if host_config.get('CapAdd'):
            create_kwargs['cap_add'] = host_config['CapAdd']
        if host_config.get('CapDrop'):
            create_kwargs['cap_drop'] = host_config['CapDrop']

        # Devices
        devices = []
        for dev in host_config.get('Devices') or []:
            host_path = dev.get('PathOnHost', '')
            container_path = dev.get('PathInContainer', '')
            perms = dev.get('CgroupPermissions', '')
            if host_path and container_path:
                devices.append(f"{host_path}:{container_path}:{perms}")
        if devices:
            create_kwargs['devices'] = devices

        # Resource limits
        if host_config.get('Memory'):
            create_kwargs['mem_limit'] = host_config['Memory']
        if host_config.get('MemorySwap'):
            create_kwargs['memswap_limit'] = host_config['MemorySwap']
        if host_config.get('CpuShares'):
            create_kwargs['cpu_shares'] = host_config['CpuShares']
        if host_config.get('CpusetCpus'):
            create_kwargs['cpuset_cpus'] = host_config['CpusetCpus']
        if host_config.get('CpuPeriod'):
            create_kwargs['cpu_period'] = host_config['CpuPeriod']
        if host_config.get('CpuQuota'):
            create_kwargs['cpu_quota'] = host_config['CpuQuota']

        # Other settings
        if host_config.get('IpcMode'):
            create_kwargs['ipc_mode'] = host_config['IpcMode']
        if host_config.get('PidMode'):
            create_kwargs['pid_mode'] = host_config['PidMode']
        if host_config.get('Sysctls'):
            create_kwargs['sysctls'] = host_config['Sysctls']
        if host_config.get('ExtraHosts'):
            create_kwargs['extra_hosts'] = host_config['ExtraHosts']

        # Set detach mode
        create_kwargs['detach'] = True

        # Remove None values
        create_kwargs = {k: v for k, v in create_kwargs.items() if v is not None}

        return create_kwargs

    except Exception as e:
        logger.error(f"[Replace] Extract config failed: {e}")
        return {}


def replace_container(container_id: str, new_image_tag: str) -> dict:
    """
    Replace a container with a new image
    Uses WatchTower's difference calculation approach
    """
    try:
        client = get_client()

        # Get old container
        try:
            old_container = client.containers.get(container_id)
        except NotFound:
            return {'success': False, 'error': f'Container {container_id} not found'}

        old_name = old_container.name
        old_image = old_container.image.tags[0] if old_container.image.tags else str(old_container.image.short_id)

        logger.info(f"[Replace] Replacing container '{old_name}' ({old_image}) with {new_image_tag}")

        # Extract configuration using difference approach
        create_kwargs = extract_container_config(old_container)
        create_kwargs['image'] = new_image_tag
        create_kwargs['name'] = old_name

        logger.info(f"[Replace] Extracted config keys: {list(create_kwargs.keys())}")

        # Step 1: Pull new image (if not already present)
        try:
            client.images.get(new_image_tag)
            logger.info(f"[Replace] Image {new_image_tag} already exists locally")
        except NotFound:
            logger.info(f"[Replace] Pulling image {new_image_tag}...")
            client.images.pull(new_image_tag)

        # Step 2: Stop old container
        logger.info(f"[Replace] Stopping old container...")
        old_container.stop(timeout=10)

        # Step 3: Rename old container
        import time
        old_backup_name = f"{old_name}_backup_{int(time.time())}"
        logger.info(f"[Replace] Renaming to {old_backup_name}")
        old_container.rename(old_backup_name)

        # Step 4: Create new container
        try:
            logger.info(f"[Replace] Creating new container...")
            new_container = client.containers.create(**create_kwargs)
        except Exception as e:
            # Rollback
            logger.error(f"[Replace] Create failed, rolling back: {e}")
            try:
                old_container.rename(old_name)
                old_container.start()
            except:
                pass
            return {'success': False, 'error': f'Create failed: {str(e)}', 'rolled_back': True}

        # Step 5: Start new container
        try:
            logger.info(f"[Replace] Starting new container...")
            new_container.start()
        except Exception as e:
            # Rollback
            logger.error(f"[Replace] Start failed, rolling back: {e}")
            try:
                new_container.remove(force=True)
                old_container.rename(old_name)
                old_container.start()
            except:
                pass
            return {'success': False, 'error': f'Start failed: {str(e)}', 'rolled_back': True}

        # Step 6: Remove old container
        try:
            logger.info(f"[Replace] Removing old container...")
            old_container.remove(v=False)
        except Exception as e:
            logger.warning(f"[Replace] Failed to remove old container: {e}")

        logger.info(f"[Replace] Container replaced successfully: {old_name}")
        return {
            'success': True,
            'container_name': old_name,
            'old_image': old_image,
            'new_image': new_image_tag,
            'message': f'Container {old_name} replaced successfully'
        }

    except Exception as e:
        logger.error(f"[Replace] Replace failed: {e}")
        return {'success': False, 'error': str(e)}


def auto_replace_containers(old_image_tag: str, new_image_tag: str) -> dict:
    """Auto-replace all containers using the old image tag"""
    containers = find_containers_by_image(old_image_tag)

    if not containers:
        return {
            'success': True,
            'replaced': 0,
            'failed': 0,
            'message': f'No containers found using image {old_image_tag}'
        }

    replaced = 0
    failed = 0
    results = []

    for container in containers:
        result = replace_container(container['full_id'], new_image_tag)
        results.append({
            'container': container['name'],
            **result
        })
        if result['success']:
            replaced += 1
        else:
            failed += 1

    return {
        'success': failed == 0,
        'replaced': replaced,
        'failed': failed,
        'total': len(containers),
        'results': results,
        'message': f'Replaced {replaced}/{len(containers)} containers'
    }
