# PrintDeck Development Guide

This guide covers a local build, the repository structure, configuration
boundaries, and the normal edit-and-verify workflow.

## Prerequisites

- Linux development environment;
- Git;
- GCC for host tests;
- Python 3;
- ShellCheck for script checks;
- the repository's pre-provisioned ESP-IDF toolchain;
- a JC4880P443 target for hardware validation.

The repository currently expects its ESP-IDF and tools to have already been
provisioned under ignored local paths. There is no supported bootstrap
installer yet.

Supported ESP-IDF range:

```text
>= 6.0, < 6.1
```

The verified local SDK version is ESP-IDF 6.0.2.

## Environment and build

From the repository root:

```sh
source scripts/idf-env.sh
scripts/setup-signing-key.sh
idf.py build
```

`setup-signing-key.sh` verifies or creates the local development signing key
under `security/private/`. That directory is ignored by Git. Read
[Security](SECURITY.md) before changing key material.

The build produces a signed ESP application image. A successful compile alone
does not qualify a release; run the checks in [Testing](TESTING.md).

## Repository layout

```text
controller/
├── CMakeLists.txt                 project metadata and version
├── main/                          application entry point
├── components/                    product components
├── docs/                          maintained product documentation
├── Reviews/                       dated review and recommendation records
├── scripts/                       environment, signing, and OTA helpers
├── security/                      committed public trust metadata
├── tests/                         host tests and repository invariants
├── managed_components/            locked ESP-IDF component dependencies
├── partitions.csv                 16 MB flash partition table
├── sdkconfig.defaults             maintained target defaults
├── CHANGELOG.md                   chronological product history
└── README.md                      concise project entry point
```

Generated build output, local tools, private keys, and local images are not
product documentation and should not be committed unless explicitly required.

## Component dependency summary

| Dependency | Current line |
|---|---|
| ESP-IDF | 6.0.2, constrained to 6.0.x |
| LVGL | 9.5 |
| `esp_lvgl_port` | 2.8.x |
| ST7701 panel component | 2.0.2 |
| GT911 touch component | locked 1.2.x line |
| ESP-Hosted | 2.11.7 |
| `wifi_remote` | 1.6.3 |
| ESP-MQTT | 1.0 |
| cJSON | 1.7.19 |

The component lock file is authoritative for exact resolved versions. When
updating dependencies, review release notes, rebuild from a clean dependency
resolution, run all tests, and perform target regression.

## Configuration ownership

Keep configuration in its established owner:

- board electrical values and pin assignments: `nh_board`;
- boot ordering: `main`;
- persistent application preferences: `nh_settings`, `nh_network`, or
  `nh_printer`;
- partition layout: `partitions.csv`;
- build defaults: `sdkconfig.defaults`;
- dependency constraints: component manifests and lock file;
- application version: top-level `CMakeLists.txt`.

Avoid introducing duplicate constants in UI code or scripts. Documentation
should describe the source of truth, not become a competing configuration
source.

## Coding expectations

- Keep network and MQTT handle ownership in their worker/actor context.
- Bound all values received from the network or UI.
- Clear stale telemetry when its connection is no longer authoritative.
- Treat UI labels as product claims: do not display unsupported controls,
  placeholder files, or a successful result before it is known.
- Revalidate queued printer actions at execution time.
- Keep credentials out of logs, fixtures, screenshots, and commits.
- Ensure cleanup paths are safe after partial initialization and disconnects.
- Preserve USB recovery and the on-device OTA authorization boundary.

## Normal change workflow

1. Read the relevant component and its tests.
2. Make the smallest coherent change.
3. Add or update host tests and repository invariants.
4. Update maintained documentation when behavior, configuration, UI, security,
   hardware, or operations change.
5. Add a `CHANGELOG.md` entry under the current unreleased/candidate version.
6. Run the verification suite.
7. Build the signed firmware.
8. For hardware-facing changes, exercise the target checklist.
9. Deploy only through the supported release process.

## Adding a printer command

Before exposing a new command in the UI:

1. Document the exact Bambu local protocol message and applicable printer
   states.
2. Add the action to the shared action model.
3. Enforce payload bounds.
4. Implement worker-side state revalidation.
5. Publish through the printer-owned MQTT client.
6. Define what constitutes acknowledgement, failure, and timeout.
7. Add parser/action tests.
8. Make the UI truthful for queued, accepted, rejected, and unsupported states.
9. Validate against a real P1S without an active print before testing during a
   job.

## Adding persistent data

NVS writes must be:

- namespaced;
- bounded;
- transactional when multiple values form one profile;
- backward compatible or explicitly migrated;
- documented in [Security](SECURITY.md);
- tested for failed writes and partial prior state.

Do not silently erase or reinterpret credentials during a normal application
upgrade.

## Documentation maintenance

The maintained-document set is indexed by [Documentation](README.md). Historical
review files are evidence and should not be rewritten to match later behavior.
If the present implementation changes, update the maintained documents and
changelog in the same patch.

## Related documents

- [Testing](TESTING.md)
- [Release Process](RELEASE_PROCESS.md)
- [Security](SECURITY.md)
- [Hardware Reference](HARDWARE.md)
