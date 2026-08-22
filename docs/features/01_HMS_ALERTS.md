# Feature Gate 1 — HMS and Print-Error Center

Version: 0.8.0
Recommendation: Actionable HMS/error and notification center
Source state: Implemented and double-verified
Hardware state: Not deployed or hardware-verified

## Delivered behavior

- Parses the P1S `print.hms` array using its unsigned `attr` and `code` fields.
- Formats HMS identity as the canonical exact value
  `HMS_AAAA-BBBB-CCCC-DDDD`.
- Parses `print_error` and the legacy `mc_print_error_code` field.
- Retains at most 12 alert records in controller memory.
- Deduplicates repeated active deltas.
- Resolves HMS records only when an explicit HMS array omits them.
- Resolves print errors only when an explicit zero or replacement code is
  observed.
- Preserves alert state when a partial MQTT delta omits error fields.
- Tracks active/resolved state, occurrence count, first/last observed epoch,
  source, severity, known/unknown mapping, and local dismissal.
- Restores a locally dismissed alert only after it resolves and recurs.
- Shows active and resolved records in an on-device alert drawer.
- Labels local hiding honestly; it does not send a printer command or claim the
  printer condition is resolved.

## Code-table policy

The local table is versioned with firmware. Version 1 contains only two
descriptions that were cross-checked against Bambu Wiki results:

- `HMS_0300-0300-0001-0001` — hotend cooling fan too slow/stopped;
- `HMS_07FF-2000-0002-0004` — filament may be stuck in the toolhead.

Every other code remains visible with its exact canonical identity and generic
guidance to consult official printer information. PrintDeck never invents a
diagnosis for an unknown value.

## Data and lifecycle rules

| Input | Result |
|---|---|
| Repeated identical active HMS list | One record; occurrence count unchanged |
| MQTT delta without `hms` | Existing HMS state retained |
| Explicit `hms: []` | Active HMS records become resolved |
| Resolved code returns | Same record reactivated; occurrence count increments |
| Local hide | Active on printer, hidden in active badge, retained in drawer |
| Nonzero `print_error` | Active print-error record |
| Explicit zero print error | Print-error record resolved |
| Malformed entry | Entry rejected without discarding valid records |
| More than 12 distinct records | Oldest resolved record is replaced first |

## UI

The Dashboard includes an `ALERTS n` control. Its drawer shows:

- active, locally hidden, or resolved state;
- severity and exact code;
- verified or deliberately generic explanation;
- safe next-step guidance;
- local-hide control for an active condition.

Critical on-device status is never automatically silenced. External webhook,
ntfy, Home Assistant, and buzzer routing are extension points, not claimed as
part of this local-only gate.

## Verification

Focused verification includes:

1. known-code mapping;
2. unknown-code preservation;
3. repeated-delta deduplication;
4. missing-delta retention;
5. explicit clear;
6. resolution and recurrence counting;
7. local dismissal semantics;
8. print-error activation and clearing;
9. malformed/overflow rejection;
10. bounded storage.

Verification 1 passed with 15 sanitizer-enabled protocol cases and 35
repository invariants.

Verification 2 passed with:

- a full signed ESP32-P4 build under ESP-IDF 6.0.2;
- valid RSA signature and expected project-key digest;
- valid ESP32-P4 checksum and image hash;
- application metadata version 0.8.0;
- 1,773,568-byte image with 72% free in each application slot;
- SHA-256
  `9baa4918e4cf487bee057fcd2ea32e49c4b5ab00ea52065ab504b9d211956730`;
- repeated host/invariant, ShellCheck, Python, link, and whitespace checks.

Hardware UI/MQTT regression remains required before this gate can be called
deployed or hardware-verified.

## Upgrade path

The alert source enum already reserves controller, material, and vision
sources. The append-only history gate will persist alert transitions. External
notification adapters can consume the same records without changing printer
parsing or making local visibility subscription-dependent.
