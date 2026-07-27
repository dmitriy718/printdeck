#include "nh_camera.h"

#include <ctype.h>
#include <stdatomic.h>
#include <stdlib.h>
#include <string.h>

#include "driver/jpeg_decode.h"
#include "driver/ppa.h"
#include "esp_check.h"
#include "esp_heap_caps.h"
#include "esp_log.h"
#include "esp_tls.h"
#include "esp_tls_errors.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "lwip/ip4_addr.h"
#include "nh_bambu.h"
#include "nh_core.h"
#include "nvs.h"

static const char *TAG = "nh_camera";

enum {
    NH_CAMERA_TLS_PORT = 6000,
    NH_CAMERA_TASK_STACK = 12288,
    NH_CAMERA_MAX_JPEG_SIZE = 1024 * 1024,
    NH_CAMERA_OUTPUT_WIDTH = 592,
    NH_CAMERA_OUTPUT_HEIGHT = 333,
    NH_CAMERA_OUTPUT_BUFFER_SIZE =
        NH_CAMERA_OUTPUT_WIDTH * NH_CAMERA_OUTPUT_HEIGHT * 2,
    NH_CAMERA_MAX_SOURCE_DIMENSION = 4096,
    NH_CAMERA_RETRY_MS = 3000,
};

typedef struct {
    char ip_address[16];
    char serial[32];
    char access_code[17];
} camera_profile_t;

static nh_camera_config_t s_config;
static nh_camera_status_t s_status;
static TaskHandle_t s_camera_task;
static atomic_bool s_active;
static bool s_initialized;

static jpeg_decoder_handle_t s_decoder;
static ppa_client_handle_t s_ppa;
static uint8_t *s_jpeg_buffer;
static size_t s_jpeg_buffer_size;
static uint8_t *s_decode_buffer;
static size_t s_decode_buffer_size;
static uint8_t *s_output_buffers[2];
static size_t s_output_buffer_sizes[2];
static uint8_t s_output_index;

static uint32_t read_le32(const uint8_t *value)
{
    return (uint32_t)value[0] |
           ((uint32_t)value[1] << 8) |
           ((uint32_t)value[2] << 16) |
           ((uint32_t)value[3] << 24);
}

static void write_le32(uint8_t *target, uint32_t value)
{
    target[0] = (uint8_t)value;
    target[1] = (uint8_t)(value >> 8);
    target[2] = (uint8_t)(value >> 16);
    target[3] = (uint8_t)(value >> 24);
}

static void notify_status(void)
{
    if (s_config.status_cb) {
        s_config.status_cb(&s_status, s_config.callback_ctx);
    }
}

static void update_status(nh_camera_state_t state, esp_err_t error)
{
    bool changed = s_status.state != state || s_status.last_error != error;
    s_status.state = state;
    s_status.last_error = error;
    if (changed) {
        notify_status();
    }
}

const char *nh_camera_state_label(nh_camera_state_t state)
{
    switch (state) {
    case NH_CAMERA_STOPPED:
        return "CAMERA READY";
    case NH_CAMERA_NO_PROFILE:
        return "PAIR P1S";
    case NH_CAMERA_CONNECTING:
        return "CONNECTING";
    case NH_CAMERA_LIVE:
        return "LIVE";
    case NH_CAMERA_RECONNECTING:
        return "RECONNECTING";
    case NH_CAMERA_ERROR:
    default:
        return "CAMERA ERROR";
    }
}

