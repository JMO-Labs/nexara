#!/usr/bin/env bash
##
# @file scripts/test-mobile-ci.sh
# @brief Static checks for the mobile CI/release pipeline (nexara#363).
#        Verifies the single Flutter pin, signing fallback, AAB job, Fastlane lanes, docs.
# @return 0 when all checks pass.
##
set -u
cd "$(dirname "$0")/.."
fail=0
chk() { if ! eval "$2"; then echo "FAIL: $1"; fail=1; fi; }

pin=$(tr -d '[:space:]' < mobile/.flutter-version 2>/dev/null)
chk "mobile/.flutter-version holds x.y.z" '[[ "$pin" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]'
chk "GitLab FLUTTER_VERSION matches pin" 'grep -qE "^  FLUTTER_VERSION: \"$pin\"" .gitlab/ci/variables.yml'
chk "GitLab mobile images use \$FLUTTER_VERSION" '! grep -n "flutter:stable" .gitlab/ci/*.yml'
chk "GitHub workflow reads pin file" 'grep -q "mobile/.flutter-version" wq-workflows/mobile-build.yml'
chk "wq-ci-test.sh uses pin file" 'grep -q ".flutter-version" scripts/wq-ci-test.sh && ! grep -q "\-b stable" scripts/wq-ci-test.sh'
chk "dart format in mobile lint" 'grep -qE "dart format .*--set-exit-if-changed" .gitlab/ci/test-mobile.yml'
g=mobile/android/app/build.gradle.kts
chk "gradle reads key.properties" 'grep -q "key.properties" $g'
chk "gradle reads env vars" 'grep -q "NEXARA_KEYSTORE_PASSWORD" $g'
chk "gradle falls back to debug" 'grep -q "\"debug\"" $g'
chk "AAB job tag-only + protected" 'grep -q "^build:mobile-aab:" .gitlab/ci/test-mobile.yml && grep -q "CI_COMMIT_TAG" .gitlab/ci/test-mobile.yml && grep -q "CI_COMMIT_REF_PROTECTED" .gitlab/ci/test-mobile.yml && grep -q "build appbundle" .gitlab/ci/test-mobile.yml'
chk "CI builds release unsigned fallback" 'grep -q "build apk --release" .gitlab/ci/test-mobile.yml'
chk "Fastfile has android+ios beta" 'grep -q "platform :android" mobile/fastlane/Fastfile && grep -q "platform :ios" mobile/fastlane/Fastfile && [ "$(grep -c "lane :beta" mobile/fastlane/Fastfile)" -ge 2 ]'
chk "fastlane jobs manual+protected" 'grep -q "when: manual" .gitlab/ci/test-mobile.yml && grep -q "fastlane:android-beta" .gitlab/ci/test-mobile.yml && grep -q "fastlane:ios-beta" .gitlab/ci/test-mobile.yml'
chk "wq-workflows target dir matches" '[ -d .github/workflows ] && [ -f wq-workflows/mobile-build.yml ] && grep -q "^name: mobile-build" wq-workflows/mobile-build.yml'
for v in NEXARA_KEYSTORE_BASE64 NEXARA_KEYSTORE_PASSWORD NEXARA_KEY_ALIAS NEXARA_KEY_PASSWORD PLAY_JSON_KEY_DATA APP_STORE_CONNECT_API_KEY_ID; do
  chk "README documents $v" 'grep -q "$v" mobile/README.md'
done
[ "$fail" -eq 0 ] && echo "OK"
exit "$fail"
