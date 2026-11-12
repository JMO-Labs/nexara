#!/usr/bin/env bash
##
# @file scripts/build-docs-site.sh
# @brief Build the full docs site into docs/site/ (MkDocs, OpenAPI ref,
#        Python Doxygen, coverage). Exits non-zero on any failure.
#
# Env: SKIP_INSTALL=1 skips pip install; COVERAGE_DIR overrides coverage/.
# Used by GitLab CI and GitHub Actions.
##
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
SITE="$ROOT/docs/site"

if [ "${SKIP_INSTALL:-0}" != "1" ]; then
  echo "Installing dependencies..."
  python3 -m pip install mkdocs mkdocs-material mkdocs-awesome-pages-plugin
fi
command -v doxygen >/dev/null 2>&1 && HAS_DOXYGEN=1 || HAS_DOXYGEN=0

# Runs before mkdocs: its output lands in docs_dir and is bundled into the site.
echo "Generating OpenAPI reference..."
if [ -f scripts/generate-api-ref.sh ]; then
  bash scripts/generate-api-ref.sh
fi

echo "Building MkDocs..."
mkdocs build --strict -f docs/mkdocs.yml -d "$SITE"

echo "Generating Python Doxygen docs..."
if [ "$HAS_DOXYGEN" -eq 1 ] && [ -f docs/Doxyfile ]; then
  (cd docs && doxygen Doxyfile)
  mkdir -p "$SITE/api-python"
  cp -r docs/build/api/. "$SITE/api-python/"
  rm -rf docs/build/api
elif [ -f docs/Doxyfile ]; then
  echo "doxygen not found; skipping api-python"
fi

echo "Copying coverage reports..."
COV="${COVERAGE_DIR:-coverage}"
if [ -d "$COV" ]; then
  mkdir -p "$SITE/coverage"
  cp -r "$COV"/. "$SITE/coverage/"
fi

echo "Checking internal links..."
python3 scripts/check-site-links.py "$SITE"

echo "Docs built to docs/site/"
