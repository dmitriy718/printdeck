idf_component_register(
    SRCS "src/nh_ota.c"
    INCLUDE_DIRS "include"
    REQUIRES
        app_update
        esp_app_format
        esp_http_server
        esp_system
        esp_timer
        freertos
        nh_diagnostics
)
