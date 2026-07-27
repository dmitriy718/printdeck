#include "nh_board.h"

#include <inttypes.h>
#include <string.h>
#include <sys/statvfs.h>

#include "driver/gpio.h"
#include "driver/i2c_master.h"
#include "driver/ledc.h"
#include "driver/sdmmc_host.h"
#include "esp_check.h"
#include "esp_lcd_mipi_dsi.h"
#include "esp_lcd_panel_io.h"
#include "esp_lcd_panel_ops.h"
#include "esp_lcd_st7701.h"
#include "esp_lcd_touch_gt911.h"
#include "esp_ldo_regulator.h"
#include "esp_log.h"
#include "esp_lvgl_port.h"
#include "esp_vfs_fat.h"
#include "sd_pwr_ctrl.h"
#include "sd_pwr_ctrl_by_on_chip_ldo.h"
#include "sdmmc_cmd.h"

static const char *TAG = "nh_board";

enum {
    NH_LCD_RESET_GPIO = GPIO_NUM_5,
    NH_LCD_BACKLIGHT_GPIO = GPIO_NUM_23,
    NH_TOUCH_SDA_GPIO = GPIO_NUM_7,
    NH_TOUCH_SCL_GPIO = GPIO_NUM_8,
    NH_MIPI_DSI_LANES = 2,
    NH_MIPI_DSI_LANE_RATE_MBPS = 500,
    NH_MIPI_DSI_LDO_CHANNEL = 3,
    NH_MIPI_DSI_LDO_MV = 2500,
    NH_SD_LDO_CHANNEL = 4,
    NH_BACKLIGHT_LEDC_TIMER = LEDC_TIMER_1,
    NH_BACKLIGHT_LEDC_CHANNEL = LEDC_CHANNEL_1,
};

static esp_ldo_channel_handle_t s_dsi_ldo;
static esp_lcd_dsi_bus_handle_t s_dsi_bus;
static esp_lcd_panel_io_handle_t s_lcd_io;
static esp_lcd_panel_handle_t s_lcd_panel;
static i2c_master_bus_handle_t s_i2c_bus;
static esp_lcd_panel_io_handle_t s_touch_io;
static esp_lcd_touch_handle_t s_touch;
static lv_display_t *s_display;
static lv_indev_t *s_touch_indev;
static sdmmc_card_t *s_sd_card;
static sd_pwr_ctrl_handle_t s_sd_power;
static bool s_backlight_initialized;

static void release_sd_mount(void)
{
    if (s_sd_card) {
        esp_err_t err = esp_vfs_fat_sdcard_unmount("/sdcard", s_sd_card);
        if (err != ESP_OK) {
            ESP_LOGW(TAG, "SD unmount cleanup failed: %s",
                     esp_err_to_name(err));
        }
        /*
         * esp_vfs_fat_sdcard_unmount() owns and frees the card descriptor even
         * when its final VFS unregister reports an error.
         */
        s_sd_card = NULL;
    }
    if (s_sd_power) {
        esp_err_t err = sd_pwr_ctrl_del_on_chip_ldo(s_sd_power);
        if (err != ESP_OK) {
            ESP_LOGW(TAG, "SD power cleanup failed: %s",
                     esp_err_to_name(err));
        }
        s_sd_power = NULL;
    }
}

/*
 * JC4880P443C ST7701S panel initialization sequence. Register values and
 * timing are hardware facts corroborated by the Guition package, ESPHome's
 * JC4880P443 profile and multiple working ESP-IDF implementations.
 */
