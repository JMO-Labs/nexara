"""Hook registration for {{cookiecutter.plugin_name}}."""

import uuid

from app.plugins.manifest import PluginManifest

PLUGIN_ID = "{{cookiecutter.plugin_id}}"


def register_hooks(community_id: uuid.UUID, manifest: PluginManifest) -> None:
    """Register hooks for one community; the plugin loader calls this.

    Declare each hook in manifest.toml too (plus the matching ``hooks_*``
    permission), then register its handler, e.g.::

        from app.plugins.hooks import HookRegistry

        HookRegistry.register(
            community_id, "after_post_created", PLUGIN_ID, on_post_created, manifest
        )
    """
