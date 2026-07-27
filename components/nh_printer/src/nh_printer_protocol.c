#include "nh_printer_protocol.h"

#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

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
