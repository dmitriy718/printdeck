#include "esp_err.h"
#include "esp_heap_caps.h"
#include "esp_log.h"
#include "nvs_flash.h"

#include "nh_ai.h"
#include "nh_board.h"
#include "nh_camera.h"
#include "nh_core.h"
#include "nh_files.h"
#include "nh_fleet.h"
#include "nh_history.h"
#include "nh_material.h"
#include "nh_network.h"
#include "nh_ota.h"
#include "nh_printer.h"
#include "nh_settings.h"
#include "nh_ui.h"

static const char *TAG = "nh_main";
static bool s_ui_ready;
static bool s_history_ready;
static bool s_files_ready;
static nh_history_snapshot_t s_history_view;
static nh_files_snapshot_t s_files_view;
static nh_fleet_snapshot_t s_fleet_view;
static bool s_fleet_ready;

static void publish_history(void)
{
    if (!s_history_ready || !s_ui_ready) {
        return;
    }
    esp_err_t err = nh_history_snapshot(&s_history_view);
    if (err == ESP_OK) {
        err = nh_ui_history_update(&s_history_view);
    }
    if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) {
        ESP_LOGW(TAG, "History UI update failed: %s", esp_err_to_name(err));
    }
}

static void publish_files(void)
{
    if (!s_files_ready || !s_ui_ready) {
        return;
    }
    esp_err_t err = nh_files_snapshot(&s_files_view);
    if (err == ESP_OK) {
        err = nh_ui_files_update(&s_files_view);
    }
    if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) {
        ESP_LOGW(TAG, "Files UI update failed: %s", esp_err_to_name(err));
    }
}

static void publish_fleet(void)
{
    if (!s_fleet_ready || !s_ui_ready) {
        return;
    }
    esp_err_t err = nh_fleet_snapshot(&s_fleet_view);
    if (err == ESP_OK) {
        err = nh_ui_fleet_update(&s_fleet_view);
    }
    if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) {
        ESP_LOGW(TAG, "Fleet UI update failed: %s", esp_err_to_name(err));
    }
}

static void start_files_if_possible(bool mounted)
{
    if (!mounted || s_files_ready) {
        return;
    }
    esp_err_t err = nh_files_init("/sdcard");
    if (err == ESP_OK) {
        s_files_ready = true;
        publish_files();
    } else if (err != ESP_ERR_INVALID_STATE) {
        ESP_LOGW(TAG, "Local file index unavailable: %s",
                 esp_err_to_name(err));
    }
}

static void start_history_if_possible(bool mounted)
{
    if (!mounted || s_history_ready) {
        return;
    }
    esp_err_t err = nh_history_init("/sdcard");
    if (err == ESP_OK) {
        s_history_ready = true;
        publish_history();
    } else if (err != ESP_ERR_INVALID_STATE) {
        ESP_LOGW(TAG, "Print history unavailable: %s", esp_err_to_name(err));
    }
}

static nh_printer_snapshot_t s_snapshot = {
    .connection = NH_CONNECTION_UNCONFIGURED,
    .job = NH_JOB_UNKNOWN,
    .telemetry_ready = false,
    .printer_name = "Bambu Lab P1S",
    .job_name = "No active print",
    .job_layer = "Layer -- / --",
    .remaining = "--h --m",
    .progress_percent = 0,
    .nozzle_current_c = 0.0f,
    .nozzle_target_c = 0.0f,
    .bed_current_c = 0.0f,
    .bed_target_c = 0.0f,
    .chamber_current_c = 0.0f,
    .part_fan_percent = 0,
    .chamber_light_on = false,
    .printer_sd_known = false,
    .printer_sd_present = false,
    .sd_mounted = false,
    .sd_mount_error = ESP_ERR_NOT_FOUND,
    .sd_capacity_bytes = 0,
    .sd_free_bytes = 0,
};

