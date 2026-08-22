# PrintDeck Changelog

This changelog records the development history of the PrintDeck controller
firmware.

The project did not have Git history until July 27, 2026. Entries before commit
`d87ef46` are therefore reconstructed from preserved filesystem birth times,
build artifacts, backups, and the contemporaneous engineering review in
`Reviews/07272026_01.md`. They are labeled as reconstructed and avoid claiming
an exact commit or release time that the evidence cannot support.

Dates use the repository's working timezone at the time: America/New_York
(EDT, UTC−04:00).

## [1.0.0] - 2026-07-29 — integrated source release

### Added

- Integrated all seven independently versioned recommendation gates:
  actionable HMS, AMS/material visibility, history/analytics, local files and
  queue, fleet/capabilities, safe command results, and optional AI sidecar.
- Indexed implementation and qualification documentation for every gate.

### Safety

- This is a source/build release, not a hardware-qualified deployment.
- Unqualified printer writes and automation remain fail-closed.
- v0.7.2 remains the last deployed firmware.

### Validation

- 30 sanitizer-backed host cases/groups and 41 repository/release invariants
  passed.
- ShellCheck, Python compilation, maintained links, and whitespace checks
  passed.
- A fresh signed ESP32-P4 build passed RSA identity and image
  checksum/validation-hash inspection.
- Image size: 1,839,104 bytes; 71% of either application slot remains free.
- Signed image SHA-256:
  `d72466447797b66a786a3ed90d8655eb1950e62de54f955136825eb758fbc4c4`.
- No firmware was deployed or hardware accessed.

## [0.9.3] - 2026-07-29 — optional local AI sidecar feature gate

### Added

- Schema-v1 HMAC-SHA-256 sidecar event contract with replay/time bounds,
  printer/job/model identity, confidence, evidence hash, and suggestions.
- Bounded audit ring, user labels, job muting, camera-health gate, temporal
  smoothing, confidence threshold, and cooldown.
- Camera-page local/notify state indicator and policy fixtures.

### Safety

- No secret, cloud route, network listener, model, or automatic action is
  enabled by default.
- Auto-pause requires explicit phrase confirmation plus a qualified command
  capability; automatic cancel/power-off do not exist.
- No AI service, printer, controller SD, or firmware deployment was touched.
- 30 sanitizer-backed host cases/groups and 41 invariants passed.
- Signed image SHA-256:
  `08f12872bb12ac2c9d29a19d1debd35df0a6e1514c718f96860defd6c0ed0127`.

## [0.9.2] - 2026-07-29 — safe command framework feature gate

### Added

- Monotonic command sequence IDs and asynchronous worker `SENT`/`REJECTED`
  results shown without claiming printer acknowledgement.
- Explicit queued/sent/acknowledged/observed/rejected/timed-out result
  vocabulary.
- Typed hard bounds for future fan, motion, speed, calibration, and
  object-skip commands.

### Safety

- Newly typed writes remain unsupported and fail closed until exact
  model/firmware hardware qualification.
- Existing pause/resume/cancel/light writes are revalidated at dispatch;
  cancellation retains its destructive-action confirmation.
- No raw G-code path was added and no command was sent during this source gate.
- 28 sanitizer-backed host cases/groups and 40 invariants passed.
- Signed image SHA-256:
  `fd99fb3d7a59eefd095e4b5344032cb285927a5882fa18792f4951d8955a5799`.

## [0.9.1] - 2026-07-29 — fleet and capability feature gate

### Added

- Bounded four-profile fleet/session registry with stable identity IDs,
  attention ordering, active transport ownership, material search, and
  Dashboard fleet overview.
- Schema/CRC-protected transactional NVS persistence for explicitly confirmed
  profiles and phrase-confirmed removal.
- Fail-closed model/firmware capability policy. Current P1S entries expose
  read capabilities only; unqualified writes remain disabled.
- Sanitizer-backed fleet attention and capability fixtures.

### Safety

- Observed sessions are not silently promoted to identity-confirmed profiles.
- The existing single active MQTT/camera transport remains the only live
  detail connection pending multi-session hardware/load qualification.
- v0.7.2 remains the last deployed version.
- 26 sanitizer-backed host cases/groups and 39 invariants passed.
- Signed image SHA-256:
  `163b847d4b6bc6fefe28f795e3184bf00eadd63d03778ce87c480cd009a3f4df`.

