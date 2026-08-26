"""
Compose Runner - Execute docker compose commands
"""

import os
import json
import logging
import tempfile
import subprocess

logger = logging.getLogger(__name__)

COMPOSE_TEMP_DIR = os.environ.get("COMPOSE_TEMP_DIR", "/config/compose")


def run_compose(project: dict, variables: dict, callback=None) -> dict:
    """
    Execute docker compose up for a project
    """
    try:
        compose_content = project.get('compose_content', '')
        project_name = project.get('name', 'project')

        if not compose_content:
            return {"success": False, "error": "Empty compose content"}

        # Resolve variables
        from app.core.project_runner import resolve_variables
        resolved_content = resolve_variables(compose_content, variables)

        logger.info(f"[Compose] Running compose for project: {project_name}")

        if callback:
            callback(f"Preparing compose files for {project_name}...")

        # Create temp directory for compose files
        os.makedirs(COMPOSE_TEMP_DIR, exist_ok=True)
        compose_dir = os.path.join(COMPOSE_TEMP_DIR, project_name.replace(' ', '_'))

        # Sanitize directory name
        import re
        compose_dir = re.sub(r'[^\w\-_]', '_', compose_dir)

        os.makedirs(compose_dir, exist_ok=True)

        # Write compose file
        compose_file = os.path.join(compose_dir, "docker-compose.yml")
        with open(compose_file, 'w', encoding='utf-8') as f:
            f.write(resolved_content)

        logger.info(f"[Compose] Compose file written to: {compose_file}")

        # Execute docker compose up -d
        result = execute_compose_up(compose_dir, project_name, callback)

        return result

    except Exception as e:
        logger.error(f"[Compose] Execution failed: {e}")
        return {"success": False, "error": str(e)}


def execute_compose_up(compose_dir: str, project_name: str, callback=None) -> dict:
    """Execute docker compose up -d"""
    try:
        cmd = ["docker", "compose", "-f", os.path.join(compose_dir, "docker-compose.yml"),
               "-p", project_name, "up", "-d"]

        logger.info(f"[Compose] Executing: {' '.join(cmd)}")

        if callback:
            callback(f"Starting compose services...")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=compose_dir
        )

        output = result.stdout + "\n" + result.stderr
        success = result.returncode == 0

        if success and callback:
            callback(f"Compose services started successfully")

        return {
            "success": success,
            "output": output.strip(),
            "compose_dir": compose_dir
        }

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Compose command timed out after 300 seconds"}
    except Exception as e:
        logger.error(f"[Compose] docker compose failed: {e}")
        return {"success": False, "error": str(e)}


def run_compose_command(args: list, callback=None) -> dict:
    """Execute arbitrary docker compose command"""
    try:
        cmd = ["docker", "compose"] + args

        if callback:
            callback(f"Executing: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )

        return {
            "success": result.returncode == 0,
            "output": result.stdout + "\n" + result.stderr
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Command timed out"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def stop_compose(project_name: str, compose_dir: str = None, callback=None) -> dict:
    """Stop docker compose services"""
    try:
        if compose_dir:
            cmd = ["docker", "compose", "-f", os.path.join(compose_dir, "docker-compose.yml"),
                   "-p", project_name, "down"]
        else:
            cmd = ["docker", "compose", "-p", project_name, "down"]

        if callback:
            callback(f"Stopping compose services...")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )

        return {
            "success": result.returncode == 0,
            "output": result.stdout + "\n" + result.stderr
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
