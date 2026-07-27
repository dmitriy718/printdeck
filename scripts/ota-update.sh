#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <controller-ip>"
    exit 2
fi

controller_ip="$1"
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd -- "${script_dir}/.." && pwd)"
firmware="${project_dir}/build/nova_horizon_controller.bin"
fingerprint_file="${project_dir}/security/SIGNING_KEY_FINGERPRINT.txt"
expected_version="$(
    sed -n 's/^set(PROJECT_VER "\([^"]*\)")/\1/p' \
        "${project_dir}/CMakeLists.txt"
)"

if ! python3 - "${controller_ip}" <<'PY'
import ipaddress
import sys

try:
    address = ipaddress.ip_address(sys.argv[1])
except ValueError as exc:
    raise SystemExit(f"Invalid controller IP address: {exc}")
if address.version != 4:
    raise SystemExit("Only an explicit private IPv4 controller address is supported")
if (
    not address.is_private
    or address.is_loopback
    or address.is_link_local
    or address.is_multicast
    or address.is_unspecified
):
    raise SystemExit("Refusing a non-private or special-purpose target address")
PY
then
    exit 2
fi

if [[ ! -f "${firmware}" ]]; then
    echo "Firmware image not found. Run: source scripts/idf-env.sh && idf.py build"
    exit 1
fi

if ! command -v espsecure >/dev/null 2>&1; then
    # shellcheck source=scripts/idf-env.sh
    source "${script_dir}/idf-env.sh" >/dev/null
fi
if ! signature_info="$(espsecure signature-info-v2 "${firmware}" 2>&1)"; then
    echo "Refusing unsigned firmware: ${firmware}"
    echo "Run scripts/setup-signing-key.sh, rebuild, and inspect the build."
    exit 1
fi
expected_digest="$(
    sed -n 's/^ESP Secure Boot v2 public-key digest: //p' "${fingerprint_file}"
)"
actual_digest="$(
    sed -n 's/^Public key digest for block 0: //p' <<<"${signature_info}" |
        tr -d ' '
)"
if [[ -z "${expected_digest}" || -z "${expected_version}" ||
      "${actual_digest}" != "${expected_digest}" ]]; then
    echo "Refusing firmware signed by an unexpected key."
    echo "Expected digest: ${expected_digest:-missing}"
    echo "Image digest:    ${actual_digest:-missing}"
    exit 1
fi

if ! status_response="$(
    curl \
        --silent \
        --show-error \
        --connect-timeout 5 \
        --max-time 10 \
        --proto '=http' \
        --write-out $'\n%{http_code}' \
        "http://${controller_ip}/api/v1/ota"
)"; then
    echo "Could not reach the controller status endpoint."
    exit 1
fi
status_code="${status_response##*$'\n'}"
status_body="${status_response%$'\n'*}"
if [[ "${status_code}" != "200" ]]; then
    echo "Controller status request returned HTTP ${status_code}."
    exit 1
fi
if ! status_values="$(
    python3 -c '
import json, sys
data = json.load(sys.stdin)
if data.get("service") != "nova-horizon-ota":
    raise SystemExit("target is not the Nova Horizon OTA service")
window = data.get("window_seconds")
if not isinstance(window, int) or window <= 0:
    raise SystemExit("physical OTA window is closed")
print(data.get("version", "unknown"), window)
' <<<"${status_body}"
)"; then
    echo "Refusing upload: target identity or physical window check failed."
    echo "On the controller, open System and tap ENABLE OTA FOR 5 MINUTES."
    exit 1
fi
read -r current_version window_seconds <<<"${status_values}"

echo "Uploading $(basename -- "${firmware}") to ${controller_ip}..."
echo "Controller ${current_version}; authorized window ${window_seconds}s."

diagnose_upload_disconnect() {
    echo "Checking the controller state before any retry..."
    for _attempt in {1..15}; do
        sleep 2
        if returned_status="$(
            curl \
                --silent \
                --show-error \
                --connect-timeout 2 \
                --max-time 3 \
                --proto '=http' \
                "http://${controller_ip}/api/v1/ota" 2>/dev/null
        )" &&
           state_values="$(
               python3 -c '
import json, sys
data = json.load(sys.stdin)
if data.get("service") != "nova-horizon-ota":
    raise SystemExit(1)
version = data.get("version", "unknown")
reset = data.get("reset_reason", "unknown")
partition = data.get("partition", "unknown")
print(version, reset, partition)
' <<<"${returned_status}"
           )"; then
            read -r returned_version reset_reason running_partition \
                <<<"${state_values}"
            echo "Controller returned on v${returned_version}, partition" \
                "${running_partition}, reset reason ${reset_reason}."
            if [[ "${returned_version}" == "${expected_version}" ]]; then
                echo "The expected version is running, but the required" \
                    "verified-success response was lost; treating this run" \
                    "as unconfirmed."
            else
                echo "The requested update was not selected. Do not retry" \
                    "blindly; diagnose the reported reset first."
            fi
            return
        fi
    done
    echo "The controller did not return to its status endpoint within 30 seconds."
}

if ! upload_response="$(
    curl \
        --silent \
        --show-error \
        --connect-timeout 5 \
        --max-time 180 \
        --proto '=http' \
        --header "Expect:" \
        --header "Content-Type: application/octet-stream" \
        --data-binary "@${firmware}" \
        --write-out $'\n%{http_code}' \
        "http://${controller_ip}/api/v1/ota"
)"; then
    echo "Firmware upload failed."
    diagnose_upload_disconnect
    exit 1
fi
upload_code="${upload_response##*$'\n'}"
upload_body="${upload_response%$'\n'*}"
if [[ "${upload_code}" != "200" ]]; then
    echo "Firmware upload returned HTTP ${upload_code}: ${upload_body}"
    exit 1
fi
if ! python3 -c '
import json, sys
data = json.load(sys.stdin)
if data.get("ok") is not True or data.get("message") != "verified; restarting":
    raise SystemExit("unexpected OTA success response")
' <<<"${upload_body}"; then
    echo "The target did not confirm a verified Nova Horizon update."
    exit 1
fi

echo "Upload accepted and verified. Waiting for controller v${expected_version}..."
for _attempt in {1..20}; do
    sleep 2
    if returned_status="$(
        curl \
            --silent \
            --show-error \
            --connect-timeout 2 \
            --max-time 3 \
            --proto '=http' \
            "http://${controller_ip}/api/v1/ota" 2>/dev/null
    )" &&
       python3 -c '
import json, sys
data = json.load(sys.stdin)
expected = sys.argv[1]
if data.get("service") != "nova-horizon-ota" or data.get("version") != expected:
    raise SystemExit(1)
' "${expected_version}" <<<"${returned_status}"; then
        echo "Controller returned on v${expected_version}; OTA verified."
        exit 0
    fi
done

echo "The upload was accepted, but v${expected_version} did not return in time."
exit 1
