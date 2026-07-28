#include "esp_err.h"
#include "esp_heap_caps.h"
#include "esp_log.h"
#include "nvs_flash.h"

#include "nh_board.h"
#include "nh_camera.h"
#include "nh_core.h"
#include "nh_network.h"
#include "nh_ota.h"
#include "nh_printer.h"
#include "nh_settings.h"
#include "nh_ui.h"

static const char *TAG = "nh_main";
static bool s_ui_ready;

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
        return refresh_controller_sd();
    }
    (void)ctx;
    return nh_printer_action(action, value);
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

static void controller_printer_update(
    const nh_printer_snapshot_t *snapshot,
    const nh_printer_status_t *status,
    void *ctx)
{
    (void)ctx;
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
        .printer_ctx = NULL,
        .ota_enable = controller_ota_enable,
        .ota_ctx = NULL,
        .timezone_name = controller_timezone_name,
        .timezone_next = controller_timezone_next,
        .timezone_ctx = NULL,
        .camera_set_active = controller_camera_set_active,
        .camera_ctx = NULL,
    };

    ESP_ERROR_CHECK(nh_ui_create(&ui_cfg));
    s_ui_ready = true;

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

    const nh_printer_config_t printer_cfg = {
        .snapshot = &s_snapshot,
        .default_ip = NULL,
        .default_serial = NULL,
        .update_cb = controller_printer_update,
        .update_ctx = NULL,
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
