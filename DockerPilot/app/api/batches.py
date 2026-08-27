"""
Batch API - Combination of images and projects
"""

import json
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List, Dict
from app.utils.response import success, error
from app.models.batch import BatchGroup, BatchItem
from app.models.project import Project
from app.models.deployment import Deployment, DeploymentStep
from app.models.registry import Registry
from app.core.image_manager import pull_image, load_image_from_url
from app.core.project_runner import run_project
from app.core.compose_runner import run_compose

router = APIRouter(prefix="/api/batches", tags=["batches"])


class BatchItemCreate(BaseModel):
    item_type: str  # "image_pull", "image_load", "project_run"
    item_id: Optional[int] = None
    item_config: dict = {}
    sort_order: int = 0


class BatchGroupCreate(BaseModel):
    name: str
    required_vars: List[str] = []
    continue_on_error: bool = False
    description: str = ""
    items: List[BatchItemCreate] = []


class BatchGroupUpdate(BaseModel):
    name: Optional[str] = None
    required_vars: Optional[List[str]] = None
    continue_on_error: Optional[bool] = None
    description: Optional[str] = None


class ReorderRequest(BaseModel):
    item_orders: List[dict]  # [{id: int, sort_order: int}]


class ExecuteRequest(BaseModel):
    profile_id: Optional[int] = None
    overrides: Dict[str, str] = {}\n    auto_replace: bool = False  # Auto-replace containers after pull/load


@router.get("")
def list_batches():
    groups = BatchGroup.get_all()
    return success(groups)


@router.get("/{group_id}")
def get_batch(group_id: int):
    group = BatchGroup.get_by_id(group_id)
    if not group:
        return error("Batch group not found", 404)
    return success(group)


@router.post("")
def create_batch(data: BatchGroupCreate):
    try:
        group_id = BatchGroup.create(
            name=data.name,
            required_vars=data.required_vars,
            continue_on_error=data.continue_on_error,
            description=data.description
        )

        # Add items
        for i, item in enumerate(data.items):
            BatchItem.create(
                group_id=group_id,
                item_type=item.item_type,
                item_id=item.item_id,
                item_config=item.item_config,
                sort_order=item.sort_order if item.sort_order else i
            )

        return success({"id": group_id}, "Batch group created")
    except Exception as e:
        return error(f"Failed to create batch: {str(e)}")


@router.put("/{group_id}")
def update_batch(group_id: int, data: BatchGroupUpdate):
    group = BatchGroup.get_by_id(group_id)
    if not group:
        return error("Batch group not found", 404)

    update_data = data.dict(exclude_unset=True)
    BatchGroup.update(group_id, **update_data)
    return success(message="Batch group updated")


@router.delete("/{group_id}")
def delete_batch(group_id: int):
    group = BatchGroup.get_by_id(group_id)
    if not group:
        return error("Batch group not found", 404)
    BatchGroup.delete(group_id)
    return success(message="Batch group deleted")


@router.post("/{group_id}/items")
def add_batch_item(group_id: int, data: BatchItemCreate):
    group = BatchGroup.get_by_id(group_id)
    if not group:
        return error("Batch group not found", 404)

    # Auto sort order
    if data.sort_order == 0:
        existing = group.get('items', [])
        data.sort_order = len(existing)

    item_id = BatchItem.create(
        group_id=group_id,
        item_type=data.item_type,
        item_id=data.item_id,
        item_config=data.item_config,
        sort_order=data.sort_order
    )
    return success({"id": item_id}, "Item added")


@router.put("/{group_id}/items/reorder")
def reorder_items(group_id: int, data: ReorderRequest):
    BatchItem.reorder(group_id, data.item_orders)
    return success(message="Items reordered")


@router.delete("/{group_id}/items/{item_id}")
def delete_batch_item(group_id: int, item_id: int):
    BatchItem.delete(item_id)
    return success(message="Item deleted")


