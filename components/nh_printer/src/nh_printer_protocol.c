#include "nh_printer_protocol.h"

#include <limits.h>
#include <inttypes.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "cJSON.h"

static cJSON *object_item(const cJSON *object, const char *name)
{
    return object ? cJSON_GetObjectItemCaseSensitive(object, name) : NULL;
}

static bool read_nonnegative_int(const cJSON *object, const char *name,
                                 int *value)
{
    cJSON *item = object_item(object, name);
    if (cJSON_IsNumber(item)) {
        if (item->valuedouble < 0 || item->valuedouble > INT_MAX) {
            return false;
        }
        *value = item->valueint;
        return true;
    }
    if (!cJSON_IsString(item) || !item->valuestring) {
        return false;
    }

    char *end = NULL;
    long parsed = strtol(item->valuestring, &end, 10);
    if (end == item->valuestring || *end != '\0' ||
        parsed < 0 || parsed > INT_MAX) {
        return false;
    }
    *value = (int)parsed;
    return true;
}

static bool update_number(const cJSON *object, const char *name, float *target)
{
    cJSON *item = object_item(object, name);
    if (!cJSON_IsNumber(item)) {
        return false;
    }
    *target = (float)item->valuedouble;
    return true;
}

static bool update_u8(const cJSON *object, const char *name, uint8_t *target)
{
    cJSON *item = object_item(object, name);
    if (!cJSON_IsNumber(item)) {
        return false;
    }
    int value = item->valueint;
    if (value < 0) {
        value = 0;
    } else if (value > 100) {
        value = 100;
    }
    *target = (uint8_t)value;
    return true;
}

static const char *string_item(const cJSON *object, const char *name)
{
    cJSON *item = object_item(object, name);
    return cJSON_IsString(item) && item->valuestring
               ? item->valuestring
               : NULL;
}

typedef struct {
    const char *raw_code;
    const char *title;
    const char *guidance;
    nh_alert_severity_t severity;
} nh_known_alert_t;

/*
 * Version 1 of the local code table. Only codes with a verified Bambu Wiki
 * description are named. Unknown values remain visible with their exact
 * canonical code and no invented diagnosis.
 */
static const nh_known_alert_t s_known_alerts[] = {
    {
        .raw_code = "HMS_0300-0300-0001-0001",
        .title = "Hotend cooling fan is too slow or stopped",
        .guidance = "Inspect the hotend fan connector and fan path before continuing.",
        .severity = NH_ALERT_CRITICAL,
    },
    {
        .raw_code = "HMS_07FF-2000-0002-0004",
        .title = "Filament may be stuck in the toolhead",
        .guidance = "Follow printer guidance and inspect the filament path and sensor.",
        .severity = NH_ALERT_ERROR,
    },
};

static uint64_t current_epoch(void)
{
    time_t now = time(NULL);
    return now > 0 ? (uint64_t)now : 0;
}

static const nh_known_alert_t *known_alert(const char *raw_code)
{
    for (size_t i = 0; i < sizeof(s_known_alerts) / sizeof(s_known_alerts[0]);
         ++i) {
        if (strcmp(s_known_alerts[i].raw_code, raw_code) == 0) {
            return &s_known_alerts[i];
        }
    }
    return NULL;
}

static nh_alert_t *find_alert(nh_printer_snapshot_t *snapshot,
                              const char *raw_code)
{
    for (uint8_t i = 0; i < snapshot->alert_count; ++i) {
        if (strcmp(snapshot->alerts[i].raw_code, raw_code) == 0) {
            return &snapshot->alerts[i];
        }
    }
    return NULL;
}

static nh_alert_t *allocate_alert(nh_printer_snapshot_t *snapshot)
{
    if (snapshot->alert_count < NH_ALERT_MAX) {
        return &snapshot->alerts[snapshot->alert_count++];
    }

    size_t replacement = 0;
    bool found_inactive = false;
    uint64_t oldest = UINT64_MAX;
    for (size_t i = 0; i < NH_ALERT_MAX; ++i) {
        nh_alert_t *candidate = &snapshot->alerts[i];
        if (!candidate->active &&
            (!found_inactive || candidate->last_seen_epoch < oldest)) {
            replacement = i;
            oldest = candidate->last_seen_epoch;
            found_inactive = true;
        } else if (!found_inactive && candidate->last_seen_epoch < oldest) {
            replacement = i;
            oldest = candidate->last_seen_epoch;
        }
    }
    return &snapshot->alerts[replacement];
}

