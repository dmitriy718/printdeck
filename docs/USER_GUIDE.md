# PrintDeck user guide

This guide describes the current v0.7.3 source interface while identifying
features that are only confirmed on the deployed v0.7.2 controller.

## Before setup

You need:

- the JC4880P443 controller with compatible PrintDeck firmware;
- a Bambu Lab P1S on the same trusted local network;
- the Wi-Fi SSID and password;
- the P1S IPv4 address;
- the P1S device serial; and
- the P1S LAN access code.

The printer must expose the local interfaces required by its firmware. On
newer Bambu firmware this can require LAN-only or Developer Mode. Enabling
Developer Mode changes the printer's local security/support boundary; secure
the LAN and understand the printer's warning before enabling it.

PrintDeck does not discover printers yet. Enter the exact IP and serial shown
by the intended P1S.

## First boot and Wi-Fi

1. Power the controller from a stable supply.
2. Wait for the display and touch interface to appear.
3. Open **System**.
4. If no saved Wi-Fi profile is valid, choose **Wi-Fi setup** and scan.
5. Select the intended network and enter its password.
6. Submit the connection and wait for the System page to show a network IP.

The password field is masked. PrintDeck accepts normal WPA/WPA2 passwords and
standards-compliant 64-character raw hexadecimal PSKs. A new profile is saved
only after the controller receives an IP address. If a replacement profile
fails authentication repeatedly, the last verified profile is restored when
available.

## Pair the P1S

1. Confirm the controller is connected to Wi-Fi.
2. On **System**, open the printer pairing dialog.
3. Enter the P1S IPv4 address, device serial, and LAN access code.
4. Submit the profile.
5. Wait for the printer status to become **ONLINE**.

The serial must be 10–31 alphanumeric characters. The access code must be
8–16 characters. The profile is not persisted until an authenticated TLS/MQTT
session succeeds. A definitively rejected replacement rolls back to the last
verified P1S profile when one exists.

If the controller clock has not synchronized yet, a certificate-time failure
is treated as transient rather than as proof that the profile is wrong.

## Navigation

The left navigation contains six pages.

### Dashboard

The Dashboard shows:

- P1S connection and telemetry readiness;
- job state and name;
- progress percentage;
- current/total layer;
- remaining time;
- nozzle, bed, and chamber temperatures;
- chamber-light state; and
- validated quick actions.

Buttons remain disabled when the printer is offline, the action is not
supported, or the current job state does not permit it.

### Job

The Job page provides a larger view of the active print and exposes:

- **Pause** only while printing;
- **Resume** only while paused; and
- **Cancel print** while preparing, printing, or paused.

Cancel opens a confirmation dialog. After a successful tap, `Command queued`
means the controller accepted the local request. It does not yet mean that the
printer acknowledged the command. Watch the live state for the observed
result.

### Control

Axis movement, homing, fan control, preheat, and cooldown remain deliberately
disabled in current firmware. Their buttons are scaffolding for validation and
do not send commands.

During an active or paused job, the page explains the additional print-state
lock. Do not interpret visible buttons as implemented capabilities.

### Files

The Files page separates two storage devices:

- **Controller SD** is the FAT32 card in the JC4880P443.
- **P1S SD** is telemetry reported by the printer.

Use **Rescan SD** after inserting or reinserting controller media. The firmware
indexes bounded `.3mf` metadata and previews from `/PrintDeck/files`. It does
not yet transfer files to the printer or start prints.
It never formats a card automatically.

### Camera

Opening Camera starts the local P1 liveview only when:

- Wi-Fi is connected;
- the P1S session is online; and
- the current printer profile has been authenticated and persisted.

Leaving Camera stops the stream and releases its large buffers. A reconnecting
message is expected during a temporary interruption. A camera error does not
enable a weaker identity check.

### System

System contains:

- printer name, model, serial, and connection state;
- firmware version;
- current and minimum internal heap;
- PSRAM and persistent-task stack health;
- brightness;
- timezone;
- Wi-Fi setup/status;
- P1S pairing/status; and
- the on-device OTA authorization control.

Tapping the timezone button cycles through 15 built-in presets and persists the
selection. Brightness changes immediately.

## SD-card behavior

- Mount point: `/sdcard`.
- Supported project configuration: FAT32.
- Mounting is non-destructive.
- Automatic formatting is disabled.
- A large SDXC card commonly ships as exFAT and may not mount.

Back up the card before any host-side reformat. PrintDeck never authorizes
formatting merely because a mount failed.

## Firmware updates

Routine LAN update procedure:

1. A developer/operator builds and verifies the signed firmware.
2. On System, tap **Enable OTA**. The window lasts five minutes.
3. From the trusted development host, run:

   ```sh
   scripts/ota-update.sh <controller-rfc1918-ip>
   ```

4. Wait for the uploader to verify the returned PrintDeck version.

The window is single-use: it closes when an upload starts. Do not retry blindly
after a disconnect. See [Operations](OPERATIONS.md) and
[Troubleshooting](TROUBLESHOOTING.md).

## Status meanings

| Display state | Meaning | Suggested response |
| --- | --- | --- |
| Setup required | No usable saved P1S profile | Configure Wi-Fi, then pair the P1S |
| Connecting | Local printer session is being established | Wait; verify network if prolonged |
| Online | Authenticated MQTT session exists | Normal operation |
| Offline | Profile exists but transport is unavailable | Check power, IP, Wi-Fi, and printer mode |
| Access code rejected | Printer denied authentication | Re-enter the exact LAN access code |
| Identity check failed | TLS certificate/identity check failed | Confirm serial/IP and synchronized time |
| Connection error | Local transport or initialization error | Inspect System status and logs |
| Camera reconnecting | Camera stream was interrupted | Wait or leave/reopen Camera |
| Controller SD / FAT32 needed | No usable controller FAT32 volume | Check insertion/filesystem; do not format without backup |

## Safe daily-use checklist

- Confirm the controller is showing the intended printer identity.
- Confirm the displayed job name/state before using a command.
- Use the physical printer controls if PrintDeck state appears stale.
- Treat cancel as irreversible.
- Do not expose the controller's HTTP OTA endpoint outside a trusted LAN.
- Do not share photos containing serials, IP addresses, access codes, or GPS
  metadata.
