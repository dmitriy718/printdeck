#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd -- "${script_dir}/.." && pwd)"
key_dir="${project_dir}/security/private"
key_file="${key_dir}/ota_signing_key.pem"
fingerprint_file="${project_dir}/security/SIGNING_KEY_FINGERPRINT.txt"
expected_fingerprint="$(
    sed -n 's/^Fingerprint: //p' "${fingerprint_file}"
)"

if [[ -f "${key_file}" ]]; then
    actual_fingerprint="$(
        openssl pkey -in "${key_file}" -pubout -outform DER 2>/dev/null |
            sha256sum |
            awk '{print $1}'
    )"
    if [[ "${actual_fingerprint}" != "${expected_fingerprint}" ]]; then
        echo "Existing OTA signing key does not match the committed fingerprint."
        echo "Refusing to replace or use it automatically."
        exit 1
    fi
    echo "Signing key exists and matches the committed public fingerprint."
    exit 0
fi

echo "The project signing identity already exists, but its private key is absent."
echo "Restore security/private/ota_signing_key.pem from the secure backup."
echo "A newly generated key will not update controllers that trust this identity."
exit 1
