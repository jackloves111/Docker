"""
Project Runner - Execute docker run or docker compose
"""

import re
import logging
import subprocess

from app.core.compose_runner import run_compose

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
    Execute an official docker run / docker compose command verbatim via bash.

    不再自己解析 docker run 参数（那套解析器无法覆盖 --env-file/--device/
    --privileged/--cap-add/--shm-size/--pid/--cpus/--memory 等全部官方参数，
    也无法正确还原数据库里被转义的反斜杠续行 \\\\n）。
    而是：变量替换 → 交给宿主机 bash 真执行。
    bash 会按官方 shell 规则处理续行、引号、转义，100% 兼容官方 docker 命令。
    """
    try:
        command = project.get('command', '').strip()
        if not command:
            return {"success": False, "error": "Empty command"}

        # 1. 变量替换（${VAR} 或 $VAR → 实际值）
        logger.info(f"[Runner] variables={variables}")
        resolved_cmd = resolve_variables(command, variables)

        # 2. 数据库里反斜杠续行可能被存成字面 "\\n"（反斜杠+n）或 "\\\n"（两反斜杠+n）。
        #    还原成真正换行，交给 bash 按续行/转义处理。
        resolved_cmd = resolved_cmd.replace('\\r\\n', '\n').replace('\\n', '\n').replace('\\r', '\n')
        logger.info(f"[Runner] Executing: {resolved_cmd}")

        if callback:
            callback(f"Executing: {resolved_cmd}")

        # 3. 通过 bash 执行，让官方 shell 处理所有语法
        result = subprocess.run(
            ["bash", "-c", resolved_cmd],
            capture_output=True,
            text=True,
            timeout=600,
        )
        output = (result.stdout or '') + (result.stderr or '')
        success = result.returncode == 0
        if not success and callback:
            callback(f"命令失败 (exit {result.returncode})")

        # 提取容器 ID（docker run -d 会打印 64 位 hex ID）
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

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Command timed out after 600 seconds"}
    except Exception as e:
        logger.error(f"[Runner] Execution failed: {e}")
        return {"success": False, "error": str(e)}