static esp_err_t load_profile(camera_profile_t *profile)
{
    memset(profile, 0, sizeof(*profile));
    nvs_handle_t nvs;
    esp_err_t err = nvs_open("nh_p1s", NVS_READONLY, &nvs);
    if (err != ESP_OK) {
        return err;
    }

    size_t ip_length = sizeof(profile->ip_address);
    size_t serial_length = sizeof(profile->serial);
    size_t code_length = sizeof(profile->access_code);
    err = nvs_get_str(nvs, "ip", profile->ip_address, &ip_length);
    if (err == ESP_OK) {
        err = nvs_get_str(nvs, "serial", profile->serial, &serial_length);
    }
    if (err == ESP_OK) {
        err = nvs_get_str(nvs, "code", profile->access_code, &code_length);
    }
    nvs_close(nvs);
    if (err == ESP_OK) {
        ip4_addr_t address;
        size_t serial_length =
            strnlen(profile->serial, sizeof(profile->serial));
        size_t code_length =
            strnlen(profile->access_code, sizeof(profile->access_code));
        bool serial_valid = serial_length >= 10 &&
                            serial_length < sizeof(profile->serial);
        for (size_t i = 0; serial_valid && i < serial_length; ++i) {
            serial_valid = isalnum((unsigned char)profile->serial[i]) != 0;
        }
        if (!ip4addr_aton(profile->ip_address, &address) ||
            !serial_valid || code_length < 8 ||
            code_length >= sizeof(profile->access_code)) {
            err = ESP_ERR_INVALID_STATE;
        }
    }
    return err;
}

static esp_err_t initialize_pipeline(void)
{
    if (!s_decoder) {
        const jpeg_decode_engine_cfg_t decoder_config = {
            .timeout_ms = 100,
        };
        ESP_RETURN_ON_ERROR(
            jpeg_new_decoder_engine(&decoder_config, &s_decoder),
            TAG, "JPEG decoder");
    }

    if (!s_ppa) {
        const ppa_client_config_t ppa_config = {
            .oper_type = PPA_OPERATION_SRM,
            .data_burst_length = PPA_DATA_BURST_LENGTH_128,
        };
        ESP_RETURN_ON_ERROR(
            ppa_register_client(&ppa_config, &s_ppa),
            TAG, "PPA scaler");
    }

    if (!s_jpeg_buffer) {
        const jpeg_decode_memory_alloc_cfg_t input_config = {
            .buffer_direction = JPEG_DEC_ALLOC_INPUT_BUFFER,
        };
        s_jpeg_buffer = jpeg_alloc_decoder_mem(
            NH_CAMERA_MAX_JPEG_SIZE, &input_config, &s_jpeg_buffer_size);
        ESP_RETURN_ON_FALSE(
            s_jpeg_buffer, ESP_ERR_NO_MEM, TAG, "camera JPEG buffer");
    }

    const jpeg_decode_memory_alloc_cfg_t output_config = {
        .buffer_direction = JPEG_DEC_ALLOC_OUTPUT_BUFFER,
    };
    for (size_t i = 0; i < 2; ++i) {
        if (!s_output_buffers[i]) {
            s_output_buffers[i] = jpeg_alloc_decoder_mem(
                NH_CAMERA_OUTPUT_BUFFER_SIZE, &output_config,
                &s_output_buffer_sizes[i]);
            ESP_RETURN_ON_FALSE(
                s_output_buffers[i], ESP_ERR_NO_MEM, TAG,
                "camera display buffer");
        }
    }
    return ESP_OK;
}

static void release_pipeline(void)
{
    free(s_decode_buffer);
    s_decode_buffer = NULL;
    s_decode_buffer_size = 0;

    free(s_jpeg_buffer);
    s_jpeg_buffer = NULL;
    s_jpeg_buffer_size = 0;

    for (size_t i = 0; i < 2; ++i) {
        free(s_output_buffers[i]);
        s_output_buffers[i] = NULL;
        s_output_buffer_sizes[i] = 0;
    }
    s_output_index = 0;

    if (s_decoder) {
        esp_err_t err = jpeg_del_decoder_engine(s_decoder);
        if (err != ESP_OK) {
            ESP_LOGW(TAG, "Could not release JPEG engine: %s",
                     esp_err_to_name(err));
        } else {
            s_decoder = NULL;
        }
    }
    if (s_ppa) {
        esp_err_t err = ppa_unregister_client(s_ppa);
        if (err != ESP_OK) {
            ESP_LOGW(TAG, "Could not release camera PPA client: %s",
                     esp_err_to_name(err));
        } else {
            s_ppa = NULL;
        }
    }
    ESP_LOGI(TAG, "Camera pipeline memory released");
}

