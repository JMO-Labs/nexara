"""API routes for {{cookiecutter.plugin_name}}."""

from app.core.dependencies import get_plugin_context
from app.plugins.context import PluginContext
from fastapi import APIRouter, Depends

router = APIRouter(prefix="", tags=["{{cookiecutter.plugin_id}}"])


@router.get("/hello")
async def hello(ctx: PluginContext = Depends(get_plugin_context)) -> dict[str, str]:
    """Example route. Replace with your plugin logic."""
    return {"message": "Hello from {{cookiecutter.plugin_name}}!"}
