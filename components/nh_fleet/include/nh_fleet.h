#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "esp_err.h"
#include "nh_core.h"
#include "nh_printer.h"

#ifdef __cplusplus
extern "C" {
#endif

enum {
    NH_FLEET_MAX_PRINTERS = 4,
    NH_FLEET_NAME_LENGTH = 32,
    NH_FLEET_MODEL_LENGTH = 16,
    NH_FLEET_FIRMWARE_LENGTH = 24,
};

typedef enum {
    NH_FLEET_CAP_TELEMETRY = 1u << 0,
    NH_FLEET_CAP_CAMERA = 1u << 1,
    NH_FLEET_CAP_AMS = 1u << 2,
    NH_FLEET_CAP_HMS = 1u << 3,
    NH_FLEET_CAP_FILES = 1u << 4,
    NH_FLEET_CAP_BASIC_COMMANDS = 1u << 5,
    NH_FLEET_CAP_OBJECT_SKIP = 1u << 6,
    NH_FLEET_CAP_TEMPERATURE = 1u << 7,
    NH_FLEET_CAP_MOTION = 1u << 8,
} nh_fleet_capability_t;

typedef enum {
    NH_FLEET_ATTENTION_ERROR = 0,
    NH_FLEET_ATTENTION_PAUSED,
    NH_FLEET_ATTENTION_FINISHING,
    NH_FLEET_ATTENTION_PRINTING,
    NH_FLEET_ATTENTION_IDLE,
    NH_FLEET_ATTENTION_OFFLINE,
} nh_fleet_attention_t;

typedef struct {
    uint64_t id;
    char name[NH_FLEET_NAME_LENGTH];
    char ip_address[NH_PRINTER_IP_MAX_LENGTH + 1];
    char serial[NH_PRINTER_SERIAL_MAX_LENGTH + 1];
    char model[NH_FLEET_MODEL_LENGTH];
    char firmware[NH_FLEET_FIRMWARE_LENGTH];
    char material[8];
    uint32_t capabilities;
    uint32_t generation;
    nh_printer_state_t connection;
    nh_job_state_t job;
    uint16_t remaining_minutes;
    uint8_t progress_percent;
    uint8_t active_alerts;
    bool identity_confirmed;
    bool active_transport;
    bool material_known;
    bool remaining_known;
} nh_fleet_printer_t;

typedef struct {
    nh_fleet_printer_t printers[NH_FLEET_MAX_PRINTERS];
    uint8_t count;
    uint8_t attention_count;
    uint32_t generation;
} nh_fleet_snapshot_t;

esp_err_t nh_fleet_init(void);
uint32_t nh_fleet_capabilities_for(const char *model, const char *firmware);
esp_err_t nh_fleet_upsert_confirmed(const nh_fleet_printer_t *printer);
esp_err_t nh_fleet_observe(const char *serial,
                           const nh_printer_snapshot_t *snapshot,
                           const nh_printer_status_t *status);
esp_err_t nh_fleet_set_active(uint64_t printer_id);
esp_err_t nh_fleet_remove(uint64_t printer_id, const char *confirmation);
esp_err_t nh_fleet_snapshot(nh_fleet_snapshot_t *snapshot);
esp_err_t nh_fleet_find_material(const char *material,
                                 uint64_t *printer_ids,
                                 size_t capacity,
                                 size_t *match_count);
nh_fleet_attention_t nh_fleet_attention(const nh_fleet_printer_t *printer);
const char *nh_fleet_attention_label(nh_fleet_attention_t attention);

#ifdef __cplusplus
}
#endif
