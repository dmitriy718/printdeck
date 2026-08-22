# PrintDeck 1.0.0 — Integrated Source Release

Version: 1.0.0
Source state: All seven recommendation gates integrated
Hardware state: Not deployed or hardware-verified

## Included feature gates

1. HMS/error and notification center.
2. AMS/material visibility and local catalog.
3. Print history, estimates, maintenance, export, backup, and retention.
4. Bounded local 3MF library, previews, favorites/search, and confirmed queue.
5. Bounded fleet registry, attention view, material lookup, and capabilities.
6. Sequence-keyed safe command framework and typed future-command bounds.
7. Authenticated, local-first, notify-only AI sidecar contract.

The component-level behavior and qualification boundaries are documented in
the seven preceding feature documents. v1.0.0 does not silently relax any of
those boundaries.

## Deliberately disabled or incomplete on hardware

- No v0.8.0–v1.0.0 image has been deployed.
- File FTPS upload and printer-side print start are unreachable.
- Motion, fan, heat, speed, calibration, and object-skip writes are unsupported.
- Acknowledged/observed/timed-out command states await response fixtures.
- The fleet registry supports four records, but one MQTT/camera transport is
  active at a time.
- AI has no compiled key, listener, cloud route, model, automatic cancel, or
  automatic power-off. Auto-pause is off.
- Controller-SD workflows and new touch surfaces await physical regression.

## Release verification

The final verification runs the complete sanitizer-backed host suite,
repository safety/release invariants, ShellCheck, Python compilation, Markdown
link checks, whitespace checks, a fresh signed ESP32-P4 build, RSA identity
inspection, and image checksum/hash inspection. Exact results and artifact hash
are:

- 30 sanitizer-backed host cases/groups: passed.
- 41 repository/release/documentation invariants: passed.
- ShellCheck, Python compilation, maintained Markdown links, and
  `git diff --check`: passed.
- Fresh ESP-IDF 6.0.2 signed build: passed for ESP32-P4 with 16 MiB flash.
- RSA signature: valid and matched the expected public-key digest.
- Image checksum and validation hash: valid.
- Signed image size: 1,839,104 bytes; 71% of either 6 MiB slot remains free.
- Signed image SHA-256:
  `d72466447797b66a786a3ed90d8655eb1950e62de54f955136825eb758fbc4c4`.
- No firmware was deployed, no serial monitor/reset was used, neither SD card
  was accessed, and no printer command/profile mutation occurred.
