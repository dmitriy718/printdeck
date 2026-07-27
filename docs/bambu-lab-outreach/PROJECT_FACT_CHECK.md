# Project Fact Check

Review basis: the complete repository state, firmware v0.7.0 source build,
host regression tests, the existing hardware photograph, prior operator
observations on the current P1S prototype, and the official Bambu Lab model
documents linked below. Review date: 2026-07-27.

The repository began this review without a Git commit at `HEAD`. A reviewed
v0.7.0 baseline now exists locally, but earlier milestones still rely on
source/build evidence and explicitly identified operator observations rather
than an independently auditable historical commit timeline.

Status definitions:

- **Verified:** supported by code plus a successful build, automated check,
  hardware observation, or operator-confirmed test.
- **Partially verified:** implemented or observed in a limited path; more
  runtime or regression testing is needed.
- **Planned:** future work or UI/architecture scaffolding only.
- **Unknown:** insufficient evidence.

| Important claim used in overview | Status | Evidence | Deliberate wording / limitation |
| --- | --- | --- | --- |
| Nova Horizon Controller is an independent project by Dima. | **Verified** | User-provided identity; `README.md`; Nova Horizon branding in `components/nh_ui/src/nh_ui.c`. | Does not imply Bambu Lab approval, affiliation, or partnership. |
| The currently supported development target is a Bambu Lab P1S. | **Verified** | P1S-specific transport, commands, profile, topics, camera path, and labels in `components/nh_printer/`, `components/nh_camera/`, and `components/nh_ui/`. | No other printer model is claimed compatible. |
| The controller is a JC4880P443 with ESP32-P4NRW32, 32 MB PSRAM, 16 MB flash, and ESP32-C6 Wi-Fi. | **Verified** | `README.md`; `sdkconfig.defaults`; visible board markings in the local hardware photograph. | Applies to the current prototype board only. |
| The display/touch stack is ST7701S 480×800 MIPI-DSI plus GT911, presented as an 800×480 landscape UI. | **Verified** | `components/nh_board/`; operator confirmed working display and aligned touch during bring-up. | No environmental or product certification is claimed. |
| The UI includes Dashboard, Job, Control, Files, Camera, and System pages. | **Verified** | Page creation/navigation in `components/nh_ui/src/nh_ui.c`; clean v0.7.0 firmware build passed. | Page existence is not equated with completion of every visible control. |
| ESP32-C6 hosted Wi-Fi supports scanning, on-screen entry, and automatic reconnect. | **Partially verified** | Actor/retry implementation in `components/nh_network/src/nh_network.c`; setup UI in `components/nh_ui/src/nh_ui.c`; operator confirmed Wi-Fi connection. | v0.7.0 retry/race hardening still needs on-device fault testing; printer discovery is not implemented. |
| The controller connects to the P1S using authenticated local TLS/MQTT. | **Verified** | MQTT configuration, Bambu CA, printer common-name check, access-code authentication, topics, and report handling in `components/nh_printer/` and `components/nh_bambu/`; operator confirmed P1S online. | Described as local integration, not an official public API. |
| Live P1S telemetry includes job state, progress, layers, remaining time, temperatures, fan level, SD state, and chamber light. | **Partially verified** | Production parser in `components/nh_printer/src/nh_printer_protocol.c`; 11 host parser cases in `tests/host/test_printer_protocol.c`; UI rendering in `components/nh_ui/src/nh_ui.c`; operator observed live print data. | Exhaustive firmware and malformed-payload coverage is not claimed. |
| Layer totals survive P1S delta reports, and stale IDLE fields cannot repopulate an active-looking job. | **Verified in host regression; hardware recheck pending** | `nh_printer_protocol.c`; `test_delta_preserves_total_layers`; `test_idle_clears_job_state`; `tests/run_host_tests.sh` passed. | The overview calls v0.7.0 a source build and does not claim this review build is already deployed. |
| Chamber-light control works on the existing P1S. | **Verified** | Guarded command mapping in `components/nh_printer/src/nh_printer.c`; operator confirmed the physical chamber light changed. | This is the printer command with direct runtime confirmation in the available record. |
| Pause, resume, and cancel paths are implemented. | **Partially verified** | Action mapping and state gating in `components/nh_printer/src/nh_printer.c`; buttons and cancel confirmation in `components/nh_ui/src/nh_ui.c`. | Runtime success is not claimed; safe validation remains pending. |
| Unsupported motion, thermal, fan, and file-start actions are blocked. | **Verified in code/UI** | `nh_printer_action_supported()` and `nh_printer_action_available()`; UI gating in `components/nh_ui/src/nh_ui.c`. | A software safety gate is not a formal safety certification. |
| A local P1-family camera liveview is implemented. | **Verified on current prototype, refining** | TLS port 6000 transport, CA/device identity validation, JPEG validation/hardware decode, PPA scaling, double-buffered RGB565 output, and tab lifecycle in `components/nh_camera/` and `components/nh_ui/`; prior operator completion observation. | Long-duration and non-P1 camera compatibility are not claimed. AI vision is not implemented. |
| Camera pipeline memory is released when the Camera tab closes. | **Verified in code/build; runtime measurement pending** | `release_pipeline()` in `components/nh_camera/src/nh_camera.c`; UI frame invalidation in `components/nh_ui/src/nh_ui.c`; v0.7.0 build passed. | No measured byte-saving claim is used in the outreach overview. |
| New Wi-Fi and P1S profiles are persisted only after successful validation. | **Verified in code; runtime fault test pending** | Deferred NVS saves in `components/nh_network/src/nh_network.c` and `components/nh_printer/src/nh_printer.c`; rejected printer replacement rollback logic. | Does not claim encrypted storage. |
| LAN OTA is physically enabled, dual-slot, signed, timeout-bounded, and rollback-capable. | **Verified in code/build; signed enforcement deployment pending** | `components/nh_ota/src/nh_ota.c`; `partitions.csv`; rollback and RSA signed-app settings in `sdkconfig.defaults`; valid RSA signature inspection; prior v0.6.0 OTA exercise. | v0.7.0 verifies project-key signatures without irreversible hardware Secure Boot; the signed-enforcement build still needs device deployment. |
| The controller SD slot mounts FAT32 without automatic formatting. | **Verified in code; media compatibility partial** | `components/nh_board/src/nh_board.c`; `README.md`; repository invariant test. | A 512 GB SDXC card may ship as exFAT and require an explicit backup/reformat. File indexing is not implemented. |
| Firmware v0.6.0 builds and boots successfully. | **Verified build and deployment** | A physically authorized OTA completed on 2026-07-27 and the controller returned to its status endpoint reporting v0.6.0. | Full on-device behavioral regression remains a separate step. |
| Firmware v0.7.0 builds as a valid signed ESP32-P4 image. | **Verified build; deployment pending** | Clean 1,704-step build passed; signed binary is 1,773,568 bytes; `espsecure` validates the RSA signature; `esptool image-info` validates checksum/hash, target, version, and 16 MiB header; 72% of the smallest OTA slot remains free. | No v0.7.0 boot or runtime claim is made until the controller is flashed and checked. |
| Automated regression and static-analysis checks exist. | **Verified** | 11 C parser cases plus 20 Python repository invariants; AddressSanitizer/UndefinedBehaviorSanitizer parser runs; ShellCheck; GCC `-fanalyzer` across all 12 first-party translation units. | No UI simulator or hardware-in-the-loop suite exists yet. |
| Runtime health instrumentation is implemented. | **Verified in code/build; device measurement pending** | `components/nh_diagnostics/`; System UI; read-only status JSON; clean v0.7.0 build. | No stack-reduction or measured runtime-memory claim is made before stress testing. |
| The clock timezone can be changed and persisted. | **Verified in code/build; UI test pending** | `components/nh_settings/`; timezone control in `components/nh_ui/`; NVS persistence and 15 POSIX presets; clean v0.7.0 build. | Hardware touch/persistence behavior still needs confirmation. |
| Credentials are masked and cleared from transient UI/command buffers. | **Partially verified** | Password-mode UI and `nh_secure_zero()` usage in UI, network, printer, and camera paths; secret scan found no literal credentials. | Wi-Fi and P1S credentials remain plaintext in NVS until a provisioning migration enables encryption at rest. |
| File selection and print initiation are working. | **Planned / not implemented** | Files-page scaffold; printer transport rejects `NH_ACTION_OPEN_FILE`. | Overview calls this “UI scaffold only.” |
| AMS or filament management is working. | **Planned / not implemented** | No AMS parser, model, workflow, or command implementation found. | Included only as future compatibility work. |
| Multi-printer support is working. | **Planned / not implemented** | One P1S profile and P1S-specific state are implemented. | Multi-printer profiles require a future capability layer. |
| Nova Horizon backend/dashboard connectivity is working. | **Planned / not implemented** | Roadmap references only; no Nova backend API client exists. | Described only as optional future work. |
| Jetson Orin Nano vision verification is working. | **Planned / not implemented** | Roadmap/architecture reference only; no Jetson protocol, model, or inference component exists. | P1 camera viewing is not described as AI verification. |
| X1 Carbon is a high-value X-series loan target. | **Verified recommendation, not compatibility** | Official [X1 Carbon technical specification](https://public-cdn.bambulab.com/store/bambulab-X1-carbon-tech-specs.pdf) identifies X-series camera/sensor differences; current code is P1S-specific. | Recommendation is for coverage; no X1 result is claimed. |
| H2D is a high-value H-series loan target. | **Verified recommendation, not compatibility** | Official [H2D technical data sheet](https://cdn1.bambulab.com/documentation/h2d/en/H2D_Laser_Full_Combo_20250305.pdf) documents dual-nozzle and H-series differences. | Recommendation is for coverage; no H2D result is claimed. |
| P1S + X1 Carbon + H2D prove compatibility with every Bambu Lab model. | **Unknown / unsupported** | No A-series or per-SKU testing exists. | The overview says “broad P/X/H family coverage,” not universal compatibility. |
| Bambu Lab has agreed to a loan, support, acknowledgment, or partnership. | **Unknown / not agreed** | No agreement exists in the repository. | All language is a proposal; acknowledgment is conditional on agreement and approval. |
| Creator coverage or promotional reach is guaranteed. | **Planned / not verified** | Promotional activities are intentions supplied by the developer; no commitments or metrics exist. | No creator is named and no performance claim is made. |

## Validation commands recorded

```sh
source scripts/idf-env.sh
idf.py build
tests/run_host_tests.sh
shellcheck scripts/*.sh tests/*.sh
python3 -m py_compile tests/review_invariants.py \
  docs/bambu-lab-outreach/tools/generate_outreach_package.py
python -m esptool --chip esp32p4 \
  image-info build/nova_horizon_controller.bin
```

Current recorded results:

- Firmware v0.7.0 clean signed source build: pass.
- Signed application binary: 1,773,568 bytes (`0x1b1000`).
- Smallest application partition: 6 MiB; 72% reported free.
- Production parser cases: 11 passed, including a sanitizer run.
- Repository safety/release invariants: 20 passed.
- Project shell scripts: ShellCheck passed.
- GCC path-sensitive analysis: 12 first-party C translation units passed.
- Live v0.6.0 OTA deployment and return to network service: passed.
- v0.7.0 deployment and full hardware behavioral regression: pending.