static void observe_alert(nh_printer_snapshot_t *snapshot,
                          const char *raw_code,
                          nh_alert_source_t source,
                          nh_alert_severity_t default_severity)
{
    nh_alert_t *alert = find_alert(snapshot, raw_code);
    uint64_t now = current_epoch();
    if (!alert) {
        alert = allocate_alert(snapshot);
        *alert = (nh_alert_t){
            .source = source,
            .severity = default_severity,
            .first_seen_epoch = now,
            .occurrence_count = 1,
        };
        strlcpy(alert->raw_code, raw_code, sizeof(alert->raw_code));
        const nh_known_alert_t *mapping = known_alert(raw_code);
        if (mapping) {
            alert->known_code = true;
            alert->severity = mapping->severity;
            strlcpy(alert->title, mapping->title, sizeof(alert->title));
            strlcpy(alert->guidance, mapping->guidance,
                    sizeof(alert->guidance));
        } else {
            strlcpy(alert->title,
                    source == NH_ALERT_SOURCE_PRINT
                        ? "Printer reported an unmapped error"
                        : "Printer reported an unmapped HMS code",
                    sizeof(alert->title));
            strlcpy(alert->guidance,
                    "Use the exact code with official printer guidance; no diagnosis is inferred.",
                    sizeof(alert->guidance));
        }
    } else if (!alert->active) {
        alert->occurrence_count++;
        alert->dismissed_locally = false;
    }
    alert->active = true;
    alert->last_seen_epoch = now;
}

static void recount_active_alerts(nh_printer_snapshot_t *snapshot)
{
    uint8_t count = 0;
    for (uint8_t i = 0; i < snapshot->alert_count; ++i) {
        if (snapshot->alerts[i].active &&
            !snapshot->alerts[i].dismissed_locally) {
            count++;
        }
    }
    snapshot->active_alert_count = count;
}

static bool read_u32(const cJSON *object, const char *name, uint32_t *value)
{
    cJSON *item = object_item(object, name);
    if (cJSON_IsNumber(item)) {
        if (item->valuedouble < 0 || item->valuedouble > UINT32_MAX) {
            return false;
        }
        *value = (uint32_t)item->valuedouble;
        return true;
    }
    if (!cJSON_IsString(item) || !item->valuestring) {
        return false;
    }
    char *end = NULL;
    unsigned long parsed = strtoul(item->valuestring, &end, 10);
    if (end == item->valuestring || *end != '\0' || parsed > UINT32_MAX) {
        return false;
    }
    *value = (uint32_t)parsed;
    return true;
}

static bool read_float_value(const cJSON *object, const char *name, float *value)
{
    cJSON *item = object_item(object, name);
    if (cJSON_IsNumber(item)) {
        *value = (float)item->valuedouble;
        return true;
    }
    if (!cJSON_IsString(item) || !item->valuestring) {
        return false;
    }
    char *end = NULL;
    float parsed = strtof(item->valuestring, &end);
    if (end == item->valuestring || *end != '\0') {
        return false;
    }
    if (!isfinite(parsed)) {
        return false;
    }
    *value = parsed;
    return true;
}

static bool copy_bounded_string(const cJSON *object, const char *name,
                                char *target, size_t target_size)
{
    const char *value = string_item(object, name);
    if (!value || strlen(value) >= target_size) {
        return false;
    }
    strlcpy(target, value, target_size);
    return true;
}

static bool valid_rgba(const char *color)
{
    if (!color || strlen(color) != 8) {
        return false;
    }
    for (size_t i = 0; i < 8; ++i) {
        char c = color[i];
        if (!((c >= '0' && c <= '9') ||
              (c >= 'a' && c <= 'f') ||
              (c >= 'A' && c <= 'F'))) {
            return false;
        }
    }
    return true;
}

