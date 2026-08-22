#include "nh_fleet.h"

#include <ctype.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>

#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "lwip/ip4_addr.h"
#include "nvs.h"

enum {
    NH_FLEET_MAGIC = 0x5044464cu,
    NH_FLEET_SCHEMA = 1,
};

typedef struct {
    uint32_t magic;
    uint16_t schema;
    uint16_t size;
    nh_fleet_printer_t printers[NH_FLEET_MAX_PRINTERS];
    uint8_t count;
    uint8_t reserved[7];
    uint32_t crc32;
} fleet_record_t;

static SemaphoreHandle_t s_mutex;
static nvs_handle_t s_nvs;
static nh_fleet_snapshot_t s_fleet;
static bool s_initialized;

static uint32_t crc32_bytes(const void *data, size_t length)
{
    const uint8_t *bytes = data;
    uint32_t crc = UINT32_MAX;
    for (size_t i = 0; i < length; ++i) {
        crc ^= bytes[i];
        for (unsigned bit = 0; bit < 8; ++bit) {
            uint32_t mask = (uint32_t)-(int32_t)(crc & 1u);
            crc = (crc >> 1) ^ (0xEDB88320u & mask);
        }
    }
    return ~crc;
}

static bool bounded_text(const char *text, size_t capacity, bool allow_empty)
{
    size_t length = text ? strnlen(text, capacity) : capacity;
    if (length >= capacity || (!allow_empty && length == 0)) {
        return false;
    }
    for (size_t i = 0; i < length; ++i) {
        unsigned char value = (unsigned char)text[i];
        if (value < 0x20 || value == 0x7f) {
            return false;
        }
    }
    return true;
}

static bool private_ipv4(const char *text)
{
    ip4_addr_t address;
    if (!ip4addr_aton(text, &address)) {
        return false;
    }
    uint8_t first = ip4_addr1(&address);
    uint8_t second = ip4_addr2(&address);
    return first == 10 ||
           (first == 172 && second >= 16 && second <= 31) ||
           (first == 192 && second == 168);
}

static uint64_t identity_id(const char *serial)
{
    uint64_t hash = UINT64_C(1469598103934665603);
    for (const unsigned char *cursor = (const unsigned char *)serial;
         *cursor; ++cursor) {
        hash ^= *cursor;
        hash *= UINT64_C(1099511628211);
    }
    return hash ? hash : 1;
}

static int compare_attention(const void *left_value,
                             const void *right_value)
{
    const nh_fleet_printer_t *left = left_value;
    const nh_fleet_printer_t *right = right_value;
    nh_fleet_attention_t left_attention = nh_fleet_attention(left);
    nh_fleet_attention_t right_attention = nh_fleet_attention(right);
    if (left_attention != right_attention) {
        return left_attention < right_attention ? -1 : 1;
    }
    return strcasecmp(left->name, right->name);
}

static esp_err_t persist_locked(void)
{
    fleet_record_t record = {
        .magic = NH_FLEET_MAGIC,
        .schema = NH_FLEET_SCHEMA,
        .size = sizeof(record),
        .count = s_fleet.count,
    };
    memcpy(record.printers, s_fleet.printers, sizeof(record.printers));
    record.crc32 = crc32_bytes(&record, offsetof(fleet_record_t, crc32));
    esp_err_t err =
        nvs_set_blob(s_nvs, "profiles", &record, sizeof(record));
    return err == ESP_OK ? nvs_commit(s_nvs) : err;
}

static esp_err_t load_locked(void)
{
    fleet_record_t record;
    size_t size = sizeof(record);
    esp_err_t err = nvs_get_blob(s_nvs, "profiles", &record, &size);
    if (err == ESP_ERR_NVS_NOT_FOUND) {
        return ESP_OK;
    }
    if (err != ESP_OK || size != sizeof(record) ||
        record.magic != NH_FLEET_MAGIC ||
        record.schema != NH_FLEET_SCHEMA ||
        record.size != sizeof(record) ||
        record.count > NH_FLEET_MAX_PRINTERS ||
        record.crc32 !=
            crc32_bytes(&record, offsetof(fleet_record_t, crc32))) {
        return ESP_ERR_INVALID_CRC;
    }
    memcpy(s_fleet.printers, record.printers, sizeof(record.printers));
    s_fleet.count = record.count;
    for (uint8_t i = 0; i < s_fleet.count; ++i) {
        s_fleet.printers[i].connection = NH_PRINTER_OFFLINE;
        s_fleet.printers[i].active_transport = false;
    }
    return ESP_OK;
}