static esp_err_t ensure_decode_buffer(uint32_t width, uint32_t height)
{
    ESP_RETURN_ON_FALSE(
        width > 0 && height > 0 &&
            width <= NH_CAMERA_MAX_SOURCE_DIMENSION &&
            height <= NH_CAMERA_MAX_SOURCE_DIMENSION,
        ESP_ERR_INVALID_SIZE, TAG, "camera dimensions out of range");
    uint32_t aligned_width = (width + 15U) & ~15U;
    uint32_t aligned_height = (height + 15U) & ~15U;
    size_t required = (size_t)aligned_width * aligned_height * 2U;
    if (s_decode_buffer && s_decode_buffer_size >= required) {
        return ESP_OK;
    }

    if (s_decode_buffer) {
        free(s_decode_buffer);
        s_decode_buffer = NULL;
        s_decode_buffer_size = 0;
    }

    const jpeg_decode_memory_alloc_cfg_t output_config = {
        .buffer_direction = JPEG_DEC_ALLOC_OUTPUT_BUFFER,
    };
    s_decode_buffer =
        jpeg_alloc_decoder_mem(required, &output_config, &s_decode_buffer_size);
    ESP_RETURN_ON_FALSE(
        s_decode_buffer, ESP_ERR_NO_MEM, TAG, "camera decode buffer");
    return ESP_OK;
}

static bool tls_write_all(esp_tls_t *tls, const uint8_t *data, size_t length)
{
    size_t sent = 0;
    while (sent < length && atomic_load(&s_active)) {
        ssize_t result = esp_tls_conn_write(tls, data + sent, length - sent);
        if (result > 0) {
            sent += (size_t)result;
        } else if (result != ESP_TLS_ERR_SSL_WANT_READ &&
                   result != ESP_TLS_ERR_SSL_WANT_WRITE) {
            return false;
        } else {
            vTaskDelay(1);
        }
    }
    return sent == length;
}

static bool tls_read_all(esp_tls_t *tls, uint8_t *data, size_t length)
{
    size_t received = 0;
    while (received < length && atomic_load(&s_active)) {
        ssize_t result =
            esp_tls_conn_read(tls, data + received, length - received);
        if (result > 0) {
            received += (size_t)result;
        } else if (result != ESP_TLS_ERR_SSL_WANT_READ &&
                   result != ESP_TLS_ERR_SSL_WANT_WRITE) {
            return false;
        } else {
            vTaskDelay(1);
        }
    }
    return received == length;
}

static esp_err_t scale_frame(const jpeg_decode_picture_info_t *picture)
{
    /*
     * P1 camera frames are 1280x720. Crop a centered 1184x666 window, then
     * use the PPA's exact 1/2 scale to produce a 592x333 display frame.
     */
    uint32_t crop_width = NH_CAMERA_OUTPUT_WIDTH * 2U;
    uint32_t crop_height = NH_CAMERA_OUTPUT_HEIGHT * 2U;
    ESP_RETURN_ON_FALSE(
        picture->width >= crop_width && picture->height >= crop_height,
        ESP_ERR_NOT_SUPPORTED, TAG, "camera frame smaller than UI viewport");

    uint32_t aligned_width = (picture->width + 15U) & ~15U;
    const ppa_srm_oper_config_t scale_config = {
        .in = {
            .buffer = s_decode_buffer,
            .pic_w = aligned_width,
            .pic_h = (picture->height + 15U) & ~15U,
            .block_w = crop_width,
            .block_h = crop_height,
            .block_offset_x = (picture->width - crop_width) / 2U,
            .block_offset_y = (picture->height - crop_height) / 2U,
            .srm_cm = PPA_SRM_COLOR_MODE_RGB565,
        },
        .out = {
            .buffer = s_output_buffers[s_output_index],
            .buffer_size = s_output_buffer_sizes[s_output_index],
            .pic_w = NH_CAMERA_OUTPUT_WIDTH,
            .pic_h = NH_CAMERA_OUTPUT_HEIGHT,
            .block_offset_x = 0,
            .block_offset_y = 0,
            .srm_cm = PPA_SRM_COLOR_MODE_RGB565,
        },
        .rotation_angle = PPA_SRM_ROTATION_ANGLE_0,
        .scale_x = 0.5f,
        .scale_y = 0.5f,
        .mode = PPA_TRANS_MODE_BLOCKING,
    };
    return ppa_do_scale_rotate_mirror(s_ppa, &scale_config);
}

