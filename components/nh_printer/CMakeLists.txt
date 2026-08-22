idf_component_register(
    SRCS
        "src/nh_printer.c"
        "src/nh_printer_policy.c"
        "src/nh_printer_protocol.c"
    INCLUDE_DIRS "include"
    PRIV_INCLUDE_DIRS "private"
    REQUIRES
        cjson
        esp_event
        esp_netif
        freertos
        heap
        mqtt
        nh_bambu
        nh_core
        nvs_flash
)
