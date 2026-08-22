# PrintDeck Operations Guide

This guide is for operating, observing, updating, and recovering a deployed
PrintDeck controller. It complements the end-user [User Guide](USER_GUIDE.md).

## Current operational baseline

| Item | Status |
|---|---|
| Most recently verified deployed firmware | 0.7.2 |
| Current source release | 1.0.0 |
| Supported printer | Bambu Lab P1S |
| Connectivity | Local network; printer MQTT/TLS and camera/TLS |
| Update transport | Local HTTP during an on-device authorization window |
| Application authenticity | RSA-3072 signed images |
| Hardware Secure Boot | Not enabled |

Do not assume a controller runs the source-tree version. Query the device
status before an update or incident investigation.

## Routine startup

A normal controller startup should:

1. show the PrintDeck UI;
2. initialize the on-board Wi-Fi coprocessor;
3. reconnect to a saved network when configured;
4. mount an inserted FAT32 SD card;
5. allow a configured printer connection;
6. report no pending OTA rollback after the stable boot interval.

The saved printer is not proof of a live connection. Confirm that telemetry is
current before using printer controls.

## OTA status endpoint

Once the controller has an IP address, retrieve:

```text
http://CONTROLLER_IP/api/v1/ota
```

The `GET` response reports operational fields including:

- service identity;
- firmware version;
- OTA-window state;
- uptime and reset reason;
- running partition;
- pending rollback state;
- coredump partition status;
- free heap;
- minimum observed task stack values.

Treat this endpoint as sensitive local operational data. It has no transport
encryption in the current design and should be reachable only on a trusted
local network.

## Health interpretation

| Signal | Healthy interpretation | Investigate when |
|---|---|---|
| Version | Matches the intended deployed release | Older, unexpected, or blank |
| Running partition | One of the intended OTA app slots | Factory/unknown partition or repeated slot changes |
| Pending rollback | Clears after stable runtime | Remains pending or device repeatedly reboots |
| Reset reason | Expected power-on/software transition | Brownout, watchdog, panic, or repeated reset |
| Coredump partition | Present with 512 KiB capacity | Missing, wrong size, or contains an unexplained crash |
| Free heap | Stable under repeated page/network use | Persistent decline or allocation failures |
| Minimum task stack | Retains a practical margin | Approaches exhaustion |

Absolute heap and stack thresholds depend on the running workload. Trend values
through repeated operations instead of treating one sample as a guarantee.

## Safe update procedure

Use the exact process in [Release Process](RELEASE_PROCESS.md). Operationally:

1. Confirm the target IP is a literal private RFC1918 address.
2. Confirm the status service identity and current version.
3. Keep the controller on stable power.
4. Open the OTA window from the controller's System page.
5. Upload the signed application with the repository uploader.
6. Wait for reboot and the stable validation interval.
7. Confirm the new version, expected partition, cleared rollback state, and
   normal UI/printer behavior.

An application OTA does not update the partition table, bootloader, ESP32-C6
firmware, or other flash regions. Use a wired release procedure when those
artifacts change.

## Backup and recovery boundaries

PrintDeck does not currently provide an export/restore workflow for NVS.
Record the following outside the device before destructive recovery:

- Wi-Fi SSID;
- printer IP address;
- printer serial number;
- the fact that the LAN access code will need to be re-entered;
- selected timezone.

Do not put access codes in issue reports or ordinary operational logs.

Native USB remains the recovery path for a non-booting application. A wired
flash can rewrite the bootloader, partition table, and application, but may
erase or invalidate stored settings depending on the command used. Resolve the
actual `/dev/ttyACM*` port immediately before flashing.

## Incident capture

For a reset, disconnect, or UI failure, capture:

1. controller firmware version;
2. approximate incident time and timezone;
3. status endpoint output with secrets removed;
4. reset reason and coredump status;
5. running OTA partition and rollback state;
6. printer model and firmware version;
7. whether a print was active;
8. the page/action in use;
9. Wi-Fi signal/environment observations;
10. whether the fault reproduces after one clean reboot.

Attach a serial log only after checking it for SSIDs, addresses, serial
numbers, access codes, and other identifying data. Remember that attaching a
serial monitor may itself reset the device.

## Factory-style reprovisioning

There is no dedicated factory-reset UI in the current release. Do not erase NVS
as a routine troubleshooting step. If a full wired erase is intentionally
performed, all saved network, printer, and timezone settings must be
re-entered.

## Network expectations

- PrintDeck and the P1S must be reachable over the local network.
- Client isolation or guest-network separation can prevent local printer
  connectivity.
- Printer MQTT uses TLS on port 8883.
- Camera traffic uses the printer's local TLS stream.
- OTA upload uses local HTTP port 80 on the controller only while authorized.
- No Horizon cloud dependency is required by the current firmware.

## SD-card operations

Use FAT32 media. Insert/remove cards while no future file operation is active;
the current release only reports status, but this remains the safe operational
habit. If the card is not recognized, use the System/Files status and the
troubleshooting guide rather than repeatedly power-cycling during a print.

## Known operational risks

- A power brownout was observed during v0.7.0 validation.
- The installed ESP32-C6 firmware and host component versions require
  compatibility qualification.
- Credentials are plaintext in NVS.
- NVS may be erased automatically after certain initialization errors.
- Bounded queues can reject/drop work under load.
- Automated hardware-in-the-loop regression is not available.

## Related documents

- [User Guide](USER_GUIDE.md)
- [Release Process](RELEASE_PROCESS.md)
- [Troubleshooting](TROUBLESHOOTING.md)
- [Security](SECURITY.md)
