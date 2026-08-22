# Feature Gate 3 — History, Cost, Maintenance, and Exports

Version: 0.8.2
Recommendation: Print history, cost analytics, and maintenance
Source state: Implemented; double-verified
Hardware state: Not deployed or hardware-verified

## Delivered behavior

- Observes printer state transitions without sending printer commands.
- Writes fixed-size schema-v1 start, finish, and maintenance-reset records to
  `/sdcard/PrintDeck/history.journal`.
- Seals every record with CRC32 and a monotonic local sequence.
- Scans the journal at startup and truncates only a partial or invalid trailing
  record, preserving every valid earlier record.
- Stores bounded names and keeps only 24 recent completed jobs in RAM while the
  journal remains the durable source.
- Classifies completed, failed, and interrupted sessions separately.
- Tracks maximum observed progress and monotonic elapsed time.
- Tracks lifetime, current-day, current-month, and since-maintenance-reset jobs
  and print time.
- Raises a local maintenance-due state after 250 print hours or 500 jobs since
  the last audited reset.
- Provides CSV and JSON exports, privacy-preserving job-name redaction, a
  byte-for-byte backup, explicit retention, and confirmation-gated deletion.
- Adds a History & Costs drawer on the Job page with recent sessions, aggregate
  state, redacted exports, and backup.

## Measured versus estimated

Duration and maximum progress are observations. Material, energy, and cost are
never described as measured. They remain unavailable until explicit non-zero
estimation inputs are configured:

- nominal material grams per print hour;
- nominal printer watts;
- material cost per kilogram;
- energy cost per kilowatt-hour.

Once configured, exported fields and the UI retain the `estimate` label. A zero
rate disables the corresponding estimate instead of manufacturing a value.
The current gate exposes the bounded configuration API; a polished settings
editor remains a hardware-qualified input workflow.

## Journal and recovery contract

Each record contains:

- magic, schema, record size, and sequence;
- event type and bounded text;
- timestamp plus an explicit wall-clock-known flag;
- duration, outcome, and maximum observed progress;
- optional estimate values and flags;
- CRC32 across every field before the checksum.

An unsynchronized clock produces an unknown wall-clock value while duration
continues to use the monotonic ESP timer. A corrupt middle record stops recovery
at that point; the implementation never scans arbitrary bytes looking for a
plausible later record. This avoids accepting fabricated or misaligned data.

## Privacy and lifecycle controls

- Touchscreen CSV and JSON export defaults to redacted names such as
  `Print-42`.
- The API also supports an explicit unredacted export for an authorized future
  workflow.
- Backup copies the journal without mutating it.
- Retention uses a temporary file, flush, sync, and atomic rename while
  preserving the most recent maintenance-reset audit marker.
- Full deletion requires the exact phrase `DELETE PRINT HISTORY`.
- No automatic retention or deletion runs in the background.

## Export schema

CSV includes current-day and current-month aggregate metadata followed by one
row per cached recent job. JSON declares schema 1,
`estimates_are_measured:false`, daily/monthly summaries, and job records. Both
include epoch validity and preserve estimate units explicitly.

## Verification contract

Verification 1 covers record sealing, deterministic validation, corruption
rejection, invalid schema/type/sequence/text bounds, telemetry regression,
repository invariants, and sanitizer execution.

Verification 2 requires a full signed ESP32-P4 build plus independent
signature, image, checksum/hash, static, formatting, and documentation-link
checks.

Controller-SD write/recovery, power-loss injection, export opening in desktop
tools, retention, deletion confirmation, timezone rollover, and Job-screen
touch behavior remain hardware qualification items.

## Verification results

- Verification 1: passed 18 telemetry-parser cases, three journal-codec cases,
  and 37 repository/release invariants under AddressSanitizer and
  UndefinedBehaviorSanitizer.
- Verification 2: passed a separate signed ESP32-P4 build, expected RSA
  identity inspection, valid image checksum/hash inspection, ShellCheck,
  Python compilation, maintained-link checks, and whitespace validation.
- Signed image size: 1,773,568 bytes; 72% of either application slot remains
  free.
- Signed image SHA-256:
  `be2101e6bed4a427576ed74bd383bd0c8bf635a653a245065e4266cdb253ec3c`.
- No firmware was deployed or controller SD accessed.