static const st7701_lcd_init_cmd_t s_st7701_init[] = {
    {0xFF, (uint8_t[]){0x77, 0x01, 0x00, 0x00, 0x13}, 5, 0},
    {0xEF, (uint8_t[]){0x08}, 1, 0},
    {0xFF, (uint8_t[]){0x77, 0x01, 0x00, 0x00, 0x10}, 5, 0},
    {0xC0, (uint8_t[]){0x63, 0x00}, 2, 0},
    {0xC1, (uint8_t[]){0x0D, 0x02}, 2, 0},
    {0xC2, (uint8_t[]){0x10, 0x08}, 2, 0},
    {0xCC, (uint8_t[]){0x10}, 1, 0},
    {0xB0, (uint8_t[]){0x80, 0x09, 0x53, 0x0C, 0xD0, 0x07, 0x0C, 0x09,
                       0x09, 0x28, 0x06, 0xD4, 0x13, 0x69, 0x2B, 0x71}, 16, 0},
    {0xB1, (uint8_t[]){0x80, 0x94, 0x5A, 0x10, 0xD3, 0x06, 0x0A, 0x08,
                       0x08, 0x25, 0x03, 0xD3, 0x12, 0x66, 0x6A, 0x0D}, 16, 0},
    {0xFF, (uint8_t[]){0x77, 0x01, 0x00, 0x00, 0x11}, 5, 0},
    {0xB0, (uint8_t[]){0x5D}, 1, 0},
    {0xB1, (uint8_t[]){0x58}, 1, 0},
    {0xB2, (uint8_t[]){0x87}, 1, 0},
    {0xB3, (uint8_t[]){0x80}, 1, 0},
    {0xB5, (uint8_t[]){0x4E}, 1, 0},
    {0xB7, (uint8_t[]){0x85}, 1, 0},
    {0xB8, (uint8_t[]){0x21}, 1, 0},
    {0xB9, (uint8_t[]){0x10, 0x1F}, 2, 0},
    {0xBB, (uint8_t[]){0x03}, 1, 0},
    {0xBC, (uint8_t[]){0x00}, 1, 0},
    {0xC1, (uint8_t[]){0x78}, 1, 0},
    {0xC2, (uint8_t[]){0x78}, 1, 0},
    {0xD0, (uint8_t[]){0x88}, 1, 0},
    {0xE0, (uint8_t[]){0x00, 0x3A, 0x02}, 3, 0},
    {0xE1, (uint8_t[]){0x04, 0xA0, 0x00, 0xA0, 0x05, 0xA0, 0x00, 0xA0,
                       0x00, 0x40, 0x40}, 11, 0},
    {0xE2, (uint8_t[]){0x30, 0x00, 0x40, 0x40, 0x32, 0xA0, 0x00, 0xA0,
                       0x00, 0xA0, 0x00, 0xA0, 0x00}, 13, 0},
    {0xE3, (uint8_t[]){0x00, 0x00, 0x33, 0x33}, 4, 0},
    {0xE4, (uint8_t[]){0x44, 0x44}, 2, 0},
    {0xE5, (uint8_t[]){0x09, 0x2E, 0xA0, 0xA0, 0x0B, 0x30, 0xA0, 0xA0,
                       0x05, 0x2A, 0xA0, 0xA0, 0x07, 0x2C, 0xA0, 0xA0}, 16, 0},
    {0xE6, (uint8_t[]){0x00, 0x00, 0x33, 0x33}, 4, 0},
    {0xE7, (uint8_t[]){0x44, 0x44}, 2, 0},
    {0xE8, (uint8_t[]){0x08, 0x2D, 0xA0, 0xA0, 0x0A, 0x2F, 0xA0, 0xA0,
                       0x04, 0x29, 0xA0, 0xA0, 0x06, 0x2B, 0xA0, 0xA0}, 16, 0},
    {0xEB, (uint8_t[]){0x00, 0x00, 0x4E, 0x4E, 0x00, 0x00, 0x00}, 7, 0},
    {0xEC, (uint8_t[]){0x08, 0x01}, 2, 0},
    {0xED, (uint8_t[]){0xB0, 0x2B, 0x98, 0xA4, 0x56, 0x7F, 0xFF, 0xFF,
                       0xFF, 0xFF, 0xF7, 0x65, 0x4A, 0x89, 0xB2, 0x0B}, 16, 0},
    {0xEF, (uint8_t[]){0x08, 0x08, 0x08, 0x45, 0x3F, 0x54}, 6, 0},
    {0xFF, (uint8_t[]){0x77, 0x01, 0x00, 0x00, 0x00}, 5, 0},
    {0x11, NULL, 0, 120},
    {0x29, NULL, 0, 20},
};

static esp_err_t init_backlight(void)
{
    if (s_backlight_initialized) {
        return ESP_OK;
    }

    const ledc_timer_config_t timer_cfg = {
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .duty_resolution = LEDC_TIMER_10_BIT,
        .timer_num = NH_BACKLIGHT_LEDC_TIMER,
        .freq_hz = 20000,
        .clk_cfg = LEDC_AUTO_CLK,
    };
    ESP_RETURN_ON_ERROR(ledc_timer_config(&timer_cfg), TAG, "backlight timer");

    const ledc_channel_config_t channel_cfg = {
        .gpio_num = NH_LCD_BACKLIGHT_GPIO,
        .speed_mode = LEDC_LOW_SPEED_MODE,
        .channel = NH_BACKLIGHT_LEDC_CHANNEL,
        .intr_type = LEDC_INTR_DISABLE,
        .timer_sel = NH_BACKLIGHT_LEDC_TIMER,
        .duty = 0,
        .hpoint = 0,
    };
    ESP_RETURN_ON_ERROR(ledc_channel_config(&channel_cfg), TAG, "backlight channel");
    s_backlight_initialized = true;
    return ESP_OK;
}

