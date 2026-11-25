"""
@file
@brief Request/response models, in-memory plugin records and the Supervisor interface.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Literal, NamedTuple, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

PLUGIN_ID_RE = r"^[a-z0-9]+(\.[a-z0-9-]+)+$"
_VERSION_RE = re.compile(r"\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?(\+[0-9A-Za-z.-]+)?", re.ASCII)

Status = Literal[
    "installing", "running", "stopped", "failed", "needs_config", "sandbox_unavailable"
]


class PluginEnv(BaseModel):
    """
    @brief Env pushed by Nexara. Held in memory only; never logged or written to disk.

    Unknown keys are rejected so Nexara cannot inject e.g. LD_PRELOAD. JSON-valued
    fields accept objects/lists and are stored as JSON strings ready for the process env.
    """

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    NEXARA_URL: str | None = None
    NEXARA_TOKEN: str
    NEXARA_WEBHOOK_SECRET: str
    NEXARA_SETTINGS: str = "{}"
    NEXARA_COMMUNITIES: str = "[]"

    @field_validator("NEXARA_SETTINGS", "NEXARA_COMMUNITIES", mode="before")
    @classmethod
    def _to_json(cls, v: Any) -> Any:
        return v if isinstance(v, str) else json.dumps(v)


class InstallSpec(BaseModel):
    """@brief Body of PUT /plugins/{id}."""

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    version: str = Field(max_length=64)
    package_url: str = Field(max_length=2048)
    sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    runtime: Literal["node", "python"]
    entrypoint: str = Field(min_length=1, max_length=255)
    env: PluginEnv = Field(repr=False)

    @field_validator("version")
    @classmethod
    def _semver(cls, v: str) -> str:
        if not _VERSION_RE.fullmatch(v):
            raise ValueError("version must be semver")
        return v

    @field_validator("entrypoint")
    @classmethod
    def _relative(cls, v: str) -> str:
        p = PurePosixPath(v)
        if p.is_absolute() or ".." in p.parts or "\\" in v or "\0" in v:
            raise ValueError("entrypoint must be a relative path inside the package")
        return v


class PluginRow(BaseModel):
    """@brief One row of GET /plugins."""

    id: str
    version: str | None
    status: Status
    restarts: int = 0
    last_error: str | None = None


@dataclass
class ProcStatus:
    """@brief Process state as reported by the supervisor."""

    status: Status
    restarts: int = 0
    last_error: str | None = None


@dataclass
class PluginRecord:
    """
    @brief In-memory state for one plugin; specs (with env) are never persisted.
    `version`/`spec` = last version that started OK (used by /start);
    `pending` = spec of the in-flight PUT, if any.
    """

    version: str | None
    status: Status
    spec: InstallSpec | None = None
    pending: InstallSpec | None = None
    last_error: str | None = None


class Endpoint(NamedTuple):
    """@brief Where a live plugin listens and the uid its listener must belong to."""

    port: int
    uid: int


class Supervisor(Protocol):
    """@brief Process supervisor contract (implemented by the sandbox supervisor)."""

    async def start(self, plugin_id: str, root: Path, spec: InstallSpec) -> None:
        """@brief (Re)start the plugin from `root` with `spec.env`."""

    async def stop(self, plugin_id: str) -> None:
        """@brief Stop the plugin if running; no-op otherwise."""

    def status(self, plugin_id: str) -> ProcStatus | None:
        """@brief Live process state, or None if the supervisor does not track it."""

    def logs(self, plugin_id: str, lines: int) -> list[str]:
        """@brief Last `lines` output lines."""

    def endpoint(self, plugin_id: str) -> Endpoint | None:
        """@brief Port + uid of a live plugin process (event proxy target), else None."""
