"""
Project Runner - Execute docker run or docker compose
"""

import re
import os
import json
import logging
import tempfile
import subprocess
from app.core.docker_client import get_client

logger = logging.getLogger(__name__)


def resolve_variables(content: str, variables: dict) -> str:
    """Replace ${VAR_NAME} or $VAR_NAME placeholders with actual values"""
    def replacer(match):
        var_name = match.group(1)
        return variables.get(var_name, match.group(0))
    # Match both ${VAR} and $VAR formats
    return re.sub(r'\$\{(\w+)\}|\$(\w+)', lambda m: variables.get(m.group(1) or m.group(2), m.group(0)), content)


def run_project(project: dict, variables: dict, callback=None) -> dict:
    """
    Execute a project - either docker run command or compose
    """
    project_type = project.get('type', 'run')

    if project_type == 'run':
        return run_docker_command(project, variables, callback)
    elif project_type == 'compose':
        return run_compose(project, variables, callback)
    else:
        return {"success": False, "error": f"Unknown project type: {project_type}"}


def run_docker_command(project: dict, variables: dict, callback=None) -> dict:
    """
    Execute a docker run command
    """
    try:
        command = project.get('command', '')
        if not command:
            return {"success": False, "error": "Empty command"}

        # Resolve variables
        resolved_cmd = resolve_variables(command, variables)
        logger.info(f"[Runner] Executing: {resolved_cmd}")

        if callback:
            callback(f"Executing: {resolved_cmd}")

        # Parse and execute
        # We use docker SDK for better control
        client = get_client()
        output_lines = []

        # Split command into parts (simple shell-like parsing)
        parts = resolved_cmd.strip().split()
        if parts[0] != 'docker':
            parts = ['docker'] + parts

        # Get the subcommand
        if len(parts) < 2:
            return {"success": False, "error": "Invalid docker command"}

        subcommand = parts[1]

        if subcommand == 'run':
            return _execute_docker_run(client, parts[2:], callback)
        elif subcommand == 'compose':
            # Delegate to compose runner
            from app.core.compose_runner import run_compose_command
            return run_compose_command(parts[2:], callback)
        else:
            # Generic execution via subprocess
            result = subprocess.run(
                parts,
                capture_output=True,
                text=True,
                timeout=300
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout + result.stderr,
                "container_id": ""
            }

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Command timed out after 300 seconds"}
    except Exception as e:
        logger.error(f"[Runner] Execution failed: {e}")
        return {"success": False, "error": str(e)}


def _execute_docker_run(client, args: list, callback=None) -> dict:
    """Parse docker run arguments and execute via SDK"""
    try:
        # Simple argument parsing
        name = None
        image = None
        ports = {}
        volumes = []
        env = []
        detach = True
        network = None
        restart_policy = None
        i = 0

        while i < len(args):
            arg = args[i]
            if arg == '-d' or arg == '--detach':
                detach = True
            elif arg == '--name' and i + 1 < len(args):
                name = args[i + 1]
                i += 1
            elif arg == '-p' and i + 1 < len(args):
                # Parse port mapping
                port_spec = args[i + 1]
                parts = port_spec.split(':')
                if len(parts) == 2:
                    host_port, container_port = parts
                    ports[f"{container_port}/tcp"] = int(host_port)
                i += 1
            elif arg == '-v' and i + 1 < len(args):
                volumes.append(args[i + 1])
                i += 1
            elif arg == '-e' and i + 1 < len(args):
                env.append(args[i + 1])
                i += 1
            elif arg == '--network' and i + 1 < len(args):
                network = args[i + 1]
                i += 1
            elif arg == '--restart' and i + 1 < len(args):
                restart_policy = {"Name": args[i + 1]}
                i += 1
            elif not arg.startswith('-'):
                # This should be the image
                image = arg
            i += 1

        if not image:
            return {"success": False, "error": "No image specified"}

        logger.info(f"[Runner] Creating container: name={name}, image={image}")

        if callback:
            callback(f"Creating container with image: {image}")

        # Create container
        create_kwargs = {
            "image": image,
            "detach": detach,
        }
        if name:
            create_kwargs["name"] = name
        if ports:
            create_kwargs["ports"] = ports
        if env:
            create_kwargs["environment"] = env
        if network:
            create_kwargs["network"] = network
        if restart_policy:
            create_kwargs["restart_policy"] = restart_policy

        # Handle volume mounts
        mount_list = []
        for vol in volumes:
            parts = vol.split(':')
            if len(parts) >= 2:
                source = parts[0]
                target = parts[1]
                read_only = len(parts) > 2 and parts[2] == 'ro'
                mount_list.append({
                    "Type": "bind",
                    "Source": os.path.abspath(source),
                    "Destination": target,
                    "RW": not read_only
                })
        if mount_list:
            # Use host_config for mounts
            from docker.types import Mount
            mounts = []
            for vol in volumes:
                parts = vol.split(':')
                if len(parts) >= 2:
                    source = parts[0]
                    target = parts[1]
                    read_only = len(parts) > 2 and parts[2] == 'ro'
                    mounts.append(Mount(
                        type="bind",
                        source=os.path.abspath(source),
                        target=target,
                        read_only=read_only
                    ))
            create_kwargs["mounts"] = mounts
            if "volumes" in create_kwargs:
                del create_kwargs["volumes"]

        container = client.containers.create(**create_kwargs)
        container.start()

        if callback:
            callback(f"Container started: {container.short_id}")

        return {
            "success": True,
            "container_id": container.short_id,
            "container_name": name or container.short_id,
            "output": f"Container {name or container.short_id} started successfully"
        }

    except Exception as e:
        logger.error(f"[Runner] Docker run failed: {e}")
        return {"success": False, "error": str(e)}
