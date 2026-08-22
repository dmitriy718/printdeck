#pragma once

#include <stdbool.h>
#include <stdint.h>

#include "esp_err.h"
#include "lvgl.h"
#include "nh_ai.h"
#include "nh_camera.h"
#include "nh_core.h"
#include "nh_files.h"
#include "nh_fleet.h"
#include "nh_history.h"
#include "nh_network.h"
#include "nh_printer.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    lv_display_t *display;
    const nh_printer_snapshot_t *snapshot;
    nh_action_handler_t action_handler;
    void *action_ctx;
    esp_err_t (*network_scan)(void *ctx);
    esp_err_t (*network_connect)(const char *ssid, const char *password, void *ctx);
    void *network_ctx;
    esp_err_t (*printer_pair)(const char *ip_address, const char *serial,
                              const char *access_code, void *ctx);
    esp_err_t (*alert_dismiss)(const char *raw_code, void *ctx);
    void *printer_ctx;
    esp_err_t (*ota_enable)(uint32_t duration_seconds, void *ctx);
    void *ota_ctx;
    const char *(*timezone_name)(void *ctx);
    esp_err_t (*timezone_next)(void *ctx);
    void *timezone_ctx;
    esp_err_t (*camera_set_active)(bool active, void *ctx);
    void *camera_ctx;
    esp_err_t (*history_export)(nh_history_export_format_t format,
                                bool redact_job_names,
                                void *ctx);
    esp_err_t (*history_backup)(void *ctx);
    void *history_ctx;
    esp_err_t (*file_review_queue)(uint64_t file_id,
                                   uint64_t *queue_id,
                                   void *ctx);
    esp_err_t (*file_bed_clear)(uint64_t queue_id, void *ctx);
    esp_err_t (*file_thumbnail)(uint64_t file_id,
                               uint8_t *buffer,
                               size_t buffer_size,
                               size_t *required_size,
                               void *ctx);
    void *files_ctx;
} nh_ui_config_t;

esp_err_t nh_ui_create(const nh_ui_config_t *config);
esp_err_t nh_ui_update(const nh_printer_snapshot_t *snapshot);
esp_err_t nh_ui_storage_update(bool mounted, esp_err_t mount_error,
                               uint64_t capacity_bytes, uint64_t free_bytes);
esp_err_t nh_ui_network_update(const nh_network_snapshot_t *snapshot);
esp_err_t nh_ui_printer_update(const nh_printer_status_t *status);
esp_err_t nh_ui_camera_status_update(const nh_camera_status_t *status);
esp_err_t nh_ui_camera_frame(const uint8_t *rgb565,
                             uint16_t width,
                             uint16_t height,
                             uint16_t source_width,
                             uint16_t source_height);
esp_err_t nh_ui_history_update(const nh_history_snapshot_t *snapshot);
esp_err_t nh_ui_files_update(const nh_files_snapshot_t *snapshot);
esp_err_t nh_ui_fleet_update(const nh_fleet_snapshot_t *snapshot);
esp_err_t nh_ui_command_result_update(const nh_command_result_t *result);
esp_err_t nh_ui_ai_update(const nh_ai_snapshot_t *snapshot);

#ifdef __cplusplus
}
#endif