static esp_err_t refresh_controller_sd(void)
{
    nh_sd_info_t sd_info = {0};
    esp_err_t err = nh_board_sd_mount(&sd_info);
    bool mounted = err == ESP_OK && sd_info.mounted;
    start_history_if_possible(mounted);
    start_files_if_possible(mounted);
    if (!s_ui_ready) {
        /*
         * Boot-time mount runs before UI/task creation and is the only safe
         * point at which main writes the shared initial snapshot directly.
         */
        s_snapshot.sd_mounted = mounted;
        s_snapshot.sd_mount_error = err;
        s_snapshot.sd_capacity_bytes =
            mounted ? sd_info.capacity_bytes : 0;
        s_snapshot.sd_free_bytes = mounted ? sd_info.free_bytes : 0;
        return err;
    }

    esp_err_t ui_err = nh_ui_storage_update(
        mounted, err, sd_info.capacity_bytes, sd_info.free_bytes);
    if (ui_err != ESP_OK) {
        ESP_LOGW(TAG, "SD status UI update failed: %s",
                 esp_err_to_name(ui_err));
    }
    return err;
}

static esp_err_t controller_action_handler(nh_action_t action, int32_t value, void *ctx)
{
    if (action == NH_ACTION_BRIGHTNESS_SET) {
        if (value < 0 || value > 100) {
            return ESP_ERR_INVALID_ARG;
        }
        return nh_board_backlight_set((uint8_t)value);
    }
    if (action == NH_ACTION_SD_RESCAN) {
        esp_err_t err = refresh_controller_sd();
        if (err == ESP_OK && s_files_ready) {
            err = nh_files_rescan();
            publish_files();
        }
        return err;
    }
    (void)ctx;
    return nh_printer_action_with_sequence(action, value, NULL);
}

static void controller_command_result(
    const nh_command_result_t *result, void *ctx)
{
    (void)ctx;
    esp_err_t err = nh_ui_command_result_update(result);
    if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) {
        ESP_LOGW(TAG, "Command result UI update failed: %s",
                 esp_err_to_name(err));
    }
}

static esp_err_t controller_network_scan(void *ctx)
{
    (void)ctx;
    return nh_network_scan();
}

static esp_err_t controller_network_connect(const char *ssid, const char *password,
                                            void *ctx)
{
    (void)ctx;
    return nh_network_connect(ssid, password);
}

static void controller_network_update(const nh_network_snapshot_t *snapshot,
                                      void *ctx)
{
    (void)ctx;
    esp_err_t err = nh_ui_network_update(snapshot);
    if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) {
        ESP_LOGW(TAG, "Network UI update failed: %s", esp_err_to_name(err));
    }
}

static esp_err_t controller_printer_pair(const char *ip_address,
                                         const char *serial,
                                         const char *access_code,
                                         void *ctx)
{
    (void)ctx;
    return nh_printer_pair(ip_address, serial, access_code);
}

static esp_err_t controller_alert_dismiss(const char *raw_code, void *ctx)
{
    (void)ctx;
    return nh_printer_alert_dismiss(raw_code);
}

static void controller_printer_update(
    const nh_printer_snapshot_t *snapshot,
    const nh_printer_status_t *status,
    void *ctx)
{
    (void)ctx;
    if (s_fleet_ready && status->configured && status->serial[0]) {
        esp_err_t fleet_err =
            nh_fleet_observe(status->serial, snapshot, status);
        if (fleet_err != ESP_OK) {
            ESP_LOGW(TAG, "Fleet observation failed: %s",
                     esp_err_to_name(fleet_err));
        }
        publish_fleet();
    }
    if (s_history_ready) {
        esp_err_t history_err = nh_history_observe(snapshot);
        if (history_err != ESP_OK) {
            ESP_LOGW(TAG, "History journal update failed: %s",
                     esp_err_to_name(history_err));
        }
        publish_history();
    }
    esp_err_t err = nh_ui_update(snapshot);
    if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) {
        ESP_LOGW(TAG, "Printer telemetry UI update failed: %s",
                 esp_err_to_name(err));
    }
    err = nh_ui_printer_update(status);
    if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) {
        ESP_LOGW(TAG, "Printer status UI update failed: %s",
                 esp_err_to_name(err));
    }
}

static esp_err_t controller_history_export(
    nh_history_export_format_t format, bool redact_job_names, void *ctx)
{
    (void)ctx;
    char path[NH_HISTORY_PATH_LENGTH];
    esp_err_t err = nh_history_export(
        format, redact_job_names, path, sizeof(path));
    if (err == ESP_OK) {
        ESP_LOGI(TAG, "History export written: %s", path);
    }
    return err;
}