esp_err_t nh_board_backlight_set(uint8_t percent)
{
    ESP_RETURN_ON_ERROR(init_backlight(), TAG, "backlight init");
    if (percent > 100) {
        percent = 100;
    }

    const uint32_t duty = (1023U * percent) / 100U;
    ESP_RETURN_ON_ERROR(
        ledc_set_duty(LEDC_LOW_SPEED_MODE, NH_BACKLIGHT_LEDC_CHANNEL, duty),
        TAG, "backlight duty");
    ESP_RETURN_ON_ERROR(
        ledc_update_duty(LEDC_LOW_SPEED_MODE, NH_BACKLIGHT_LEDC_CHANNEL),
        TAG, "backlight update");
    ESP_LOGI(TAG, "Backlight %u%%", percent);
    return ESP_OK;
}

static esp_err_t init_panel(void)
{
    ESP_RETURN_ON_ERROR(init_backlight(), TAG, "backlight init");
    ESP_RETURN_ON_ERROR(nh_board_backlight_set(0), TAG, "backlight off");

    const esp_ldo_channel_config_t ldo_cfg = {
        .chan_id = NH_MIPI_DSI_LDO_CHANNEL,
        .voltage_mv = NH_MIPI_DSI_LDO_MV,
    };
    ESP_RETURN_ON_ERROR(
        esp_ldo_acquire_channel(&ldo_cfg, &s_dsi_ldo),
        TAG, "MIPI D-PHY LDO");

    const esp_lcd_dsi_bus_config_t dsi_cfg = {
        .bus_id = 0,
        .num_data_lanes = NH_MIPI_DSI_LANES,
        .phy_clk_src = MIPI_DSI_PHY_CLK_SRC_DEFAULT,
        .lane_bit_rate_mbps = NH_MIPI_DSI_LANE_RATE_MBPS,
    };
    ESP_RETURN_ON_ERROR(
        esp_lcd_new_dsi_bus(&dsi_cfg, &s_dsi_bus),
        TAG, "MIPI-DSI bus");

    const esp_lcd_dbi_io_config_t dbi_cfg = {
        .virtual_channel = 0,
        .lcd_cmd_bits = 8,
        .lcd_param_bits = 8,
    };
    ESP_RETURN_ON_ERROR(
        esp_lcd_new_panel_io_dbi(s_dsi_bus, &dbi_cfg, &s_lcd_io),
        TAG, "MIPI-DBI command IO");

    const esp_lcd_dpi_panel_config_t dpi_cfg = {
        .virtual_channel = 0,
        .dpi_clk_src = MIPI_DSI_DPI_CLK_SRC_DEFAULT,
        .dpi_clock_freq_mhz = 34,
        .in_color_format = LCD_COLOR_FMT_RGB565,
        .out_color_format = LCD_COLOR_FMT_RGB565,
        .num_fbs = 2,
        .video_timing = {
            .h_size = NH_BOARD_NATIVE_WIDTH,
            .v_size = NH_BOARD_NATIVE_HEIGHT,
            .hsync_pulse_width = 12,
            .hsync_back_porch = 42,
            .hsync_front_porch = 42,
            .vsync_pulse_width = 2,
            .vsync_back_porch = 8,
            .vsync_front_porch = 166,
        },
    };

    const st7701_vendor_config_t vendor_cfg = {
        .init_cmds = s_st7701_init,
        .init_cmds_size = sizeof(s_st7701_init) / sizeof(s_st7701_init[0]),
        .mipi_config = {
            .dsi_bus = s_dsi_bus,
            .dpi_config = &dpi_cfg,
        },
        .flags = {
            .use_mipi_interface = 1,
        },
    };

    const esp_lcd_panel_dev_config_t panel_cfg = {
        .rgb_ele_order = LCD_RGB_ELEMENT_ORDER_RGB,
        .data_endian = LCD_RGB_DATA_ENDIAN_LITTLE,
        .bits_per_pixel = 16,
        .reset_gpio_num = NH_LCD_RESET_GPIO,
        .vendor_config = (void *)&vendor_cfg,
    };

    ESP_RETURN_ON_ERROR(
        esp_lcd_new_panel_st7701(s_lcd_io, &panel_cfg, &s_lcd_panel),
        TAG, "ST7701S panel");
    ESP_RETURN_ON_ERROR(esp_lcd_panel_reset(s_lcd_panel), TAG, "panel reset");
    ESP_RETURN_ON_ERROR(esp_lcd_panel_init(s_lcd_panel), TAG, "panel init");
    ESP_RETURN_ON_ERROR(esp_lcd_panel_disp_on_off(s_lcd_panel, true), TAG, "panel on");

    ESP_LOGI(TAG, "ST7701S ready: 480x800, 2-lane DSI at 500 Mbps");
    return ESP_OK;
}

