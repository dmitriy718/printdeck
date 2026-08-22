# PrintDeck Architecture

This document describes the current architecture of the PrintDeck firmware. It
is written for source version **1.0.0**, the integrated seven-feature release.
The most recently verified deployed version is **0.7.2**.

## System context

PrintDeck is an ESP32-P4 touchscreen controller for a Bambu Lab P1S printer.
The ESP32-P4 runs the application and UI. An on-board ESP32-C6 provides Wi-Fi
through Espressif's Hosted SDIO transport.

```text
                       local network
  ┌──────────────┐       MQTT/TLS       ┌──────────────┐
  │ Bambu Lab P1S│◀────────────────────▶│              │
  │              │      Camera/TLS      │  PrintDeck   │
  └──────────────┘◀────────────────────▶│  ESP32-P4    │
                                        │              │
  ┌──────────────┐   SDIO / ESP-Hosted  │              │
  │   ESP32-C6   │◀────────────────────▶│              │
  │ Wi-Fi radio  │                      └──────┬───────┘
  └──────────────┘                             │
                                        DSI, I²C, PWM,
                                         SDMMC, USB
                                               │
                                  ┌────────────┴────────────┐
                                  │ display, touch, SD card,│
                                  │ backlight, development  │
                                  └─────────────────────────┘
```

PrintDeck does not require a Horizon cloud service. The current printer
integration uses the printer's local MQTT and camera interfaces.

## Boot sequence

The application starts subsystems in this order:

1. Initialize NVS. If NVS reports `NO_FREE_PAGES` or
   `NEW_VERSION_FOUND`, erase and reinitialize it.
2. Load application settings.
3. Initialize the display and UI.
4. Start the camera service.
5. Set the backlight to 82%.
6. Initialize ESP-Hosted and Wi-Fi.
7. Mount the external SD card after the shared SDMMC host is ready.
8. Initialize the printer client.
9. Start the OTA service after TCP/IP is available.

The current automatic NVS erase behavior prevents a boot loop but can remove
saved Wi-Fi, printer, and timezone settings. It is a documented product risk,
not a durability guarantee.

## Component map

| Component | Responsibility |
|---|---|
| `main` | Application entry point and subsystem startup order |
| `nh_board` | Board pins, display, touch, backlight, and SD-card lifecycle |
| `nh_network` | Wi-Fi actor, scanning, connection transitions, persistence, and reconnect behavior |
| `nh_settings` | Timezone persistence and the supported timezone preset table |
| `nh_core` | Shared UI/printer state, action queue, and state synchronization |
| `nh_bambu` | Bambu MQTT parsing support and the pinned trust anchor |
| `nh_printer` | Printer profile, TLS MQTT session, telemetry, command publishing, and command eligibility |
| `nh_camera` | Local TLS/JPEG camera connection, decode, and display pipeline |
| `nh_ui` | LVGL screens, widgets, navigation, state presentation, and user interactions |
| `nh_ota` | On-device authorization window, signed-image upload, validation, and rollback handling |
| `nh_diagnostics` | Reset, partition, rollback, coredump, heap, and stack diagnostics |

## State and concurrency

`nh_core` is the boundary between the UI and asynchronous printer/network
work. The UI reads shared snapshots and submits actions; it does not directly
operate the MQTT client.

The printer worker owns the MQTT lifecycle. Wi-Fi operations use an actor-style
queue so connect, disconnect, scan, and reconnect transitions occur in one
execution context. This avoids cross-task mutation of network handles.

Printer actions are validated twice:

1. The UI enables an action only when the latest state reports it as valid.
2. The printer worker revalidates the queued action immediately before
   publishing it.

The second check matters because printer state may change between a touch
event and execution. A full action queue can still drop a request; the UI must
never imply that a queued command has already completed.

## Printer data path

The configured P1S profile contains:

- IPv4 address;
- printer serial number;
- LAN access code.

The client connects to MQTT over TLS on port 8883 with:

