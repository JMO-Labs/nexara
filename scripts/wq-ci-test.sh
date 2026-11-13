#!/usr/bin/env bash
##
# @file scripts/wq-ci-test.sh
# @brief wq-ci test entrypoint: backend unit + integration + frontend vitest + mobile flutter test.
#        Writes coverage.xml (backend Cobertura) and junit.xml (merged) to repo root.
##
set -uo pipefail
cd "$(dirname "$0")/.."
ROOT=$PWD; rc=0

(cd backend && { command -v uv >/dev/null || pipx install -q uv; } && uv venv -q .venv --clear && { uv sync -q --frozen --extra dev || uv sync -q --extra dev; } \
  && .venv/bin/pytest tests/unit/ -q --cov=app --cov-report=xml:"$ROOT/coverage.xml" --junitxml="$ROOT/junit-be.xml") || rc=1

# Integration (dockerized Postgres + Valkey); appends to coverage.xml. Skips locally without docker.
bash scripts/wq-ci-integration.sh || rc=1

(cd frontend && npm ci --no-audit --no-fund && npx vitest run --reporter=default --reporter=junit --outputFile.junit="$ROOT/junit-fe.xml" && npx tsc --noEmit && npm run build) || rc=1

# Mobile (Flutter): install the stable SDK when absent, then analyze (infos non-fatal) and test.
if [ -d mobile ]; then
  ( if ! command -v flutter >/dev/null; then
      [ -x "$HOME/flutter/bin/flutter" ] || git clone -q --depth 1 -b stable https://github.com/flutter/flutter.git "$HOME/flutter"
      export PATH="$HOME/flutter/bin:$PATH"
    fi
    cd mobile && flutter --version && flutter pub get && flutter analyze --no-fatal-infos && flutter test ) || rc=1
fi

python3 - <<'PY'
import glob, xml.etree.ElementTree as ET
out = ET.Element("testsuites")
for f in sorted(glob.glob("junit-*.xml")):
    r = ET.parse(f).getroot()
    out.extend(r if r.tag == "testsuites" else [r])
ET.ElementTree(out).write("junit.xml", encoding="utf-8", xml_declaration=True)
PY
rm -f junit-be.xml junit-int.xml junit-fe.xml
exit $rc
