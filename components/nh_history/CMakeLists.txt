idf_component_register(
    SRCS
        "src/nh_history.c"
        "src/nh_history_codec.c"
    INCLUDE_DIRS "include"
    PRIV_INCLUDE_DIRS "private"
    REQUIRES
        esp_timer
        freertos
        nh_core
)
