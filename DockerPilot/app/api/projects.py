"""
Project API - Saved docker run or compose configurations
"""

import json
from fastapi import APIRouter, Body
from pydantic import BaseModel
from typing import Optional, List, Dict
from app.utils.response import success, error
from app.models.project import Project
from app.models.deployment import Deployment
from app.core.project_runner import run_project

router = APIRouter(prefix="/api/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    name: str
    type: str  # "run" or "compose"
    command: str = ""
    compose_content: str = ""
    description: str = ""


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    command: Optional[str] = None
    compose_content: Optional[str] = None
    description: Optional[str] = None


@router.get("")
def list_projects():
    projects = Project.get_all()
    return success(projects)


@router.get("/{project_id}")
def get_project(project_id: int):
    project = Project.get_by_id(project_id)
    if not project:
        return error("Project not found", 404)
    return success(project)


@router.post("")
def create_project(data: ProjectCreate):
    if data.type not in ('run', 'compose'):
        return error("Invalid project type. Must be 'run' or 'compose'")

    if data.type == 'run' and not data.command:
        return error("Command is required for run type")

    if data.type == 'compose' and not data.compose_content:
        return error("Compose content is required for compose type")

    try:
        project_id = Project.create(
            name=data.name,
            project_type=data.type,
            command=data.command,
            compose_content=data.compose_content,
            description=data.description
        )
        return success({"id": project_id}, "Project created")
    except Exception as e:
        return error(f"Failed to create project: {str(e)}")


@router.put("/{project_id}")
def update_project(project_id: int, data: ProjectUpdate):
    project = Project.get_by_id(project_id)
    if not project:
        return error("Project not found", 404)

    update_data = data.dict(exclude_unset=True)
    Project.update(project_id, **update_data)
    return success(message="Project updated")


@router.delete("/{project_id}")
def delete_project(project_id: int):
    project = Project.get_by_id(project_id)
    if not project:
        return error("Project not found", 404)
    Project.delete(project_id)
    return success(message="Project deleted")


@router.get("/{project_id}/deployments")
def get_project_deployments(project_id: int):
    project = Project.get_by_id(project_id)
    if not project:
        return error("Project not found", 404)
    deployments = Deployment.get_by_project(project_id)
    return success(deployments)


@router.post("/{project_id}/run")
def run_project_api(project_id: int, profile_id: int = None, overrides: Optional[Dict[str, str]] = Body(None)):
    """Execute a project with specified profile"""
    project = Project.get_by_id(project_id)
    if not project:
        return error("Project not found", 404)

    # Get variables
    variables = _resolve_variables(profile_id, overrides or {})

    # Create deployment record
    deployment_id = Deployment.create(
        project_id=project_id,
        profile_id=profile_id,
        overrides=overrides
    )

    # Execute
    result = run_project(project, variables)

    # Update deployment
    if result['success']:
        Deployment.update_status(deployment_id, 'success', result.get('output', ''))
    else:
        Deployment.update_status(deployment_id, 'failed', result.get('error', ''))

    return success({
        "deployment_id": deployment_id,
        "result": result
    })


@router.get("/scan/variables")
def scan_project_variables():
    """Scan all projects and extract variable names used in commands/compose"""
    import re
    projects = Project.get_all()
    var_usage = {}  # var_name -> project_count

    for project in projects:
        content = project.get('command', '') + ' ' + project.get('compose_content', '')
        # Match both ${VAR} and $VAR formats
        found = re.findall(r'\$\{(\w+)\}|\$(\w+)', content)
        for groups in found:
            var_name = groups[0] or groups[1]
            if var_name:
                var_usage[var_name] = var_usage.get(var_name, 0) + 1

    # Sort by usage count descending
    result = [
        {"name": name, "count": count}
        for name, count in sorted(var_usage.items(), key=lambda x: -x[1])
    ]
    return success(result)


def _resolve_variables(profile_id: int = None, overrides: dict = {}) -> dict:
    """Resolve variables from profile and overrides"""
    variables = {}

    # Load ALL variables from profile
    if profile_id:
        from app.models.variable_profile import VariableProfile
        profile = VariableProfile.get_by_id(profile_id)
        if profile:
            for v in profile.get('variables', []):
                variables[v['var_name']] = v['var_value']

    # Apply overrides
    variables.update(overrides)

    return variables
