#!/usr/bin/env bash
##
# @file scripts/wq-ci-test.sh
# @brief wq-ci test entrypoint: backend unit + frontend vitest.
#        Writes coverage.xml (backend Cobertura) and junit.xml (merged) to repo root.
##
# ponytail: backend unit only (no Postgres); integration stays in GitLab CI (allow_failure there).
set -uo pipefail
cd "$(dirname "$0")/.."
ROOT=$PWD; rc=0

(cd backend && { command -v uv >/dev/null || pipx install -q uv; } && uv venv -q .venv --clear && { uv sync -q --frozen --extra dev || uv sync -q --extra dev; } \
  && .venv/bin/pytest tests/unit/ -q --cov=app --cov-report=xml:"$ROOT/coverage.xml" --junitxml="$ROOT/junit-be.xml") || rc=1

(cd frontend && npm ci --no-audit --no-fund && npx vitest run --reporter=default --reporter=junit --outputFile.junit="$ROOT/junit-fe.xml") || rc=1

python3 - <<'PY'
import glob, xml.etree.ElementTree as ET
out = ET.Element("testsuites")
for f in sorted(glob.glob("junit-*.xml")):
    r = ET.parse(f).getroot()
    out.extend(r if r.tag == "testsuites" else [r])
ET.ElementTree(out).write("junit.xml", encoding="utf-8", xml_declaration=True)
PY
rm -f junit-be.xml junit-fe.xml
exit $rc
