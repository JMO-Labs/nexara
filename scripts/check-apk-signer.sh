#!/usr/bin/env bash
##
# @file scripts/check-apk-signer.sh
# @brief Assert an APK is signed by a certificate whose DN contains a string (nexara#363).
#        Uses apksigner (v1-v3 schemes) when found, else keytool (v1 jar signature).
# @param $1 Path to the APK.
# @param $2 Substring expected in the signer DN, e.g. "CN=ci" or "CN=Android Debug".
# @return 0 when the signer matches.
##
set -euo pipefail
apk=${1:?apk path required}
want=${2:?expected DN substring required}
signer=""
for d in "${ANDROID_HOME:-}" "${ANDROID_SDK_ROOT:-}"; do
  [ -n "$d" ] || continue
  cand=$(ls -d "$d"/build-tools/*/apksigner 2>/dev/null | sort -V | tail -1 || true)
  [ -n "$cand" ] && { signer=$cand; break; }
done
if [ -n "$signer" ]; then
  certs=$("$signer" verify --print-certs "$apk")
else
  certs=$(keytool -printcert -jarfile "$apk")
fi
# Match the DN exactly up to a separator so "CN=ci" does not match "CN=ci2".
if grep -qE "(^|[ :])${want}(,|$)" <<<"$certs"; then
  echo "OK: $apk signed by $want"
else
  echo "FAIL: $apk not signed by $want"; echo "$certs"; exit 1
fi