static esp_err_t controller_history_backup(void *ctx)
{
    (void)ctx;
    char path[NH_HISTORY_PATH_LENGTH];
    esp_err_t err = nh_history_backup(path, sizeof(path));
    if (err == ESP_OK) {
        ESP_LOGI(TAG, "History backup written: %s", path);
    }
    return err;
}

static esp_err_t controller_file_review_queue(
    uint64_t file_id, uint64_t *queue_id, void *ctx)
{
    (void)ctx;
    if (!s_files_ready || !queue_id) {
        return ESP_ERR_INVALID_STATE;
    }
    nh_files_snapshot_t *snapshot = &s_files_view;
    esp_err_t err = nh_files_snapshot(snapshot);
    const nh_file_entry_t *file = NULL;
    if (err == ESP_OK) {
        for (uint8_t i = 0; i < snapshot->file_count; ++i) {
            if (snapshot->files[i].id == file_id) {
                file = &snapshot->files[i];
                break;
            }
        }
        err = file ? ESP_OK : ESP_ERR_NOT_FOUND;
    }
    if (err == ESP_OK) {
        err = nh_files_queue_add_reviewed(
            file_id, file->sha256, queue_id);
    }
    publish_files();
    return err;
}

static esp_err_t controller_file_bed_clear(uint64_t queue_id, void *ctx)
{
    (void)ctx;
    esp_err_t err = nh_files_queue_confirm_bed_clear(queue_id, true);
    publish_files();
    return err;
}

static esp_err_t controller_file_thumbnail(
    uint64_t file_id, uint8_t *buffer, size_t buffer_size,
    size_t *required_size, void *ctx)
{
    (void)ctx;
    return nh_files_thumbnail(
        file_id, buffer, buffer_size, required_size);
}

static esp_err_t controller_ota_enable(uint32_t duration_seconds, void *ctx)
{
    (void)ctx;
    return nh_ota_enable_window(duration_seconds);
}

static const char *controller_timezone_name(void *ctx)
{
    (void)ctx;
    return nh_settings_timezone_name();
}

static esp_err_t controller_timezone_next(void *ctx)
{
    (void)ctx;
    return nh_settings_timezone_next();
}

static esp_err_t controller_camera_set_active(bool active, void *ctx)
{
    (void)ctx;
    return nh_camera_set_active(active);
}

static void controller_camera_status(const nh_camera_status_t *status, void *ctx)
{
    (void)ctx;
    esp_err_t err = nh_ui_camera_status_update(status);
    if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) {
        ESP_LOGW(TAG, "Camera status UI update failed: %s",
                 esp_err_to_name(err));
    }
}

static void controller_camera_frame(const uint8_t *rgb565,
                                    uint16_t width,
                                    uint16_t height,
                                    uint16_t source_width,
                                    uint16_t source_height,
                                    void *ctx)
{
    (void)ctx;
    esp_err_t err = nh_ui_camera_frame(
        rgb565, width, height, source_width, source_height);
    if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) {
        ESP_LOGW(TAG, "Camera frame UI update failed: %s",
                 esp_err_to_name(err));
    }
}

static void init_nvs(void)
{
    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        err = nvs_flash_init();
    }
    ESP_ERROR_CHECK(err);
}

