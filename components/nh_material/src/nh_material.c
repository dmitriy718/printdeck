#include "nh_material.h"

#include <ctype.h>
#include <stddef.h>
#include <string.h>

#include "esp_rom_crc.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "nvs.h"

enum {
    NH_MATERIAL_SCHEMA_VERSION = 1,
};

typedef struct {
    uint32_t schema_version;
    nh_material_catalog_t catalog;
    uint32_t crc32;
} nh_material_record_t;

static const char *const NVS_NAMESPACE = "nh_material";
static const char *const NVS_CATALOG_KEY = "catalog_v1";
static nh_material_catalog_t s_catalog;
static SemaphoreHandle_t s_mutex;
static bool s_initialized;

static bool valid_text(const char *value, size_t maximum, bool allow_empty)
{
    if (!value) {
        return false;
    }
    size_t length = strnlen(value, maximum);
    if (length >= maximum || (!allow_empty && length == 0)) {
        return false;
    }
    for (size_t i = 0; i < length; ++i) {
        unsigned char c = (unsigned char)value[i];
        if (c < 0x20 || c == 0x7F) {
            return false;
        }
    }
    return true;
}

static bool valid_color(const char *color)
{
    if (!color || strlen(color) != 8) {
        return false;
    }
    for (size_t i = 0; i < 8; ++i) {
        if (!isxdigit((unsigned char)color[i])) {
            return false;
        }
    }
    return true;
}

static bool valid_entry(const nh_material_entry_t *entry)
{
    return entry &&
           valid_text(entry->id, sizeof(entry->id), false) &&
           valid_text(entry->label, sizeof(entry->label), false) &&
           valid_text(entry->material, sizeof(entry->material), false) &&
           valid_color(entry->color_rgba) &&
           entry->nominal_weight_grams > 0 &&
           entry->nominal_weight_grams <= 10000;
}

static uint32_t record_crc(const nh_material_record_t *record)
{
    return esp_rom_crc32_le(
        0, (const uint8_t *)record,
        offsetof(nh_material_record_t, crc32));
}

static esp_err_t persist_locked(void)
{
    nh_material_record_t record = {
        .schema_version = NH_MATERIAL_SCHEMA_VERSION,
        .catalog = s_catalog,
    };
    record.crc32 = record_crc(&record);

    nvs_handle_t nvs;
    esp_err_t err = nvs_open(NVS_NAMESPACE, NVS_READWRITE, &nvs);
    if (err != ESP_OK) {
        return err;
    }
    err = nvs_set_blob(nvs, NVS_CATALOG_KEY, &record, sizeof(record));
    if (err == ESP_OK) {
        err = nvs_commit(nvs);
    }
    nvs_close(nvs);
    return err;
}

esp_err_t nh_material_init(void)
{
    if (s_initialized) {
        return ESP_ERR_INVALID_STATE;
    }
    s_mutex = xSemaphoreCreateMutex();
    if (!s_mutex) {
        return ESP_ERR_NO_MEM;
    }

    nvs_handle_t nvs;
    esp_err_t err = nvs_open(NVS_NAMESPACE, NVS_READONLY, &nvs);
    if (err == ESP_ERR_NVS_NOT_FOUND) {
        memset(&s_catalog, 0, sizeof(s_catalog));
        s_initialized = true;
        return ESP_OK;
    }
    if (err != ESP_OK) {
        vSemaphoreDelete(s_mutex);
        s_mutex = NULL;
        return err;
    }

    nh_material_record_t record = {0};
    size_t size = sizeof(record);
    err = nvs_get_blob(nvs, NVS_CATALOG_KEY, &record, &size);
    nvs_close(nvs);
    if (err == ESP_ERR_NVS_NOT_FOUND) {
        memset(&s_catalog, 0, sizeof(s_catalog));
        s_initialized = true;
        return ESP_OK;
    }
    if (err != ESP_OK || size != sizeof(record) ||
        record.schema_version != NH_MATERIAL_SCHEMA_VERSION ||
        record.catalog.count > NH_MATERIAL_CATALOG_MAX ||
        record.crc32 != record_crc(&record)) {
        vSemaphoreDelete(s_mutex);
        s_mutex = NULL;
        return ESP_ERR_INVALID_CRC;
    }
    for (uint8_t i = 0; i < record.catalog.count; ++i) {
        if (!valid_entry(&record.catalog.entries[i])) {
            vSemaphoreDelete(s_mutex);
            s_mutex = NULL;
            return ESP_ERR_INVALID_ARG;
        }
    }
    s_catalog = record.catalog;
    s_initialized = true;
    return ESP_OK;
}

esp_err_t nh_material_snapshot(nh_material_catalog_t *catalog)
{
    if (!s_initialized || !catalog) {
        return ESP_ERR_INVALID_STATE;
    }
    (void)xSemaphoreTake(s_mutex, portMAX_DELAY);
    *catalog = s_catalog;
    (void)xSemaphoreGive(s_mutex);
    return ESP_OK;
}

esp_err_t nh_material_upsert(const nh_material_entry_t *entry)
{
    if (!s_initialized) {
        return ESP_ERR_INVALID_STATE;
    }
    if (!valid_entry(entry)) {
        return ESP_ERR_INVALID_ARG;
    }

    (void)xSemaphoreTake(s_mutex, portMAX_DELAY);
    nh_material_catalog_t previous = s_catalog;
    size_t index = s_catalog.count;
    for (size_t i = 0; i < s_catalog.count; ++i) {
        if (strcmp(s_catalog.entries[i].id, entry->id) == 0) {
            index = i;
            break;
        }
    }
    if (index == s_catalog.count) {
        if (s_catalog.count >= NH_MATERIAL_CATALOG_MAX) {
            (void)xSemaphoreGive(s_mutex);
            return ESP_ERR_NO_MEM;
        }
        s_catalog.count++;
    }
    s_catalog.entries[index] = *entry;
    esp_err_t err = persist_locked();
    if (err != ESP_OK) {
        s_catalog = previous;
    }
    (void)xSemaphoreGive(s_mutex);
    return err;
}

esp_err_t nh_material_remove(const char *id)
{
    if (!s_initialized || !id || !id[0]) {
        return ESP_ERR_INVALID_ARG;
    }
    (void)xSemaphoreTake(s_mutex, portMAX_DELAY);
    size_t index = s_catalog.count;
    for (size_t i = 0; i < s_catalog.count; ++i) {
        if (strcmp(s_catalog.entries[i].id, id) == 0) {
            index = i;
            break;
        }
    }
    if (index == s_catalog.count) {
        (void)xSemaphoreGive(s_mutex);
        return ESP_ERR_NOT_FOUND;
    }
    nh_material_catalog_t previous = s_catalog;
    for (size_t i = index + 1; i < s_catalog.count; ++i) {
        s_catalog.entries[i - 1] = s_catalog.entries[i];
    }
    memset(&s_catalog.entries[s_catalog.count - 1], 0,
           sizeof(s_catalog.entries[0]));
    s_catalog.count--;
    esp_err_t err = persist_locked();
    if (err != ESP_OK) {
        s_catalog = previous;
    }
    (void)xSemaphoreGive(s_mutex);
    return err;
}