esp_err_t nh_fleet_init(void)
{
    if (s_initialized) {
        return ESP_ERR_INVALID_STATE;
    }
    s_mutex = xSemaphoreCreateMutex();
    if (!s_mutex) {
        return ESP_ERR_NO_MEM;
    }
    esp_err_t err = nvs_open("nh_fleet", NVS_READWRITE, &s_nvs);
    if (err == ESP_OK) {
        err = load_locked();
    }
    if (err != ESP_OK) {
        if (s_nvs) {
            nvs_close(s_nvs);
            s_nvs = 0;
        }
        vSemaphoreDelete(s_mutex);
        s_mutex = NULL;
        return err;
    }
    s_initialized = true;
    return ESP_OK;
}

static int find_serial_locked(const char *serial)
{
    for (uint8_t i = 0; i < s_fleet.count; ++i) {
        if (strcmp(s_fleet.printers[i].serial, serial) == 0) {
            return i;
        }
    }
    return -1;
}

static void update_remaining(nh_fleet_printer_t *printer,
                             const char *remaining)
{
    unsigned hours = 0;
    unsigned minutes = 0;
    printer->remaining_known = false;
    printer->remaining_minutes = 0;
    if (remaining &&
        sscanf(remaining, "%uh %um", &hours, &minutes) == 2 &&
        hours <= 1000 && minutes < 60 &&
        hours * 60u + minutes <= UINT16_MAX) {
        printer->remaining_minutes =
            (uint16_t)(hours * 60u + minutes);
        printer->remaining_known = true;
    }
}

esp_err_t nh_fleet_upsert_confirmed(const nh_fleet_printer_t *printer)
{
    if (!s_initialized || !printer || !printer->identity_confirmed ||
        !private_ipv4(printer->ip_address) ||
        !bounded_text(printer->serial, sizeof(printer->serial), false) ||
        !bounded_text(printer->name, sizeof(printer->name), false) ||
        !bounded_text(printer->model, sizeof(printer->model), false) ||
        !bounded_text(printer->firmware, sizeof(printer->firmware), true)) {
        return ESP_ERR_INVALID_ARG;
    }
    (void)xSemaphoreTake(s_mutex, portMAX_DELAY);
    nh_fleet_snapshot_t previous = s_fleet;
    int index = find_serial_locked(printer->serial);
    if (index < 0) {
        if (s_fleet.count >= NH_FLEET_MAX_PRINTERS) {
            (void)xSemaphoreGive(s_mutex);
            return ESP_ERR_NO_MEM;
        }
        index = s_fleet.count++;
    }
    nh_fleet_printer_t *saved = &s_fleet.printers[index];
    *saved = *printer;
    saved->id = identity_id(saved->serial);
    saved->capabilities =
        nh_fleet_capabilities_for(saved->model, saved->firmware);
    s_fleet.generation++;
    esp_err_t err = persist_locked();
    if (err != ESP_OK) {
        s_fleet = previous;
    }
    (void)xSemaphoreGive(s_mutex);
    return err;
}

esp_err_t nh_fleet_observe(const char *serial,
                           const nh_printer_snapshot_t *snapshot,
                           const nh_printer_status_t *status)
{
    if (!s_initialized || !serial || !snapshot || !status) {
        return ESP_ERR_INVALID_ARG;
    }
    (void)xSemaphoreTake(s_mutex, portMAX_DELAY);
    int index = find_serial_locked(serial);
    if (index < 0) {
        if (s_fleet.count >= NH_FLEET_MAX_PRINTERS ||
            !bounded_text(serial, NH_PRINTER_SERIAL_MAX_LENGTH + 1, false)) {
            (void)xSemaphoreGive(s_mutex);
            return ESP_ERR_NOT_FOUND;
        }
        index = s_fleet.count++;
        nh_fleet_printer_t *discovered = &s_fleet.printers[index];
        memset(discovered, 0, sizeof(*discovered));
        discovered->id = identity_id(serial);
        strlcpy(discovered->serial, serial, sizeof(discovered->serial));
        strlcpy(discovered->ip_address, status->ip_address,
                sizeof(discovered->ip_address));
        strlcpy(discovered->name,
                snapshot->printer_name && snapshot->printer_name[0]
                    ? snapshot->printer_name
                    : "Observed printer",
                sizeof(discovered->name));
    }
    nh_fleet_printer_t *printer = &s_fleet.printers[index];
    printer->connection = status->state;
    printer->job = snapshot->job;
    printer->progress_percent = snapshot->progress_percent;
    update_remaining(printer, snapshot->remaining);
    printer->active_alerts = snapshot->active_alert_count;
    printer->active_transport = true;
    printer->generation++;
    for (uint8_t i = 0; i < s_fleet.count; ++i) {
        if (i != index) {
            s_fleet.printers[i].active_transport = false;
        }
    }
    s_fleet.generation++;
    (void)xSemaphoreGive(s_mutex);
    return ESP_OK;
}