void app_main(void)
{
    ESP_LOGI(TAG, "PrintDeck booting");
    init_nvs();
    ESP_ERROR_CHECK(nh_settings_init());
    esp_err_t material_err = nh_material_init();
    if (material_err != ESP_OK) {
        ESP_LOGW(TAG, "Material catalog unavailable: %s",
                 esp_err_to_name(material_err));
    }
    esp_err_t fleet_err = nh_fleet_init();
    if (fleet_err == ESP_OK) {
        s_fleet_ready = true;
    } else {
        ESP_LOGW(TAG, "Fleet registry unavailable: %s",
                 esp_err_to_name(fleet_err));
    }

    nh_board_handles_t board = {0};
    ESP_ERROR_CHECK(nh_board_display_init(&board));

    const nh_ui_config_t ui_cfg = {
        .display = board.display,
        .snapshot = &s_snapshot,
        .action_handler = controller_action_handler,
        .action_ctx = &s_snapshot,
        .network_scan = controller_network_scan,
        .network_connect = controller_network_connect,
        .network_ctx = NULL,
        .printer_pair = controller_printer_pair,
        .alert_dismiss = controller_alert_dismiss,
        .printer_ctx = NULL,
        .ota_enable = controller_ota_enable,
        .ota_ctx = NULL,
        .timezone_name = controller_timezone_name,
        .timezone_next = controller_timezone_next,
        .timezone_ctx = NULL,
        .camera_set_active = controller_camera_set_active,
        .camera_ctx = NULL,
        .history_export = controller_history_export,
        .history_backup = controller_history_backup,
        .history_ctx = NULL,
        .file_review_queue = controller_file_review_queue,
        .file_bed_clear = controller_file_bed_clear,
        .file_thumbnail = controller_file_thumbnail,
        .files_ctx = NULL,
    };

    ESP_ERROR_CHECK(nh_ui_create(&ui_cfg));
    s_ui_ready = true;
    const nh_ai_snapshot_t ai_disabled = {
        .local_only = true,
        .notify_only = true,
    };
    ESP_ERROR_CHECK(nh_ui_ai_update(&ai_disabled));

    /*
     * Initialize the on-demand camera service before the display becomes
     * interactive so an immediate tap cannot race service creation.
     */
    const nh_camera_config_t camera_cfg = {
        .status_cb = controller_camera_status,
        .frame_cb = controller_camera_frame,
        .callback_ctx = NULL,
    };
    esp_err_t camera_err = nh_camera_init(&camera_cfg);
    if (camera_err != ESP_OK) {
        ESP_LOGE(TAG, "P1S camera service failed: %s",
                 esp_err_to_name(camera_err));
    }
    ESP_ERROR_CHECK(nh_board_backlight_set(82));

    const nh_network_config_t network_cfg = {
        .update_cb = controller_network_update,
        .update_ctx = NULL,
    };
    esp_err_t network_err = nh_network_init(&network_cfg);
    if (network_err != ESP_OK) {
        ESP_LOGE(TAG, "ESP32-C6 hosted Wi-Fi failed: %s",
                 esp_err_to_name(network_err));
    }

    /*
     * ESP-Hosted owns the P4's shared SDMMC controller (C6 on slot 1). Mount
     * the card on slot 0 only after network initialization has created that
     * controller. A failed card mount remains non-fatal to the UI and Wi-Fi.
     */
    esp_err_t sd_err = refresh_controller_sd();
    if (sd_err != ESP_OK) {
        ESP_LOGW(TAG, "SD card unavailable: %s", esp_err_to_name(sd_err));
    }
    publish_history();
    publish_files();
    publish_fleet();

    const nh_printer_config_t printer_cfg = {
        .snapshot = &s_snapshot,
        .default_ip = NULL,
        .default_serial = NULL,
        .update_cb = controller_printer_update,
        .update_ctx = NULL,
        .command_result_cb = controller_command_result,
        .command_result_ctx = NULL,
    };
    esp_err_t printer_err = nh_printer_init(&printer_cfg);
    if (printer_err != ESP_OK) {
        ESP_LOGE(TAG, "P1S LAN transport failed: %s",
                 esp_err_to_name(printer_err));
    }

    /*
     * esp_http_server requires the TCP/IP stack created by nh_network_init().
     * Starting OTA first can assert inside lwIP during boot.
     */
    esp_err_t ota_err = nh_ota_init();
    if (ota_err != ESP_OK) {
        ESP_LOGE(TAG, "Guarded LAN OTA failed: %s",
                 esp_err_to_name(ota_err));
    }

    ESP_LOGI(TAG,
             "PrintDeck UI ready; heap free internal=%u, PSRAM=%u bytes",
             (unsigned)heap_caps_get_free_size(MALLOC_CAP_INTERNAL),
             (unsigned)heap_caps_get_free_size(MALLOC_CAP_SPIRAM));
}
