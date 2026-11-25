#!/bin/sh
# Build dist/dev.nexara.echo-<version>.tar.gz (manifest + echo.py at the tar root); print sha256.
set -eu
cd "$(dirname "$0")"
v=$(sed -n 's/^version *= *"\(.*\)"/\1/p' nexara-plugin.toml | head -1)
out="dist/dev.nexara.echo-$v.tar.gz"
mkdir -p dist
tar -czf "$out" --owner=0 --group=0 nexara-plugin.toml echo.py
echo "$out"
sha256sum "$out"
