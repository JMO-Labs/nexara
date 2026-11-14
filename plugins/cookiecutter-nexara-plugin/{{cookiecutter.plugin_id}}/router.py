"""API routes for {{cookiecutter.plugin_name}}."""

from fastapi import APIRouter

router = APIRouter(prefix="", tags=["{{cookiecutter.plugin_id}}"])


@router.get("/hello")
async def hello() -> dict[str, str]:
    """Example route. Replace with your plugin logic.

    Once the core exposes PluginContext, inject it with
    ``ctx: PluginContext = Depends(get_plugin_context)`` for scoped DB access.
    """
    return {"message": "Hello from {{cookiecutter.plugin_name}}!"}
