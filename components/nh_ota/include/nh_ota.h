#pragma once

#include <stdint.h>

#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * Starts the local HTTP OTA service. Uploads remain rejected until a physical
 * user action opens a short authorization window.
 */
esp_err_t nh_ota_init(void);

/**
 * Allows one LAN firmware upload for the requested number of seconds.
 * The window closes as soon as an upload starts.
 */
esp_err_t nh_ota_enable_window(uint32_t duration_seconds);

#ifdef __cplusplus
}
#endif
