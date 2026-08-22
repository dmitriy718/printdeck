# PrintDeck product overview

## Product definition

PrintDeck is a local-first touchscreen companion controller developed by
Horizon Services LLC for the Guition JC4880P443 board and, currently, one Bambu
Lab P1S. It presents live printer state, guarded controls, local camera
liveview, controller health, setup, and update workflows on a dedicated
800 × 480 interface.

PrintDeck is an independent project. It is not a Bambu Lab product and the
current local printer integration is not an official public API.

## Product goals

- Make the printer's state understandable at a glance.
- Keep core monitoring and supported controls on the local network.
- Fail closed when printer identity, connection state, or command support is
  uncertain.
- Avoid presenting future features as available.
- Preserve a recoverable wired path while the prototype security model
  matures.
- Keep display, transport, protocol, and future backend/vision integrations
  separable.

## Intended users

- P1S owners who want a modern printer-side display.
- Privacy-conscious users operating locally.
- Developers validating Bambu LAN integration.
- Future small-team and multi-printer operators.

The current firmware is a single-printer prototype, not a certified appliance,
industrial safety controller, or completed print-farm product.

## Current status

| Layer | Status |
| --- | --- |
| Source | v1.0.0 integrated seven-feature release |
| Signed build | v1.0.0 passed both local verification layers |
| Last deployed version | v0.7.2 |
| Current printer target | One Bambu Lab P1S |
| Hardware target | One JC4880P443 prototype |
| Hardware regression for v1.0.0 | Pending |

## Feature matrix

| Capability | State | Notes |
| --- | --- | --- |
| ST7701S display and GT911 touch | Hardware-verified | Native portrait panel rendered as 800 × 480 landscape |
| Backlight control | Built/deployed | PWM slider on System page; boot default 82% |
| Wi-Fi scan and setup | Built/deployed | ESP32-C6 hosted Wi-Fi; up to eight visible AP entries |
| Saved Wi-Fi reconnect | Built/deployed, partial fault coverage | Transactional replacement and rollback exist |
| Time synchronization | Built/deployed | SNTP starts after DHCP address acquisition |
| Persistent timezone | Built/deployed | Fifteen presets; cycles from System page |
| P1S profile setup | Built/deployed | Manual IP, device serial, and LAN access code |
| P1S TLS/MQTT telemetry | Built/deployed | CA verification plus configured serial identity |
| Job state and progress | Built/deployed | State, percent, layer, remaining time, and job name |
| Temperatures and fan status | Built/deployed | Nozzle, bed, chamber, and part-fan telemetry |
| Chamber-light command | Hardware-verified | Guarded online command |
| Pause/resume/cancel | Built, hardware regression incomplete | State-gated; cancel requires confirmation |
| Axis, fan, and thermal commands | Deliberately disabled | Visible as honest scaffolding; no command sent |
| P1 camera liveview | Hardware-verified, duration testing pending | TLS/JPEG, hardware decode, PPA scale; active only on Camera page |
| Controller SD mount | Built/deployed, media coverage incomplete | Native four-bit FAT32 mount; never auto-formats |
| File library and local queue | Built and build-verified in v0.9.0; hardware validation pending | Bounded 3MF metadata/previews and human-confirmed queue; transfer/start disabled |
| Signed dual-slot OTA | Built/deployed | Physical five-minute window, one upload, rollback |
| Runtime health | Built/deployed | Heap, stack, uptime, reset, partition, OTA state |
| HMS/error center | Built and build-verified in v0.8.0; hardware validation pending | Bounded active/history model, exact unknown codes, local dismissal |
| AMS/material center | Built and build-verified in v0.8.1; hardware validation pending | Up to four units/16 trays, external spool, moisture-risk alerts, local catalog |
| Print history/cost analytics | Built and build-verified in v0.8.2; hardware validation pending | Recoverable SD journal, honest estimates, maintenance counters, redacted CSV/JSON export |
| Multi-printer support | Not implemented | Current printer component is a singleton |
| AI failure detection | Not implemented | Planned as an optional external adapter |
| novahorizon.net backend | Not implemented | Domain/roadmap only |

## User interface

| Page | Purpose |
| --- | --- |
| Dashboard | Connection, current job, progress, temperatures, and validated quick actions |
| Job | Detailed session state plus pause, resume, and confirmed cancel |
| Control | Honest scaffold for motion and material controls; currently disabled |
| Files | Controller/P1S SD status and explicit file-indexing boundary |
| Camera | On-demand local P1 liveview |
| System | Printer identity, controller health, brightness, timezone, network/printer setup, and OTA authorization |

## Safety model

PrintDeck uses layers of protection:

- commands are typed rather than accepted as arbitrary G-code;
- unsupported actions return `ESP_ERR_NOT_SUPPORTED`;
- online actions require an authenticated printer session;
- pause/resume/cancel are gated by current print state and rechecked when
  actually dispatched;
- cancel requires a UI confirmation;
- the UI reports a local command as queued, not printer-acknowledged;
- printer leaf certificates are checked against Bambu's CA and the configured
  device serial;
- firmware uploads require an on-device, single-use authorization window and the
  expected signing key.

This is an engineering safety boundary, not formal safety certification.

## Known product limitations

- Wi-Fi and printer credentials remain plaintext in NVS.
- The installed ESP32-C6 coprocessor firmware and host component versions do
  not match; Wi-Fi currently works, but migration needs a tested recovery plan.
- One prior hardware brownout remains without an inline power measurement.
- Event queues log and drop events if saturated; reconnect-storm testing and a
  stronger critical-event design remain open.
- NVS initialization can erase NVS on two unrecoverable layout conditions,
  which requires a product recovery policy before broader distribution.
- UI simulation, hardware-in-the-loop tests, and full long-duration testing do
  not yet exist.

See [Testing](TESTING.md), [Security](SECURITY.md), and
[Troubleshooting](TROUBLESHOOTING.md) for the operational implications.

## Product direction

Research supports positioning PrintDeck as a local printer-side operations
console rather than a duplicate phone app. The ranked roadmap is:

1. actionable HMS/error center;
2. AMS/material management;
3. print history, cost, and maintenance analytics;
4. fast local reprint and a human-confirmed queue;
5. multi-printer sessions and fleet overview;
6. hardware-validated control parity and object rescue; and
7. optional local AI failure detection.

The full evidence and scoring method are in
[Reviews/recommendations.md](../Reviews/recommendations.md).
