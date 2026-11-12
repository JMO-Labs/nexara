"""@file Validates unRAID Community Applications templates in deploy/unraid."""

from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

DIR = Path(__file__).resolve().parents[3] / "deploy" / "unraid"
FILES = ["nexara.xml", "nexara-postgres.xml", "nexara-valkey.xml"]


def _load(name: str) -> ET.Element:
    return ET.parse(DIR / name).getroot()


def _configs(root: ET.Element) -> dict[str, ET.Element]:
    return {c.get("Target"): c for c in root.findall("Config")}


@pytest.mark.parametrize("name", FILES)
def test_template_parses_with_required_fields(name: str) -> None:
    root = _load(name)
    assert root.tag == "Container"
    assert root.get("version") == "2"
    for tag in ("Name", "Repository", "Overview", "Project", "Icon", "Privileged"):
        el = root.find(tag)
        assert el is not None and (el.text or "").strip(), tag
    assert root.findtext("Privileged") == "false"
    assert "unless-stopped" in (root.findtext("ExtraParams") or "")


@pytest.mark.parametrize("name", FILES)
def test_configs_have_description_and_valid_type(name: str) -> None:
    for c in _load(name).findall("Config"):
        assert c.get("Type") in {"Port", "Variable", "Path"}
        assert c.get("Name") and c.get("Description")


def test_main_declares_env_port_and_volumes() -> None:
    root = _load("nexara.xml")
    cfg = _configs(root)
    for var in ("DATABASE_URL", "REDIS_URL", "SECRET_KEY", "LOG_LEVEL"):
        assert cfg[var].get("Type") == "Variable"
    assert cfg["SECRET_KEY"].get("Mask") == "true"
    port = cfg["8080"]
    assert port.get("Type") == "Port" and port.get("Default") == "8080"
    assert 1 <= int(port.text) <= 65535
    assert cfg["/data/media"].get("Type") == "Path"
    assert cfg["/cache"].get("Required") == "false"
    assert root.findtext("Network") in {"bridge", "host"}


def test_webui_uses_port_placeholder() -> None:
    assert _load("nexara.xml").findtext("WebUI") == "http://[IP]:[PORT:8080]/"


def test_postgres_template() -> None:
    root = _load("nexara-postgres.xml")
    assert root.findtext("Repository") == "postgres:16"
    cfg = _configs(root)
    for var in ("POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB"):
        assert var in cfg
    assert cfg["POSTGRES_PASSWORD"].get("Mask") == "true"
    assert cfg["/var/lib/postgresql/data"].get("Type") == "Path"
    assert not [c for c in cfg.values() if c.get("Type") == "Port"]


def test_valkey_template() -> None:
    root = _load("nexara-valkey.xml")
    assert root.findtext("Repository").startswith("valkey/valkey")
    cfg = _configs(root)
    assert cfg["/data"].get("Type") == "Path"
    assert not [c for c in cfg.values() if c.get("Type") == "Port"]


def test_unraid_doc_exists_and_in_nav() -> None:
    root = DIR.parents[1]
    assert (root / "docs/docs/deployment/unraid.md").exists()
    assert "deployment/unraid.md" in (root / "docs/mkdocs.yml").read_text()
