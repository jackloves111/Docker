"""
Container Replace - Replace containers with new images
Using docker inspect whitelist approach (like WatchTower)
"""

import logging
import docker
from docker.errors import NotFound, APIError

logger = logging.getLogger(__name__)

# Parameters to extract from docker inspect (whitelist)
EXTRACT_CONFIG_KEYS = {
    'Config': ['Env', 'Hostname', 'Tty', 'OpenStdin', 'StdinOnce', 'Cmd', 'Entrypoint'],
    'HostConfig': [
        'PortBindings', 'NetworkMode', 'RestartPolicy',
        'Privileged', 'CapAdd', 'CapDrop', 'Devices',
        'Memory', 'MemorySwap', 'CpuShares', 'CpusetCpus',
        'CpuPeriod', 'CpuQuota', 'IpcMode', 'PidMode',
        'Sysctls', 'ExtraHosts', 'Ulimits', 'SecurityOpt',
        'ReadonlyRootfs', 'ShmSize', 'OomScoreAdj',
    ],
}


def get_client():
    import os
    socket_path = os.environ.get("DOCKER_SOCKET", "/var/run/docker.sock")
    return docker.DockerClient(base_url=f"unix://{socket_path}")


def find_containers_by_image(image_tag: str) -> list:
    """Find all containers using a specific image tag"""
    try:
        client = get_client()
        # Get all containers
        containers = client.containers.list(all=True)
        result = []
        for c in containers:
            # Check if container uses this image
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


def extract_container_config(container) -> dict:
    """Extract container configuration using whitelist approach"""
    try:
        attrs = container.attrs
        config = attrs.get('Config', {})
        host_config = attrs.get('HostConfig', {})

        create_kwargs = {}

        # Extract from Config
        for key in EXTRACT_CONFIG_KEYS.get('Config', []):
            if key in config and config[key] is not None:
                create_kwargs[key] = config[key]

        # Extract from HostConfig
        for key in EXTRACT_CONFIG_KEYS.get('HostConfig', []):
            if key in host_config and host_config[key] is not None:
                create_kwargs[key] = host_config[key]

        # Convert PortBindings to docker format
        if 'PortBindings' in create_kwargs:
            port_bindings = create_kwargs.pop('PortBindings')
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

        # Convert Mounts
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

        # Set detach mode
        create_kwargs['detach'] = True

        return create_kwargs

    except Exception as e:
        logger.error(f"[Replace] Extract config failed: {e}")
        return {}


def replace_container(container_id: str, new_image_tag: str) -> dict:
    """
    Replace a container with a new image
    Returns dict with success status and details
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

        # Extract configuration
        create_kwargs = extract_container_config(old_container)
        create_kwargs['image'] = new_image_tag
        create_kwargs['name'] = old_name

        logger.info(f"[Replace] Extracted config: {list(create_kwargs.keys())}")

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
        old_backup_name = f"{old_name}_backup_{int(datetime.now().timestamp())}"
        logger.info(f"[Replace] Renaming to {old_backup_name}")
        old_container.rename(old_backup_name)

        # Step 4: Create new container
        try:
            logger.info(f"[Replace] Creating new container...")
            new_container = client.containers.create(**create_kwargs)
        except Exception as e:
            # Rollback: restore old container
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
            # Rollback: remove new container, restore old
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
    """
    Auto-replace all containers using the old image tag
    Returns summary of replacements
    """
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
