# PrintDeck documentation

This directory contains the maintained product and engineering documentation
for PrintDeck, the Horizon Services LLC touchscreen controller for the
JC4880P443 and Bambu Lab P1S.

## Current release state

| Item | Version | Status |
| --- | --- | --- |
| Current source | 1.0.0 | Seven-gate integrated source release |
| Last hardware-deployed firmware | 0.7.2 | Deployed by guarded LAN OTA on 2026-07-28 |
| ESP-IDF | 6.0.2 | Current project toolchain |
| LVGL | 9.5.x | Current UI dependency |

Do not call v1.0.0 hardware-verified until its on-device regression checklist
has passed. The source/deployment distinction is intentional throughout these
documents.

## Start here

| Audience or task | Document |
| --- | --- |
| Understand the product, status, and feature boundaries | [Product overview](PRODUCT_OVERVIEW.md) |
| Set up and operate the controller | [User guide](USER_GUIDE.md) |
| Understand components, state, tasks, and data flow | [Architecture](ARCHITECTURE.md) |
| Wire, flash, or diagnose the prototype hardware | [Hardware reference](HARDWARE.md) |
| Build or modify the firmware | [Development guide](DEVELOPMENT.md) |
| Maintain a deployed controller | [Operations guide](OPERATIONS.md) |
| Prepare and qualify a release | [Release process](RELEASE_PROCESS.md) |
| Run automated and hardware validation | [Testing guide](TESTING.md) |
| Understand the threat model and current limitations | [Security](SECURITY.md) |
| Diagnose common failures | [Troubleshooting](TROUBLESHOOTING.md) |
| Decode project terminology | [Glossary](GLOSSARY.md) |
| Review feature-gate implementation contracts | [Feature implementation notes](features/README.md) |
| Review every reconstructed version milestone | [Changelog](../CHANGELOG.md) |
| Review prioritized future features and evidence | [Product recommendations](../Reviews/recommendations.md) |

## Specialized and historical material

- [Security provisioning](SECURITY_PROVISIONING.md) documents the irreversible
  eFuse and recovery decisions required before enabling encrypted NVS.
- `bambu-lab-outreach/` is an external outreach package. It is a dated v0.7.2
  product snapshot, not the source of truth for current development status.
- `../Reviews/` contains timestamped engineering records. Review logs preserve
  facts as they were observed and may mention previous product names, versions,
  filenames, device states, or open findings that were later resolved.

## Documentation truth rules

1. Current implementation claims must be supported by current source and, when
   hardware behavior is claimed, a recorded hardware observation.
2. “Built” means present in source. “Build-verified” means the target firmware
   compiled and passed image checks. “Deployed” means a specific controller
   reported the version after flashing. “Hardware-verified” requires the
   relevant behavior to have been exercised.
3. Planned UI or architecture must never be described as implemented.
4. Pre-Git history is explicitly labeled reconstructed. Git history begins on
   2026-07-27 at v0.7.0; earlier facts come from preserved artifacts,
   filesystem creation metadata, and the first comprehensive review.
5. Secrets, private IP addresses, access codes, Wi-Fi credentials, private
   signing material, and precise photo location metadata do not belong in
   documentation.
6. Commands that can flash, upload, erase, format, burn eFuses, or control a
   printer must state their prerequisites and safety boundary.

## Updating these documents

When product behavior changes:

1. Update the relevant technical or user document.
2. Update `../CHANGELOG.md` under the actual source version.
3. Update the version/status table above if source or deployed state changed.
4. Update `../README.md` only where its concise overview is affected.
5. Add or update automated invariants when a documentation claim is critical
   to release safety.
6. Record hardware deployment separately from source completion.
