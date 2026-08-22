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
    -fsanitize=address,undefined \
    -fno-omit-frame-pointer \
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

cc \
    -std=c11 \
    -Wall \
    -Wextra \
    -Werror \
    -fsanitize=address,undefined \
    -fno-omit-frame-pointer \
    -I"${project_dir}/components/nh_history/private" \
    "${project_dir}/components/nh_history/src/nh_history_codec.c" \
    "${project_dir}/tests/host/test_history_codec.c" \
    -o "${test_build_dir}/test_history_codec"

"${test_build_dir}/test_history_codec"

cc \
    -std=c11 \
    -Wall \
    -Wextra \
    -Werror \
    -fsanitize=address,undefined \
    -fno-omit-frame-pointer \
    -ffunction-sections \
    -fdata-sections \
    -include "${project_dir}/tests/host/compat.h" \
    -I"${project_dir}/tests/host" \
    -I"${project_dir}/components/nh_files/private" \
    -I"${project_dir}/.tools/esp-idf/components/esp_rom/include" \
    "${project_dir}/tests/host/compat.c" \
    "${project_dir}/components/nh_files/src/nh_3mf.c" \
    "${project_dir}/tests/host/test_3mf_codec.c" \
    -Wl,--gc-sections \
    -lm \
    -o "${test_build_dir}/test_3mf_codec"

"${test_build_dir}/test_3mf_codec"

cc \
    -std=c11 \
    -Wall \
    -Wextra \
    -Werror \
    -fsanitize=address,undefined \
    -fno-omit-frame-pointer \
    -I"${project_dir}/tests/host" \
    -I"${project_dir}/components/nh_core/include" \
    -I"${project_dir}/components/nh_printer/include" \
    -I"${project_dir}/components/nh_fleet/include" \
    "${project_dir}/components/nh_fleet/src/nh_fleet_policy.c" \
    "${project_dir}/tests/host/test_fleet_policy.c" \
    -o "${test_build_dir}/test_fleet_policy"

"${test_build_dir}/test_fleet_policy"

cc \
    -std=c11 \
    -Wall \
    -Wextra \
    -Werror \
    -fsanitize=address,undefined \
    -fno-omit-frame-pointer \
    -I"${project_dir}/tests/host" \
    -I"${project_dir}/components/nh_core/include" \
    -I"${project_dir}/components/nh_printer/include" \
    "${project_dir}/components/nh_printer/src/nh_printer_policy.c" \
    "${project_dir}/tests/host/test_control_policy.c" \
    -o "${test_build_dir}/test_control_policy"

"${test_build_dir}/test_control_policy"

cc \
    -std=c11 \
    -Wall \
    -Wextra \
    -Werror \
    -fsanitize=address,undefined \
    -fno-omit-frame-pointer \
    -I"${project_dir}/tests/host" \
    -I"${project_dir}/components/nh_ai/include" \
    "${project_dir}/components/nh_ai/src/nh_ai_policy.c" \
    "${project_dir}/tests/host/test_ai_policy.c" \
    -o "${test_build_dir}/test_ai_policy"

"${test_build_dir}/test_ai_policy"

python3 "${project_dir}/tests/review_invariants.py"
