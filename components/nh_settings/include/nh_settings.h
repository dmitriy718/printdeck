#pragma once

#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * Load and apply persistent, non-secret controller settings.
 */
esp_err_t nh_settings_init(void);

/**
 * Return the short display name of the active timezone preset.
 */
const char *nh_settings_timezone_name(void);

/**
 * Select, persist, and apply the next timezone preset.
 */
esp_err_t nh_settings_timezone_next(void);

#ifdef __cplusplus
}
#endif
