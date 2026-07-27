#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

#define NH_NETWORK_MAX_ACCESS_POINTS 8
#define NH_NETWORK_SSID_MAX_LENGTH   32

typedef enum {
    NH_NETWORK_DISABLED = 0,
    NH_NETWORK_INITIALIZING,
    NH_NETWORK_SCANNING,
    NH_NETWORK_READY,
    NH_NETWORK_CONNECTING,
    NH_NETWORK_CONNECTED,
    NH_NETWORK_ERROR,
} nh_network_state_t;

typedef struct {
    char ssid[NH_NETWORK_SSID_MAX_LENGTH + 1];
    int8_t rssi;
    bool secured;
} nh_access_point_t;

typedef struct {
    nh_network_state_t state;
    char connected_ssid[NH_NETWORK_SSID_MAX_LENGTH + 1];
    char ip_address[16];
    int8_t rssi;
    uint8_t access_point_count;
    nh_access_point_t access_points[NH_NETWORK_MAX_ACCESS_POINTS];
    uint32_t reconnect_delay_ms;
    uint16_t last_disconnect_reason;
    esp_err_t last_error;
} nh_network_snapshot_t;

typedef void (*nh_network_update_cb_t)(const nh_network_snapshot_t *snapshot,
                                       void *ctx);

typedef struct {
    nh_network_update_cb_t update_cb;
    void *update_ctx;
} nh_network_config_t;

/**
 * Starts ESP32-C6 hosted Wi-Fi. Saved credentials are used when present;
 * otherwise an asynchronous access-point scan is started.
 */
esp_err_t nh_network_init(const nh_network_config_t *config);

/**
 * Queues an asynchronous Wi-Fi scan on the network worker. The call never
 * blocks the LVGL/touch task on an ESP-Hosted RPC.
 */
esp_err_t nh_network_scan(void);

/**
 * Queues a connection attempt and stores the credentials only after the
 * connection receives an IP address. The SSID and password are copied before
 * this function returns.
 */
esp_err_t nh_network_connect(const char *ssid, const char *password);

const char *nh_network_state_label(nh_network_state_t state);

#ifdef __cplusplus
}
#endif
