#!/usr/bin/env bash
##
# @file scripts/test-deployment-docs.sh
# @brief Checks the deployment docs set: files exist, are linked from the
#        guide, are in the awesome-pages nav, and stay under 400 lines.
# @return 0 when all checks pass.
##
set -u
root="$(cd "$(dirname "$0")/.." && pwd)"
d="$root/docs/docs/deployment"
pages=(deployment-guide docker-compose kubernetes security troubleshooting monitoring unraid)
fail=0
for p in "${pages[@]}"; do
  f="$d/$p.md"
  [ -f "$f" ] || { echo "FAIL: missing $p.md"; fail=1; continue; }
  [ "$(wc -l <"$f")" -lt 400 ] || { echo "FAIL: $p.md >= 400 lines"; fail=1; }
  [ "$p" = deployment-guide ] && continue
  grep -q "($p.md)" "$d/deployment-guide.md" 2>/dev/null || { echo "FAIL: guide does not link $p.md"; fail=1; }
  grep -qE "^  - $p.md\s*$" "$d/.pages" || { echo "FAIL: $p.md not in deployment/.pages"; fail=1; }
done
grep -qE "^  - deployment-guide.md\s*$" "$d/.pages" || { echo "FAIL: guide not in nav"; fail=1; }
[ ! -f "$root/docs/docs/deployment.md" ] || { echo "FAIL: old deployment.md still present"; fail=1; }
[ "$fail" -eq 0 ] && echo OK
exit "$fail"
