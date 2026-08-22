#pragma once

#include <stdbool.h>
#include <stdint.h>

#include "esp_err.h"
#include "nh_core.h"

#ifdef __cplusplus
extern "C" {
#endif

enum {
    NH_PRINTER_IP_MAX_LENGTH = 15,
    NH_PRINTER_SERIAL_MAX_LENGTH = 31,
    NH_PRINTER_ACCESS_CODE_MAX_LENGTH = 16,
};

typedef enum {
    NH_PRINTER_UNCONFIGURED = 0,
    NH_PRINTER_CONNECTING,
    NH_PRINTER_ONLINE,
    NH_PRINTER_OFFLINE,
    NH_PRINTER_AUTH_ERROR,
    NH_PRINTER_TLS_ERROR,
    NH_PRINTER_ERROR,
} nh_printer_state_t;

typedef struct {
    nh_printer_state_t state;
    bool configured;
    bool profile_ready;
    char ip_address[NH_PRINTER_IP_MAX_LENGTH + 1];
    char serial[NH_PRINTER_SERIAL_MAX_LENGTH + 1];
    esp_err_t last_error;
} nh_printer_status_t;

typedef void (*nh_printer_update_cb_t)(
    const nh_printer_snapshot_t *snapshot,
    const nh_printer_status_t *status,
    void *ctx);

typedef enum {
    NH_COMMAND_RESULT_QUEUED = 0,
    NH_COMMAND_RESULT_SENT,
    NH_COMMAND_RESULT_ACKNOWLEDGED,
    NH_COMMAND_RESULT_OBSERVED,
    NH_COMMAND_RESULT_REJECTED,
    NH_COMMAND_RESULT_TIMED_OUT,
} nh_command_result_state_t;

typedef struct {
    uint32_t sequence_id;
    nh_action_t action;
    nh_command_result_state_t state;
    esp_err_t error;
} nh_command_result_t;

typedef void (*nh_printer_command_result_cb_t)(
    const nh_command_result_t *result, void *ctx);

typedef struct {
    nh_printer_snapshot_t *snapshot;
    const char *default_ip;
    const char *default_serial;
    nh_printer_update_cb_t update_cb;
    void *update_ctx;
    nh_printer_command_result_cb_t command_result_cb;
    void *command_result_ctx;
} nh_printer_config_t;

/**
 * Initializes the P1S LAN transport. Saved credentials are loaded from NVS.
 * If no profile exists, default_ip and default_serial are exposed to the
 * on-device pairing screen but no network authentication is attempted.
 */
esp_err_t nh_printer_init(const nh_printer_config_t *config);

/**
 * Queues a P1S profile for validation and connection. The access code is never
 * logged or returned through status callbacks.
 */
esp_err_t nh_printer_pair(const char *ip_address, const char *serial,
                          const char *access_code);

/**
 * Queues a guarded printer command. Unsupported motion/thermal commands remain
 * rejected until their behavior is validated on this exact printer.
 */
esp_err_t nh_printer_action(nh_action_t action, int32_t value);
esp_err_t nh_printer_action_with_sequence(nh_action_t action,
                                          int32_t value,
                                          uint32_t *sequence_id);
const char *nh_command_result_label(nh_command_result_state_t state);

/**
 * Hides an alert locally. This does not send a printer command and does not
 * mark the underlying condition resolved.
 */
esp_err_t nh_printer_alert_dismiss(const char *raw_code);

bool nh_printer_action_supported(nh_action_t action);
bool nh_printer_typed_action_valid(nh_action_t action, int32_t value);
bool nh_printer_action_available(
    nh_action_t action, const nh_printer_snapshot_t *snapshot);
const char *nh_printer_state_label(nh_printer_state_t state);

#ifdef __cplusplus
}
#endif