static void parse_ams_tray(nh_ams_tray_t *target, const cJSON *tray,
                           uint8_t unit_id, bool external)
{
    uint32_t value;
    *target = (nh_ams_tray_t){
        .unit_id = unit_id,
        .external = external,
        .tray_id = external ? 254 : 0,
    };
    if (read_u32(tray, "id", &value) && value <= UINT8_MAX) {
        target->tray_id = (uint8_t)value;
    }
    (void)copy_bounded_string(
        tray, "tray_type", target->material, sizeof(target->material));
    (void)copy_bounded_string(
        tray, "tray_info_idx", target->profile_id, sizeof(target->profile_id));
    (void)copy_bounded_string(
        tray, "tag_uid", target->rfid_uid, sizeof(target->rfid_uid));
    char color[NH_AMS_COLOR_LENGTH] = {0};
    if (copy_bounded_string(tray, "tray_color", color, sizeof(color)) &&
        valid_rgba(color)) {
        strlcpy(target->color_rgba, color, sizeof(target->color_rgba));
    }
    if (read_u32(tray, "remain", &value) && value <= 100) {
        target->remaining_percent = (uint8_t)value;
        target->remaining_known = true;
    }
    if (read_u32(tray, "nozzle_temp_min", &value) && value <= INT16_MAX) {
        target->nozzle_min_c = (int16_t)value;
    }
    if (read_u32(tray, "nozzle_temp_max", &value) && value <= INT16_MAX) {
        target->nozzle_max_c = (int16_t)value;
    }
    target->rfid_present =
        target->rfid_uid[0] != '\0' &&
        strcmp(target->rfid_uid, "0000000000000000") != 0;
    target->present = target->material[0] != '\0' ||
                      target->profile_id[0] != '\0' ||
                      target->rfid_present;
}

static void update_material_risk_alerts(
    nh_printer_snapshot_t *snapshot, bool seen[NH_ALERT_MAX])
{
    for (uint8_t i = 0; i < snapshot->ams.unit_count; ++i) {
        const nh_ams_unit_t *unit = &snapshot->ams.units[i];
        if (!unit->material_at_risk) {
            continue;
        }
        char raw_code[NH_ALERT_CODE_LENGTH];
        snprintf(raw_code, sizeof(raw_code), "MATERIAL_AMS_%u_HUMIDITY_%u",
                 (unsigned)unit->id, (unsigned)unit->humidity_index);
        observe_alert(snapshot, raw_code, NH_ALERT_SOURCE_MATERIAL,
                      NH_ALERT_WARNING);
        nh_alert_t *alert = find_alert(snapshot, raw_code);
        if (alert) {
            strlcpy(alert->title, "AMS humidity needs attention",
                    sizeof(alert->title));
            strlcpy(
                alert->guidance,
                "Check desiccant and material condition; the printer reports an index, not relative humidity.",
                sizeof(alert->guidance));
            seen[(size_t)(alert - snapshot->alerts)] = true;
        }
    }
    for (uint8_t i = 0; i < snapshot->alert_count; ++i) {
        if (snapshot->alerts[i].source == NH_ALERT_SOURCE_MATERIAL && !seen[i]) {
            snapshot->alerts[i].active = false;
            snapshot->alerts[i].dismissed_locally = false;
        }
    }
}

static void parse_ams(nh_printer_protocol_t *protocol, const cJSON *print)
{
    nh_printer_snapshot_t *snapshot = protocol->snapshot;
    cJSON *ams_root = object_item(print, "ams");
    bool material_seen[NH_ALERT_MAX] = {false};

    if (cJSON_IsObject(ams_root)) {
        cJSON *units = object_item(ams_root, "ams");
        if (cJSON_IsArray(units)) {
            snapshot->ams.known = true;
            snapshot->ams.unit_count = 0;
            snapshot->ams.tray_count = 0;
            memset(snapshot->ams.units, 0, sizeof(snapshot->ams.units));
            memset(snapshot->ams.trays, 0, sizeof(snapshot->ams.trays));

            cJSON *unit = NULL;
            cJSON_ArrayForEach(unit, units) {
                if (!cJSON_IsObject(unit) ||
                    snapshot->ams.unit_count >= NH_AMS_MAX_UNITS) {
                    continue;
                }
                nh_ams_unit_t *unit_out =
                    &snapshot->ams.units[snapshot->ams.unit_count++];
                *unit_out = (nh_ams_unit_t){.present = true};
                uint32_t value;
                if (read_u32(unit, "id", &value) && value <= UINT8_MAX) {
                    unit_out->id = (uint8_t)value;
                }
                if (read_u32(unit, "humidity", &value) && value <= UINT8_MAX) {
                    unit_out->humidity_index = (uint8_t)value;
                    unit_out->humidity_known = true;
                    unit_out->material_at_risk = value >= 4;
                }
                unit_out->temperature_known = read_float_value(
                    unit, "temp", &unit_out->temperature_c);

                cJSON *trays = object_item(unit, "tray");
                if (!cJSON_IsArray(trays)) {
                    continue;
                }
                cJSON *tray = NULL;
                cJSON_ArrayForEach(tray, trays) {
                    if (!cJSON_IsObject(tray) ||
                        snapshot->ams.tray_count >= NH_AMS_MAX_TRAYS) {
                        continue;
                    }
                    parse_ams_tray(
                        &snapshot->ams.trays[snapshot->ams.tray_count++],
                        tray, unit_out->id, false);
                }
            }
        }
    }

    cJSON *external = object_item(print, "vt_tray");
    if (cJSON_IsObject(external)) {
        nh_ams_tray_t parsed;
        parse_ams_tray(&parsed, external, UINT8_MAX, true);
        snapshot->ams.external_spool_present = parsed.present;
        size_t external_index = NH_AMS_MAX_TRAYS;
        snapshot->ams.trays[external_index] = parsed;
    }

    if (cJSON_IsObject(ams_root) || cJSON_IsObject(external)) {
        update_material_risk_alerts(snapshot, material_seen);
    }
}

