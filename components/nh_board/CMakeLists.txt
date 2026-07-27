idf_component_register(
    SRCS "src/nh_board.c"
    INCLUDE_DIRS "include"
    REQUIRES
        esp_hw_support
        esp_lcd
        esp_driver_gpio
        esp_driver_i2c
        esp_driver_ledc
        esp_driver_sdmmc
        fatfs
        sdmmc
        esp_lvgl_port
        esp_lcd_st7701
        esp_lcd_touch
        esp_lcd_touch_gt911
)
