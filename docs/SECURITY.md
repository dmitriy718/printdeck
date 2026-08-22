# PrintDeck Security

This document describes the security properties of the current PrintDeck
firmware, its trust boundaries, known gaps, and the rules for handling
credentials and signing material.

## Security summary

| Area | Current control | Important limitation |
|---|---|---|
| Printer telemetry/commands | MQTT over TLS; Bambu CA plus configured printer serial identity | Depends on correct local profile and printer interface behavior |
| Camera | Local printer TLS stream using the persisted authenticated profile | Credentials must be available in controller memory |
| OTA authenticity | RSA-3072 signed application verification | Hardware Secure Boot is not enabled |
| OTA authorization | Five-minute, single-use window opened on the controller UI | Status/upload service uses plaintext HTTP on the LAN |
| Recovery | Native USB remains available | Physical access can replace firmware |
| Credential storage | Bounded NVS values and sensitive-buffer clearing | NVS is not encrypted at rest |
| Secrets in source control | Private key directory ignored; public fingerprints committed | Backup and workstation handling remain operational responsibilities |

PrintDeck is designed for a trusted local network. It is not hardened for
direct exposure to the internet or an untrusted shared LAN.

## Trust model

The controller trusts:

- locally entered Wi-Fi credentials;
- a locally entered P1S IP address, serial, and LAN access code;
- Bambu's pinned certificate authority for the printer session;
- the configured P1S serial as the expected MQTT certificate common name;
- application images signed by the project's RSA-3072 key;
- physical access to the controller and its native USB recovery port.

The current Horizon Services LLC backend/domain is roadmap context only. No
Horizon cloud service is required or trusted by this firmware.

## Printer connection security

Printer MQTT uses `mqtts://PRINTER_IP:8883`, username `bblp`, and the configured
LAN access code. The client verifies the Bambu trust anchor and the configured
serial identity.

The camera uses the local printer profile. It does not intentionally weaken
certificate checks after a failure. The profile becomes persistent only after
an authenticated printer connection succeeds, and a definitively rejected
replacement can restore the previous valid profile.

Some printer firmware requires LAN-only or Developer Mode for local
integration. That is a printer-side security and support decision. PrintDeck
must not represent enabling that mode as risk-free.

## Persistent data

The default NVS partition currently stores:

| Namespace | Key | Data |
|---|---|---|
| `nh_wifi` | `ssid` | Wi-Fi network name |
| `nh_wifi` | `password` | Wi-Fi password or raw PSK |
| `nh_p1s` | `ip` | Printer IPv4 address |
| `nh_p1s` | `serial` | Printer device serial |
| `nh_p1s` | `code` | Printer LAN access code |
| `nh_settings` | `timezone` | Timezone preset index |

These values are plaintext at rest. File-system permissions on a developer
machine do not protect values already written to controller flash.

Sensitive UI fields are masked and temporary buffers are cleared where
practical, but this does not make credentials immune to physical extraction,
memory inspection, or an untrusted replacement firmware.

## OTA trust and authorization

The firmware enables signed-app verification without hardware Secure Boot.
Supported OTA images must be signed with the private key corresponding to the
committed project identity.

The OTA HTTP server:

- listens on local port 80;
- exposes read-only status through `GET /api/v1/ota`;
- accepts an application image through `POST /api/v1/ota`;
- rejects uploads until the System-page control opens a 300-second window;
- consumes that window when an upload begins;
- limits repeated receive timeouts;
- relies on ESP-IDF validation and the embedded signing key;
- uses rollback until the new application survives its validation interval.

The host updater adds target-side safeguards: literal RFC1918 address, expected
service identity, open window, image-key digest, exact success response, and
returned-version checks. These controls reduce accidental or misdirected
uploads; they do not encrypt the HTTP exchange.

Never port-forward the OTA service, publish it through a reverse proxy, or
place it on a hostile network.

## Signing-key handling

Private key:

```text
security/private/ota_signing_key.pem
```

It must:

- remain excluded from Git;
- have restrictive local permissions;
- be backed up in a controlled, offline-capable location;
- never appear in logs, screenshots, tickets, or chat messages;
- be restored from backup rather than replaced for deployed controllers.

Public identity metadata in `security/SIGNING_KEY_FINGERPRINT.txt` is not
secret. `scripts/setup-signing-key.sh` verifies that the local private key
matches it and refuses to silently introduce a new identity.

Loss of the private key blocks future supported OTA updates to controllers that
trust it. Because hardware Secure Boot remains disabled, a deliberate wired
recovery is still possible.

## Hardware Secure Boot and encrypted NVS

Routine builds must not enable Secure Boot, flash encryption, or HMAC-derived
NVS encryption and must not burn eFuses. Those changes are irreversible or
materially alter the native USB recovery path on this target.

The required decision process is maintained in
[Security Provisioning](SECURITY_PROVISIONING.md). No repository script burns
eFuses.

## Logging and disclosure

Do not record:

- Wi-Fi passwords;
- LAN access codes;
- private signing-key content;
- full memory dumps without controlled handling.

Minimize or redact:

- SSIDs;
- IP addresses;
- printer/controller serials;
- job names;
- camera images;
- precise location/time metadata.

A coredump may contain in-memory credentials. Handle it as confidential,
restrict access, and destroy unneeded copies through an approved process.

## Known security gaps

- credentials are plaintext in NVS;
- the OTA status and upload channel is HTTP rather than HTTPS;
- native USB plus physical access can replace firmware;
- there is no per-device OTA key or fleet identity;
- there is no role-based access control or user authentication;
- no automated secret scan or dependency-vulnerability pipeline is documented;
- local printer integration inherits changes to Bambu firmware and Developer
  Mode policy;
- automatic NVS erase on certain initialization errors can remove settings.

## Security change checklist

1. Define the attacker and asset being protected.
2. Preserve fail-closed certificate and signature behavior.
3. Avoid adding credentials to URLs, logs, telemetry, fixtures, or source.
4. Add negative tests for malformed, unauthorized, stale, and replayed inputs.
5. Confirm USB recovery implications.
6. Treat any eFuse operation as separately authorized, device-specific, and
   irreversible.
7. Update this document, the provisioning policy, tests, and changelog.

## Related documents

- [Security Provisioning](SECURITY_PROVISIONING.md)
- [Architecture](ARCHITECTURE.md)
- [Operations](OPERATIONS.md)
- [Release Process](RELEASE_PROCESS.md)

