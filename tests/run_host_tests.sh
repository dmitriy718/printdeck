#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd -- "${script_dir}/.." && pwd)"
test_build_dir="$(mktemp -d)"
trap 'rm -rf -- "${test_build_dir}"' EXIT

cc \
    -std=c11 \
    -Wall \
    -Wextra \
    -Werror \
    -include "${project_dir}/tests/host/compat.h" \
    -I"${project_dir}/tests/host" \
    -I"${project_dir}/components/nh_core/include" \
    -I"${project_dir}/components/nh_printer/private" \
    -I"${project_dir}/managed_components/espressif__cjson/cJSON" \
    "${project_dir}/tests/host/compat.c" \
    "${project_dir}/managed_components/espressif__cjson/cJSON/cJSON.c" \
    "${project_dir}/components/nh_printer/src/nh_printer_protocol.c" \
    "${project_dir}/tests/host/test_printer_protocol.c" \
    -lm \
    -o "${test_build_dir}/test_printer_protocol"

"${test_build_dir}/test_printer_protocol"
python3 "${project_dir}/tests/review_invariants.py"