@router.get("/{group_id}/execute/preview")
def preview_execution(group_id: int, profile_id: int = None):
    """Preview what will be executed with resolved variables"""
    group = BatchGroup.get_by_id(group_id)
    if not group:
        return error("Batch group not found", 404)

    # Resolve variables
    variables = {}

    if profile_id:
        from app.models.variable_profile import VariableProfile
        profile = VariableProfile.get_by_id(profile_id)
        if profile:
            for v in profile.get('variables', []):
                variables[v['var_name']] = v['var_value']

    # Build preview
    preview_items = []
    for item in group.get('items', []):
        config = json.loads(item.get('item_config', '{}'))
        preview = {
            "id": item['id'],
            "type": item['item_type'],
            "config": config,
            "status": "pending"
        }
        preview_items.append(preview)

    return success({
        "group": group,
        "variables": variables,
        "items": preview_items
    })


@router.post("/{group_id}/execute")
def execute_batch(group_id: int, data: ExecuteRequest):
    group = BatchGroup.get_by_id(group_id)
    if not group:
        return error("Batch group not found", 404)

    # Resolve variables
    variables = {}

    # Load ALL variables from profile
    if data.profile_id:
        from app.models.variable_profile import VariableProfile
        profile = VariableProfile.get_by_id(data.profile_id)
        if profile:
            for v in profile.get('variables', []):
                variables[v['var_name']] = v['var_value']

    # Apply overrides
    variables.update(data.overrides)

    # Create deployment
    deployment_id = Deployment.create(
        batch_group_id=group_id,
        profile_id=data.profile_id,
        overrides=data.overrides
    )

    # Execute items sequentially
    items = group.get('items', [])
    continue_on_error = group.get('continue_on_error', False)
    overall_success = True

    for item in items:
        item_type = item['item_type']
        item_config = json.loads(item.get('item_config', '{}'))
        item_id = item.get('item_id')

        # Create step
        step_id = DeploymentStep.create(
            deployment_id=deployment_id,
            batch_item_id=item['id'],
            step_type=item_type,
            step_config=item_config
        )

        DeploymentStep.update_status(step_id, 'running')

        try:
            if item_type == 'image_pull':
                # Pull image
                registry_id = item_config.get('registry_id')
                image_name = item_config.get('image_name', '')

                if registry_id:
                    from app.models.registry import Registry
                    registry = Registry.get_by_id(registry_id)
                    if registry:
                        result = pull_image(
                            registry['url'],
                            image_name,
                            registry.get('username', ''),
                            registry.get('password', '')
                        )
                    else:
                        result = pull_image("", image_name)
                else:
                    registry = Registry.get_default()
                    if registry:
                        result = pull_image(
                            registry['url'],
                            image_name,
                            registry.get('username', ''),
                            registry.get('password', '')
                        )
                    else:
                        result = pull_image("", image_name)

            elif item_type == 'image_load':
                # Load image from URL
                url = item_config.get('url', '')
                result = load_image_from_url(url)

            elif item_type == 'project_run':
                # Run project
                project = Project.get_by_id(item_id)
                if project:
                    result = run_project(project, variables)
                else:
                    result = {"success": False, "error": f"Project {item_id} not found"}

            else:
                result = {"success": False, "error": f"Unknown item type: {item_type}"}

            # Update step
            if result['success']:
                DeploymentStep.update_status(step_id, 'success', result.get('output', ''))
            else:
                DeploymentStep.update_status(step_id, 'failed', result.get('error', ''))
                overall_success = False

                if not continue_on_error:
                    # Stop execution
                    break

        except Exception as e:
            DeploymentStep.update_status(step_id, 'failed', str(e))
            overall_success = False
            if not continue_on_error:
                break

    # Update deployment status
    if overall_success:
        Deployment.update_status(deployment_id, 'success')
    else:
        Deployment.update_status(deployment_id, 'failed')

    # Get all steps with their status
    steps = DeploymentStep.get_by_deployment(deployment_id)
    step_results = []
    for step in steps:
        step_config = json.loads(step.get('step_config', '{}'))
        step_results.append({
            "id": step['id'],
            "type": step['step_type'],
            "status": step['status'],
            "output": step.get('output', ''),
            "config": step_config
        })

    return success({
        "deployment_id": deployment_id,
        "success": overall_success,
        "steps": step_results
    })


@router.get("/{group_id}/executions")
def get_batch_executions(group_id: int, limit: int = 20):
    executions = Deployment.get_by_batch(group_id, limit)
    return success(executions)




