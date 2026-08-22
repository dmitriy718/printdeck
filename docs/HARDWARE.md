# PrintDeck Hardware Reference

This is the maintained hardware reference for the current PrintDeck target.
Changing pins, bus ownership, partition boundaries, or power assumptions
requires hardware validation before deployment.

## Supported board

| Item | Value |
|---|---|
| Board | JC4880P443 |
| Main SoC | ESP32-P4NRW32 |
| PSRAM | 32 MB |
| Flash | 16 MB |
| Wi-Fi coprocessor | ESP32-C6 over ESP-Hosted SDIO |
| Display controller | ST7701S |
| Display resolution | 480 × 800 native; 800 × 480 application landscape |
| Touch controller | GT911 |
| Development/recovery | Native USB 2.0 |

## Display

The ST7701S display uses MIPI DSI:

| Parameter | Value |
|---|---|
| Pixel clock | 34 MHz |
| Data lanes | 2 |
| Lane bit rate | 500 Mbps |
| Horizontal back porch | 42 |
| Horizontal pulse width | 12 |
| Horizontal front porch | 42 |
| Vertical back porch | 8 |
| Vertical pulse width | 2 |
| Vertical front porch | 166 |
| Panel reset | GPIO 5 |
| DSI power | LDO channel 3 at 2.5 V |

The UI is landscape. Rotation from the panel's native orientation is performed
with the ESP32-P4 PPA path.

## Touch

| Signal | GPIO |
|---|---:|
| I²C SDA | 7 |
| I²C SCL | 8 |

The current target uses a GT911 capacitive touch controller.

## Backlight

| Parameter | Value |
|---|---|
| PWM GPIO | 23 |
| PWM frequency | 20 kHz |
| Initial application level | 82% |

Brightness control is local to PrintDeck and does not send a printer command.

## Wi-Fi coprocessor

The ESP32-C6 connects to the ESP32-P4 using Espressif's Hosted SDIO transport.

| Signal group | GPIOs |
|---|---|
| SDIO bus | 14–19 |
| C6 reset | 54 |
| SDMMC controller/slot | Shared controller, slot 1 |

The source currently uses ESP-Hosted host component 2.11.7. A deployed C6
firmware version of 2.3.0 has been observed. Treat that mismatch as an open
compatibility qualification item rather than an assumed-safe pairing.

## External SD card

The external card uses native four-bit SDMMC and shares the controller with
ESP-Hosted:

| Signal | GPIO |
|---|---:|
| CLK | 43 |
| CMD | 44 |
| D0 | 39 |
| D1 | 40 |
| D2 | 41 |
| D3 | 42 |
| SDMMC slot | 0 |
| Power | LDO channel 4 |

The supported filesystem is FAT32 and the mount point is `/sdcard`. The current
product reports card status and indexes bounded 3MF metadata under
`/PrintDeck/files`, but does not transfer or start files.

## Boot strap

| Function | GPIO |
|---|---:|
| BOOT strap | 35 |

The current application opens its 300-second OTA upload window from the
on-screen System page, not from GPIO 35. The BOOT strap remains relevant to
board recovery and must not be documented as OTA authorization.

## USB

Native USB is used for development flashing, recovery, and serial monitoring.
On Linux it normally appears as `/dev/ttyACM*` with USB VID/PID `303a:1001`.

The device number is not stable across reconnects. Resolve the active port
immediately before flashing. Opening a serial monitor may reset the controller,
so do not treat monitor attachment as a passive production-health check.

## Flash partition map

| Name | Offset | Size | Purpose |
|---|---:|---:|---|
| `nvs` | `0x11000` | `0x6000` | Preferences and credentials |
| `otadata` | `0x17000` | `0x2000` | Active OTA slot metadata |
| `phy_init` | `0x19000` | `0x1000` | Radio PHY data |
| `ota_0` | `0x20000` | `0x600000` | Application slot A |
| `ota_1` | `0x620000` | `0x600000` | Application slot B |
| `storage` | `0xC20000` | `0x360000` | Reserved LittleFS partition |
| `coredump` | `0xF80000` | `0x80000` | 512 KiB flash coredump area |

The internal `storage` partition is reserved but not currently mounted or used.
Do not confuse it with the external SD card.

Partition-table changes cannot be delivered safely as an application-only OTA
update. Use a wired flash that writes the generated partition table and verify
the runtime partition report afterward.

## Hardware validation checklist

After changes involving board configuration or deployment:

1. Confirm the expected panel image and touch alignment.
2. Exercise backlight control across its range.
3. Connect Wi-Fi and verify ESP-Hosted remains stable.
4. Mount and remove a FAT32 SD card.
5. Connect to the printer and observe telemetry.
6. Open and leave the Camera page repeatedly.
7. Inspect reset reason, coredump partition size, free heap, and minimum task
   stack values.
8. Power-cycle more than once and watch for brownout or boot-loop behavior.
9. Confirm native USB recovery remains available.

## Related documents

- [Architecture](ARCHITECTURE.md)
- [Operations](OPERATIONS.md)
- [Release Process](RELEASE_PROCESS.md)
- [Troubleshooting](TROUBLESHOOTING.md)
