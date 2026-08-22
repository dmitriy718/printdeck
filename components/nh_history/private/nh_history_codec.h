#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

enum {
    NH_HISTORY_DISK_MAGIC = 0x5044484Au,
    NH_HISTORY_DISK_SCHEMA = 1,
    NH_HISTORY_DISK_TEXT_LENGTH = 96,
};

typedef enum {
    NH_HISTORY_EVENT_START = 1,
    NH_HISTORY_EVENT_FINISH = 2,
    NH_HISTORY_EVENT_MAINTENANCE_RESET = 3,
} nh_history_event_type_t;

typedef struct {
    uint32_t magic;
    uint16_t schema;
    uint16_t record_size;
    uint64_t sequence;
    uint64_t timestamp_epoch;
    uint32_t duration_seconds;
    uint32_t material_grams_estimate;
    uint32_t energy_wh_estimate;
    uint64_t material_cost_micros_estimate;
    uint64_t energy_cost_micros_estimate;
    uint8_t event_type;
    uint8_t outcome;
    uint8_t maximum_progress_percent;
    uint8_t flags;
    char text[NH_HISTORY_DISK_TEXT_LENGTH];
    uint32_t crc32;
} nh_history_disk_record_t;

uint32_t nh_history_crc32(const void *data, size_t length);
void nh_history_record_seal(nh_history_disk_record_t *record);
bool nh_history_record_valid(const nh_history_disk_record_t *record);
