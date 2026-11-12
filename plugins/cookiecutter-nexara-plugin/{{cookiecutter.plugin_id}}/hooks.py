"""Hook registration for {{cookiecutter.plugin_name}}."""

from typing import Any


def register_hooks(ctx: Any) -> None:
    """Register hooks. Declare them in manifest.toml too."""
    # @ctx.registry.hook("after_post_created")
    # async def on_post_created(**kwargs):
    #     pass
