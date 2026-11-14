"""Validate cookiecutter inputs before generation."""

import json
import re
import sys

PLUGIN_ID = "{{ cookiecutter.plugin_id }}"
PERMISSIONS = '{{ cookiecutter.backend_permissions }}'
ALLOWED = {
    "db_read", "db_write", "hooks_before_post_created", "hooks_after_post_created",
    "hooks_before_chat_sent", "hooks_after_chat_sent", "hooks_on_user_joined",
    "hooks_on_community_created", "send_notifications", "storage_access", "external_http", "frontend_routes",
    "celery_tasks",
}  # fmt: skip

if not re.match(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$", PLUGIN_ID):
    sys.exit(f"ERROR: plugin_id '{PLUGIN_ID}' must be slug-case (a-z, 0-9, '-')")

try:
    perms = json.loads(PERMISSIONS)
except ValueError:
    sys.exit('ERROR: backend_permissions must be a JSON list, e.g. ["db_read"]')
if not isinstance(perms, list) or not set(perms) <= ALLOWED or len(set(perms)) != len(perms):
    sys.exit(f"ERROR: backend_permissions must be unique values from {sorted(ALLOWED)}")
