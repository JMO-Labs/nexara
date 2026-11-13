#!/usr/bin/env bash
##
# @file scripts/test-wq-ci-integration.sh
# @brief Tests scripts/wq-ci-integration.sh using stub docker/pg_isready/pytest.
##
set -uo pipefail
S="$(cd "$(dirname "$0")" && pwd)/wq-ci-integration.sh"
fail=0
mk() { T=$(mktemp -d); mkdir "$T/bin"; LOG="$T/log"; : >"$LOG"
  printf '#!/bin/sh\necho "docker $*" >>%s\n' "$LOG" >"$T/bin/docker"
  printf '#!/bin/sh\nexit 0\n' >"$T/bin/pg_isready"
  printf '#!/bin/sh\necho "pytest $*" >>%s\nexit ${PYTEST_RC:-0}\n' "$LOG" >"$T/bin/pytest"
  chmod +x "$T"/bin/*; }
ok() { [ "$1" = 0 ] && echo "PASS $2" || { echo "FAIL $2"; fail=1; }; }
# stubs live in an isolated dir; keep /usr/bin:/bin for coreutils only
BASE=/usr/bin:/bin
mk; PATH="$T/bin:$BASE" PYTEST_BIN="$T/bin/pytest" bash "$S" >/dev/null 2>&1; rc=$?
ok $rc "success path"
grep -q "docker run -d --name nexara-ci-pg" "$LOG"; ok $? "starts postgres"
grep -q "docker run -d --name nexara-ci-valkey" "$LOG"; ok $? "starts valkey"
grep -q "pytest tests/integration .*--cov-append" "$LOG"; ok $? "runs integration w/ cov-append"
grep -q "docker rm -f nexara-ci-pg" "$LOG"; ok $? "cleans up on success"
mk; PYTEST_RC=1 PATH="$T/bin:$BASE" PYTEST_BIN="$T/bin/pytest" bash "$S" >/dev/null 2>&1; rc=$?
[ $rc -ne 0 ]; ok $? "propagates pytest failure"
grep -q "docker rm -f nexara-ci-pg" "$LOG"; ok $? "cleans up on failure"
mk; rm "$T/bin/docker"; CI=true PATH="$T/bin:$BASE" PYTEST_BIN="$T/bin/pytest" bash "$S" >/dev/null 2>&1; rc=$?
[ $rc -ne 0 ]; ok $? "no docker + CI fails"
mk; rm "$T/bin/docker"; env -u CI PATH="$T/bin:$BASE" PYTEST_BIN="$T/bin/pytest" bash "$S" >/dev/null 2>&1; rc=$?
ok $rc "no docker locally skips"
exit $fail
