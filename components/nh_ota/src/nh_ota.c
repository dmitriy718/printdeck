#include "nh_ota.h"

#include <stdbool.h>
#include <stdio.h>

#include "esp_app_desc.h"
#include "esp_http_server.h"
#include "esp_log.h"
#include "esp_ota_ops.h"
#include "esp_system.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "nh_diagnostics.h"

static const char *TAG = "nh_ota";

static httpd_handle_t s_server;
static portMUX_TYPE s_state_lock = portMUX_INITIALIZER_UNLOCKED;
static int64_t s_window_deadline_us;
static bool s_update_in_progress;

enum {
    NH_OTA_RECEIVE_BUFFER_SIZE = 4096,
    NH_OTA_MAX_CONSECUTIVE_TIMEOUTS = 5,
    NH_OTA_RESTART_DELAY_MS = 1000,
    NH_OTA_VALIDATION_DELAY_MS = 10000,
};

static uint32_t window_seconds_remaining(void)
{
    int64_t deadline;
    portENTER_CRITICAL(&s_state_lock);
    deadline = s_window_deadline_us;
    portEXIT_CRITICAL(&s_state_lock);

    int64_t remaining = deadline - esp_timer_get_time();
    if (remaining <= 0) {
        return 0;
    }
    return (uint32_t)((remaining + 999999) / 1000000);
}

static bool claim_update_window(void)
{
    bool claimed = false;
    int64_t now = esp_timer_get_time();

    portENTER_CRITICAL(&s_state_lock);
    if (!s_update_in_progress && s_window_deadline_us > now) {
        s_update_in_progress = true;
        s_window_deadline_us = 0;
        claimed = true;
    }
    portEXIT_CRITICAL(&s_state_lock);
    return claimed;
}

static void release_failed_update(void)
{
    portENTER_CRITICAL(&s_state_lock);
    s_update_in_progress = false;
    portEXIT_CRITICAL(&s_state_lock);
}

static esp_err_t ota_status_handler(httpd_req_t *request)
{
    const esp_app_desc_t *app = esp_app_get_description();
    nh_diagnostics_snapshot_t health;
    nh_diagnostics_snapshot(&health);
    char response[640];
    snprintf(response, sizeof(response),
             "{\"service\":\"printdeck-ota\",\"version\":\"%s\","
             "\"window_seconds\":%lu,\"upload\":\"POST /api/v1/ota\","
             "\"uptime_seconds\":%lu,\"reset_reason\":%d,"
             "\"partition\":\"%s\",\"ota_pending_verification\":%s,"
             "\"coredump\":{\"partition_bytes\":%u},"
             "\"heap\":{\"internal_free\":%u,\"internal_minimum\":%u,"
             "\"psram_free\":%u},"
             "\"stack\":{\"minimum_free\":%u,\"task\":\"%s\","
             "\"tracked_tasks\":%u}}",
             app ? app->version : "unknown",
             (unsigned long)window_seconds_remaining(),
             (unsigned long)health.uptime_seconds,
             (int)health.reset_reason,
             health.running_partition,
             health.ota_pending_verification ? "true" : "false",
             (unsigned)health.coredump_partition_bytes,
             (unsigned)health.internal_free_bytes,
             (unsigned)health.internal_minimum_bytes,
             (unsigned)health.psram_free_bytes,
             (unsigned)health.minimum_task_stack_bytes,
             health.minimum_stack_task,
             (unsigned)health.tracked_task_count);
    httpd_resp_set_type(request, "application/json");
    httpd_resp_set_hdr(request, "Cache-Control", "no-store");
    return httpd_resp_send(request, response, HTTPD_RESP_USE_STRLEN);
}

static void restart_task(void *arg)
{
    (void)arg;
    vTaskDelay(pdMS_TO_TICKS(NH_OTA_RESTART_DELAY_MS));
    esp_restart();
}

