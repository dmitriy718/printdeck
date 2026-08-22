# Feature Gate 5 — Fleet Dashboard and Capability Layer

Version: 0.9.1
Recommendation: Multi-printer fleet dashboard and capability layer
Source state: Implemented; double-verified
Hardware state: Not deployed or hardware-verified

## Delivered behavior

- Defines four bounded printer-session records with stable serial-derived IDs,
  fixed strings, connection/job state, alerts, progress, material, generation,
  capabilities, identity status, and active-transport status.
- Persists explicitly identity-confirmed profiles as a schema-v1 CRC32-sealed
  NVS blob and rolls RAM back if persistence fails.
- Keeps an observed active printer visible without falsely marking its
  identity confirmed or persisting it as a confirmed profile.
- Orders fleet copies by error, paused, finishing soon, printing, idle, then
  offline.
- Adds an attention count and Dashboard fleet drawer.
- Exposes bounded material-to-printer search and explicit active focus.
- Requires the exact phrase `REMOVE PRINTER` for profile removal.

## Capability policy

Unknown model or missing firmware yields zero capabilities. P1S rows currently
advertise only read capabilities (telemetry, camera, AMS, HMS, and files).
Basic commands, file writes, object skip, temperature, and motion remain absent
until an exact model/firmware row passes hardware qualification.

The existing single active MQTT/camera transport remains the only live-detail
session. The registry/session boundary supports four profiles, but background
connections and focus switching are not represented as complete until
reconnect-storm, memory, wrong-IP identity, and simultaneous-delta tests pass.
This distinction is shown in the UI as `ACTIVE`, `OBSERVED ONLY`, or
`IDENTITY CONFIRMED`.

## Verification contract

Verification 1 exercises capability fail-closed behavior and attention
ordering under sanitizers, plus repository invariants and static checks.
Verification 2 is a signed ESP32-P4 build and independent image/signature/hash
inspection.

Profile onboarding/removal on real NVS, simultaneous live sessions, printer
discovery, focus switching, camera arbitration, and load testing remain
hardware/product qualification items.

## Verification results

- Verification 1 passed 26 sanitizer-backed host cases/groups and 39
  repository/release invariants, plus static and documentation checks.
- Verification 2 passed signed ESP32-P4 build, RSA identity, checksum, image
  validation hash, and SHA-256 inspection.
- Signed image size: 1,839,104 bytes; 71% of either application slot remains
  free.
- Signed image SHA-256:
  `163b847d4b6bc6fefe28f795e3184bf00eadd63d03778ce87c480cd009a3f4df`.
- No firmware was deployed and no hardware was accessed.
