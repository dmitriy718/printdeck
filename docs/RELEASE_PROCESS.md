# PrintDeck Release Process

This is the supported procedure for preparing, validating, deploying, and
recording a PrintDeck firmware release.

## Release principles

- A source version, built artifact, and deployed version are three separate
  facts.
- Every shipped application image is signed.
- A release is not considered deployed until the running device reports it and
  clears pending rollback.
- Application OTA is used only when the flash layout and non-application
  artifacts remain compatible.
- Release notes describe user-visible behavior and unresolved risk honestly.

## 1. Prepare the version

Update the project version in the top-level `CMakeLists.txt`. Add the release
entry to `CHANGELOG.md` with:

- version and date;
- user-visible additions and changes;
- important fixes;
- security or deployment changes;
- known limitations that materially affect use;
- whether the entry represents source, candidate, or verified deployment.

Update all maintained documentation affected by the change. Do not rewrite
historical review evidence to make it match the new release.

## 2. Verify the repository

From the repository root:

```sh
tests/run_host_tests.sh
shellcheck scripts/*.sh tests/*.sh
python3 -m py_compile tests/*.py \
    docs/bambu-lab-outreach/tools/generate_outreach_package.py
git diff --check
```

Run the compiler static analyzer using the current compile database when the
change affects C/C++ code. See [Testing](TESTING.md) for the maintained
verification matrix and commands.

Review:

```sh
git status --short
git diff --stat
git diff
```

Ensure private signing material, credentials, generated build output, and
unrelated user files are not staged.

## 3. Build the signed application

```sh
source scripts/idf-env.sh
scripts/setup-signing-key.sh
idf.py build
```

Record at least:

- project version;
- ESP-IDF version;
- application image path and byte size;
- SHA-256 digest;
- signing-key public fingerprint;
- build/test result.

The signing setup script must refuse to silently replace an expected key when
the private key is missing or does not match the committed public identity.

## 4. Choose the deployment path

### Application-only OTA

OTA is appropriate when only the application slot contents change and all of
the following remain compatible:

- bootloader;
- partition table;
- OTA data layout;
- ESP32-C6 firmware;
- required NVS schema.

### Wired flash

Use native USB when changing:

- partition boundaries or types;
- bootloader behavior;
- flash-encryption/Secure Boot policy;
- recovery-critical SDK configuration;
- ESP32-C6 firmware or transport pairing;
- any artifact outside the application slot.

Partition-table changes require a wired flash. An application-only OTA cannot
make the runtime flash map match `partitions.csv`.

## 5. Deploy by OTA

The supported uploader is `scripts/ota-update.sh`. It accepts exactly one
argument: the controller's literal RFC1918 IPv4 address.

The uploader enforces:

- a literal RFC1918 target address;
- expected PrintDeck OTA service identity;
- an open on-device authorization window;
- expected signing-key digest;
- exact successful response semantics;
- post-reboot version verification.

Deployment sequence:

1. Place the controller on reliable power and the trusted local network.
2. Query `GET /api/v1/ota`; record the old version and running partition.
3. On the System page, tap **ENABLE OTA** to open the 300-second, single-use
   window.
4. Upload the newly built signed application:

   ```sh
   scripts/ota-update.sh CONTROLLER_RFC1918_IP
   ```
5. Do not remove power during write or reboot.
6. Wait for the controller to boot and pass its stable validation interval.
7. Query status again.

## 6. Deploy by native USB

Resolve the current port:

```sh
ls -l /dev/serial/by-id/ /dev/ttyACM* 2>/dev/null
```

Then use the explicit device path:

```sh
idf.py -p /dev/ttyACM0 flash
```

Replace `/dev/ttyACM0` with the port actually present. The generated flash
arguments determine which artifacts are written; review the build output when
the release depends on a partition or bootloader change.

Do not rely on a remembered device number. Do not erase all flash unless the
release or recovery procedure explicitly requires losing saved state.

## 7. Post-deployment acceptance

Verify on the actual controller:

- reported version equals the intended release;
- service identity is correct;
- running partition is the newly selected slot;
- pending rollback clears;
- coredump partition is present at 512 KiB;
- reset reason is expected;
- UI boots and touch is aligned;
- Wi-Fi reconnects;
- printer connects and telemetry becomes live;
- pause/resume/cancel controls follow printer state;
- chamber-light toggle works;
- camera enters and exits repeatedly without resource decline;
- external FAT32 SD status is correct;
- free heap and task stack margins remain stable;
- at least one cold power cycle succeeds.

For a change touching shared SDMMC ownership, validate both ESP-Hosted Wi-Fi
and external SD in the same run.

## 8. Record the release

Record:

- commit ID;
- artifact SHA-256 and size;
- deployment method;
- controller identity without secrets;
- old and new versions;
- old and new running partitions;
- rollback result;
- validation observations;
- unresolved anomalies.

Use the established dated record under `Reviews/` for a formal review or
deployment log. Update the changelog only with facts supported by source,
artifacts, device output, or preserved review evidence.

## Rollback

If the new application cannot reach stable validation, allow the ESP-IDF OTA
rollback mechanism to select the previous valid slot. Do not mark a failing
image valid merely to keep its version installed.

If both application slots or the flash layout are unusable, recover over native
USB from a known signed build and matching partition table. Re-enter settings
only after the recovery image is stable.

## Release checklist

- [ ] Version and changelog updated
- [ ] Maintained documentation updated
- [ ] Host tests and invariants pass
- [ ] Shell and Python checks pass
- [ ] Static analysis reviewed
- [ ] Signed build succeeds
- [ ] Artifact size, SHA-256, and key fingerprint recorded
- [ ] Correct deployment path selected
- [ ] Running version and partition verified
- [ ] Pending rollback cleared
- [ ] Hardware acceptance completed
- [ ] Release/deployment evidence saved
