idf_component_register(
    SRCS "src/nh_camera.c"
    INCLUDE_DIRS "include"
    REQUIRES
        esp_driver_jpeg
        esp_driver_ppa
        esp-tls
        freertos
        heap
        nh_bambu
        nh_core
        nvs_flash
)