- username `bblp`;
- the configured access code as the password;
- the Bambu trust anchor;
- the configured printer serial as the expected certificate common name.

It subscribes to the printer report topic and publishes to the request topic.
Telemetry is parsed into a bounded shared state structure. Stale connections
clear connection-dependent fields rather than preserving old values as though
they were live.

HMS arrays and printer-error fields feed a bounded 12-record alert model.
Repeated reports are deduplicated, explicit empty/zero fields resolve the
corresponding active condition, and missing delta fields preserve prior state.
Unknown codes remain exact and visible. Local dismissal is a presentation
choice and is not represented as printer-side resolution.

AMS telemetry is modeled as collections rather than four fixed UI slots. The
bounded snapshot supports four AMS units, 16 internal trays, and one external
spool. A present `ams.ams` collection replaces the prior collection; a delta
without AMS fields preserves it. Humidity is labeled as the printer's index,
not an invented relative-humidity percentage. The independent `nh_material`
component persists a checksummed, versioned 16-entry local spool catalog.

Currently implemented printer actions are:

- connect;
- pause;
- resume;
- cancel;
- chamber-light toggle.

Motion, fan, preheat, and file-start actions are deliberately reported as
unsupported until their command paths and safety constraints are implemented.

## Camera data path

The camera service uses the configured local printer profile and opens the
P1S's TLS camera stream only while the Camera page is active. Frames are JPEG
decoded and transformed for the display using available hardware acceleration.
Leaving the page tears down the stream and releases its resources.

The camera connection reuses the printer's local credentials; there is no
separate camera account.

## Display and input

The ST7701S panel has a native 480 × 800 framebuffer. PrintDeck presents an
800 × 480 landscape UI, with PPA-assisted rotation. LVGL 9.5 provides the UI
and the GT911 touch controller supplies input over I²C.

The main pages are:

- Dashboard;
- Job;
- Control;
- Files;
- Camera;
- System.

The Files page currently reports external SD-card status only. It does not
The file component indexes bounded local 3MF metadata. Transfer and print start
remain disabled pending idle-hardware qualification.

## Storage

PrintDeck uses three distinct storage mechanisms:

| Storage | Current use |
|---|---|
| NVS | Wi-Fi profile, printer profile, and timezone |
| External FAT32 SD card at `/sdcard` | Mounted media and status reporting |
| Internal `storage` partition | Reserved LittleFS partition; not currently mounted or consumed |

NVS namespaces and values are described in [Security](SECURITY.md).

## OTA and recovery

The OTA service exposes `GET` and `POST /api/v1/ota` over local HTTP. Upload is
allowed only during a 300-second, locally authorized, single-use window opened
from the controller's System page. Application images must carry a valid
RSA-3072 signature.

The bootloader's hardware Secure Boot feature is intentionally not enabled.
This retains native USB recovery while still requiring signed application
images through the supported OTA path.

After an OTA boot, the application waits for a stable runtime interval before
marking the image valid. Until then, the bootloader can roll back to the
previous application slot.

See [Release Process](RELEASE_PROCESS.md) for the supported build and deployment
workflow and [Security](SECURITY.md) for the trust model.

## Known architectural constraints

- Only one printer profile is supported.
- Printer discovery is not implemented; the address and credentials are
  entered manually.
- The installed ESP32-C6 firmware version must remain compatible with the
  ESP-Hosted host component. The known deployed C6/host versions are not
  aligned and require qualification.
- Credentials are stored in plaintext NVS.
- There is no UI simulator or automated hardware-in-the-loop suite.
- The event queues are bounded and do not yet provide durable command
  acknowledgement.
- Power stability requires continued validation because a brownout was
  observed during v0.7.0 verification.

## Related documents

- [Product Overview](PRODUCT_OVERVIEW.md)
- [Hardware Reference](HARDWARE.md)
- [Development Guide](DEVELOPMENT.md)
- [Testing](TESTING.md)
- [Security](SECURITY.md)