static void parse_hms(nh_printer_protocol_t *protocol, const cJSON *print)
{
    cJSON *hms = object_item(print, "hms");
    if (!hms) {
        return;
    }
    if (!cJSON_IsArray(hms)) {
        return;
    }

    nh_printer_snapshot_t *snapshot = protocol->snapshot;
    bool seen[NH_ALERT_MAX] = {false};

    cJSON *entry = NULL;
    cJSON_ArrayForEach(entry, hms) {
        uint32_t attr;
        uint32_t code;
        if (!cJSON_IsObject(entry) ||
            !read_u32(entry, "attr", &attr) ||
            !read_u32(entry, "code", &code)) {
            continue;
        }
        char raw_code[NH_ALERT_CODE_LENGTH];
        snprintf(raw_code, sizeof(raw_code),
                 "HMS_%04" PRIX32 "-%04" PRIX32 "-%04" PRIX32 "-%04" PRIX32,
                 attr >> 16, attr & 0xFFFFU, code >> 16, code & 0xFFFFU);
        observe_alert(snapshot, raw_code, NH_ALERT_SOURCE_HMS,
                      NH_ALERT_WARNING);
        nh_alert_t *observed = find_alert(snapshot, raw_code);
        if (observed) {
            seen[(size_t)(observed - snapshot->alerts)] = true;
        }
    }
    for (uint8_t i = 0; i < snapshot->alert_count; ++i) {
        if (snapshot->alerts[i].source == NH_ALERT_SOURCE_HMS && !seen[i]) {
            snapshot->alerts[i].active = false;
            snapshot->alerts[i].dismissed_locally = false;
        }
    }
}

static void parse_print_error(nh_printer_protocol_t *protocol,
                              const cJSON *print)
{
    uint32_t error_code;
    bool present = read_u32(print, "print_error", &error_code);
    if (!present) {
        present = read_u32(print, "mc_print_error_code", &error_code);
    }
    if (!present) {
        return;
    }

    nh_printer_snapshot_t *snapshot = protocol->snapshot;
    if (error_code != 0) {
        char raw_code[NH_ALERT_CODE_LENGTH];
        snprintf(raw_code, sizeof(raw_code), "PRINT_ERROR_%" PRIu32,
                 error_code);
        observe_alert(snapshot, raw_code, NH_ALERT_SOURCE_PRINT,
                      NH_ALERT_ERROR);
    }
    for (uint8_t i = 0; i < snapshot->alert_count; ++i) {
        nh_alert_t *alert = &snapshot->alerts[i];
        if (alert->source != NH_ALERT_SOURCE_PRINT) {
            continue;
        }
        char raw_code[NH_ALERT_CODE_LENGTH];
        snprintf(raw_code, sizeof(raw_code), "PRINT_ERROR_%" PRIu32,
                 error_code);
        if (error_code == 0 || strcmp(alert->raw_code, raw_code) != 0) {
            alert->active = false;
            alert->dismissed_locally = false;
        }
    }
}

static bool job_active(nh_job_state_t job)
{
    return job == NH_JOB_PREPARING ||
           job == NH_JOB_PRINTING ||
           job == NH_JOB_PAUSED;
}

