#include "nh_diagnostics.h"

#include <limits.h>
#include <string.h>

#include "esp_heap_caps.h"
#include "esp_ota_ops.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

/*
 * Only persistent tasks are sampled. Excluding short-lived restart and OTA
 * validation tasks avoids retaining a handle while a task is being deleted.
 */
static const char *const s_tracked_tasks[] = {
    "taskLVGL",
    "nh_wifi_worker",
    "nh_p1s_worker",
    "nh_p1s_camera",
    "httpd",
};

void nh_diagnostics_snapshot(nh_diagnostics_snapshot_t *snapshot)
{
    if (!snapshot) {
        return;
    }

    memset(snapshot, 0, sizeof(*snapshot));
    snapshot->uptime_seconds =
        (uint32_t)(esp_timer_get_time() / 1000000);
    snapshot->internal_free_bytes =
        heap_caps_get_free_size(MALLOC_CAP_INTERNAL);
    snapshot->internal_minimum_bytes =
        heap_caps_get_minimum_free_size(MALLOC_CAP_INTERNAL);
    snapshot->psram_free_bytes =
        heap_caps_get_free_size(MALLOC_CAP_SPIRAM);
    snapshot->reset_reason = esp_reset_reason();
    strlcpy(snapshot->minimum_stack_task, "unavailable",
            sizeof(snapshot->minimum_stack_task));
    strlcpy(snapshot->running_partition, "unknown",
            sizeof(snapshot->running_partition));

    size_t minimum_stack = SIZE_MAX;
    for (size_t i = 0;
         i < sizeof(s_tracked_tasks) / sizeof(s_tracked_tasks[0]);
         ++i) {
        TaskHandle_t task = xTaskGetHandle(s_tracked_tasks[i]);
        if (!task) {
            continue;
        }

        /*
         * ESP-IDF's FreeRTOS port reports this value in bytes. The result is
         * the task's lifetime minimum, not merely its current unused stack.
         */
        size_t free_stack = (size_t)uxTaskGetStackHighWaterMark(task);
        snapshot->tracked_task_count++;
        if (free_stack < minimum_stack) {
            minimum_stack = free_stack;
            strlcpy(snapshot->minimum_stack_task, s_tracked_tasks[i],
                    sizeof(snapshot->minimum_stack_task));
        }
    }
    snapshot->minimum_task_stack_bytes =
        minimum_stack == SIZE_MAX ? 0 : minimum_stack;

    const esp_partition_t *running = esp_ota_get_running_partition();
    if (running) {
        strlcpy(snapshot->running_partition, running->label,
                sizeof(snapshot->running_partition));
        esp_ota_img_states_t state;
        if (esp_ota_get_state_partition(running, &state) == ESP_OK) {
            snapshot->ota_pending_verification =
                state == ESP_OTA_IMG_PENDING_VERIFY;
        }
    }
}