## [0.9.0] - 2026-07-29 — local files and confirmed queue feature gate

### Added

- Bounded controller-SD `.3mf` index with SHA-256 identity, duplicate
  detection, favorites/recent ordering, search, compatibility metadata, and
  embedded PNG previews.
- Fail-closed 3MF ZIP parsing with member, path, method, encryption, size,
  compression-ratio, CRC32, and image-dimension limits.
- Checksummed eight-item local queue with priority, copies, cancellation,
  guarded transitions, explicit compatibility and bed-clear confirmations,
  resumable offsets, and conservative reboot recovery.
- Transactional in-memory rollback when queue/favorite persistence fails.
- Compiled, disabled-by-default implicit-FTPS adapter with certificate and
  target validation, protected data connection, immediate file-hash check,
  resumable temporary upload, and atomic remote rename.
- Files browser/detail/preview UI and dedicated feature documentation.

### Safety and validation

- Transfer and print start remain unreachable until idle-hardware
  qualification; a queue action does not imply printer acceptance.
- v0.7.2 remains the last deployed version.
- No firmware was deployed and neither printer nor controller SD was accessed.
- 24 sanitizer-backed host groups/cases and 38 repository/release invariants
  passed, followed by an independently inspected signed ESP32-P4 build.
- Image size: 1,839,104 bytes; 71% of either application slot remains free.
- Signed image SHA-256:
  `024f92ab726d300862db7d28503c305037f5f38231263e6ed3e8fd7bc30fa54a`.

## [0.8.2] - 2026-07-29 — history and analytics feature gate

### Added

- Schema-v1, CRC32-protected append-only controller-SD journal for print start,
  finish, and maintenance-reset events.
- Tail recovery that discards only an incomplete or invalid trailing record.
- Bounded recent-session cache with complete, failed, and interrupted outcomes.
- Lifetime, daily, monthly, and since-maintenance-reset counters.
- Explicitly configured material, energy, and cost estimates that are never
  represented as measured values.
- Local maintenance-due thresholds and audited resets.
- Redacted CSV/JSON exports, byte-for-byte backup, explicit atomic retention,
  and phrase-confirmed deletion APIs.
- Job-page History & Costs drawer with recent jobs and privacy-default export
  actions.
- Sanitizer-backed journal codec fixtures and feature documentation.

### Safety

- History observes telemetry and does not send printer commands.
- No automatic deletion, retention, or fabricated estimate defaults are used.
- v0.7.2 remains the last deployed version.

### Validation

- 21 sanitizer-backed host cases and 37 repository/release invariants passed.
- A separate signed ESP32-P4 build passed expected RSA identity, image
  checksum, and validation-hash inspection.
- Image size: 1,773,568 bytes; 72% of either application slot remains free.
- Signed image SHA-256:
  `be2101e6bed4a427576ed74bd383bd0c8bf635a653a245065e4266cdb253ec3c`.
- No firmware was deployed or controller SD accessed during the active print.

## [0.8.1] - 2026-07-29 — AMS/material feature gate

### Added

- Bounded collection model for four AMS units, 16 internal trays, and one
  external spool.
- Delta-aware parsing for humidity index, temperature, material, color,
  profile, RFID presence, remaining percentage, and nozzle range.
- Material-risk alerts without mislabeling the printer's humidity index as
  relative humidity.
- Read-only AMS glance cards and detailed material drawer.
- Checksummed, schema-versioned, transactional 16-entry NVS spool catalog.
- AMS fixtures and dedicated implementation documentation.

### Safety

- Printer-side RFID, slot editing, load/unload, and drying writes remain
  fail-closed until the typed command/capability gate and hardware validation.
- v0.7.2 remains the last deployed version.

### Validation

- 18 sanitizer-backed protocol cases and 36 repository/release invariants
  passed.
- A separate signed ESP32-P4 build passed RSA identity, image checksum, and
  validation-hash inspection.
- Image size: 1,773,568 bytes; 72% of either application slot remains free.
- Signed image SHA-256:
  `324eb08b60bbb37aa3939ef4042c9c4df3d28322088b49dcc6f0d3f25f8fd703`.
- Hardware qualification remains pending; the firmware was not deployed during
  the active print.

