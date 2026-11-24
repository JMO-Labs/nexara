"""
@file
@brief Per-plugin log ring buffer: lines go to host stdout as `[plugin_id] …` and the
       last 200 are kept for GET /plugins/{id}/logs. The plugin's own secrets are redacted.
"""

import json
import sys
from collections import deque
from typing import Any

from host.models import PluginEnv

RING_SIZE = 200
MAX_LINE = 2000
MIN_SECRET_LEN = 8
REDACTED = "[redacted]"


def _leaves(v: Any, key: str = "") -> list[str]:
    """@brief String leaves of a JSON value, skipping `*_id` keys (ids are not secrets)."""
    if isinstance(v, dict):
        return [s for k, x in v.items() for s in _leaves(x, str(k))]
    if isinstance(v, list):
        return [s for x in v for s in _leaves(x, key)]
    return [v] if isinstance(v, str) and not key.endswith("_id") else []


def secrets_of(env: PluginEnv) -> tuple[str, ...]:
    """@brief Token, webhook secret and every settings/community string worth redacting."""
    found = [env.NEXARA_TOKEN, env.NEXARA_WEBHOOK_SECRET]
    for raw in (env.NEXARA_SETTINGS, env.NEXARA_COMMUNITIES):
        try:
            found += _leaves(json.loads(raw))
        except ValueError:
            found.append(raw)
    keep = {s for s in found if len(s) >= MIN_SECRET_LEN}
    return tuple(sorted(keep, key=len, reverse=True))


def _clean(line: str) -> str:
    """@brief Drop control chars (no terminal escapes / forged lines in host logs)."""
    return "".join(c if c.isprintable() or c == "\t" else "?" for c in line[:MAX_LINE])


class LogBuffer:
    """@brief Last RING_SIZE output lines of one plugin, redacted."""

    def __init__(self, plugin_id: str) -> None:
        self.plugin_id = plugin_id
        self.lines: deque[str] = deque(maxlen=RING_SIZE)
        self.secrets: tuple[str, ...] = ()

    def add(self, line: str) -> None:
        """@brief Redact, keep and echo one line to host stdout."""
        for s in self.secrets:
            line = line.replace(s, REDACTED)
        line = _clean(line)
        self.lines.append(line)
        sys.stdout.write(f"[{self.plugin_id}] {line}\n")
        sys.stdout.flush()

    def tail(self, n: int) -> list[str]:
        """@brief Last `n` lines, oldest first."""
        return list(self.lines)[-n:] if n > 0 else []
