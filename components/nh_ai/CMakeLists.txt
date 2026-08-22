idf_component_register(
    SRCS
        "src/nh_ai.c"
        "src/nh_ai_policy.c"
    INCLUDE_DIRS "include"
    REQUIRES
        freertos
        mbedtls
        nh_core
)