static esp_err_t decode_frame(size_t jpeg_size)
{
    jpeg_decode_picture_info_t picture = {0};
    ESP_RETURN_ON_ERROR(
        jpeg_decoder_get_info(s_jpeg_buffer, jpeg_size, &picture),
        TAG, "JPEG header");
    ESP_RETURN_ON_ERROR(
        ensure_decode_buffer(picture.width, picture.height),
        TAG, "JPEG output allocation");

    const jpeg_decode_cfg_t decode_config = {
        .output_format = JPEG_DECODE_OUT_FORMAT_RGB565,
        .rgb_order = JPEG_DEC_RGB_ELEMENT_ORDER_BGR,
        .conv_std = JPEG_YUV_RGB_CONV_STD_BT601,
    };
    uint32_t decoded_size = 0;
    ESP_RETURN_ON_ERROR(
        jpeg_decoder_process(
            s_decoder, &decode_config, s_jpeg_buffer, jpeg_size,
            s_decode_buffer, s_decode_buffer_size, &decoded_size),
        TAG, "JPEG decode");
    (void)decoded_size;

    ESP_RETURN_ON_ERROR(scale_frame(&picture), TAG, "camera frame scale");

    s_status.source_width = (uint16_t)picture.width;
    s_status.source_height = (uint16_t)picture.height;
    s_status.frame_count++;
    update_status(NH_CAMERA_LIVE, ESP_OK);
    if (s_config.frame_cb) {
        s_config.frame_cb(
            s_output_buffers[s_output_index],
            NH_CAMERA_OUTPUT_WIDTH, NH_CAMERA_OUTPUT_HEIGHT,
            s_status.source_width, s_status.source_height,
            s_config.callback_ctx);
    }
    s_output_index ^= 1U;
    return ESP_OK;
}

