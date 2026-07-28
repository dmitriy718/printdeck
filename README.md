# Nova Horizon Controller

Touch controller firmware for the Guition **JC4880P443** and a Bambu Lab P1S.
The first milestone brings up the exact display and touch hardware, presents a
custom Nova Horizon interface, and establishes a safety boundary for printer
commands. Firmware 0.7.2 includes the onboard ESP32-C6 hosted-Wi-Fi transport,
on-screen Wi-Fi and P1S pairing, live P1S telemetry over pinned local TLS/MQTT,
an on-demand encrypted P1S camera feed, and physically authorized dual-slot LAN
OTA updates. OTA uploads are rejected unless the five-minute update window has
been opened from the controller display. Release images are RSA-3072 signed,
and a signed-enforcement image rejects future OTA uploads from any other key.

## Current status

- ESP32-P4 firmware builds with ESP-IDF 6.0.2 and LVGL 9.5.
- ST7701S MIPI-DSI display runs at its native 480 x 800 resolution.
- The interface is rendered in landscape at 800 x 480 using PPA rotation.
- The header clock updates from SNTP-synchronized local time. The System page
  cycles through persistent UTC and regional timezone presets.
- GT911 capacitive touch, backlight PWM, and the native SD-card slot are wired.
- Dashboard, Job, Control, Files, Camera, and System screens are implemented.
- ESP32-C6 hosted Wi-Fi uses Guition's four-bit SDIO profile, with access-point
  scanning and masked on-screen password entry.
- The P1S pairing screen keeps the LAN access code on the controller and verifies
  both Bambu Lab's CA and the configured printer device ID.
- Live job state, progress, layers, remaining time, temperatures, fan state, and
  chamber-light state feed the dashboard.
- Layer totals persist correctly across the P1S's partial MQTT status updates.
- Job-state transitions reject stale progress, timing, and name values left in
  an `IDLE` report.
- Dashboard and Job headings follow the live printer state instead of retaining
  their initial idle placeholders.
- The System page presents the printer name prominently with its model and
  device serial below it.
- The Files page distinguishes the controller's FAT32 mount from the P1S SD-card
  presence reported over MQTT.
- The Camera page opens the P1-family TLS/JPEG liveview only while that page is
  visible. Frames use the ESP32-P4 hardware JPEG decoder and PPA scaler before
  being rendered in RGB565. Its multi-megabyte pipeline is released when the
  tab closes.
- Pause, resume, cancel, and chamber-light controls unlock only after an
  authenticated printer session. Cancel also requires confirmation.
- Motion, fan, and thermal commands remain disabled until validated safely on
  the exact P1S.
- New Wi-Fi and printer profiles are persisted only after a successful
  connection. A rejected replacement printer profile rolls back to the last
  verified profile without requiring a controller reset.
- The System page and read-only status endpoint report internal-heap lifetime
  minimums and persistent-task stack high-water marks without enabling the
  heavier FreeRTOS trace facility.

## Target hardware

| Function | JC4880P443 configuration |
| --- | --- |
| Main SoC | ESP32-P4NRW32 |
| Memory | 32 MB PSRAM, 16 MB flash |
| Connectivity | ESP32-C6 Wi-Fi coprocessor |
| Display | 4.3-inch ST7701S, 480 x 800, two-lane MIPI-DSI |
| Touch | GT911 on I2C, SDA GPIO7 / SCL GPIO8 |
| LCD reset | GPIO5 |
| Backlight | GPIO23, 20 kHz PWM |
| DSI power | Internal LDO channel 3 at 2.5 V |
| SD card | Native four-bit SDMMC slot 0 on GPIO39-44, internal LDO channel 4 |
| Boot strap | BOOT on GPIO35 |
| Programming | Native USB2 connector, `/dev/ttyACM0` on Linux |
| Hosted Wi-Fi | SDIO GPIO14-19, C6 reset GPIO54 |

The display profile uses a 34 MHz pixel clock, two DSI lanes at 500 Mbps, and
the timing required by this specific panel: HBP 42, HPW 12, HFP 42, VBP 8,
VPW 2, and VFP 166.

## Build and flash

The project-local toolchain lives under `.tools/` and is intentionally ignored
by Git. From Bash or Zsh:

```sh
source scripts/idf-env.sh
scripts/setup-signing-key.sh
idf.py build
idf.py -p /dev/ttyACM0 flash
```

