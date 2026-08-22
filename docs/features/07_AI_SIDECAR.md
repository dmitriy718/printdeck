# Feature Gate 7 — Optional Local AI Sidecar

Version: 0.9.3
Recommendation: Optional local AI failure-detection sidecar
Source state: Implemented as an authenticated orchestration contract
Hardware state: Not deployed or hardware-verified

## Delivered behavior

- Defines a schema-v1 signed-event contract carrying sequence, timestamp,
  printer/job identity, model version, failure type, confidence, evidence
  SHA-256, and suggested action.
- Authenticates canonical event data with HMAC-SHA-256 and compares MACs without
  an early-exit timing leak.
- Rejects invalid bounds, replayed/out-of-order sequence IDs, invalid evidence
  hashes, unknown event types, and events outside a ±120-second window when the
  controller clock is synchronized.
- Keeps a bounded 16-event audit ring with user true/false-positive labels.
- Requires three matching job/type observations averaging at least 85%
  confidence, a healthy camera, no job mute, and a five-minute cooldown before
  an event becomes actionable.
- Starts local-only and notify-only, exposes job mute and camera-health state,
  and shows `AI OFF / LOCAL` until a sidecar key is provisioned.
- Requires both a qualified pause capability and the exact phrase
  `ENABLE AUTO PAUSE` before automation can be enabled.

## Privacy and automation boundary

No shared key is compiled into firmware and the product does not initialize the
adapter until an authorized provisioning workflow supplies one. The key is
held in RAM and securely zeroed on deinitialization. Evidence is represented by
a hash; this gate does not upload images, enable cloud routing, or open a
network listener.

The controller does not run a production vision model and does not claim
accuracy. A Jetson/Obico bridge must translate its output into this contract.
Automatic cancel and power-off do not exist. Even when auto-pause is opted in,
this component only classifies an event as actionable; dispatch remains subject
to the qualified command framework.

## Verification contract

Verification 1 covers malformed contracts, confidence bounds, evidence hashes,
temporal smoothing, mixed event rejection, sanitizer execution, and repository
security invariants. Verification 2 covers signed target build and independent
signature/image/hash inspection.

Before commercial automation claims, validation must measure precision,
recall, false-stop rate, latency, camera failures, material saved, and user
overrides on representative prints.

## Verification results

- Verification 1 passed 30 sanitizer-backed host cases/groups and 41
  repository/release invariants, plus static and documentation checks.
- Verification 2 passed signed ESP32-P4 build, expected RSA identity, checksum,
  image validation hash, and SHA-256 inspection.
- Signed image size: 1,839,104 bytes; 71% of either application slot remains
  free.
- Signed image SHA-256:
  `08f12872bb12ac2c9d29a19d1debd35df0a6e1514c718f96860defd6c0ed0127`.
- No firmware was deployed and no AI or printer service was contacted.