esp_err_t nh_fleet_set_active(uint64_t printer_id)
{
    if (!s_initialized || printer_id == 0) {
        return ESP_ERR_INVALID_ARG;
    }
    (void)xSemaphoreTake(s_mutex, portMAX_DELAY);
    bool found = false;
    for (uint8_t i = 0; i < s_fleet.count; ++i) {
        bool active = s_fleet.printers[i].id == printer_id;
        s_fleet.printers[i].active_transport = active;
        found = found || active;
    }
    if (found) {
        s_fleet.generation++;
    }
    (void)xSemaphoreGive(s_mutex);
    return found ? ESP_OK : ESP_ERR_NOT_FOUND;
}

esp_err_t nh_fleet_remove(uint64_t printer_id, const char *confirmation)
{
    if (!s_initialized || printer_id == 0 || !confirmation ||
        strcmp(confirmation, "REMOVE PRINTER") != 0) {
        return ESP_ERR_INVALID_ARG;
    }
    (void)xSemaphoreTake(s_mutex, portMAX_DELAY);
    int index = -1;
    for (uint8_t i = 0; i < s_fleet.count; ++i) {
        if (s_fleet.printers[i].id == printer_id) {
            index = i;
            break;
        }
    }
    if (index < 0) {
        (void)xSemaphoreGive(s_mutex);
        return ESP_ERR_NOT_FOUND;
    }
    nh_fleet_snapshot_t previous = s_fleet;
    for (uint8_t i = (uint8_t)index + 1; i < s_fleet.count; ++i) {
        s_fleet.printers[i - 1] = s_fleet.printers[i];
    }
    memset(&s_fleet.printers[--s_fleet.count], 0,
           sizeof(s_fleet.printers[0]));
    s_fleet.generation++;
    esp_err_t err = persist_locked();
    if (err != ESP_OK) {
        s_fleet = previous;
    }
    (void)xSemaphoreGive(s_mutex);
    return err;
}

esp_err_t nh_fleet_snapshot(nh_fleet_snapshot_t *snapshot)
{
    if (!s_initialized || !snapshot) {
        return ESP_ERR_INVALID_ARG;
    }
    (void)xSemaphoreTake(s_mutex, portMAX_DELAY);
    *snapshot = s_fleet;
    snapshot->attention_count = 0;
    for (uint8_t i = 0; i < snapshot->count; ++i) {
        nh_fleet_attention_t attention =
            nh_fleet_attention(&snapshot->printers[i]);
        if (attention == NH_FLEET_ATTENTION_ERROR ||
            attention == NH_FLEET_ATTENTION_PAUSED ||
            attention == NH_FLEET_ATTENTION_FINISHING) {
            snapshot->attention_count++;
        }
    }
    qsort(snapshot->printers, snapshot->count,
          sizeof(snapshot->printers[0]), compare_attention);
    (void)xSemaphoreGive(s_mutex);
    return ESP_OK;
}

esp_err_t nh_fleet_find_material(const char *material,
                                 uint64_t *printer_ids,
                                 size_t capacity,
                                 size_t *match_count)
{
    if (!s_initialized || !material || !material[0] || !match_count ||
        (capacity && !printer_ids) || strnlen(material, 8) >= 8) {
        return ESP_ERR_INVALID_ARG;
    }
    (void)xSemaphoreTake(s_mutex, portMAX_DELAY);
    size_t matches = 0;
    for (uint8_t i = 0; i < s_fleet.count; ++i) {
        if (s_fleet.printers[i].material_known &&
            strcasecmp(s_fleet.printers[i].material, material) == 0) {
            if (matches < capacity) {
                printer_ids[matches] = s_fleet.printers[i].id;
            }
            matches++;
        }
    }
    *match_count = matches;
    (void)xSemaphoreGive(s_mutex);
    return matches > capacity ? ESP_ERR_INVALID_SIZE : ESP_OK;
}
