# PrintDeck Testing

Testing is layered because host checks cannot validate electrical behavior and
target testing alone does not efficiently cover parser and repository
invariants.

## Verification matrix

| Layer | What it covers | Current automation |
|---|---|---|
| Host parser tests | MQTT telemetry parsing, bounds, stale data, malformed input | Automated with ASan/UBSan |
| Repository invariants | Security, configuration, UI truthfulness, release assumptions | Automated Python checks |
| Script checks | Shell correctness and common unsafe constructs | ShellCheck |
| Python checks | Syntax of test and documentation tooling | `py_compile` |
| Compiler analysis | Cross-function C defects and suspicious flows | GCC `-fanalyzer` review |
| Firmware build | ESP-IDF integration, link, image signing, size | Automated build |
| Target regression | Display, touch, buses, Wi-Fi, printer, camera, OTA | Manual |
| Long-duration/HIL | Leaks, reconnect endurance, power and printer-state matrices | Not yet automated |

## Standard host suite

Run:

```sh
tests/run_host_tests.sh
```

The suite compiles the telemetry parser with AddressSanitizer and
UndefinedBehaviorSanitizer, executes its cases, and then runs the Python
repository invariants.

The telemetry parser suite contains 18 cases and the history-record codec suite
contains three cases. Both run with AddressSanitizer and
UndefinedBehaviorSanitizer. The invariant count can grow as new product
guarantees are encoded; use the test output as the authoritative current count.

## Supporting checks

```sh
shellcheck scripts/*.sh tests/*.sh
python3 -m py_compile tests/*.py \
    docs/bambu-lab-outreach/tools/generate_outreach_package.py
git diff --check
```

If a new Python or shell file is added, include it in the appropriate check.
Warnings must be reviewed; do not suppress them globally to make a release
green.

## Firmware build

```sh
source scripts/idf-env.sh
scripts/setup-signing-key.sh
idf.py build
```

Verify:

- the configured source version;
- signed image generation;
- partition fit;
- no newly introduced warnings;
- the final artifact size and SHA-256.

## Compiler static analysis

Generate or use the ESP-IDF compile database, then apply GCC's `-fanalyzer` to
the product translation units with their actual compiler flags. Review every
diagnostic in context; generated/managed dependencies should be separated from
product findings.

Static analysis is a defect-finding aid, not proof that concurrent task,
hardware, or protocol behavior is correct.

## Manual target regression

Perform this checklist on the JC4880P443:

### Boot and display

- cold boot;
- correct PrintDeck branding;
- no visible boot loop;
- landscape image and correct touch coordinates;
- stable brightness control.

### Network and persistence

- scan;
- join a WPA2 network;
- reconnect after reboot;
- reject invalid-length credentials;
- recover after an unavailable access point;
- preserve the last valid profile after a failed replacement.

### Printer

- reject invalid profile fields;
- connect to the P1S over local MQTT/TLS;
- show live temperatures, progress, layers, and job name;
- clear or visibly stale connection-dependent data after disconnect;
- validate pause, resume, cancel, and light state eligibility;
- confirm UI says a command is queued rather than completed;
- exercise reconnect and printer reboot.

Use an idle printer for destructive/cancel-path validation unless the test plan
explicitly authorizes interrupting a job.

### Camera

- open a live camera stream;
- leave and re-enter the page repeatedly;
- disconnect Wi-Fi while active;
- change/reload printer profile;
- observe free heap across repeated cycles.

### Storage and shared bus

- boot with and without a FAT32 card;
- insert/remove a card;
- verify SD status;
- exercise Wi-Fi and SD during the same session;
- confirm neither shared SDMMC slot disrupts the other.

### OTA and recovery

- status endpoint identifies the service and old version;
- upload is rejected outside the on-device authorization window;
- invalid/unsigned image is rejected;
- valid image is accepted once inside the window;
- window cannot be reused;
- new version boots from the expected slot;
- pending rollback clears after stability;
- native USB recovery remains available.

### Diagnostics and endurance

- inspect reset reason and coredump partition;
- repeat page transitions and connection cycles;
- monitor free heap and minimum task stack;
- perform repeated warm and cold restarts;
- investigate any brownout, watchdog, or panic.

## Required tests by change type

| Change | Minimum additional validation |
|---|---|
| Parser or telemetry | Host cases for valid, missing, malformed, bounded, and stale inputs |
| UI | Truthfulness invariant plus target touch/page regression |
| Network/MQTT concurrency | Disconnect/reconnect stress and static analysis |
| Camera | Repeated enter/exit and failure cleanup with heap trend |
| Board pins/bus | Full hardware checklist and simultaneous shared-bus exercise |
| Partition/bootloader | Wired flash, runtime partition verification, recovery test |
| OTA/security | Negative signature/window/identity tests and rollback test |
| Persistence | Upgrade, partial-write, failed replacement, and reboot tests |
| Documentation-only | Link/invariant checks and command verification |

## Known test gaps

- no automated hardware-in-the-loop rig;
- no UI simulator or screenshot regression;
- no long-duration soak in continuous integration;
- no automated power-fault injection;
- no broad printer-firmware compatibility matrix;
- no qualified matrix for ESP-Hosted host vs installed ESP32-C6 firmware;
- no automated credential-at-rest security test.

These gaps must be considered in release risk; they are not reasons to describe
manual observations as automated guarantees.

## Related documents

- [Development Guide](DEVELOPMENT.md)
- [Release Process](RELEASE_PROCESS.md)
- [Hardware Reference](HARDWARE.md)
- [Troubleshooting](TROUBLESHOOTING.md)
