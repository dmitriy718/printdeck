idf_component_register(
    SRCS "src/nh_material.c"
    INCLUDE_DIRS "include"
    REQUIRES
        esp_common
        esp_rom
        freertos
        nh_core
        nvs_flash
)

