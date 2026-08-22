#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    NH_CONNECTION_UNCONFIGURED = 0,
    NH_CONNECTION_CONNECTING,
    NH_CONNECTION_ONLINE,
    NH_CONNECTION_OFFLINE,
    NH_CONNECTION_ERROR,
} nh_connection_state_t;

typedef enum {
    NH_JOB_UNKNOWN = 0,
    NH_JOB_IDLE,
    NH_JOB_PREPARING,
    NH_JOB_PRINTING,
    NH_JOB_PAUSED,
    NH_JOB_COMPLETE,
    NH_JOB_FAILED,
} nh_job_state_t;

enum {
    NH_ALERT_MAX = 12,
    NH_ALERT_CODE_LENGTH = 32,
    NH_ALERT_TITLE_LENGTH = 80,
    NH_ALERT_GUIDANCE_LENGTH = 120,
    NH_AMS_MAX_UNITS = 4,
    NH_AMS_MAX_TRAYS = 16,
    NH_AMS_MATERIAL_LENGTH = 20,
    NH_AMS_COLOR_LENGTH = 9,
    NH_AMS_PROFILE_LENGTH = 20,
    NH_AMS_RFID_LENGTH = 33,
};

typedef enum {
    NH_ALERT_SOURCE_HMS = 0,
    NH_ALERT_SOURCE_PRINT,
    NH_ALERT_SOURCE_CONTROLLER,
    NH_ALERT_SOURCE_MATERIAL,
    NH_ALERT_SOURCE_VISION,
} nh_alert_source_t;

typedef enum {
    NH_ALERT_INFO = 0,
    NH_ALERT_WARNING,
    NH_ALERT_ERROR,
    NH_ALERT_CRITICAL,
} nh_alert_severity_t;

typedef struct {
    char raw_code[NH_ALERT_CODE_LENGTH];
    char title[NH_ALERT_TITLE_LENGTH];
    char guidance[NH_ALERT_GUIDANCE_LENGTH];
    nh_alert_source_t source;
    nh_alert_severity_t severity;
    uint64_t first_seen_epoch;
    uint64_t last_seen_epoch;
    uint32_t occurrence_count;
    bool active;
    bool dismissed_locally;
    bool known_code;
} nh_alert_t;

typedef struct {
    uint8_t id;
    uint8_t humidity_index;
    float temperature_c;
    bool present;
    bool humidity_known;
    bool temperature_known;
    bool material_at_risk;
} nh_ams_unit_t;

typedef struct {
    uint8_t unit_id;
    uint8_t tray_id;
    uint8_t remaining_percent;
    int16_t nozzle_min_c;
    int16_t nozzle_max_c;
    char material[NH_AMS_MATERIAL_LENGTH];
    char color_rgba[NH_AMS_COLOR_LENGTH];
    char profile_id[NH_AMS_PROFILE_LENGTH];
    char rfid_uid[NH_AMS_RFID_LENGTH];
    bool present;
    bool external;
    bool remaining_known;
    bool rfid_present;
} nh_ams_tray_t;

typedef struct {
    nh_ams_unit_t units[NH_AMS_MAX_UNITS];
    nh_ams_tray_t trays[NH_AMS_MAX_TRAYS + 1];
    uint8_t unit_count;
    uint8_t tray_count;
    bool known;
    bool external_spool_present;
} nh_ams_snapshot_t;

typedef struct {
    nh_connection_state_t connection;
    nh_job_state_t job;
    bool telemetry_ready;
    const char *printer_name;
    const char *job_name;
    const char *job_layer;
    const char *remaining;
    uint8_t progress_percent;
    float nozzle_current_c;
    float nozzle_target_c;
    float bed_current_c;
    float bed_target_c;
    float chamber_current_c;
    uint8_t part_fan_percent;
    bool chamber_light_on;
    bool printer_sd_known;
    bool printer_sd_present;
    bool sd_mounted;
    esp_err_t sd_mount_error;
    uint64_t sd_capacity_bytes;
    uint64_t sd_free_bytes;
    nh_alert_t alerts[NH_ALERT_MAX];
    uint8_t alert_count;
    uint8_t active_alert_count;
    nh_ams_snapshot_t ams;
} nh_printer_snapshot_t;

typedef enum {
    NH_ACTION_NONE = 0,
    NH_ACTION_CONNECT,
    NH_ACTION_PAUSE,
    NH_ACTION_RESUME,
    NH_ACTION_CANCEL,
    NH_ACTION_HOME,
    NH_ACTION_JOG_X,
    NH_ACTION_JOG_Y,
    NH_ACTION_JOG_Z,
    NH_ACTION_LIGHT_TOGGLE,
    NH_ACTION_FAN_SET,
    NH_ACTION_PREHEAT_PLA,
    NH_ACTION_PREHEAT_PETG,
    NH_ACTION_COOLDOWN,
    NH_ACTION_OPEN_FILE,
    NH_ACTION_BRIGHTNESS_SET,
    NH_ACTION_SD_RESCAN,
    NH_ACTION_SPEED_PROFILE,
    NH_ACTION_CALIBRATE,
    NH_ACTION_SKIP_OBJECT,
} nh_action_t;

typedef esp_err_t (*nh_action_handler_t)(nh_action_t action, int32_t value, void *ctx);

const char *nh_connection_label(nh_connection_state_t state);
const char *nh_job_label(nh_job_state_t state);
const char *nh_action_label(nh_action_t action);
bool nh_action_requires_online(nh_action_t action);
bool nh_action_requires_confirmation(nh_action_t action);

/**
 * Clears sensitive memory through volatile writes so the compiler cannot
 * optimize the operation away.
 */
void nh_secure_zero(void *buffer, size_t length);

/**
 * Safe placeholder transport used until the P1S LAN credentials are provisioned.
 * It logs requested actions, rejects printer-dependent commands while offline, and
 * never sends network or motion commands.
 */
esp_err_t nh_demo_action_handler(nh_action_t action, int32_t value, void *ctx);

#ifdef __cplusplus
}
#endif
