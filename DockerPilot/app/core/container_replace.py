"""
Container Replace - Replace containers with new images
Following Portainer's Recreate() implementation:
  1. Get container config (no diff calculation)
  2. Pull latest image with same tag
  3. Stop old container
  4. Rename old container to xxx-old
  5. Disconnect all networks
  6. Create new container with original Config + HostConfig
  7. Connect networks
  8. Start new container
  9. Remove old container
  10. Auto-rollback on failure
"""

import os
import time
import logging
import docker
from docker.errors import NotFound, APIError

logger = logging.getLogger(__name__)


def get_client():
    socket_path = os.environ.get("DOCKER_SOCKET", "/var/run/docker.sock")
    return docker.DockerClient(base_url=f"unix://{socket_path}")


def find_containers_by_image(image_tag: str) -> list:
    """
    Find containers that should be recreated when image_tag is updated.
    Uses Docker CLI (reliable) instead of Docker SDK which may have issues.
    """
    try:
        import subprocess, json

        image_name = image_tag.split(':')[0] if ':' in image_tag else image_tag

        # Get full container list via CLI (we know this works)
        cmd = ["docker", "ps", "-a", "--format",
               '{"id":"{{.ID}}","name":"{{.Names}}","image":"{{.Image}}","state":"{{.State}}"}']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            logger.error(f"[Detect] Docker CLI error: {result.stderr}")
            return []

        containers = []
        for line in result.stdout.strip().split('\n'):
            if line:
                try:
                    c = json.loads(line)
                    containers.append(c)
                except json.JSONDecodeError:
                    continue

        # Get full config for each container to check Image and Config.Image
        matched = []
        for c in containers:
            # Get full container inspect via CLI
            inspect_cmd = ["docker", "inspect", c['id'],
                           "--format", '{"Image":"{{.Image}}","Config":{"Image":"{{.Config.Image}}","Labels":{{json .Config.Labels}}}}']
            inspect_result = subprocess.run(inspect_cmd, capture_output=True, text=True, timeout=10)
            if inspect_result.returncode != 0:
                continue

            try:
                info = json.loads(inspect_result.stdout)
                config_image = info.get('Config', {}).get('Image', '')
                actual_image_id = info.get('Image', '')  # The image ID the container was CREATED with
                labels = info.get('Config', {}).get('Labels') or {}

                match = False
                config_image_name = config_image.split(':')[0] if ':' in config_image else config_image

                # Match 1: Config.Image equals the tag
                if config_image == image_tag:
                    match = True
                # Match 2: same image name
                elif config_image_name == image_name and config_image_name:
                    match = True
                # Match 3: dockerpilot.image_source label
                if not match and labels.get('dockerpilot.image_source') == image_tag:
                    match = True

                if match:
                    matched.append({
                        'id': c['id'][:12],
                        'full_id': c['id'],
                        'name': c['name'],
                        'image': config_image or c['image'],
                        'actual_image_id': actual_image_id,  # Container's actual image ID
                        'state': c['state'],
                    })
            except json.JSONDecodeError:
                continue

        return matched

    except Exception as e:
        logger.error(f"[Detect] Find containers failed: {e}")
        return []