## [0.8.0] - 2026-07-29 — HMS feature gate

### Added

- Bounded 12-record HMS/print-error model with exact raw-code preservation.
- Versioned known-code table that leaves unmapped codes explicitly unknown.
- Active/resolved lifecycle, recurrence counts, timestamps, source, severity,
  and local-dismissal state.
- Delta-aware deduplication: omitted fields preserve state; explicit empty HMS
  or zero print error resolves it.
- Dashboard alert badge and active/history drawer with safe guidance and honest
  local-hide semantics.
- Sanitizer-backed HMS fixtures and dedicated implementation documentation.

### Status

- Source implementation passed both verification gates: sanitizer-backed host
  tests/repository invariants and a separate signed ESP32-P4 build/image check.
- Signed image SHA-256:
  `9baa4918e4cf487bee057fcd2ea32e49c4b5ab00ea52065ab504b9d211956730`.
- v0.7.2 remains the last deployed controller firmware.

## [0.7.3] - 2026-07-29 — source candidate, not deployed

### Fixed

- Stopped and destroyed the MQTT client before freeing its shared
  report-fragment buffer, closing a possible late-callback use-after-free
  during profile replacement or shutdown.
- Centralized pause/resume/cancel eligibility and revalidated queued actions
  against the latest printer state immediately before dispatch.
- Changed immediate UI feedback from `Accepted` to `Command queued`, avoiding a
  false claim of printer acknowledgement.
- Restricted the host OTA updater to the three explicit RFC1918 IPv4 networks
  rather than Python's broader `is_private` classification.
- Corrected camera API documentation that incorrectly described plaintext NVS
  profile data as encrypted.
- Corrected README source/deployed/partition status.

### Documentation

- Established an indexed maintained-document set covering product behavior,
  users, architecture, hardware, development, operations, release, testing,
  security, troubleshooting, and terminology.
- Added this evidence-qualified changelog dating to the earliest defensible
  project-start date.
- Preserved the v0.7.2 outreach package as a historical deployed snapshot
  instead of treating it as current engineering documentation.

### Validation

- 11 production parser cases passed with AddressSanitizer and
  UndefinedBehaviorSanitizer.
- 32 repository/release invariants passed before the documentation expansion.
- ShellCheck, Python compilation, whitespace validation, and GCC `-fanalyzer`
  over 12 first-party C translation units passed.
- Signed ESP32-P4 build passed with ESP-IDF 6.0.2.
- Candidate image size: 1,773,568 bytes (`0x1b1000`).
- Candidate SHA-256:
  `86dd1a8642f1519766c5ac53eb232f63a69de3892cee42f4da48954ad509b7a9`.

### Remaining qualification

- v0.7.3 has not been deployed or hardware-regressed.
- Queue saturation, plaintext NVS credentials, C6/host version mismatch, the
  prior brownout, and NVS recovery policy remain open.

## [0.7.2] - 2026-07-28 — deployed

Prepared on July 27 and deployed by guarded OTA on July 28.

### Changed

- Renamed the controller product from the provisional Nova Horizon identity to
  **PrintDeck**.
- Established **Horizon Services LLC** as the parent company and retained
  `novahorizon.net` only as a planned backend/domain name.
- Renamed the build artifact/project and runtime UI, logging, MQTT client, and
  OTA service identities.
- Added controlled OTA migration from legacy `nova-horizon-ota` before upload
  to required `printdeck-ota` after restart.
- Changed the header clock to locale-independent 12-hour `h:mm AM/PM` format.
- Removed cloud/import pseudo-file rows from Files; it now states that SD status
  exists while indexing, browsing, and print start do not.
- Made Control-page explanations distinguish unsupported actions from
  print-state locks.

### Validation and deployment

- Signed image size: 1,773,568 bytes.
- Deployed from v0.7.1 by `scripts/ota-update.sh`.
- Returned on `ota_1` as `printdeck-ota` v0.7.2.
- Cleared pending rollback and remained stable through the preserved short
  health samples.
- Deployment artifact SHA-256:
  `ebc49b2d6f024beed8e162c4d04badff174b886ef444cda761a1d60e2a5c1978`.
- Git checkpoints:
  - `36b3f70` — UI truthfulness candidate;
  - `32b61a4` — PrintDeck rename;
  - `ff3940d` — deployment and handoff.

