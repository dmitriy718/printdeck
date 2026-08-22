# PrintDeck Product Recommendations

Research date: 2026-07-29

Product: PrintDeck for the JC4880P443 and Bambu Lab P1S

Company: Horizon Services LLC

Decision horizon: next 6–18 months

## Executive result

The research does not support building a generic copy of Bambu Handy on a
different screen. Many users are satisfied with their phone or computer and
touch the printer display only for immediate, physical workflows. The strongest
opportunity is therefore a **local-first printer-side operations console**:
faster at faults, filament changes, maintenance, rescue, reprints, and
multi-printer awareness than a general mobile app.

The seven recommendations, ranked by the evidence-weighted model below, are:

| Rank | Recommendation | Priority / 100 | Difficulty | Impact |
| ---: | --- | ---: | ---: | ---: |
| 1 | Actionable HMS/error and notification center | 86 | 5 | 9 |
| 2 | AMS and material command center | 82 | 6 | 9 |
| 3 | Print history, cost, maintenance, and export analytics | 81 | 5 | 8 |
| 4 | Local file library, fast reprint, and human-confirmed queue | 78 | 7 | 9 |
| 5 | Multi-printer fleet dashboard and capability layer | 77 | 8 | 9 |
| 6 | Safe control parity and object-rescue workflow | 70 | 8 | 9 |
| 7 | Optional local AI failure-detection sidecar | 68 | 9 | 9 |

These began as product recommendations. Their bounded, fail-closed source
implementations were delivered sequentially in v0.8.0 through v0.9.3 and are
documented in `docs/features/`. “Implemented” does not mean hardware-qualified:
unvalidated writes, file transfer/start, concurrent live fleet transports, and
automatic AI pause remain disabled or unconnected until their recorded
hardware gates pass. The difficulty and impact ratings use the requested 0–10
scale, where 10 is hardest and 10 is highest impact.

## Current product boundary

### Built and hardware-deployed in v0.7.2

- 800 × 480 landscape LVGL interface on the JC4880P443 with working touch,
  backlight, clock, and persistent timezone selection.
- Dashboard, Job, Control, Files, Camera, and System pages.
- On-device Wi-Fi scan/setup, reconnect behavior, and verified-profile
  persistence with rollback of failed replacement credentials.
- Manual P1S pairing using local IP, serial, and LAN access code.
- Authenticated local TLS/MQTT with Bambu CA and configured-device identity
  verification.
- Live state, progress, layer, time, temperature, fan, SD, and chamber-light
  telemetry.
- On-demand encrypted P1-family camera liveview with hardware JPEG decode and
  PPA scaling.
- Guarded pause, resume, cancel, reconnect, and chamber-light commands; cancel
  requires confirmation.
- Non-destructive FAT32 controller-SD mounting and an honest empty file-page
  scaffold.
- Physically authorized, signed, dual-slot LAN OTA with rollback.
- Runtime heap, stack, reset, coredump-partition, uptime, and OTA diagnostics.

### Source-built in v0.7.3; awaiting hardware regression

- MQTT teardown no longer frees its shared fragment buffer while the MQTT
  event task can still be writing it.
- Queued pause/resume/cancel actions are revalidated against the latest job
  state at actual dispatch time.
- The UI says a command was queued rather than claiming the printer accepted
  it without an acknowledgment.
- The OTA uploader accepts only literal RFC 1918 IPv4 destinations.
- Security and partition-roadmap documentation now matches the real
  implementation.

### Not built

- HMS interpretation/history, AMS management, file indexing/transfer/start,
  object exclusion, multi-printer sessions, long-term print/cost records,
  backend integration, and AI inference.

## Research and weighting system

### Evidence classes

Demand and feasibility are different questions, so a source is not given equal
authority for both:

| Evidence class | Credibility | How it is used |
| --- | ---: | --- |
| Official protocol, security, or product documentation | 1.00 for facts; 0.65 for demand | Establishes supported modes, technical constraints, and incumbent features; vendor marketing is not treated as neutral user demand. |
| Repeated independent user requests/problems | 0.90 | Strongest demand signal when the same workflow appears in unrelated communities or products. |
| Maintained open-source implementation with real users | 0.85 | Strong feasibility and market-validation signal; feature breadth alone does not prove willingness to pay. |
| Commercial competitor feature | 0.75 | Shows a sellable category and expected parity, with a marketing-bias discount. |
| One anecdote or one unsupported comment | 0.45 | Useful for discovering an idea, insufficient by itself to rank it. |