def replace_container(container_id: str, target_image: str = '') -> dict:
    """
    Replace a container following Portainer's Recreate() approach.
    Image resolution priority:
      1. target_image (explicit, caller-provided — always used, e.g. auto-replace
         knows the just-loaded image tag)
      2. dockerpilot.image_source label (containers created via 容器部署)
      3. Config.Image (may be a tag or an image ID — ID resolves to the old image)
    Do NOT pull image (image is expected to be local already).
    Auto-rollback on failure.
    """
    client = get_client()
    ctx_restore = {'restore': False}

    try:
        # 1. Get container full config
        try:
            container = client.containers.get(container_id)
        except NotFound:
            return {'success': False, 'error': f'Container {container_id} not found'}

        attrs = container.attrs
        old_name = container.name
        config = attrs.get('Config', {})
        config_image = config.get('Image', '')

        # Determine which image reference to use
        if target_image:
            final_image = target_image
            logger.info(f"[Replace] Using explicit target image: {final_image!r}")
        else:
            labels = config.get('Labels') or {}
            label_source = labels.get('dockerpilot.image_source', '')
            if label_source:
                final_image = label_source
                logger.info(f"[Replace] Using label source image: {final_image!r}")
            else:
                final_image = config_image
                logger.info(f"[Replace] Using Config.Image: {final_image!r}")

        logger.info(f"[Replace] Container attrs Image field: {attrs.get('Image', '')!r}")

        # Note: Portainer does NOT pull image by default (PullImage=false)
        # The image is expected to be already local (e.g., user pulled/loaded it before)
        # Uncomment to force pull:
        # client.images.pull(final_image)

        # 3. Stop old container
        logger.info(f"[Replace] Stopping container: {old_name}")
        try:
            container.stop(timeout=10)
        except Exception as e:
            logger.warning(f"[Replace] Stop warning: {e}")

        # 4. Arm rollback (Portainer's restore flag)
        ctx_restore['restore'] = True

        def rollback():
            """Restore old container on failure (Portainer's defer)"""
            if not ctx_restore.get('restore'):
                return
            logger.info("[Replace] Rolling back...")
            try:
                old = client.containers.get(container_id)
                # Rename back if needed
                if old.name != old_name:
                    old.rename(old_name)
            except NotFound:
                pass
            try:
                old = client.containers.get(container_id)
                # Reconnect networks
                networks = old.attrs.get('NetworkSettings', {}).get('Networks', {})
                for net_name, net_cfg in networks.items():
                    try:
                        net = client.networks.get(net_name)
                        net.connect(old, aliases=net_cfg.get('Aliases'))
                    except:
                        pass
                # Start container
                old.start()
                logger.info("[Replace] Old container restored")
            except Exception as e:
                logger.error(f"[Replace] Rollback failed: {e}")

        # 5. Rename old container to xxx-old
        old_backup_name = f"{old_name}-old"
        logger.info(f"[Replace] Renaming to: {old_backup_name}")
        try:
            # Remove existing backup if any
            try:
                old_backup = client.containers.get(old_backup_name)
                old_backup.remove(force=True)
            except NotFound:
                pass
            container.rename(old_backup_name)
        except Exception as e:
            rollback()
            return {'success': False, 'error': f'Rename failed: {str(e)}', 'rolled_back': True}

        # 6. Disconnect all networks from old container
        try:
            old = client.containers.get(container_id)  # now renamed
            networks = old.attrs.get('NetworkSettings', {}).get('Networks', {})
            for net_name, net_cfg in networks.items():
                try:
                    client.api.disconnect_container_from_network(
                        container=container_id,
                        network=net_cfg.get('NetworkID', net_name),
                        force=True
                    )
                except Exception as e:
                    logger.warning(f"[Replace] Disconnect network {net_name} warning: {e}")
        except Exception as e:
            logger.warning(f"[Replace] Network disconnect warning: {e}")

        # 7. Create new container using WatchTower's difference calculation
        #    (Container Config - Image Default Config = User Overrides)
        config = attrs.get('Config', {})
        host_config = attrs.get('HostConfig', {})
        network_settings = attrs.get('NetworkSettings', {}).get('Networks', {})

        # Get the NEW image's default config for diff calculation
        try:
            new_image_info = client.api.inspect_image(final_image)
            image_config = new_image_info.get('Config', {})
        except Exception:
            image_config = {}
            logger.warning(f"[Replace] Could not inspect image {final_image}, using empty config for diff")

        # --- WatchTower-style difference calculation ---
        # Only keep user overrides: container_config - image_default_config

        # Env: subtract image defaults (only user-defined env vars remain)
        container_env = config.get('Env') or []
        image_env = image_config.get('Env') or []
        env_diff = [e for e in container_env if e not in image_env]

        # Entrypoint: clear if same as image default
        container_entrypoint = config.get('Entrypoint') or []
        image_entrypoint = image_config.get('Entrypoint') or []
        entrypoint_diff = container_entrypoint if container_entrypoint != image_entrypoint else None

        # Cmd: clear if same as image default
        container_cmd = config.get('Cmd') or []
        image_cmd = image_config.get('Cmd') or []
        cmd_diff = container_cmd if container_cmd != image_cmd else None

        # Labels: subtract image defaults
        container_labels = config.get('Labels') or {}
        image_labels = image_config.get('Labels') or {}
        labels_diff = {k: v for k, v in container_labels.items() if k not in image_labels}

        # Healthcheck: clear if same as image default
        container_hc = config.get('Healthcheck') or {}
        image_hc = image_config.get('Healthcheck') or {}
        hc_diff = None
        if container_hc and image_hc:
            if (container_hc.get('Test') != image_hc.get('Test') or
                container_hc.get('Retries') != image_hc.get('Retries') or
                container_hc.get('Interval') != image_hc.get('Interval') or
                container_hc.get('Timeout') != image_hc.get('Timeout')):
                hc_diff = container_hc
        elif container_hc and not image_hc:
            hc_diff = container_hc

        # Build final config
        config_data = {
            'Image': final_image,
            'Env': env_diff if env_diff else None,
            'Entrypoint': entrypoint_diff,
            'Cmd': cmd_diff,
            'Labels': labels_diff if labels_diff else None,
            'Healthcheck': hc_diff,
            'Hostname': config.get('Hostname'),
            'User': config.get('User'),
            'WorkingDir': config.get('WorkingDir'),
            'Domainname': config.get('Domainname'),
            'AttachStdin': config.get('AttachStdin', False),
            'AttachStdout': config.get('AttachStdout', False),
            'AttachStderr': config.get('AttachStderr', False),
            'Tty': config.get('Tty', False),
            'OpenStdin': config.get('OpenStdin', False),
            'StdinOnce': config.get('StdinOnce', False),
        }

        # Remove None values
        config_data = {k: v for k, v in config_data.items() if v is not None}

        config_data['HostConfig'] = host_config

        # NetworkingConfig: use the first network from old container
        if network_settings:
            first_net_name = list(network_settings.keys())[0]
            config_data['NetworkingConfig'] = {
                'EndpointsConfig': {
                    first_net_name: network_settings[first_net_name]
                }
            }

        logger.info(f"[Replace] Creating new container with WatchTower diff calculation...")
        logger.info(f"[Replace] Image: {final_image}")
        logger.info(f"[Replace] Env diff ({len(env_diff)} items): {env_diff}")
        logger.info(f"[Replace] Entrypoint override: {entrypoint_diff is not None}")
        logger.info(f"[Replace] Cmd override: {cmd_diff is not None}")
        logger.info(f"[Replace] Labels diff ({len(labels_diff)} items): {list(labels_diff.keys())}")

        try:
            create_response = client.api.create_container_from_config(
                config_data,
                name=old_name
            )
            new_container_id = create_response.get('Id', '')
            logger.info(f"[Replace] New container created: {new_container_id[:12]}")
        except Exception as e:
            rollback()
            return {'success': False, 'error': f'Create failed: {str(e)}', 'rolled_back': True}

        # 8. Connect to networks (Portainer connects to all except the first one)
        try:
            old = client.containers.get(container_id)
            networks = old.attrs.get('NetworkSettings', {}).get('Networks', {})
            first_network = None
            for net_name, net_cfg in networks.items():
                if first_network is None:
                    first_network = net_name
                    continue
                try:
                    net = client.networks.get(net_name)
                    net.connect(new_container_id, aliases=net_cfg.get('Aliases'))
                except Exception as e:
                    logger.warning(f"[Replace] Connect network {net_name} warning: {e}")
        except Exception as e:
            logger.warning(f"[Replace] Network connect warning: {e}")

        # 9. Start new container
        try:
            logger.info(f"[Replace] Starting new container...")
            new_container = client.containers.get(new_container_id)
            new_container.start()
        except Exception as e:
            # Stop and remove new container, rollback old
            try:
                client.containers.get(new_container_id).remove(force=True)
            except:
                pass
            rollback()
            return {'success': False, 'error': f'Start failed: {str(e)}', 'rolled_back': True}

        # 10. Remove old container
        try:
            logger.info(f"[Replace] Removing old container...")
            client.containers.get(container_id).remove(force=True, v=False)
        except Exception as e:
            logger.warning(f"[Replace] Remove old container warning: {e}")

        # Disarm rollback
        ctx_restore['restore'] = False

        logger.info(f"[Replace] Container '{old_name}' recreated successfully with {final_image}")
        return {
            'success': True,
            'container_name': old_name,
            'old_image': config_image,
            'new_image': final_image,
            'message': f'Container {old_name} recreated with {final_image}'
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
            'message': f'未找到使用镜像 {old_image_tag} 的容器'
        }

    replaced = 0
    failed = 0
    results = []

    for container in containers:
        # Pass the explicit target image tag so even containers whose
        # Config.Image stored an ID will be recreated with the NEW image
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
        'message': f'已替换 {replaced}/{len(containers)} 个容器'
    }


