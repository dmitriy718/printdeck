# PrintDeck Troubleshooting

Start with the least destructive check. Do not erase NVS, reformat media, retry
an uncertain OTA, or interrupt a live print merely to gather more evidence.

## First checks

1. Confirm stable controller and printer power.
2. Record the PrintDeck version shown on System.
3. Confirm the intended printer identity.
4. Note whether a print is active.
5. If networking works, retrieve `GET /api/v1/ota` and record reset reason,
   running partition, rollback state, heap, stack, and coredump size.
6. Reproduce once only if doing so is safe.

## Controller does not boot

Check:

- display power and cable/board connections;
- whether native USB enumerates;
- status LED or serial output;
- reset reason after recovery;
- whether the fault followed an application OTA or a wired partition change.

If an OTA candidate repeatedly resets before validation, allow automatic
rollback. If neither application slot boots, use native USB with the matching
known-good build and partition table. A serial monitor can reset the device, so
account for that in the timeline.

## Display is blank or touch is wrong

- Confirm the firmware targets JC4880P443 and ESP32-P4 revision v1.x.
- Confirm LCD reset GPIO 5, touch SDA/SCL GPIO 7/8, and backlight GPIO 23.
- Verify the 480 × 800 native panel is configured for 800 × 480 application
  landscape.
- If the image appears but touch coordinates are rotated, inspect display and
  touch transform settings as one change.
- If the image is very dark, test the System brightness control.

Do not deploy guessed panel timing to production hardware. Use the values in
[Hardware Reference](HARDWARE.md).

## Wi-Fi scan shows no networks

- Wait for ESP-Hosted initialization to finish.
- Confirm the ESP32-C6 reset and SDIO GPIO configuration.
- Retry a scan after the UI returns to a ready state.
- Check whether the host reports the known C6/ESP-Hosted version mismatch.
- Test close to the access point to separate signal from transport failure.

If both Wi-Fi and external SD fail, inspect shared SDMMC controller ownership
and slot assignment before treating them as separate faults.

## Wi-Fi will not connect

- Confirm the exact SSID and password.
- For a normal WPA/WPA2 passphrase, use 8–63 characters.
- A 64-character password must be raw hexadecimal.
- Check guest-network/client-isolation settings.
- Confirm the access point supports a mode compatible with the controller.
- Observe whether the previous verified profile is restored after the failed
  replacement.

Do not post the password or a full connection log publicly.

## Clock is wrong

- Confirm the controller received an IP address; SNTP starts after that point.
- Wait for time synchronization.
- Cycle the timezone preset on System to the correct region.
- Reboot once to confirm persistence.

A bad clock can temporarily affect certificate validation. Do not replace a
known-good printer profile solely because time has not synchronized.

## Printer remains offline

- Confirm PrintDeck and the P1S can reach each other on the LAN.
- Verify the printer IPv4 address has not changed.
- Re-enter the exact device serial and LAN access code.
- Confirm the serial is 10–31 alphanumeric characters and the access code is
  8–16 characters.
- Check whether the printer's current firmware requires LAN-only or Developer
  Mode for local integration.
- Inspect whether the failure is transport, authentication, or TLS identity.

`Access code rejected` points to authentication. `Identity check failed` points
to certificate/serial/time validation. Do not bypass TLS verification to make
either message disappear.

## Telemetry looks stale

- Confirm the printer state says Online.
- Compare the displayed job name and state with the physical printer.
- Wait for a complete report cycle after reconnect.
- Leave printer controls alone if PrintDeck and the printer disagree.
- Capture the sequence of MQTT partial/delta reports with credentials removed
  if the problem is reproducible.

The physical printer is the authority during a disagreement.

## A command appears to do nothing

`Command queued` means the local queue accepted the action, not that the P1S
acknowledged or completed it.

- Confirm the live printer state still permits the action.
- Watch for the expected state change.
- Check for a reconnect between touch and dispatch.
- Review queue-full or publish errors.
- Use the printer's own controls if immediate intervention is needed.

Motion, fan, preheat, cooldown, homing, and file-start controls are not
implemented in the current release.

## Camera will not start

- Confirm Wi-Fi and the authenticated P1S session are online.
- Confirm the current profile was successfully persisted.
- Leave and reopen Camera once.
- Check printer-side camera availability and local integration mode.
- Observe free heap before and after repeated page entry/exit.

Do not weaken identity validation or log the camera authentication packet.

## SD card is not recognized

- Use FAT32 media.
- Confirm the card is inserted correctly.
- Tap **Rescan SD**.
- Check whether the card is exFAT, which is common for larger SDXC media.
- Back up the card before any host-side conversion or formatting.
- Test a known-good FAT32 card to separate media from bus/power faults.

PrintDeck does not auto-format a failed mount. The internal LittleFS `storage`
partition is unrelated to the external `/sdcard` mount.

## OTA updater refuses the target

The updater intentionally requires:

- a literal IPv4 address in `10.0.0.0/8`, `172.16.0.0/12`, or
  `192.168.0.0/16`;
- HTTP 200 from the expected PrintDeck-compatible service;
- an open System-page OTA window;
- a firmware image signed by the committed key identity.

Use:

```sh
scripts/ota-update.sh CONTROLLER_RFC1918_IP
```

Hostnames, public addresses, redirects, closed windows, unsigned builds, and
unexpected services are rejected.

## OTA connection drops during upload

Do not immediately retry.

1. Let `scripts/ota-update.sh` perform its return-state checks.
2. Query the status endpoint after the controller returns.
3. Record version, partition, and reset reason.
4. If the requested version is not selected, diagnose the reset before opening
   a new window.
5. If the requested version runs but the success response was lost, treat the
   deployment as unconfirmed until rollback clears and acceptance passes.

An older v0.7.0 OTA write triggered a watchdog reset on BOYA flash before the
v0.7.1 flash-driver correction. Do not infer the same cause without current
evidence.

## New version rolls back

- Record the candidate's reset reason and coredump.
- Confirm whether it survived the 10-second validation interval.
- Preserve the rolled-back, working slot.
- Reproduce on a development controller using native USB/serial evidence.
- Fix and rebuild; do not force-mark a crashing candidate valid.

## Brownout or unexplained reset

- Use a stable supply and short, appropriate cable.
- Record reset reason.
- Observe whether camera, Wi-Fi, or flash write load triggers the event.
- Check power at the board under load if suitable instrumentation is available.
- Distinguish brownout, watchdog, panic, and operator-induced monitor reset.

One brownout was observed during v0.7.0 validation; it remains an open hardware
risk, not a confirmed universal defect.

## Reporting a defect

Include the non-secret evidence listed in [Operations](OPERATIONS.md). State
what you expected, what happened, and whether the same action is safe to repeat.
Redact credentials and treat coredumps as confidential.

