idf_component_register(
    SRCS "src/nh_ui.c"
    INCLUDE_DIRS "include"
    REQUIRES
        esp_app_format
        heap
        nh_camera
        nh_core
        nh_diagnostics
        nh_network
        nh_printer
        esp_lvgl_port
        lvgl
)