static void parse_job_state(nh_printer_protocol_t *protocol,
                            const cJSON *print)
{
    const char *state = string_item(print, "gcode_state");
    if (!state) {
        return;
    }

    nh_printer_snapshot_t *snapshot = protocol->snapshot;
    nh_job_state_t previous = snapshot->job;
    if (strcmp(state, "RUNNING") == 0) {
        snapshot->job = NH_JOB_PRINTING;
    } else if (strcmp(state, "PAUSE") == 0) {
        snapshot->job = NH_JOB_PAUSED;
    } else if (strcmp(state, "PREPARE") == 0) {
        snapshot->job = NH_JOB_PREPARING;
    } else if (strcmp(state, "FINISH") == 0) {
        snapshot->job = NH_JOB_COMPLETE;
    } else if (strcmp(state, "FAILED") == 0) {
        snapshot->job = NH_JOB_FAILED;
    } else if (strcmp(state, "IDLE") == 0) {
        snapshot->job = NH_JOB_IDLE;
        snapshot->progress_percent = 0;
        protocol->current_layer = -1;
        protocol->total_layers = -1;
        strlcpy(protocol->job_name, "No active print",
                protocol->job_name_size);
        strlcpy(protocol->job_layer, "Layer -- / --",
                protocol->job_layer_size);
        strlcpy(protocol->remaining, "--h --m",
                protocol->remaining_size);
    }

    if (job_active(snapshot->job) && !job_active(previous)) {
        snapshot->progress_percent = 0;
        protocol->current_layer = -1;
        protocol->total_layers = -1;
        strlcpy(protocol->job_name, "Active print",
                protocol->job_name_size);
        strlcpy(protocol->job_layer, "Layer -- / --",
                protocol->job_layer_size);
        strlcpy(protocol->remaining, "--h --m",
                protocol->remaining_size);
    }
}

static void parse_lights(nh_printer_protocol_t *protocol,
                         const cJSON *print)
{
    cJSON *lights = object_item(print, "lights_report");
    if (!cJSON_IsArray(lights)) {
        return;
    }
    cJSON *light = NULL;
    cJSON_ArrayForEach(light, lights) {
        const char *node = string_item(light, "node");
        const char *mode = string_item(light, "mode");
        if (node && mode && strcmp(node, "chamber_light") == 0) {
            protocol->snapshot->chamber_light_on =
                strcmp(mode, "on") == 0;
            return;
        }
    }
}

void nh_printer_protocol_init(
    nh_printer_protocol_t *protocol,
    nh_printer_snapshot_t *snapshot,
    char *job_name,
    size_t job_name_size,
    char *job_layer,
    size_t job_layer_size,
    char *remaining,
    size_t remaining_size)
{
    if (!protocol) {
        return;
    }
    *protocol = (nh_printer_protocol_t){
        .snapshot = snapshot,
        .job_name = job_name,
        .job_name_size = job_name_size,
        .job_layer = job_layer,
        .job_layer_size = job_layer_size,
        .remaining = remaining,
        .remaining_size = remaining_size,
        .current_layer = -1,
        .total_layers = -1,
    };
    if (snapshot) {
        snapshot->job_name = job_name;
        snapshot->job_layer = job_layer;
        snapshot->remaining = remaining;
    }
}

void nh_printer_protocol_reset(nh_printer_protocol_t *protocol)
{
    if (!protocol || !protocol->snapshot) {
        return;
    }

    nh_printer_snapshot_t *snapshot = protocol->snapshot;
    snapshot->telemetry_ready = false;
    snapshot->job = NH_JOB_UNKNOWN;
    snapshot->progress_percent = 0;
    snapshot->nozzle_current_c = 0.0f;
    snapshot->nozzle_target_c = 0.0f;
    snapshot->bed_current_c = 0.0f;
    snapshot->bed_target_c = 0.0f;
    snapshot->chamber_current_c = 0.0f;
    snapshot->part_fan_percent = 0;
    snapshot->chamber_light_on = false;
    snapshot->printer_sd_known = false;
    snapshot->printer_sd_present = false;
    protocol->current_layer = -1;
    protocol->total_layers = -1;
    strlcpy(protocol->job_name, "Waiting for printer status",
            protocol->job_name_size);
    strlcpy(protocol->job_layer, "Layer -- / --",
            protocol->job_layer_size);
    strlcpy(protocol->remaining, "--h --m",
            protocol->remaining_size);
}

