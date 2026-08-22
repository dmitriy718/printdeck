idf_component_register(
    SRCS "src/nh_ftps.c"
    INCLUDE_DIRS "include"
    REQUIRES
        esp-tls
        esp_netif
        freertos
        mbedtls
        nh_bambu
        nh_core
)
