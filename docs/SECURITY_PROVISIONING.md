# Controller security provisioning

This specialized policy is part of the maintained
[PrintDeck security documentation](SECURITY.md).

## Current release policy

PrintDeck firmware uses RSA-3072 signed-app verification for LAN OTA
updates without enabling hardware Secure Boot. This is a reversible ESP-IDF
mode: an application installed through the OTA service must match the public
key embedded in the running application, while the native USB ROM recovery
path remains available.

The private key is generated locally at
`security/private/ota_signing_key.pem`, is excluded from Git, and must be
backed up securely. Losing it prevents further signed OTA updates from a
signed-enforcement application. Because hardware Secure Boot remains disabled,
a deliberate wired recovery flash is still possible.

The non-secret SHA-256 fingerprint of the public key is committed at
`security/SIGNING_KEY_FINGERPRINT.txt`. The setup script refuses to accept a
different private key silently.

Verify that the locally restored key matches the project identity:

```sh
scripts/setup-signing-key.sh
```

If the key is absent, the script refuses to generate a replacement because a
random new key cannot update controllers that already trust the committed
identity. Restore the original key from the secure backup instead.

Before any wired security work, inspect the exact attached controller with the
read-only command:

```sh
scripts/security-status.sh /dev/ttyACM0
```

## Credential encryption boundary

Wi-Fi credentials and the Bambu Lab LAN access code are currently stored in
the default NVS partition. TLS protects printer traffic in transit, but these
values are not yet encrypted at rest.

On ESP32-P4, genuine NVS encryption requires a device secret protected by
either flash encryption or the HMAC peripheral. The HMAC option permanently
programs an eFuse key block. Enabling hardware Secure Boot or flash encryption
also changes recovery behavior; ESP-IDF documents that those features disable
the ROM USB-OTG serial-emulation/DFU path used by this board.

For those reasons, routine builds and OTA updates must not:

- enable `CONFIG_NVS_ENCRYPTION`;
- select an HMAC eFuse key block;
- enable `CONFIG_SECURE_BOOT`;
- enable `CONFIG_SECURE_FLASH_ENC_ENABLED`; or
- execute any `espefuse` burn command.

## Required production decision

Encrypted credential storage is intentionally gated until all of the following
have been completed:

1. Confirm a second recovery/programming path that remains available after the
   ROM USB-OTG path is disabled, or explicitly accept losing that path.
2. Read and archive the controller's current eFuse summary.
3. Choose a verified empty eFuse key block for the HMAC key.
4. Decide whether existing Wi-Fi and printer credentials will be re-entered
   after provisioning or migrated through a separately reviewed process.
5. Back up the OTA signing key and a known-good recovery image.
6. Review the exact generated eFuse commands and obtain Dima's explicit
   approval for those commands and that one physical controller.

No script in this repository burns eFuses. That omission is deliberate. A
future production-provisioning tool must default to a dry run, identify one
serial device exactly, print every irreversible change, and require a
device-specific confirmation before execution.

## Source basis

This policy follows the ESP-IDF 6.0.2 documentation shipped in `.tools/esp-idf`:

- `docs/en/api-reference/system/ota.rst` describes signed OTA verification
  without hardware Secure Boot.
- `docs/en/api-reference/storage/nvs_encryption.rst` describes HMAC-derived
  encrypted NVS and its eFuse key requirement.
- `docs/en/security/secure-boot-v2.rst` describes the USB-OTG restriction after
  hardware Secure Boot or flash encryption is enabled.
