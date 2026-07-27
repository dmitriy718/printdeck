#pragma once

#include <stdbool.h>
#include <stdint.h>

#include "esp_err.h"
#include "lvgl.h"

#ifdef __cplusplus
extern "C" {
#endif

#define NH_BOARD_NATIVE_WIDTH  480
#define NH_BOARD_NATIVE_HEIGHT 800
#define NH_BOARD_UI_WIDTH      800
#define NH_BOARD_UI_HEIGHT     480

typedef struct {
    lv_display_t *display;
    lv_indev_t *touch;
    bool touch_ready;
} nh_board_handles_t;

typedef struct {
    bool mounted;
    uint64_t capacity_bytes;
    uint64_t free_bytes;
    char name[32];
} nh_sd_info_t;

/**
 * Initializes the JC4880P443 display as a native 480x800 ST7701S MIPI-DSI
 * panel, GT911 touch, LVGL 9 and PPA-assisted 90-degree UI rotation.
 * The backlight remains off until nh_board_backlight_set() is called.
 */
esp_err_t nh_board_display_init(nh_board_handles_t *out);

/**
 * Sets display brightness from 0 to 100 percent.
 */
esp_err_t nh_board_backlight_set(uint8_t percent);

/**
 * Mounts a FAT32 volume in the native four-bit SDMMC slot at /sdcard.
 * Mount failure is non-destructive: the card is never formatted automatically.
 */
esp_err_t nh_board_sd_mount(nh_sd_info_t *out);

#ifdef __cplusplus
}
#endif
