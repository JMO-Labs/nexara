"""Remove files for the backend/frontend parts that were not selected."""

import shutil
from pathlib import Path

if not {{ cookiecutter.has_frontend }}:
    shutil.rmtree("frontend", ignore_errors=True)

if not {{ cookiecutter.has_backend }}:
    for name in ("router.py", "tasks.py", "models.py", "hooks.py"):
        Path(name).unlink(missing_ok=True)