static esp_err_t ota_upload_handler(httpd_req_t *request)
{
    if (!claim_update_window()) {
        httpd_resp_set_status(request, "403 Forbidden");
        return httpd_resp_send(
            request,
            "OTA is locked. Enable the five-minute update window on the display.",
            HTTPD_RESP_USE_STRLEN);
    }

    const esp_partition_t *partition =
        esp_ota_get_next_update_partition(NULL);
    if (!partition || request->content_len <= 0 ||
        request->content_len > partition->size) {
        release_failed_update();
        return httpd_resp_send_err(request, HTTPD_400_BAD_REQUEST,
                                   "Invalid firmware size");
    }

    esp_ota_handle_t update_handle = 0;
    esp_err_t err =
        esp_ota_begin(partition, request->content_len, &update_handle);
    if (err != ESP_OK) {
        release_failed_update();
        ESP_LOGE(TAG, "OTA begin failed: %s", esp_err_to_name(err));
        return httpd_resp_send_err(request, HTTPD_500_INTERNAL_SERVER_ERROR,
                                   "Could not begin OTA");
    }

    uint8_t buffer[NH_OTA_RECEIVE_BUFFER_SIZE];
    size_t remaining = request->content_len;
    unsigned consecutive_timeouts = 0;
    while (remaining > 0) {
        size_t wanted =
            remaining < sizeof(buffer) ? remaining : sizeof(buffer);
        int received = httpd_req_recv(request, (char *)buffer, wanted);
        if (received == HTTPD_SOCK_ERR_TIMEOUT) {
            if (++consecutive_timeouts >= NH_OTA_MAX_CONSECUTIVE_TIMEOUTS) {
                err = ESP_ERR_TIMEOUT;
                ESP_LOGW(TAG, "OTA upload abandoned after repeated idle timeouts");
                break;
            }
            continue;
        }
        if (received <= 0) {
            err = ESP_FAIL;
            break;
        }
        consecutive_timeouts = 0;

        err = esp_ota_write(update_handle, buffer, (size_t)received);
        if (err != ESP_OK) {
            break;
        }
        remaining -= (size_t)received;
    }

    if (err == ESP_OK && remaining == 0) {
        err = esp_ota_end(update_handle);
    } else {
        esp_ota_abort(update_handle);
    }
    if (err == ESP_OK) {
        err = esp_ota_set_boot_partition(partition);
    }
    if (err != ESP_OK) {
        release_failed_update();
        ESP_LOGE(TAG, "OTA upload failed: %s", esp_err_to_name(err));
        return httpd_resp_send_err(request, HTTPD_500_INTERNAL_SERVER_ERROR,
                                   "Firmware validation failed");
    }

    ESP_LOGI(TAG, "OTA image verified in %s; restarting", partition->label);
    httpd_resp_set_type(request, "application/json");
    httpd_resp_send(request,
                    "{\"ok\":true,\"message\":\"verified; restarting\"}",
                    HTTPD_RESP_USE_STRLEN);
    if (xTaskCreate(restart_task, "nh_ota_restart", 3072,
                    NULL, 5, NULL) != pdPASS) {
        /*
         * The new image is already selected and will boot on the next reset.
         * Keep the current image alive instead of forcing a restart from a
         * low-memory failure path.
         */
        ESP_LOGE(TAG, "Could not allocate OTA restart task; reset manually");
    }
    return ESP_OK;
}

static void validation_task(void *arg)
{
    (void)arg;
    vTaskDelay(pdMS_TO_TICKS(NH_OTA_VALIDATION_DELAY_MS));
    esp_err_t err = esp_ota_mark_app_valid_cancel_rollback();
    if (err == ESP_OK) {
        ESP_LOGI(TAG, "Running OTA image marked valid");
    } else if (err != ESP_ERR_OTA_ROLLBACK_INVALID_STATE) {
        ESP_LOGW(TAG, "Could not confirm OTA image: %s",
                 esp_err_to_name(err));
    }
    vTaskDelete(NULL);
}

esp_err_t nh_ota_enable_window(uint32_t duration_seconds)
{
    if (!s_server || duration_seconds == 0) {
        return ESP_ERR_INVALID_STATE;
    }

    int64_t deadline =
        esp_timer_get_time() + (int64_t)duration_seconds * 1000000;
    portENTER_CRITICAL(&s_state_lock);
    bool busy = s_update_in_progress;
    if (!busy) {
        s_window_deadline_us = deadline;
    }
    portEXIT_CRITICAL(&s_state_lock);
    if (busy) {
        return ESP_ERR_INVALID_STATE;
    }

    ESP_LOGI(TAG, "LAN OTA enabled for %lu seconds",
             (unsigned long)duration_seconds);
    return ESP_OK;
}

esp_err_t nh_ota_init(void)
{
    if (s_server) {
        return ESP_ERR_INVALID_STATE;
    }

    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    config.stack_size = 12 * 1024;
    config.max_uri_handlers = 4;
    config.lru_purge_enable = true;

    esp_err_t err = httpd_start(&s_server, &config);
    if (err != ESP_OK) {
        return err;
    }

    const httpd_uri_t status_uri = {
        .uri = "/api/v1/ota",
        .method = HTTP_GET,
        .handler = ota_status_handler,
    };
    const httpd_uri_t upload_uri = {
        .uri = "/api/v1/ota",
        .method = HTTP_POST,
        .handler = ota_upload_handler,
    };
    err = httpd_register_uri_handler(s_server, &status_uri);
    if (err == ESP_OK) {
        err = httpd_register_uri_handler(s_server, &upload_uri);
    }
    if (err != ESP_OK) {
        httpd_stop(s_server);
        s_server = NULL;
        return err;
    }

    BaseType_t task_created =
        xTaskCreate(validation_task, "nh_ota_validate", 3072, NULL, 3, NULL);
    if (task_created != pdPASS) {
        httpd_stop(s_server);
        s_server = NULL;
        return ESP_ERR_NO_MEM;
    }

    ESP_LOGI(TAG, "Guarded LAN OTA service ready on port 80");
    return ESP_OK;
}
