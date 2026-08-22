# PrintDeck Glossary

| Term | Meaning in this project |
|---|---|
| Application slot | One of the two flash regions (`ota_0`, `ota_1`) that can hold PrintDeck firmware |
| Bambu local API | The printer-local MQTT and camera interfaces used by PrintDeck; availability depends on printer firmware and mode |
| BOYA | Flash-chip manufacturer detected on the current board and explicitly enabled in the bootloader/application configuration |
| Candidate | Source and artifact prepared for validation but not yet accepted as the deployed release |
| Coredump | Crash-state data stored in the dedicated 512 KiB flash partition; potentially contains secrets |
| Deployed | Observed running on the target hardware, not merely compiled |
| Developer Mode | A Bambu printer setting that can expose local integrations while changing the printer's security/support boundary |
| ESP32-C6 | On-board Wi-Fi coprocessor connected to the ESP32-P4 through ESP-Hosted |
| ESP32-P4 | Main controller SoC that runs the PrintDeck application and UI |
| ESP-Hosted | Espressif transport that lets the P4 use networking supplied by the C6 |
| FAT32 | Supported filesystem for the external controller SD card |
| GT911 | Capacitive touch controller used by the JC4880P443 |
| HIL | Hardware-in-the-loop automated testing against real electronics |
| HMS | Bambu's health/error reporting system; an actionable HMS center is recommended but not implemented |
| JC4880P443 | Current 4.3-inch ESP32-P4 controller board target |
| LAN access code | P1S credential used for authenticated local printer services |
| LittleFS | Embedded filesystem type assigned to the reserved internal `storage` partition; not currently mounted |
| LVGL | Graphics/UI library used to render PrintDeck |
| MQTT | Publish/subscribe protocol used for P1S telemetry and supported commands |
| NVS | ESP-IDF key/value flash storage used for Wi-Fi, printer, and timezone settings |
| On-device authorization window | Five-minute, single-use OTA permission opened from PrintDeck's System page |
| OTA | Over-the-air application update written to the inactive application slot |
| P1S | Bambu Lab printer model currently supported by PrintDeck |
| PPA | ESP32-P4 Pixel Processing Accelerator used in display/camera image transformations |
| PSK | Pre-shared Wi-Fi key; PrintDeck accepts passphrases or a 64-character raw hexadecimal value |
| PSRAM | External pseudo-static RAM used by the UI and camera pipeline |
| RFC1918 | The private IPv4 ranges accepted by the host OTA updater |
| Rollback | Bootloader recovery to the prior valid application if a new image fails validation |
| Signed app | Application image carrying a signature from the PrintDeck RSA-3072 project key |
| SNTP | Network time synchronization started after Wi-Fi obtains an IP address |
| Source version | Version declared by the current source tree; it may be newer than deployed hardware |
| ST7701S | MIPI-DSI display controller used by the target panel |
| Telemetry | Printer-reported live state such as job progress, temperatures, layers, and fan/light status |
| Trust anchor | CA certificate used to validate the printer's TLS certificate chain |

