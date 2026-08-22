idf_component_register(
    SRCS
        "src/nh_fleet.c"
        "src/nh_fleet_policy.c"
    INCLUDE_DIRS "include"
    REQUIRES
        freertos
        lwip
        nh_core
        nh_printer
        nvs_flash
)
