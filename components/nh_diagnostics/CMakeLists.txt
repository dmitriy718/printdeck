idf_component_register(
    SRCS "src/nh_diagnostics.c"
    INCLUDE_DIRS "include"
    REQUIRES
        app_update
        esp_system
        esp_timer
        freertos
        heap
)