### Known limitations

- Full UI behavior, active-job control, SD-media compatibility, and long camera
  duration testing were not represented as complete.

## [0.7.1] - 2026-07-27 — deployed

### Fixed

- Corrected the SD/Wi-Fi hardware conflict using Espressif's shared-controller
  pattern: ESP-Hosted owns the P4 SDMMC controller/C6 slot 1, while the
  controller card uses native four-bit slot 0.
- Moved external-card mounting after hosted-network initialization.
- Preserved non-destructive FAT32 mounting and correct per-slot cleanup.
- Enabled the BOYA flash driver after the installed device was identified.
- Hardened OTA disconnect diagnostics so an interrupted upload reports the
  returned version, partition, and reset reason and remains failed if the exact
  success response was lost.

### Validation and deployment

- Initial v0.7.0-to-v0.7.1 OTA write reset under flash load; the updater
  correctly failed and observed return to v0.7.0.
- v0.7.1 was then installed by a controlled native-USB flash without erasing or
  writing NVS.
- Runtime confirmed the 524,288-byte coredump partition, expected application
  slot, and cleared rollback state.
- Five short health samples were stable.
- Successful later v0.7.1-to-v0.7.2 OTA closed the BOYA application write-path
  retest.
- Signed candidate SHA-256:
  `de2cb25e8fd31a64db7ab2d6883de35020e129762ade5979d28a5dff601599bc`.
- Git checkpoint: `4945f77`.

### Observed risks

- ESP-Hosted host 2.11.7 reported installed ESP32-C6 firmware 2.3.0.
- One genuine brownout occurred after Wi-Fi/P1S authentication; subsequent
  monitored operation was stable, but no inline power diagnosis closed it.
- Native USB serial monitoring reset the controller and its ACM device number
  changed across enumeration.

## [0.7.0] - 2026-07-27 — deployed by native USB

### Added

- `nh_diagnostics` runtime health snapshots:
  - uptime and reset reason;
  - running OTA partition and pending-verification state;
  - current/lifetime-minimum internal heap;
  - current PSRAM;
  - lowest tracked persistent-task stack reserve;
  - runtime coredump partition size.
- `nh_settings` with 15 persistent timezone presets and immediate clock refresh.
- RSA-3072 signed-application verification for OTA without hardware Secure
  Boot.
- Local signing-key verification and committed public identity metadata.
- Security provisioning policy for the irreversible encrypted-NVS/eFuse
  decision.
- First reviewed Git baseline on `main`.

### Changed

- Enlarged the coredump partition to 512 KiB and reduced captured task limit to
  16.
- Hardened the uploader to require an appropriate private target, expected
  service, open on-device window, HTTP 200, exact success JSON, project-key
  digest, and expected returned version.
- Added bounded read-only health fields to the OTA status response.
- Kept native USB recovery by leaving hardware Secure Boot and flash encryption
  disabled.

### Validation and deployment

- Clean 1,704-step, six-job build passed after a host reboot resolved an
  abnormal kernel/compiler condition.
- Signed image size: 1,773,568 bytes; SHA-256:
  `06c17cce2febc31fec58265219b8fbae8db22965ae038232061fb174323bc807`.
- Native-USB maintenance flash wrote bootloader, partition table, OTA metadata,
  and signed application without writing NVS.
- Runtime confirmed the 512 KiB coredump map; saved Wi-Fi and printer profiles
  survived and reconnected.
- First Git baseline: `d87ef46`; follow-up checkpoints `801d98a` and `fe83a21`.

## [0.6.0] - 2026-07-27 — reconstructed pre-Git release, deployed

### Reliability and concurrency

- Replaced cross-task Wi-Fi mutation with an actor queue, asynchronous
  disconnect sequencing, bounded reconnect backoff, and connected-scan state
  preservation.
- Delayed Wi-Fi persistence until address acquisition and added rollback to the
  prior verified profile.
- Added generation-aware, actor-serialized printer profile validation,
  persistence, and rollback.
- Serialized shared printer/UI state and delivered locked deep-copy snapshots.
- Added retry-deadline checks to prevent cancelled Wi-Fi timers acting on a
  superseded profile.

### Protocol and input hardening

