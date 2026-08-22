idf_component_register(
    SRCS
        "src/nh_files.c"
        "src/nh_3mf.c"
    INCLUDE_DIRS "include"
    PRIV_INCLUDE_DIRS "private"
    REQUIRES
        esp_rom
        freertos
        mbedtls
        nh_core
)
