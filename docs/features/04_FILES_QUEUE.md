# Feature Gate 4 — Local Files, Reprint, and Confirmed Queue

Version: 0.9.0
Recommendation: Local file library, fast reprint, and human-confirmed queue
Source state: Implemented; double-verified
Hardware state: Not deployed or hardware-verified

## Delivered behavior

- Indexes at most 48 `.3mf` files beneath `/sdcard/PrintDeck/files`, to a
  maximum directory depth of two, without formatting the controller card.
- Hashes every indexed file with SHA-256 and marks exact-size/hash duplicates.
- Sorts favorites first and remaining files by most-recent modification time.
- Provides bounded case-insensitive search over display name and target model.
- Parses selected 3MF metadata and PNG previews with a purpose-built,
  fail-closed ZIP reader.
- Shows file name, size, compatibility, duplicate/favorite state, metadata,
  SHA-256 prefix, and a bounded embedded preview in the Files screen.
- Persists an eight-item local queue with CRC32, schema, atomic replacement,
  priority, copies, resumable offset, expected hash, and recovery state.
- Requires compatibility review and a separate human assertion that the
  physical bed is clear before an item becomes transfer-ready.
- Supports explicit cancellation and rejects invalid state transitions.
- Compiles an implicit-FTPS upload adapter using Bambu's CA, certificate common
  name verification, access-code authentication, protected data channels,
  exact local hash verification, server-confirmed resume offsets, a temporary
  remote name, and atomic rename.

## Safety boundary

Version 0.9.0 does not call the FTPS adapter and does not issue a print-start
command. Those capabilities remain fail-closed until the printer model,
firmware, storage behavior, command payload, acknowledgement, and cancellation
semantics are qualified on idle hardware. A local `READY_TO_TRANSFER` state is
not represented as printer acceptance.

The UI's bed-clear action records a human assertion; the controller cannot
detect an object or plate on the bed. It never auto-confirms this condition.
Incompatible target metadata is rejected. Missing target metadata requires
review and is never silently treated as compatible.

## Archive and persistence limits

The 3MF reader rejects absolute/traversing/backslash member names, multipart
archives, encrypted entries, unsupported compression, ZIP64 sentinel sizes,
more than 512 members, compressed members over 512 KiB, metadata over 64 KiB,
previews over 256 KiB, images over 8192 pixels per axis, invalid CRC32, and a
compression ratio above 128:1. It extracts only selected metadata/preview
members and never writes archive contents to the filesystem.

Queue and favorite mutations snapshot their prior in-memory values and restore
them when durable replacement fails. A recovered transfer returns to
`READY_TO_TRANSFER` with its offset; an interrupted start/print becomes
`FAILED` because success cannot be inferred after reboot.

## Verification contract

Verification 1 covers safe member names, PNG bounds, scalar/array metadata,
sanitizers, queue/persistence invariants, static checks, and documentation
links.

Verification 2 requires a clean signed ESP32-P4 target build, expected RSA
identity, image checksum/hash inspection, and independent repetition of the
host/invariant suite.

Controller-SD indexing, real 3MF diversity, preview rendering, power-loss
fault injection, FTPS interoperability, remote capacity handling, and any
printer start remain hardware-qualification items.

## Verification results

- Verification 1 passed 18 telemetry cases, three history-codec cases, three
  3MF-codec groups, and 38 repository/release invariants under
  AddressSanitizer and UndefinedBehaviorSanitizer.
- Verification 2 passed a separate signed ESP32-P4 build, expected RSA
  identity inspection, valid image checksum/hash inspection, ShellCheck,
  Python compilation, maintained-link checks, and whitespace validation.
- Signed image size: 1,839,104 bytes; 71% of either application slot remains
  free.
- Signed image SHA-256:
  `024f92ab726d300862db7d28503c305037f5f38231263e6ed3e8fd7bc30fa54a`.
- No firmware was deployed and neither SD card was accessed.
