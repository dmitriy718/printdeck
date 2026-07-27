#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "esp_system.h"

#ifdef __cplusplus
extern "C" {
#endif

#define NH_DIAGNOSTICS_TASK_NAME_LENGTH 24
#define NH_DIAGNOSTICS_PARTITION_NAME_LENGTH 17

typedef struct {
    uint32_t uptime_seconds;
    size_t internal_free_bytes;
    size_t internal_minimum_bytes;
    size_t psram_free_bytes;
    size_t coredump_partition_bytes;
    size_t minimum_task_stack_bytes;
    uint8_t tracked_task_count;
    char minimum_stack_task[NH_DIAGNOSTICS_TASK_NAME_LENGTH];
    char running_partition[NH_DIAGNOSTICS_PARTITION_NAME_LENGTH];
    esp_reset_reason_t reset_reason;
    bool ota_pending_verification;
} nh_diagnostics_snapshot_t;

/**
 * Capture a bounded health snapshot without enabling FreeRTOS trace support.
 *
 * Stack measurements cover the persistent controller, UI, HTTP, and printer
 * service tasks that are present at the time of the call. Each FreeRTOS high
 * water mark is already the lowest free stack observed since that task began.
 */
void nh_diagnostics_snapshot(nh_diagnostics_snapshot_t *snapshot);

#ifdef __cplusplus
}
#endif
