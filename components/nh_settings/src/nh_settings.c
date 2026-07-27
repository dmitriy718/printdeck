#include "nh_settings.h"

#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <time.h>

#include "esp_log.h"
#include "nvs.h"

typedef struct {
    const char *name;
    const char *posix_rule;
} timezone_preset_t;

/*
 * POSIX TZ strings keep this feature independent of a filesystem timezone
 * database. The selected preset is stored as a non-sensitive NVS byte.
 */
static const timezone_preset_t s_timezones[] = {
    {"UTC", "UTC0"},
    {"NEW YORK", "EST5EDT,M3.2.0/2,M11.1.0/2"},
    {"CHICAGO", "CST6CDT,M3.2.0/2,M11.1.0/2"},
    {"DENVER", "MST7MDT,M3.2.0/2,M11.1.0/2"},
    {"PHOENIX", "MST7"},
    {"LOS ANGELES", "PST8PDT,M3.2.0/2,M11.1.0/2"},
    {"ANCHORAGE", "AKST9AKDT,M3.2.0/2,M11.1.0/2"},
    {"HONOLULU", "HST10"},
    {"LONDON", "GMT0BST,M3.5.0/1,M10.5.0/2"},
    {"BERLIN", "CET-1CEST,M3.5.0/2,M10.5.0/3"},
    {"DUBAI", "GST-4"},
    {"INDIA", "IST-5:30"},
    {"SINGAPORE", "SGT-8"},
    {"TOKYO", "JST-9"},
    {"SYDNEY", "AEST-10AEDT,M10.1.0/2,M4.1.0/3"},
};

static const char *TAG = "nh_settings";
static const char *const NVS_NAMESPACE = "nh_settings";
static const char *const NVS_TIMEZONE_KEY = "timezone";
static const uint8_t DEFAULT_TIMEZONE_INDEX = 1;

static nvs_handle_t s_nvs;
static uint8_t s_timezone_index = DEFAULT_TIMEZONE_INDEX;
static bool s_initialized;

static esp_err_t apply_timezone(uint8_t index)
{
    if (index >= sizeof(s_timezones) / sizeof(s_timezones[0])) {
        return ESP_ERR_INVALID_ARG;
    }
    if (setenv("TZ", s_timezones[index].posix_rule, 1) != 0) {
        return ESP_FAIL;
    }
    tzset();
    return ESP_OK;
}

esp_err_t nh_settings_init(void)
{
    if (s_initialized) {
        return ESP_ERR_INVALID_STATE;
    }

    esp_err_t err = nvs_open(NVS_NAMESPACE, NVS_READWRITE, &s_nvs);
    if (err != ESP_OK) {
        return err;
    }

    uint8_t stored_index = DEFAULT_TIMEZONE_INDEX;
    err = nvs_get_u8(s_nvs, NVS_TIMEZONE_KEY, &stored_index);
    if (err != ESP_OK && err != ESP_ERR_NVS_NOT_FOUND) {
        nvs_close(s_nvs);
        s_nvs = 0;
        return err;
    }
    if (stored_index >= sizeof(s_timezones) / sizeof(s_timezones[0])) {
        ESP_LOGW(TAG, "Ignoring invalid timezone preset %u",
                 (unsigned)stored_index);
        stored_index = DEFAULT_TIMEZONE_INDEX;
    }

    err = apply_timezone(stored_index);
    if (err != ESP_OK) {
        nvs_close(s_nvs);
        s_nvs = 0;
        return err;
    }
    s_timezone_index = stored_index;
    s_initialized = true;
    ESP_LOGI(TAG, "Timezone set to %s",
             s_timezones[s_timezone_index].name);
    return ESP_OK;
}

const char *nh_settings_timezone_name(void)
{
    return s_timezones[s_timezone_index].name;
}

esp_err_t nh_settings_timezone_next(void)
{
    if (!s_initialized || !s_nvs) {
        return ESP_ERR_INVALID_STATE;
    }

    uint8_t next = (uint8_t)(
        (s_timezone_index + 1U) %
        (sizeof(s_timezones) / sizeof(s_timezones[0])));
    uint8_t previous = s_timezone_index;
    esp_err_t err = apply_timezone(next);
    if (err != ESP_OK) {
        return err;
    }

    err = nvs_set_u8(s_nvs, NVS_TIMEZONE_KEY, next);
    if (err == ESP_OK) {
        err = nvs_commit(s_nvs);
    }
    if (err != ESP_OK) {
        if (apply_timezone(previous) != ESP_OK) {
            ESP_LOGE(TAG, "Could not restore timezone after NVS failure");
        }
        return err;
    }

    s_timezone_index = next;
    ESP_LOGI(TAG, "Timezone changed to %s",
             s_timezones[s_timezone_index].name);
    return ESP_OK;
}