nh_printer_protocol_result_t nh_printer_protocol_parse(
    nh_printer_protocol_t *protocol, const char *data, size_t length)
{
    if (!protocol || !protocol->snapshot || !data || length == 0) {
        return NH_PRINTER_PROTOCOL_INVALID;
    }

    cJSON *root = cJSON_ParseWithLength(data, length);
    if (!root) {
        return NH_PRINTER_PROTOCOL_INVALID;
    }

    cJSON *print = object_item(root, "print");
    if (!cJSON_IsObject(print)) {
        cJSON_Delete(root);
        return NH_PRINTER_PROTOCOL_IGNORED;
    }

    nh_printer_snapshot_t *snapshot = protocol->snapshot;
    snapshot->telemetry_ready = true;
    protocol->report_sequence++;
    parse_hms(protocol, print);
    parse_print_error(protocol, print);
    parse_ams(protocol, print);
    recount_active_alerts(snapshot);
    parse_job_state(protocol, print);
    /*
     * P1 printers may leave job-specific fields in the same report that
     * announces IDLE. The state transition is authoritative: stale progress
     * and timing values must not make an idle printer look active.
     */
    if (snapshot->job != NH_JOB_IDLE) {
        update_u8(print, "mc_percent", &snapshot->progress_percent);
    }
    update_number(print, "nozzle_temper", &snapshot->nozzle_current_c);
    update_number(print, "nozzle_target_temper", &snapshot->nozzle_target_c);
    update_number(print, "bed_temper", &snapshot->bed_current_c);
    update_number(print, "bed_target_temper", &snapshot->bed_target_c);
    update_number(print, "chamber_temper", &snapshot->chamber_current_c);

    cJSON *printer_sd = object_item(print, "sdcard");
    if (cJSON_IsBool(printer_sd)) {
        snapshot->printer_sd_known = true;
        snapshot->printer_sd_present = cJSON_IsTrue(printer_sd);
    } else if (cJSON_IsNumber(printer_sd)) {
        snapshot->printer_sd_known = true;
        snapshot->printer_sd_present = printer_sd->valueint != 0;
    }

    const char *job = string_item(print, "subtask_name");
    if (job && job[0] && snapshot->job != NH_JOB_IDLE) {
        strlcpy(protocol->job_name, job, protocol->job_name_size);
    } else if (snapshot->job == NH_JOB_IDLE) {
        strlcpy(protocol->job_name, "No active print",
                protocol->job_name_size);
    }

    if (snapshot->job != NH_JOB_IDLE) {
        int reported_layer = 0;
        int reported_total = 0;
        bool layer_updated =
            read_nonnegative_int(print, "layer_num", &reported_layer);
        bool total_updated =
            read_nonnegative_int(print, "total_layer_num", &reported_total);

        if (layer_updated) {
            protocol->current_layer = reported_layer;
        }
        if (total_updated && reported_total > 0) {
            protocol->total_layers = reported_total;
        }
        if (layer_updated || total_updated) {
            if (protocol->current_layer >= 0 &&
                protocol->total_layers > 0) {
                snprintf(protocol->job_layer, protocol->job_layer_size,
                         "Layer %d / %d", protocol->current_layer,
                         protocol->total_layers);
            } else if (protocol->current_layer >= 0) {
                snprintf(protocol->job_layer, protocol->job_layer_size,
                         "Layer %d / --", protocol->current_layer);
            } else if (protocol->total_layers > 0) {
                snprintf(protocol->job_layer, protocol->job_layer_size,
                         "Layer -- / %d", protocol->total_layers);
            }
        }
    }

    if (snapshot->job != NH_JOB_IDLE) {
        int remaining = 0;
        if (read_nonnegative_int(print, "mc_remaining_time", &remaining)) {
            snprintf(protocol->remaining, protocol->remaining_size,
                     "%dh %02dm", remaining / 60, remaining % 60);
        }
    }

    int fan_level = 0;
    if (read_nonnegative_int(print, "cooling_fan_speed", &fan_level)) {
        if (fan_level > 15) {
            fan_level = 15;
        }
        snapshot->part_fan_percent =
            (uint8_t)((fan_level * 100) / 15);
    }
    parse_lights(protocol, print);

    cJSON_Delete(root);
    return NH_PRINTER_PROTOCOL_UPDATED;
}

bool nh_printer_protocol_dismiss_alert(
    nh_printer_protocol_t *protocol, const char *raw_code)
{
    if (!protocol || !protocol->snapshot || !raw_code || !raw_code[0]) {
        return false;
    }
    nh_alert_t *alert = find_alert(protocol->snapshot, raw_code);
    if (!alert || !alert->active) {
        return false;
    }
    alert->dismissed_locally = true;
    recount_active_alerts(protocol->snapshot);
    return true;
}
