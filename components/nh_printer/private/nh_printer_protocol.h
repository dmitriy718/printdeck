#pragma once

#include <stddef.h>

#include "nh_core.h"

typedef enum {
    NH_PRINTER_PROTOCOL_INVALID = 0,
    NH_PRINTER_PROTOCOL_IGNORED,
    NH_PRINTER_PROTOCOL_UPDATED,
} nh_printer_protocol_result_t;

typedef struct {
    nh_printer_snapshot_t *snapshot;
    char *job_name;
    size_t job_name_size;
    char *job_layer;
    size_t job_layer_size;
    char *remaining;
    size_t remaining_size;
    int current_layer;
    int total_layers;
    uint32_t report_sequence;
} nh_printer_protocol_t;

void nh_printer_protocol_init(
    nh_printer_protocol_t *protocol,
    nh_printer_snapshot_t *snapshot,
    char *job_name,
    size_t job_name_size,
    char *job_layer,
    size_t job_layer_size,
    char *remaining,
    size_t remaining_size);

void nh_printer_protocol_reset(nh_printer_protocol_t *protocol);

nh_printer_protocol_result_t nh_printer_protocol_parse(
    nh_printer_protocol_t *protocol, const char *data, size_t length);

/**
 * Dismisses one alert in the local view without claiming that the printer
 * resolved it. A later active report makes the alert visible again.
 */
bool nh_printer_protocol_dismiss_alert(
    nh_printer_protocol_t *protocol, const char *raw_code);