static esp_err_t init_touch(void)
{
    const i2c_master_bus_config_t bus_cfg = {
        .i2c_port = I2C_NUM_0,
        .sda_io_num = NH_TOUCH_SDA_GPIO,
        .scl_io_num = NH_TOUCH_SCL_GPIO,
        .clk_source = I2C_CLK_SRC_DEFAULT,
        .glitch_ignore_cnt = 7,
        .flags.enable_internal_pullup = true,
    };
    ESP_RETURN_ON_ERROR(i2c_new_master_bus(&bus_cfg, &s_i2c_bus), TAG, "touch I2C");

    esp_lcd_panel_io_i2c_config_t io_cfg = ESP_LCD_TOUCH_IO_I2C_GT911_CONFIG();
    io_cfg.scl_speed_hz = 400000;
    ESP_RETURN_ON_ERROR(
        esp_lcd_new_panel_io_i2c(s_i2c_bus, &io_cfg, &s_touch_io),
        TAG, "GT911 I2C IO");

    const esp_lcd_touch_config_t touch_cfg = {
        .x_max = NH_BOARD_NATIVE_WIDTH,
        .y_max = NH_BOARD_NATIVE_HEIGHT,
        .rst_gpio_num = GPIO_NUM_NC,
        .int_gpio_num = GPIO_NUM_NC,
        .levels = {
            .reset = 0,
            .interrupt = 0,
        },
        .flags = {
            .swap_xy = false,
            .mirror_x = false,
            .mirror_y = false,
        },
    };

    ESP_RETURN_ON_ERROR(
        esp_lcd_touch_new_i2c_gt911(s_touch_io, &touch_cfg, &s_touch),
        TAG, "GT911 touch");
    ESP_LOGI(TAG, "GT911 touch ready on I2C GPIO7/8");
    return ESP_OK;
}

static esp_err_t init_lvgl(void)
{
    const lvgl_port_cfg_t port_cfg = {
        .task_priority = 5,
        .task_stack = 24 * 1024,
        .task_affinity = -1,
        .task_max_sleep_ms = 250,
        .task_stack_caps = MALLOC_CAP_INTERNAL | MALLOC_CAP_DEFAULT,
        .timer_period_ms = 5,
    };
    ESP_RETURN_ON_ERROR(lvgl_port_init(&port_cfg), TAG, "LVGL port");

    const lvgl_port_display_cfg_t display_cfg = {
        .io_handle = s_lcd_io,
        .panel_handle = s_lcd_panel,
        .control_handle = s_lcd_panel,
        .buffer_size = NH_BOARD_NATIVE_WIDTH * NH_BOARD_NATIVE_HEIGHT,
        .double_buffer = true,
        .hres = NH_BOARD_NATIVE_WIDTH,
        .vres = NH_BOARD_NATIVE_HEIGHT,
        .monochrome = false,
        .rotation = {
            .swap_xy = false,
            .mirror_x = false,
            .mirror_y = false,
        },
        .color_format = LV_COLOR_FORMAT_RGB565,
        .flags = {
            .buff_dma = false,
            .buff_spiram = true,
            .sw_rotate = true,
            .swap_bytes = false,
            .full_refresh = false,
            .direct_mode = false,
        },
    };

    const lvgl_port_display_dsi_cfg_t dsi_port_cfg = {
        .flags.avoid_tearing = false,
    };
    s_display = lvgl_port_add_disp_dsi(&display_cfg, &dsi_port_cfg);
    ESP_RETURN_ON_FALSE(s_display, ESP_ERR_NO_MEM, TAG, "LVGL display registration");

    const lvgl_port_touch_cfg_t touch_port_cfg = {
        .disp = s_display,
        .handle = s_touch,
    };
    s_touch_indev = lvgl_port_add_touch(&touch_port_cfg);
    ESP_RETURN_ON_FALSE(s_touch_indev, ESP_ERR_NO_MEM, TAG, "LVGL touch registration");

    lvgl_port_lock(0);
    lv_display_set_rotation(s_display, LV_DISPLAY_ROTATION_90);
    lvgl_port_unlock();
    ESP_LOGI(TAG, "LVGL ready at logical 800x480 with PPA rotation");
    return ESP_OK;
}

