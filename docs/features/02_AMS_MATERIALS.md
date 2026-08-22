# Feature Gate 2 — AMS and Material Command Center

Version: 0.8.1
Recommendation: AMS and material command center
Source state: Implemented; double-verified
Hardware state: Not deployed or hardware-verified

## Delivered behavior

- Models up to four AMS units and 16 internal trays as bounded collections.
- Models the external spool separately.
- Parses unit ID, humidity index, temperature, tray ID, material, RGBA color,
  profile ID, RFID presence, remaining percentage, and nozzle range.
- Preserves AMS state across partial MQTT deltas that omit AMS fields.
- Replaces the collection only when an explicit `ams.ams` array is observed.
- Rejects overlong strings, invalid colors, invalid percentages, and excess
  units/trays without writing outside fixed storage.
- Raises material-risk alerts when the printer-reported humidity index is 4 or
  higher and resolves them when current AMS telemetry no longer reports risk.
- Labels humidity as an index rather than incorrectly claiming relative
  humidity.
- Shows a four-slot glance view and a scrollable read-only material drawer.
- Adds a checksummed, versioned NVS spool catalog with 16 bounded entries,
  cost/kg, nominal weight, dry-state timestamp, color, material, and AMS
  compatibility.
- Makes catalog writes transactional in memory: a failed NVS commit restores
  the prior catalog.

## Safety boundary

This gate is read-only toward the printer. It does not send RFID, slot-edit,
load, unload, or drying commands. Those writes depend on the acknowledged
typed-command/capability framework and exact P1S hardware validation in feature
gate 6. Displaying unavailable controls would be misleading, so none are
enabled here.

## Partial-report rules

| Input | Result |
|---|---|
| Delta without `ams` or `vt_tray` | Existing material snapshot retained |
| Explicit `ams.ams: []` | AMS unit/tray collection cleared |
| More than four units | First four valid bounded units retained |
| More than 16 trays | Excess entries ignored |
| Empty tray containing only `id` | Preserved as an empty physical slot |
| Invalid RGBA or remaining value | Field remains unknown |
| External `vt_tray` | Stored in the dedicated external-spool slot |
| Humidity index ≥ 4 | Local material-risk alert |

## Local catalog

The `nh_material` NVS namespace stores one schema-v1 record under
`catalog_v1`. The record includes a CRC32 over its schema and payload. Invalid
schema, size, count, entry, or CRC fails closed and does not silently overwrite
the stored record.

Catalog APIs support snapshot, bounded upsert, and removal. They are ready for
history/cost integration in gate 3 and future UI editing after input workflows
are designed.

## Verification contract

Verification 1 covers:

- one AMS with empty and populated trays;
- humidity/temperature and material-risk alert;
- partial-delta preservation;
- explicit collection clear;
- multiple-unit bound;
- external spool;
- invalid color and remaining bounds;
- existing HMS/parser regression suite.

Verification 2 requires the full signed ESP32-P4 build, image/signature
inspection, repository invariants, and static/format checks. Real P1S AMS,
no-AMS, multi-AMS, mid-print swap, and disconnect behavior remain hardware
qualification items.

## Verification results

- Verification 1: passed 18 sanitizer-backed protocol cases and 36
  repository/release invariants.
- Verification 2: passed a separate signed ESP32-P4 build, RSA identity
  inspection, image checksum/hash validation, ShellCheck, Python compilation,
  maintained-link checks, and whitespace validation.
- Signed image size: 1,773,568 bytes; 72% of either 6 MiB application slot
  remains free.
- Signed image SHA-256:
  `324eb08b60bbb37aa3939ef4042c9c4df3d28322088b49dcc6f0d3f25f8fd703`.
- No firmware was deployed. Hardware qualification remains pending.