If automatic reset cannot enter the ROM loader:

1. Hold **BOOT**.
2. Tap and release **RESET** while keeping BOOT held.
3. Release BOOT after two to three seconds.
4. Start the flash command against `/dev/ttyACM0`.

Exit the serial monitor with `Ctrl-]`.

## LAN OTA updates

After the controller is connected to Wi-Fi, routine development updates do not
require BOOT or RESET:

1. Build the new firmware with `idf.py build`.
2. On the System page, tap **ENABLE OTA FOR 5 MINUTES**.
3. Run `scripts/ota-update.sh <controller-ip>`.

The upload script first refuses an unsigned image. The service accepts one
upload into the inactive OTA slot, validates the image, switches boot slots,
and restarts automatically. The new image marks itself valid after a stable
ten-second boot; otherwise the rollback-enabled bootloader returns to the
previous slot. Uploads are rejected outside the physical five-minute
authorization window. Firmware 0.7.2 uses ESP-IDF's signed-app verification
without hardware Secure Boot, protecting the OTA path while retaining native
USB recovery.

If an upload connection drops, the uploader keeps the operation in a failed
state and performs a read-only recovery check. It reports the returned firmware
version, partition, and reset reason when available. Do not immediately repeat
an upload after a disconnect; diagnose that state and explicitly reopen the
physical authorization window only after the controller is known healthy.

OTA updates replace only the application slot. Changes to `partitions.csv`
(including the v0.6.0 expansion of crash-dump storage from 64 KiB to 512 KiB)
require a deliberate wired maintenance flash of the partition table. Do not
assume an OTA application update has changed the device partition layout.

## SD card safety

The firmware mounts `/sdcard` without ever formatting it automatically.
ESP-IDF's current FatFs configuration expects FAT32. A 512 GB SDXC card usually
ships as exFAT and therefore may not mount until it is backed up and reformatted
as FAT32. Reformatting is deliberately left as an explicit host-side operation.
The card uses SDMMC slot 0 while the ESP32-C6 link uses slot 1. ESP-Hosted owns
the shared controller; card mount and cleanup are deliberately limited to slot
0 so rescans cannot interrupt Wi-Fi.

## Project layout

```text
main/                    Application composition and boot sequence
components/nh_board/     JC4880P443 display, touch, backlight, and SD support
components/nh_camera/    On-demand P1 TLS/JPEG liveview and frame pipeline
components/nh_core/      Printer state and guarded command boundary
components/nh_diagnostics/ Runtime heap, stack, reset, and OTA health data
components/nh_network/   ESP32-C6 hosted Wi-Fi state and worker
components/nh_ota/       Physically authorized dual-slot LAN updater
components/nh_printer/   Pinned-TLS P1S telemetry and guarded command worker
components/nh_settings/  Persistent controller timezone and future settings
components/nh_ui/        Nova Horizon LVGL interface
scripts/idf-env.sh       Project-local ESP-IDF environment
scripts/ota-update.sh    Guarded LAN firmware uploader
tests/                   Host protocol regression tests and review checks
Reviews/                 Timestamped comprehensive review records
partitions.csv           Dual-OTA 16 MB flash layout
```

## Validation

The host regression suite compiles the production telemetry parser against
recorded-style JSON fixtures:

```sh
tests/run_host_tests.sh
shellcheck scripts/*.sh tests/*.sh
```

These checks complement, but do not replace, on-device P1S validation. The
reviewed firmware binary must still be exercised on the controller before a
release is called hardware-verified.

## Security status

Printer traffic uses local TLS with CA and configured-device identity
verification. OTA requires a physical five-minute authorization window and
release images use RSA-3072 signed-update verification without burning hardware
Secure Boot eFuses. The signing key is excluded from Git and checked against a
committed public fingerprint.

Wi-Fi and P1S LAN credentials are still stored in plaintext NVS. Genuine NVS
encryption on this ESP32-P4 requires an irreversible HMAC or flash-encryption
eFuse decision, so routine builds deliberately leave it disabled. See
`docs/SECURITY_PROVISIONING.md` for the recovery constraints and approval gate.

## Integration roadmap

The next controller milestone is on-device v0.7.2 regression testing and a
deliberate wired partition-table update, followed by a reviewed decision on
encrypted-at-rest credential provisioning. Nova Horizon backend and Jetson Orin
Nano vision adapters can then be added without coupling them to the display
driver, printer transport, or UI.