- Enforced WPA2 minimum security for protected Wi-Fi profiles.
- Supported exact 32-byte SSIDs and standards-compliant 64-character
  hexadecimal PSKs.
- Removed compiled private development IP and printer serial defaults.
- Separated printer authentication, TLS identity/handshake, and transport
  errors.
- Hardened MQTT fragment bounds, ordering, overflow behavior, session cleanup,
  and stale telemetry resets.
- Consolidated the Bambu CA in one component.
- Limited repeated idle OTA receives and checked restart/validation task
  allocation.
- Pinned `esp_wifi_remote` to 1.6.3.

### UI, camera, storage, and time

- Added explicit telemetry-synchronization state and correct action-specific
  pause/resume/cancel gating.
- Corrected stale IDLE progress/timing/name behavior and partial layer totals.
- Distinguished controller SD state from printer-reported SD state.
- Made SD refresh detect failed/removed media and kept mounting
  non-destructive.
- Started SNTP after DHCP address acquisition.
- Released camera JPEG/decode/PPA/output resources when leaving Camera and
  rejected late frames.
- Required the camera to use the persisted current printer profile.
- Cleared sensitive UI/transient buffers where practical.
- Removed unused LVGL features and corrected clean-build configuration.

### Tests and documentation

- Extracted a host-testable telemetry parser.
- Expanded to 11 parser cases with ASan/UBSan.
- Added repository safety/release invariants, ShellCheck, and compiler-analyzer
  review.
- Corrected the Bambu outreach material to reflect the implemented camera.

### Deployment

- Built image size: 1,717,504 bytes.
- Deployed by guarded application OTA at 15:51 EDT.
- Returned to network service as v0.6.0.
- The application OTA did not install the new partition table; that occurred
  later with the v0.7.0 native-USB maintenance flash.

## [0.5.1] - 2026-07-27 — reconstructed source baseline

This was the source version found when the first formal review began. It had no
Git commit because the repository did not yet have a valid `HEAD`.

### Verified baseline capabilities

- JC4880P443 ESP32-P4 display, touch, backlight, and SDMMC component structure.
- ESP32-C6 hosted Wi-Fi, profile persistence, and SNTP.
- P1S local TLS/MQTT telemetry and guarded command structure.
- P1-family authenticated TLS/JPEG liveview.
- LVGL pages for Dashboard, Job, Control, Files, Camera, and System.
- Dual-slot LAN OTA gated by a five-minute on-device authorization window.

### Baseline validation

- Firmware built with ESP-IDF 6.0.2 without a first-party compiler warning.
- Image size: `0x1b12c0`.
- Image metadata reported ESP32-P4, 16 MiB flash, and application v0.5.1.

### Review findings

The first review found material issues in network transition ownership,
transactional profile persistence, MQTT reassembly, stale telemetry, UI
truthfulness, credential handling, reproducible defaults, tests, camera
resource lifecycle, SD lifecycle, and OTA trust. These were addressed or
tracked in v0.6.0 and later releases.

## [0.5.0] - by 2026-07-27 — reconstructed deployed baseline

The first formal review recorded v0.5.0 as the version running on the
controller while v0.5.1 was in source. No preserved Git history supports a more
precise deployment date or a reliable per-change list, so none is invented
here.

## Project inception - 2026-07-26 — reconstructed

July 26, 2026 is the earliest defensible project-start date in the present
workspace:

- `board.jpg` has filesystem birth time 02:48:23 EDT;
- the preserved pre-v0.7 SDK configuration has birth time 05:51:18 EDT;
- factory flash-part backups were created from 06:01 through 06:04 EDT;
- `components/nh_ota/include/nh_ota.h` has birth time 09:31:46 EDT;
- preserved v0.6 build configuration/artifacts begin on this date.

These records establish that board identification, recovery backups, ESP-IDF
configuration, and firmware/OTA development were underway that day. They do
not establish exact version boundaries or authorship for individual changes,
so the changelog does not assign unsupported details to July 26.

## Evidence references

- `Reviews/07272026_01.md` — first comprehensive review and deployment record
- `Reviews/07292026_01.md` — v0.7.3 comprehensive review
- `Reviews/recommendations.md` — product research and ranked roadmap
- Git history beginning at `d87ef46`
- preserved ignored backup/build artifacts and filesystem birth metadata
