#!/usr/bin/env bash
##
# @file scripts/test-docs-nav.sh
# @brief Checks docs/mkdocs.yml uses awesome-pages instead of an explicit nav.
# @return 0 when no top-level nav: key and search + awesome-pages are plugins.
##
set -u
cfg="${1:-$(dirname "$0")/../docs/mkdocs.yml}"
fail=0
if grep -qE '^nav:' "$cfg"; then echo "FAIL: nav: key present"; fail=1; fi
for p in search awesome-pages; do
  if ! grep -qE "^  - ${p}\s*$" "$cfg"; then echo "FAIL: plugin $p missing"; fail=1; fi
done
if ! grep -qE '^plugins:' "$cfg"; then echo "FAIL: plugins: missing"; fail=1; fi
[ "$fail" -eq 0 ] && echo "OK"
exit "$fail"
