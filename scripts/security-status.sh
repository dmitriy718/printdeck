#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 </dev/ttyACM#>"
    exit 2
fi

port="$1"
if [[ ! "${port}" =~ ^/dev/ttyACM[0-9]+$ ]]; then
    echo "Refusing unexpected serial target: ${port}"
    echo "Expected an explicit /dev/ttyACM# device."
    exit 2
fi
if [[ ! -c "${port}" ]]; then
    echo "Serial device is not present: ${port}"
    exit 1
fi

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if ! command -v esptool >/dev/null 2>&1 ||
   ! command -v espefuse >/dev/null 2>&1; then
    # shellcheck source=scripts/idf-env.sh
    source "${script_dir}/idf-env.sh" >/dev/null
fi

echo "Read-only ESP32-P4 security report for ${port}"
esptool --chip esp32p4 --port "${port}" get-security-info
espefuse --chip esp32p4 --port "${port}" summary