Signals are also adjusted for recency, visible engagement, specificity of the
problem, whether the speaker appears to operate one printer or a farm, and
whether independent sources corroborate it. Duplicate posts describing the
same project are not counted as independent demand.

### Priority formula

Every candidate receives 0–10 values for:

- **D** — repeated user demand;
- **U** — user outcome: time, material, reliability, or cognitive load saved;
- **B** — business value and realistic revenue/retention potential;
- **F** — implementation feasibility in the present code and hardware;
- **Fit** — alignment with a local, printer-side PrintDeck;
- **Scale** — ability to extend to more printers, users, and paid tiers;
- **C** — evidence confidence; and
- **Risk** — safety, protocol, privacy, support, and false-action risk.

The reproducible score is:

```text
Raw = 10 × (0.25D + 0.20U + 0.20B + 0.15F + 0.10Fit + 0.10Scale)
Confidence multiplier = 0.70 + 0.03C
Priority = round(Raw × Confidence multiplier − Risk)
```

Risk can subtract 0–10 points. This prevents an exciting but unsafe automated
control from outranking a less glamorous feature that is demanded, profitable,
and straightforward. A recommendation also needs at least two independent
demand signals and one credible feasibility signal.

### Candidate scorecard

| Candidate | D | U | B | F | Fit | Scale | C | Risk | Result |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| HMS/error center and alerts | 9.5 | 9.5 | 8.5 | 7.5 | 9.5 | 9.0 | 9.5 | 2 | **86** |
| AMS/material command center | 9.5 | 9.0 | 9.0 | 6.0 | 9.5 | 9.5 | 9.0 | 3 | **82** |
| History/cost/maintenance | 8.5 | 8.5 | 9.0 | 7.0 | 8.5 | 10.0 | 9.0 | 2 | **81** |
| Local files/reprint/queue | 8.5 | 9.0 | 8.5 | 6.0 | 10.0 | 9.0 | 9.0 | 4 | **78** |
| Multi-printer fleet | 9.0 | 8.5 | 9.5 | 4.0 | 8.5 | 10.0 | 9.0 | 4 | **77** |
| Safe controls/object rescue | 8.5 | 9.5 | 7.5 | 5.0 | 10.0 | 8.0 | 8.5 | 7 | **70** |
| Local AI sidecar | 8.0 | 9.0 | 9.5 | 3.0 | 8.5 | 10.0 | 8.5 | 8 | **68** |
| Localization/accessibility | 6.0 | 7.5 | 6.0 | 8.0 | 8.0 | 8.0 | 7.0 | 1 | 63 |
| Cloud-only remote access | 6.0 | 7.0 | 8.0 | 4.0 | 2.0 | 9.0 | 6.0 | 8 | 47 |
| Touchscreen clone with no unique workflow | 5.0 | 4.0 | 4.0 | 8.0 | 3.0 | 4.0 | 7.0 | 2 | 41 |
| Cosmetic themes | 4.0 | 4.0 | 4.0 | 8.0 | 4.0 | 6.0 | 5.0 | 1 | 40 |

Localization and accessibility remain worthwhile release-quality work. They
did not enter the seven because their available evidence and direct revenue
leverage are weaker than the selected workflows. They should be designed into
new screens, not indefinitely postponed.

## Opinion and market evidence

The sample deliberately mixes official constraints, competitor behavior,
maintained community products, direct requests, high-engagement discussions,
and negative opinions:

