# {{cookiecutter.plugin_name}}

{{cookiecutter.description}}

## Overview

Describe what the plugin does, who it is for, and which Nexara features it
extends. Requires Nexara core >= {{cookiecutter.min_core_version}}.

## Installation

- **Zip upload:** zip the `{{cookiecutter.plugin_id}}/` directory and upload it
  in the Nexara admin plugin page.
- **Git clone:** clone this repository into the server's `plugins/` directory
  and restart the backend and Celery workers.

## Configuration

Declare settings in `manifest.toml` under `[settings.<key>]` and document each
one here. Delete this section if the plugin has no settings.

## Development

1. Edit `manifest.toml` and keep `permissions` to the minimum needed.
2. Replace the example code in `router.py`, `tasks.py` and `hooks.py`.
3. Add optional dependencies to `requirements.txt`.
4. Run `ruff check .` and `mypy .` before publishing.

## Testing

```bash
pytest tests/ -v
```

Add tests for every route, task and hook.

## Contributing

Open an issue before large changes, keep commits conventional (`feat:`,
`fix:`), and include tests with each pull request.

## License

MIT, see `LICENSE`.
