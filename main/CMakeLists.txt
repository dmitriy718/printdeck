idf_component_register(
    SRCS "app_main.c"
    INCLUDE_DIRS "."
    REQUIRES
        nh_ai
        nh_board
        nh_camera
        nh_core
        nh_files
        nh_fleet
        nh_ftps
        nh_history
        nh_material
        nh_network
        nh_ota
        nh_printer
        nh_settings
        nh_ui
        nvs_flash
)