def detect_and_update_containers(image_tag: str) -> dict:
    """
    After pulling/loading an image, detect containers using that tag
    and update only those with outdated images (WatchTower HasNewImage logic).
    Uses Docker CLI for reliability.
    """
    import subprocess, json

    # Step 1: Get the NEW image's ID via CLI
    try:
        cmd = ["docker", "inspect", "--format", "{{.Id}}", image_tag]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            return {'success': False, 'error': f'Could not inspect image {image_tag}: {result.stderr}',
                    'updated': 0, 'skipped': 0, 'failed': 0}
        new_image_id = result.stdout.strip()
    except Exception as e:
        return {'success': False, 'error': f'Could not inspect image {image_tag}: {str(e)}',
                'updated': 0, 'skipped': 0, 'failed': 0}

    # Step 2: Find all containers using this image tag
    containers = find_containers_by_image(image_tag)

    if not containers:
        return {
            'success': True,
            'updated': 0,
            'skipped': 0,
            'failed': 0,
            'results': [],
            'message': f'未找到使用镜像 {image_tag} 的容器'
        }

    updated = 0
    skipped = 0
    failed = 0
    results = []

    # Step 3: For each container, check if it's using an old version
    for container in containers:
        container_id = container['full_id']
        container_name = container['name']

        try:
            # Use the container's actual image ID (not Config.Image which is a tag)
            container_image_id = container.get('actual_image_id', '')

            # If actual_image_id is empty, fall back to inspecting Config.Image
            if not container_image_id:
                config_image = container['image']
                try:
                    inspect_cmd = ["docker", "inspect", "--format", "{{.Id}}", config_image]
                    inspect_result = subprocess.run(inspect_cmd, capture_output=True, text=True, timeout=10)
                    container_image_id = inspect_result.stdout.strip() if inspect_result.returncode == 0 else config_image
                except:
                    container_image_id = config_image

            # WatchTower's HasNewImage logic: compare IDs
            if container_image_id == new_image_id:
                logger.info(f"[Detect] {container_name}: already using latest image, skipping")
                results.append({
                    'container': container_name,
                    'status': 'skipped',
                    'message': '已是最新镜像'
                })
                skipped += 1
                continue

            # Old version detected - recreate container
            logger.info(f"[Detect] {container_name}: old image detected, recreating...")
            result = replace_container(container_id, image_tag)
            results.append({
                'container': container_name,
                **result
            })

            if result['success']:
                updated += 1
            else:
                failed += 1

        except Exception as e:
            logger.error(f"[Detect] Error processing {container_name}: {e}")
            results.append({
                'container': container_name,
                'status': 'error',
                'error': str(e)
            })
            failed += 1

    return {
        'success': failed == 0,
        'updated': updated,
        'skipped': skipped,
        'failed': failed,
        'total': len(containers),
        'results': results,
        'message': f'已更新 {updated}，跳过 {skipped}，失败 {failed}（共 {len(containers)} 个）'
    }