esp_err_t nh_board_display_init(nh_board_handles_t *out)
{
    ESP_RETURN_ON_FALSE(out, ESP_ERR_INVALID_ARG, TAG, "output handles required");
    memset(out, 0, sizeof(*out));

    ESP_RETURN_ON_ERROR(init_panel(), TAG, "display panel");
    ESP_RETURN_ON_ERROR(init_touch(), TAG, "touch controller");
    ESP_RETURN_ON_ERROR(init_lvgl(), TAG, "LVGL");

    out->display = s_display;
    out->touch = s_touch_indev;
    out->touch_ready = true;
    return ESP_OK;
}

esp_err_t nh_board_sd_mount(nh_sd_info_t *out)
{
    ESP_RETURN_ON_FALSE(out, ESP_ERR_INVALID_ARG, TAG, "SD info required");
    memset(out, 0, sizeof(*out));
    if (s_sd_card) {
        /*
         * With no card-detect GPIO, a non-NULL descriptor only proves that a
         * card mounted earlier. Probe it on every explicit refresh so removal
         * or media failure cannot continue to be displayed as "mounted".
         */
        esp_err_t status = sdmmc_get_status(s_sd_card);
        if (status != ESP_OK) {
            ESP_LOGW(TAG, "Previously mounted SD is no longer responding: %s",
                     esp_err_to_name(status));
            release_sd_mount();
            return status;
        }
        out->mounted = true;
        out->capacity_bytes =
            (uint64_t)s_sd_card->csd.capacity * s_sd_card->csd.sector_size;
        strlcpy(out->name, s_sd_card->cid.name, sizeof(out->name));
        struct statvfs fs = {0};
        if (statvfs("/sdcard", &fs) == 0) {
            out->free_bytes = (uint64_t)fs.f_bavail * fs.f_frsize;
        }
        return ESP_OK;
    }

    const sd_pwr_ctrl_ldo_config_t ldo_cfg = {
        .ldo_chan_id = NH_SD_LDO_CHANNEL,
    };
    ESP_RETURN_ON_ERROR(
        sd_pwr_ctrl_new_on_chip_ldo(&ldo_cfg, &s_sd_power),
        TAG, "SD LDO4 power");

    sdmmc_host_t host = SDMMC_HOST_DEFAULT();
    host.slot = SDMMC_HOST_SLOT_0;
    host.max_freq_khz = SDMMC_FREQ_HIGHSPEED;
    host.pwr_ctrl_handle = s_sd_power;

    const sdmmc_slot_config_t slot_cfg = {
        .cd = SDMMC_SLOT_NO_CD,
        .wp = SDMMC_SLOT_NO_WP,
        .width = 4,
        .flags = 0,
    };

    const esp_vfs_fat_mount_config_t mount_cfg = {
        .format_if_mount_failed = false,
        .max_files = 8,
        .allocation_unit_size = 32 * 1024,
    };

    esp_err_t err = esp_vfs_fat_sdmmc_mount(
        "/sdcard", &host, &slot_cfg, &mount_cfg, &s_sd_card);
    if (err != ESP_OK) {
        (void)sd_pwr_ctrl_del_on_chip_ldo(s_sd_power);
        s_sd_power = NULL;
        return err;
    }

    out->mounted = true;
    out->capacity_bytes =
        (uint64_t)s_sd_card->csd.capacity * s_sd_card->csd.sector_size;
    strlcpy(out->name, s_sd_card->cid.name, sizeof(out->name));

    struct statvfs fs = {0};
    if (statvfs("/sdcard", &fs) == 0) {
        out->free_bytes = (uint64_t)fs.f_bavail * fs.f_frsize;
    }

    ESP_LOGI(TAG, "SD mounted: %s, capacity=%" PRIu64 " bytes, free=%" PRIu64,
             out->name, out->capacity_bytes, out->free_bytes);
    return ESP_OK;
}
