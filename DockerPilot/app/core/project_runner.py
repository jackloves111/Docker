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
    Execute an official docker run command verbatim via the docker CLI.

    不再自己解析 docker run 参数（那套解析器无法覆盖 --env-file/--device/
    --privileged/--cap-add/--shm-size/--pid/--cpus/--memory 等全部官方参数）。
    而是：变量替换 → 参数按 shell 规则切分 → 原样交给宿主机 docker 执行。
    这样 100% 兼容官方 docker command 语法。
    """
    try:
        command = project.get('command', '')
        if not command:
            return {"success": False, "error": "Empty command"}

        # 1. 变量替换（${VAR} 或 $VAR → 实际值）
        logger.info(f"[Runner] variables={variables}")
        resolved_cmd = resolve_variables(command, variables)
        logger.info(f"[Runner] Executing: {resolved_cmd}")

        if callback:
            callback(f"Executing: {resolved_cmd}")

        # 2. 按 shell 词法切分命令（支持引号内的空格，不做变量求值）
        parts = _shell_split(resolved_cmd)
        if not parts:
            return {"success": False, "error": "Empty command"}
        if parts[0] not in ('docker', 'docker-compose'):
            return {"success": False, "error": f"不支持的命令: '{parts[0]}'，请使用官方 docker 或 docker compose 命令"}

        # 3. 判断子命令，分派到官方 CLI 执行
        subcommand = parts[1] if len(parts) > 1 else ''

        if subcommand == 'run':
            return _run_cli_sync(parts, callback)
        elif subcommand == 'compose':
            from app.core.compose_runner import run_compose_command
            return run_compose_command(parts[2:], callback)
        elif subcommand == 'rm' or subcommand == 'stop' or subcommand == 'start' or \
             subcommand == 'restart' or subcommand == 'kill' or subcommand == 'logs' or \
             subcommand == 'ps' or subcommand == 'pull' or subcommand == 'images':
            # 其他官方 docker 子命令：原样交给 CLI
            return _run_cli_sync(parts, callback)
        else:
            # 默认：原样交给 docker CLI，由它自行报错
            return _run_cli_sync(parts, callback)

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Command timed out after 300 seconds"}
    except Exception as e:
        logger.error(f"[Runner] Execution failed: {e}")
        return {"success": False, "error": str(e)}


def _shell_split(cmd: str) -> list:
    """按 shell 规则切分命令字符串，支持 '单引号' 和 \"双引号\" 内的空格。

    注意：这里只做词法切分，不做 $ 变量求值（$VAR 已由 resolve_variables 替换）。
    """
    import shlex
    return shlex.split(cmd, posix=True)


def _run_cli_sync(parts: list, callback=None) -> dict:
    """用官方 docker CLI 同步执行命令，返回输出。"""
    # 规范化：docker run / docker compose 都转成 'docker' + 参数调用
    cmd = parts
    # 兼容 docker-compose（旧版独立命令）→ 直接执行
    logger.info(f"[Runner] CLI exec: {' '.join(cmd)}")
    if callback:
        callback(f"Executing: {' '.join(cmd)}")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=600
    )
    output = (result.stdout or '') + (result.stderr or '')
    success = result.returncode == 0
    if not success and callback:
        callback(f"命令失败 (exit {result.returncode})")

    # 尝试从输出中提取容器 ID（docker run -d 会打印容器ID 或 --cidfile）
    container_id = ''
    m = re.search(r'(?m)^([0-9a-f]{64})$', result.stdout or '')
    if m:
        container_id = m.group(1)

    return {
        "success": success,
        "output": output.strip(),
        "container_id": container_id,
        "container_name": "",
    }
