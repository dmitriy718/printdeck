#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    NH_CAMERA_STOPPED = 0,
    NH_CAMERA_NO_PROFILE,
    NH_CAMERA_CONNECTING,
    NH_CAMERA_LIVE,
    NH_CAMERA_RECONNECTING,
    NH_CAMERA_ERROR,
} nh_camera_state_t;

typedef struct {
    nh_camera_state_t state;
    esp_err_t last_error;
    uint32_t frame_count;
    uint16_t source_width;
    uint16_t source_height;
} nh_camera_status_t;

typedef void (*nh_camera_status_cb_t)(const nh_camera_status_t *status,
                                      void *ctx);
typedef void (*nh_camera_frame_cb_t)(const uint8_t *rgb565,
                                     uint16_t width,
                                     uint16_t height,
                                     uint16_t source_width,
                                     uint16_t source_height,
                                     void *ctx);

typedef struct {
    nh_camera_status_cb_t status_cb;
    nh_camera_frame_cb_t frame_cb;
    void *callback_ctx;
} nh_camera_config_t;

/**
 * Starts the local P1-family camera service. The stream remains stopped until
 * nh_camera_set_active(true) is called. Printer credentials are read directly
 * from the existing local-LAN profile in NVS and are never returned.
 */
esp_err_t nh_camera_init(const nh_camera_config_t *config);

/**
 * Starts or stops the camera stream. The UI calls this when the Camera page is
 * entered or left so the printer and controller do not carry unused traffic.
 */
esp_err_t nh_camera_set_active(bool active);

const char *nh_camera_state_label(nh_camera_state_t state);

#ifdef __cplusplus
}
#endif
