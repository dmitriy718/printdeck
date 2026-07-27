#!/usr/bin/env bash
set -e

if [[ -n "${ZSH_VERSION:-}" ]]; then
    # shellcheck disable=SC2296 # guarded zsh-only current-script expansion
    NH_ENV_SCRIPT_PATH="${(%):-%x}"
else
    NH_ENV_SCRIPT_PATH="${BASH_SOURCE[0]}"
fi

NH_PROJECT_DIR="$(cd "$(dirname "${NH_ENV_SCRIPT_PATH}")/.." && pwd)"
export IDF_TOOLS_PATH="${NH_PROJECT_DIR}/.tools/espressif"

if [[ ! -f "${NH_PROJECT_DIR}/.tools/esp-idf/export.sh" ]]; then
    echo "ESP-IDF is not installed in ${NH_PROJECT_DIR}/.tools/esp-idf" >&2
    exit 1
fi

# shellcheck source=/dev/null
source "${NH_PROJECT_DIR}/.tools/esp-idf/export.sh"
