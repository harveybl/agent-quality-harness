#!/usr/bin/env bash
set -euo pipefail

failures=0
check() {
  local label="$1"
  shift
  if "$@" >/dev/null 2>&1; then
    printf 'PASS %s\n' "$label"
  else
    printf 'FAIL %s\n' "$label"
    failures=$((failures + 1))
  fi
}

check "Ubuntu 24.04" sh -c 'test -r /etc/os-release && grep -q "VERSION_ID=\"24.04\"" /etc/os-release'
check "NVIDIA driver" nvidia-smi
check "Docker" docker version
check "Docker Compose" docker compose version
check "NVIDIA container runtime" sh -c 'docker info --format "{{json .Runtimes}}" | grep -qi nvidia'

exit "$failures"

