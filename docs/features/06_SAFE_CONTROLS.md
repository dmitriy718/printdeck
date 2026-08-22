# Feature Gate 6 — Safe Controls and Object-Rescue Foundation

Version: 0.9.2
Recommendation: Safe control parity and object-rescue workflow
Source state: Implemented for the qualified command subset
Hardware state: Not deployed or hardware-verified

## Delivered behavior

- Gives each queued printer action a monotonic sequence ID.
- Emits asynchronous `SENT` or `REJECTED` results from the worker after it
  revalidates the newest connection/job state and attempts MQTT enqueue.
- Defines distinct queued, sent, acknowledged, observed, rejected, and timed
  out states so later protocol qualification cannot conflate them.
- Shows asynchronous sequence/action/result status in the UI footer.
- Preserves the existing second confirmation for irreversible print cancel.
- Adds typed hard bounds for fan (0–100%), X/Y jog (±10 mm, non-zero), Z jog
  (±1 mm, non-zero), speed profile (1–4), and object ID (0–63).
- Adds typed calibration, speed-profile, and skip-object actions to the common
  command vocabulary.
- Keeps pause, resume, cancel, and chamber light as the only currently
  supported printer writes; these are revalidated again at dispatch.

## Fail-closed boundary

Motion, fan, temperature, calibration, speed-profile, file start, and object
skip are still rejected by `nh_printer_action_supported`. The typed validators
are necessary but not sufficient authorization. No raw G-code console exists.

Acknowledged, observed, and timed-out states are part of the API but are not
emitted until exact firmware response fixtures and timeout/observation rules
are hardware-qualified. `SENT` means accepted by the local MQTT client queue,
not accepted or executed by the printer.

Object skip is deliberately not exposed in the UI until the printer-reported
eligible object list, active plate identity, two-step object preview, and
post-command observation are implemented and tested. This avoids creating a
dangerous button that only looks complete.

## Verification contract

Verification 1 exercises every typed boundary and command-result label under
AddressSanitizer/UndefinedBehaviorSanitizer, plus repository safety invariants.
Verification 2 is a signed target build and independent image/signature/hash
inspection.

Hardware qualification remains required for each command across idle,
preparing, printing, paused, error, reconnect, and stale-queue states.

## Verification results

- Verification 1 passed 28 sanitizer-backed host cases/groups and 40
  repository/release invariants, plus static and documentation checks.
- Verification 2 passed signed ESP32-P4 build, expected RSA identity, checksum,
  image validation hash, and SHA-256 inspection.
- Signed image size: 1,839,104 bytes; 71% of either application slot remains
  free.
- Signed image SHA-256:
  `fd99fb3d7a59eefd095e4b5344032cb285927a5882fa18792f4951d8955a5799`.
- No firmware was deployed and no printer command was sent.
