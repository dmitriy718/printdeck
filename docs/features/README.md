# PrintDeck Feature Implementation Notes

Each recommendation is delivered as a separate source-version gate. A gate is
documented and verified twice before work begins on the next one.

| Gate | Version | Feature | Document |
|---:|---|---|---|
| 1 | 0.8.0 | HMS/error and notification center | [HMS and alerts](01_HMS_ALERTS.md) |
| 2 | 0.8.1 | AMS/material command center | [AMS and materials](02_AMS_MATERIALS.md) |
| 3 | 0.8.2 | History, cost, maintenance, and exports | [History and analytics](03_HISTORY_ANALYTICS.md) |
| 4 | 0.9.0 | Local files, reprint, and confirmed queue | [Files and queue](04_FILES_QUEUE.md) |
| 5 | 0.9.1 | Multi-printer fleet and capabilities | [Fleet and capabilities](05_FLEET_CAPABILITIES.md) |
| 6 | 0.9.2 | Safe controls and object rescue | [Safe controls](06_SAFE_CONTROLS.md) |
| 7 | 0.9.3 | Optional local AI sidecar | [AI sidecar](07_AI_SIDECAR.md) |
| Final | 1.0.0 | Integrated source release | [Release 1.0](08_RELEASE_1_0.md) |

“Verified” in these notes identifies the exact verification layer. Host tests
and a successful target build do not constitute hardware validation.
