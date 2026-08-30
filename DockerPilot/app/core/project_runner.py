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
        logger.info(f"[Runner] variables={variables}")
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
            # 支持 --opt=value 形式
            eq_arg = None
            eq_value = None
            if arg.startswith('-') and '=' in arg:
                eq_arg, eq_value = arg.split('=', 1)

            if arg == '-d' or arg == '--detach':
                detach = True
            elif eq_arg == '--name' or (arg == '--name' and i + 1 < len(args)):
                name = eq_value if eq_arg == '--name' else args[i + 1]
                if eq_arg != '--name':
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
            elif (arg == '--network' or arg == '--net') and i + 1 < len(args):
                network = args[i + 1]
                i += 1
            elif eq_arg == '--network' or eq_arg == '--net':
                # 支持 --network=host / --net=host
                network = eq_value
            elif (arg == '--restart' and i + 1 < len(args)):
                restart_policy = {"Name": args[i + 1]}
                i += 1
            elif eq_arg == '--restart':
                restart_policy = {"Name": eq_value}
            elif not arg.startswith('-'):
                # This should be the image
                image = arg
            i += 1

        if not image:
            return {"success": False, "error": "No image specified"}

        # host 网络模式下端口映射 -p 无效，忽略（Docker API 不接受 host 网络的端口绑定）
        if network == 'host' and ports:
            logger.info(f"[Runner] network=host, ignoring port mappings: {ports}")
            ports = {}

        logger.info(f"[Runner] Creating container: name={name}, image={image}, network={network}")

        if callback:
            callback(f"Creating container with image: {image}")

        # Create container
        create_kwargs = {
            "image": image,
            "detach": detach,
            "labels": {
                "dockerpilot.image_source": image,  # 记录原始镜像引用（tag）
            },
        }
        if name:
            create_kwargs["name"] = name
        if ports:
            create_kwargs["ports"] = ports
        if env:
            create_kwargs["environment"] = env
        if network:
            # host/bridge/none 是内置网络模式，须用 network_mode 指定，
            # 用 network 参数反而会尝试连接同名自定义网络
            if network in ('host', 'bridge', 'none'):
                create_kwargs["network_mode"] = network
            else:
                create_kwargs["network"] = network
        if restart_policy:
            create_kwargs["restart_policy"] = restart_policy

        # Handle volume mounts
        from docker.types import Mount
        mounts = []
        for vol in volumes:
            parts = vol.split(':')
            if len(parts) >= 2:
                source = parts[0]
                target = parts[1]
                read_only = len(parts) > 2 and parts[2] == 'ro'
                # bind 源路径直接使用解析后的原样路径（不做 abspath，
                # 容器内 cwd 不是宿主机目录，abspath 会错误加上 /app 前缀）
                # 但需显式判断：绝对路径原样用；相对路径属于宿主机相对路径，保持原样
                if not os.path.isabs(source):
                    logger.warning(f"[Runner] bind source '{source}' is NOT an absolute host path")
                # 检查变量是否已全部替换（不应再残留 $ 占位符）
                if "$" in source or "${" in source:
                    return {
                        "success": False,
                        "error": f"bind 挂载源路径仍包含未替换的变量占位符: '{source}'。请检查变量名是否已正确传入解析器"
                    }
                # 检查源路径是否存在（单文件/目录都要求宿主上已存在）
                if not os.path.exists(source):
                    return {
                        "success": False,
                        "error": f"bind 挂载源路径不存在: '{source}'（单文件挂载要求宿主源文件已存在；目录挂载要求目录已存在）"
                    }
                mounts.append(Mount(
                    type="bind",
                    source=source,
                    target=target,
                    read_only=read_only
                ))
            else:
                logger.warning(f"[Runner] Skip invalid volume spec: {vol}")
        if mounts:
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