1. BIGTREETECH documents filament type/color editing, load/unload, local file
   access, reprint history, multi-printer groups, and background HMS
   notifications in [Panda Touch documentation](https://global.bttwiki.com/Panda%20Touch.html?h=panda+touch+image).
2. Bambuddy's maintained project supports local ownership, one-to-40-printer
   operation, reprint with AMS mapping, per-run history, queueing, automation,
   and analytics in its [project README](https://github.com/maziggy/bambuddy).
3. Its detailed notification/inventory feature set includes HMS alerts,
   webhooks, Home Assistant, missing-spool warnings, consumption, and per-spool
   cost in the [current README](https://github.com/maziggy/bambuddy/blob/main/README.md).
4. A 2026 user-built app was motivated by slow camera access and single-printer
   live activity, then added unlimited printer cards, simultaneous cameras,
   summaries, and loaded-filament search; the author reports a small paid
   unlock for additional printers in
   [PandaWatch](https://www.reddit.com/r/BambuLab/comments/1rrkyu7/introducing_pandawatch_a_mobile_app_for_ataglance/).
5. A local-only iOS project attracted substantial positive engagement for
   camera, telemetry, AMS, drying, controls, and privacy in
   [PandaBeFree](https://www.reddit.com/r/BambuLab/comments/1rsl7o3/i_built_a_free_opensource_ios_app_for_bambu_lab/).
6. A direct small-company/family request asks for a queue master, priorities,
   16 waiting slots, reusable jobs, and a timeline, while another user says a
   separate server feels excessive in
   [Queueing Lite](https://forum.bambulab.com/t/new-product-request-queueing-lite/224372).
7. A current ESP32 display user specifically asks for historical AMS humidity
   and home-automation exposure; the project confirms the live data exists in
   [BambuHelper](https://forum.bambulab.com/t/diy-read-only-esp32-status-display-for-bambu-printers-bambuhelper-v3-0/251743).
8. Users describe AMS filament assignment as the primary reason they use an
   add-on screen in
   [PandaTouch and Bambu Cloud](https://www.reddit.com/r/BambuLab/comments/1c4q7t4).
9. Another hands-on review praises AMS setup but requests humidity, thumbnails,
   printer identity, and fast printer switching; it also supplies negative
   evidence from a user who never uses print-from-file in
   [Panda Touch Observations](https://www.reddit.com/r/BambuLab/comments/1ap89g0).
10. A high-engagement filament discussion asks for downloadable print history
    and exposes widespread guesswork around remaining spool quantity in
    [filament usage tracking](https://www.reddit.com/r/BambuLab/comments/1krzf6n/how_do_you_track_your_filament_usage_for_non_bbl/).
11. A workplace user wants historical material and cost comparisons against
    outsourced manufacturing in
    [printing cost logs](https://www.reddit.com/r/BambuLab/comments/1k2gg39).
12. A 2026 Home Assistant add-on combines multi-printer discovery, automatic
    print logs, spool deduction, low-stock warnings, and notifications in
    [HA Filament SpoolTracker](https://www.reddit.com/r/BambuLab/comments/1rpvl6r/addon_ha_filament_spooltracker_track_3d_printer/).
13. Users continue asking for automatic per-print material and cost records in
    [detailed print-cost tracking](https://www.reddit.com/r/BambuLab/comments/1spsr7b/tracking_print_cost_detailed/).
14. Users also identify the missing distinction between estimated whole-job
    usage and material actually consumed by a failed print in
    [failed-print usage](https://www.reddit.com/r/BambuLab/comments/1qo9i3w/check_how_much_filament_a_failed_print_used/).
15. P1S users report needing a phone or desktop because the printer lacks a
    touchscreen object selector in
    [P1S skip-parts discussion](https://forum.bambulab.com/t/is-skipping-parts-on-p1s-not-possible-anymore/253895).
16. Users report object skipping saving the rest of a multi-object plate in
    [Skipping Objects](https://forum.bambulab.com/t/skipping-objects/33693).
17. Obico markets failure alerts and optional pause as protection against
    wasted material and equipment damage in its
    [failure-detection product](https://www.obico.io/failure-detection.html).
18. Obico also explains confidence thresholds, local inference, and the reality
    of lighting/geometry false positives in
    [how its detection works](https://www.obico.io/blog/how-obico-ai-failure-detection-works/).
19. Real users report damaging false AI stops on long prints, establishing the
    need for notify-first defaults and explicit opt-in automation in
    [X1C spaghetti-detection reports](https://forum.bambulab.com/t/x1c-stops-printing-almost-every-print/5206).
20. Users report stale AMS/HMS alerts that remain long after resolution in
    [alert-clearing reports](https://www.reddit.com/r/BambuLab/comments/15vq425/how_to_clear_alertsmessages/).
21. Other users ask for readable HMS definitions rather than raw codes in
    [HMS error discussion](https://forum.bambulab.com/t/does-anyone-know-what-hms-err-0300-0c00-0001-0004-is/13531).
22. A self-hosted project discussion explicitly combines fleet monitoring,
    skip-object, HMS history, cost analytics, and exports in
    [Bambuddy's community launch](https://forum.bambulab.com/t/bambuddy-stay-connected-to-your-prints/230168).
23. Privacy-minded users describe switching to LAN-only mode and rebuilding
    dashboards/automation locally in
    [Home Assistant LAN-only discussion](https://www.reddit.com/r/BambuLab/comments/1kj7khs).
24. Bambu Lab's current security paper confirms Developer Mode is intended to
    preserve third-party MQTT operation, partly in response to print-farm
    concerns, in the
    [Bambu Lab Security White Paper](https://cdn1.bambulab.com/trust-center/file/bambulab-security-whitepaper-en.pdf).
25. Bambu Lab separately states that Developer Mode opens MQTT, live stream,
    and FTP for advanced local integrations, but those protocols are not an
    officially supported public API, in
    [its integration update](https://blog.bambulab.com/updates-and-third-party-integration-with-bambu-connect/).
26. The major counter-signal is a broad, mixed discussion where many people say
    a touchscreen is unnecessary, while others use it precisely for AMS,
    maintenance, quick cancellation, and LAN-only operation:
    [touchscreen necessity discussion](https://www.reddit.com/r/BambuLab/comments/1lv48tq/just_me_or_do_you_feel_the_touch_screen_really/).

### Interpretation

- **Strongest consensus:** errors/alerts, AMS/material workflows, local
  visibility, history, and fast physical interventions.
- **Strong commercial segment:** owners with two or more printers, small
  businesses, schools/families sharing printers, and farms.
- **Important negative evidence:** single-printer owners near a PC may not pay
  for feature parity alone; file browsing is weak if it is slower or less
  reliable than sending from a slicer.
- **Protocol risk:** local MQTT/FTPS capability exists, but Bambu calls the
  Developer Mode interfaces unsupported. Every write feature needs capability
  detection, version testing, and a fail-closed policy.
- **Product implication:** PrintDeck should win on glanceability, local
  resilience, printer-side workflows, and trust—not on the number of screens.

## 1. Actionable HMS/error and notification center

**Difficulty: 5/10. Impact: 9/10. Priority: 86/100.**

### Why implement it

Faults are the moment when a printer-side display is most valuable. Current
PrintDeck represents transport failures, but it does not parse, explain,
deduplicate, retain, or resolve P1S HMS/print errors. Community reports show
that raw codes and stale alerts create confusion, while competitor products
treat background HMS monitoring as basic controller behavior.

### Implementation plan

1. Add a bounded error/event model to `nh_printer_protocol`, including raw
   code, source, severity, first/last seen time, active/cleared state, and
   occurrence count.
2. Preserve unknown codes exactly. Map known codes through a versioned local
   data table; never invent a diagnosis.
3. Deduplicate repeated MQTT deltas and clear an alert only from observed
   printer state or explicit local dismissal. Distinguish “dismissed here”
   from “resolved on printer.”
4. Add a notification drawer with critical pop-ups, active/history tabs,
   plain-language next steps, and a deep link to the relevant local control.
5. Add configurable local outputs: screen/banner first, then optional Home
   Assistant MQTT, webhook, ntfy, or a future confirmed buzzer.
6. Add quiet hours and severity routing, but never silence safety-critical
   on-device status.
7. Test recorded HMS fixtures, unknown codes, repeated deltas, reconnects,
   stale clear events, and queue saturation.

### Value to Horizon Services LLC

This makes PrintDeck feel trustworthy rather than decorative, reduces support
load, and creates a natural base feature for every unit. Notification routing,
retention, and fleet-wide incident views can form a paid Pro/Fleet tier without
making local fault visibility subscription-dependent.

### Value to users

Users get the error, meaning, recency, affected printer, and safe next action in
one place. They spend less time searching codes, miss fewer stopped prints, and
can see whether an alert is active or merely historical.

### Upgradeability and scalability

High. The event schema can accept additional printer families, maintenance
events, AI events, and cloud/backend sinks. Code tables can be delivered as
signed firmware data updates while unknown-code handling preserves forward
compatibility.

## 2. AMS and material command center

**Difficulty: 6/10. Impact: 9/10. Priority: 82/100.**

### Why implement it

AMS assignment is one of the clearest printer-side touchscreen use cases.
Users repeatedly want slot identity, color/material editing, humidity, drying,
load/unload, and remaining-spool context without walking back to a computer.
It is also a bridge from a one-printer accessory to valuable material
inventory and fleet workflows.

### Implementation plan

1. Extend the protocol snapshot with AMS units and trays: presence, slot,
   material, color, RFID identity when available, remaining percentage,
   humidity, temperature, drying state, and external spool.
2. Build read-only cards first and validate across partial/delta reports.
3. Add humidity thresholds, history, and “material at risk” alerts.
4. Add bounded slot editing and RFID reread. Add load/unload/drying only after
   exact-message validation and state interlocks.
5. Add a local spool catalog for third-party material, duplicate rolls,
   cost/kg, dry-state timestamp, and AMS compatibility.
6. Join live trays to the print-history ledger so material consumption is
   assigned to the right spool, including failed/cancelled jobs.
7. Validate no-AMS, one AMS, multiple AMS, external spool, empty slot, unknown
   material, mid-print swap, and disconnect cases.

### Value to Horizon Services LLC

This is a visible sales differentiator for P1S owners and a foundation for
inventory, low-stock alerts, purchasing integrations, and paid multi-printer
material search. It increases daily interaction and makes the hardware useful
even when no print is active.

### Value to users

Users can identify and configure what they physically loaded at the printer,
watch moisture risk, find a usable spool, and avoid starts with the wrong or
insufficient material.

### Upgradeability and scalability

Very high. Model AMS units and trays as collections rather than four fixed
slots. The same inventory IDs can later serve AMS Lite/newer AMS variants,
multiple printers, barcode/NFC accessories, and the backend.

## 3. Print history, cost, maintenance, and export analytics

**Difficulty: 5/10. Impact: 8/10. Priority: 81/100.**

### Why implement it

Users and businesses ask for actual historical consumption, failed-print
usage, cost, success rate, and exports. This is more valuable than a dashboard
that forgets everything after the job ends, and it creates durable product
data without requiring risky printer control.

### Implementation plan

1. Convert job-state transitions into an append-only event journal on
   controller SD: start, pause, resume, failure, cancellation, completion,
   layer/progress samples, and material assignment changes.
2. Use checksummed, versioned records and recovery scanning so a power loss can
   discard one incomplete tail record without corrupting history.
3. Build a compact job summary: printer, file/job, timestamps, result,
   duration, estimated/actualized material, temperatures, pauses, and error
   codes.
4. Add configurable material cost/kg and optional energy estimates. Label
   estimated data honestly and support later smart-plug measurements.
5. Add maintenance counters and reminders based on time, print hours, and
   material, with user-reset audit history.
6. Add on-device daily/monthly summaries and CSV/JSON export. Keep detailed
   charts for an optional local web/backend companion rather than overloading
   the 800 × 480 screen.
7. Add data retention, redaction, backup, and “delete all history”
   controls.

### Value to Horizon Services LLC

History increases retention and enables business-facing Pro features:
quoting, utilization, failure cost, maintenance compliance, and fleet reports.
An optional hosted sync can be monetized later, while local records remain a
strong privacy differentiator and reduce cloud cost.

### Value to users

Users can answer what printed, what failed, how much material/time it used,
what it cost, and when maintenance is due. They can reprint confidently and
export evidence for a customer, classroom, or accounting workflow.

### Upgradeability and scalability

Excellent. A versioned event log can feed on-device summaries, web dashboards,
fleet aggregation, backups, and future analytics without changing how the
printer transport works.

## 4. Local file library, fast reprint, and human-confirmed queue

**Difficulty: 7/10. Impact: 9/10. Priority: 78/100.**

### Why implement it

A Files tab already exists, but file browsing alone is not enough—some users
never use competitor file browsers. The valuable workflow is a reliable
thumbnail, compatible printer/material check, and fast reprint or next-job
handoff without reopening a slicer. Queue demand extends from families to
small shops, but users do not want mandatory server overhead.

### Implementation plan

1. Safely index controller-SD `.3mf` files without modifying media. Parse ZIP
   metadata and thumbnails with strict entry-count, path, compression-ratio,
   and size limits.
2. Add search, recent/favorite jobs, plate thumbnails, nozzle/material
   requirements, and duplicate detection.
3. Implement read-only printer-side history and “reprint last” before general
   transfer.
4. Add authenticated FTPS upload and print start behind capability detection,
   exact-target confirmation, and per-firmware integration tests.
5. Require AMS/nozzle/plate compatibility review and an explicit final Start
   confirmation. Never infer that a bed is clear.
6. Add a small local queue with priority and copies. Each job stops in
   `WAITING_FOR_BED_CLEAR`; a person confirms removal and plate readiness.
7. Add resumable transfer, hashes, available-space checks, cancellation, and
   power-loss recovery before adding multi-user/backend submission.

### Value to Horizon Services LLC

This turns the display into a job appliance, increases repeat usage, and
supports a paid small-team/fleet queue later. A polished local workflow is more
defensible than a plain SD directory browser.

### Value to users

Common jobs can be found and repeated in seconds with the right material and
plate context. Families and small teams gain an understandable waiting list
without leaving a server running or risking unattended automatic starts.

### Upgradeability and scalability

High. Use content hashes and a versioned job manifest so the same library can
live on SD, NAS, or Horizon backend storage. Queue scheduling can later target
printer capabilities and material availability.

## 5. Multi-printer fleet dashboard and capability layer

**Difficulty: 8/10. Impact: 9/10. Priority: 77/100.**

### Why implement it

Multi-printer glanceability, cameras, loaded-material search, and queue
assignment recur across independent products and user requests. It also has
the clearest willingness-to-pay signal. The present printer component is a
singleton, however, so this requires an architectural investment rather than
duplicating screens.

### Implementation plan

1. Refactor `nh_printer` static session state into an opaque
   `nh_printer_session_t` with one profile, transport, snapshot, pending
   commands, and generation.
2. Add a persistent profile store and LAN discovery/onboarding. Discovery may
   suggest devices but must bind commands to a confirmed serial identity.
3. Introduce a capability matrix by model/firmware: telemetry, camera,
   AMS, files, object skip, temperatures, and each write command.
4. Start with two printers, then test a bounded target such as four concurrent
   status sessions. Keep only one active camera upstream and multiplex or
   suspend views to respect printer/controller memory limits.
5. Build fleet cards ordered by attention: error, paused, finishing soon,
   printing, idle, offline. Add one-tap focus, not global destructive actions.
6. Add loaded-material search and queue assignment after AMS and files are
   stable.
7. Load-test reconnect storms, simultaneous delta traffic, profile deletion,
   wrong-IP identity, and partial outages before raising limits.

### Value to Horizon Services LLC

This unlocks tiered pricing by printer count, raises account value for farms
and small businesses, and creates a route to recurring fleet/backend revenue.
The capability layer also reduces the cost of supporting future Bambu models.

### Value to users

Owners stop switching between devices to find failures, finish times, cameras,
or loaded material. A shop can assign work to the right printer and see what
needs human attention first.

### Upgradeability and scalability

This recommendation is the scalability foundation. The session/capability
model should support local-only single-printer operation, a bounded standalone
fleet, and larger backend-assisted fleets without forking the UI or protocol.

## 6. Safe control parity and object-rescue workflow

**Difficulty: 8/10. Impact: 9/10. Priority: 70/100.**

### Why implement it

Users who do value the printer display disproportionately use it for loading,
maintenance, axis movement, calibration, quick cancellation, and rescuing a
plate when one object fails. Current PrintDeck deliberately blocks motion,
thermal, fan, and file actions; that safety boundary should be expanded only
with evidence and hardware tests.

### Implementation plan

1. Add an asynchronous command-result model keyed by sequence ID so the UI can
   distinguish queued, sent, acknowledged/observed, rejected, and timed out.
2. Validate low-risk speed profiles and calibration operations first.
3. Add fan, temperature, and axis controls with hard bounds, homing/state
   prerequisites, press-and-hold or confirmation where appropriate, and no
   arbitrary G-code console.
4. Parse object IDs and plate thumbnails from the active `.3mf`; show only
   objects the printer reports as eligible to skip.
5. Make skip-object a two-step operation showing object name/thumbnail and
   irreversible effect. Confirm success from subsequent printer state.
6. Maintain a per-model/firmware command matrix and fail closed when the
   capability is unknown.
7. Execute a hardware test matrix for every command in idle, preparing,
   printing, paused, error, reconnect, and stale-queue states.

### Value to Horizon Services LLC

Control completeness removes a major purchase objection and differentiates
PrintDeck from read-only displays. Object rescue is an easy demonstration of
material savings. The strict command framework reduces liability and future
support cost.

### Value to users

Users can perform real printer-side maintenance and save the remainder of a
multi-object build instead of cancelling the entire plate. Acknowledged status
eliminates uncertainty about whether a tap actually reached the printer.

### Upgradeability and scalability

High if built on capabilities and typed commands; poor if implemented as raw
JSON scattered through UI callbacks. The same framework can add future printer
models and backend-issued commands with identical guardrails.

## 7. Optional local AI failure-detection sidecar

**Difficulty: 9/10. Impact: 9/10. Priority: 68/100.**

### Why implement it

Failure detection has clear material, time, and equipment value and supports a
premium product story. It is ranked seventh because inference quality,
false-positive harm, camera constraints, and automatic printer actions make it
the riskiest recommendation. The ESP32-P4 display should orchestrate a Jetson
or local service, not pretend to run a production vision model itself.

### Implementation plan

1. Define a versioned, authenticated LAN adapter contract for frame/snapshot
   input and events: printer/job identity, model version, confidence,
   evidence image, timestamps, and suggested action.
2. Preserve or expose a bounded JPEG snapshot from the existing camera
   pipeline without opening competing upstream camera sessions.
3. Build a Jetson Orin Nano reference adapter and an Obico-compatible optional
   adapter. Keep images local by default and disclose any cloud route.
4. Launch in **notify-only** mode. Show confidence and evidence and let the user
   label true/false detections.
5. Add temporal smoothing, cooldowns, job-specific muting, camera-health
   checks, and per-event audit history.
6. Permit automatic pause only after opt-in, repeated high-confidence evidence,
   a healthy command channel, and the same guarded command framework as
   recommendation 6. Never default to cancel or power-off.
7. Measure precision, recall, false-stop rate, detection latency, material
   saved, and user overrides on a representative validation set before selling
   automation claims.

### Value to Horizon Services LLC

This can support premium hardware bundles, local inference licensing, or a
hosted opt-in service. It differentiates PrintDeck beyond UI parity and creates
an evidence/data flywheel, provided consent and privacy are handled correctly.

### Value to users

Users gain an extra set of eyes during long prints, earlier warning of
spaghetti/detachment, and potential material/equipment savings without making
cloud video mandatory.

### Upgradeability and scalability

Very high at the service boundary: models and compute can improve independently
of firmware. The same event interface can support one local Jetson, a fleet
server, or an opt-in hosted service. Automatic actions remain separately gated.

## Recommended execution order

1. Complete v0.7.3 hardware regression and close the existing credential,
   C6-firmware, power-integrity, and hardware-test risks.
2. Build the shared event journal and command-result primitives.
3. Deliver HMS/error center.
4. Add read-only AMS plus history/cost foundations in parallel at the design
   level, then validate each separately.
5. Deliver fast local reprint before general queue automation.
6. Refactor into session/capability architecture before adding a second
   printer.
7. Add typed control parity and object rescue only with hardware test coverage.
8. Start AI as a separate notify-only adapter after the event, camera, and
   command foundations are stable.

## Product and revenue packaging

- **PrintDeck Core:** local telemetry, camera, guarded basic controls, HMS
  visibility, and one-printer operation. No subscription should be required
  for safe local use.
- **PrintDeck Pro:** deeper history, cost/maintenance analytics, exports,
  advanced material inventory, and integrations.
- **PrintDeck Fleet:** more printer profiles, fleet attention view, queue,
  material search, roles, and optional backend sync.
- **PrintDeck Vision:** optional Jetson bundle or hosted/local inference
  service, always explicit about privacy and automated-action settings.

This packaging makes the hardware useful by itself, creates upgrade paths, and
does not hold safety-critical local operation hostage to a cloud service.