static esp_err_t stream_camera(const camera_profile_t *profile)
{
    esp_tls_t *tls = esp_tls_init();
    ESP_RETURN_ON_FALSE(tls, ESP_ERR_NO_MEM, TAG, "camera TLS context");

    const esp_tls_cfg_t tls_config = {
        .cacert_buf = (const unsigned char *)nh_bambu_ca_pem,
        .cacert_bytes = nh_bambu_ca_pem_size,
        .timeout_ms = 7000,
        .common_name = profile->serial,
    };

    update_status(
        s_status.state == NH_CAMERA_STOPPED
            ? NH_CAMERA_CONNECTING
            : NH_CAMERA_RECONNECTING,
        ESP_OK);
    int connected = esp_tls_conn_new_sync(
        profile->ip_address, strlen(profile->ip_address),
        NH_CAMERA_TLS_PORT, &tls_config, tls);
    if (connected != 1) {
        esp_tls_conn_destroy(tls);
        return ESP_ERR_TIMEOUT;
    }

    uint8_t auth_packet[80] = {0};
    write_le32(auth_packet, 0x40);
    write_le32(auth_packet + 4, 0x3000);
    memcpy(auth_packet + 16, "bblp", 4);
    strlcpy((char *)auth_packet + 48, profile->access_code, 32);
    if (!tls_write_all(tls, auth_packet, sizeof(auth_packet))) {
        nh_secure_zero(auth_packet, sizeof(auth_packet));
        esp_tls_conn_destroy(tls);
        return ESP_FAIL;
    }
    nh_secure_zero(auth_packet, sizeof(auth_packet));

    esp_err_t result = ESP_OK;
    while (atomic_load(&s_active)) {
        uint8_t frame_header[16];
        if (!tls_read_all(tls, frame_header, sizeof(frame_header))) {
            result = ESP_ERR_INVALID_RESPONSE;
            break;
        }

        uint32_t payload_size = read_le32(frame_header);
        if (payload_size < 4 || payload_size > s_jpeg_buffer_size) {
            ESP_LOGW(TAG, "Rejected camera frame size: %lu",
                     (unsigned long)payload_size);
            result = ESP_ERR_INVALID_SIZE;
            break;
        }
        if (!tls_read_all(tls, s_jpeg_buffer, payload_size)) {
            result = ESP_ERR_INVALID_RESPONSE;
            break;
        }
        if (s_jpeg_buffer[0] != 0xFF || s_jpeg_buffer[1] != 0xD8 ||
            s_jpeg_buffer[payload_size - 2] != 0xFF ||
            s_jpeg_buffer[payload_size - 1] != 0xD9) {
            ESP_LOGW(TAG, "Rejected malformed camera JPEG");
            result = ESP_ERR_INVALID_RESPONSE;
            break;
        }

        result = decode_frame(payload_size);
        if (result != ESP_OK) {
            break;
        }
    }

    esp_tls_conn_destroy(tls);
    return result;
}

static void camera_task(void *arg)
{
    (void)arg;
    while (true) {
        ulTaskNotifyTake(pdTRUE, portMAX_DELAY);
        while (atomic_load(&s_active)) {
            esp_err_t err = initialize_pipeline();
            if (err != ESP_OK) {
                update_status(NH_CAMERA_ERROR, err);
            } else {
                camera_profile_t profile;
                err = load_profile(&profile);
                if (err != ESP_OK) {
                    update_status(NH_CAMERA_NO_PROFILE, err);
                } else {
                    err = stream_camera(&profile);
                }
                nh_secure_zero(&profile, sizeof(profile));
                if (atomic_load(&s_active) && err != ESP_OK) {
                    ESP_LOGW(TAG, "Camera stream retry: %s",
                             esp_err_to_name(err));
                    update_status(NH_CAMERA_RECONNECTING, err);
                }
            }

            if (atomic_load(&s_active)) {
                ulTaskNotifyTake(pdTRUE, pdMS_TO_TICKS(NH_CAMERA_RETRY_MS));
            }
        }
        release_pipeline();
        update_status(NH_CAMERA_STOPPED, ESP_OK);
    }
}

esp_err_t nh_camera_init(const nh_camera_config_t *config)
{
    ESP_RETURN_ON_FALSE(config && config->frame_cb,
                        ESP_ERR_INVALID_ARG, TAG, "camera config required");
    ESP_RETURN_ON_FALSE(!s_initialized, ESP_ERR_INVALID_STATE,
                        TAG, "camera already initialized");

    s_config = *config;
    s_status.state = NH_CAMERA_STOPPED;
    BaseType_t created = xTaskCreate(
        camera_task, "nh_p1s_camera", NH_CAMERA_TASK_STACK,
        NULL, 4, &s_camera_task);
    ESP_RETURN_ON_FALSE(created == pdPASS, ESP_ERR_NO_MEM,
                        TAG, "camera task");
    s_initialized = true;
    notify_status();
    ESP_LOGI(TAG, "P1 local camera service ready");
    return ESP_OK;
}

esp_err_t nh_camera_set_active(bool active)
{
    ESP_RETURN_ON_FALSE(s_initialized && s_camera_task,
                        ESP_ERR_INVALID_STATE, TAG, "camera not initialized");
    atomic_store(&s_active, active);
    xTaskNotifyGive(s_camera_task);
    return ESP_OK;
}
