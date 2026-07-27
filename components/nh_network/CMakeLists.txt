idf_component_register(
    SRCS "src/nh_network.c"
    INCLUDE_DIRS "include"
    REQUIRES
        esp_event
        esp_netif
        esp_timer
        esp_wifi
        freertos
        nh_core
        nvs_flash
)
