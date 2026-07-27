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
