#include "nh_printer.h"

#include <ctype.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "esp_event.h"
#include "esp_heap_caps.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/semphr.h"
#include "freertos/task.h"
#include "lwip/ip4_addr.h"
#include "mqtt_client.h"
#include "nh_bambu.h"
#include "nh_printer_protocol.h"
#include "nvs.h"

static const char *TAG = "nh_printer";

enum {
    NH_PRINTER_QUEUE_DEPTH = 8,
    NH_PRINTER_WORKER_STACK = 10240,
    NH_PRINTER_MQTT_STACK = 10240,
    NH_PRINTER_MQTT_BUFFER = 32768,
    NH_PRINTER_MAX_REPORT = 65536,
};

typedef enum {
    NH_PRINTER_COMMAND_PAIR = 0,
    NH_PRINTER_COMMAND_ACTION,
    NH_PRINTER_COMMAND_PROFILE_VALIDATED,
    NH_PRINTER_COMMAND_PROFILE_RESTORE,
} nh_printer_command_type_t;

typedef struct {
    nh_printer_command_type_t type;
    nh_action_t action;
    int32_t value;
    char ip_address[NH_PRINTER_IP_MAX_LENGTH + 1];
    char serial[NH_PRINTER_SERIAL_MAX_LENGTH + 1];
    char access_code[NH_PRINTER_ACCESS_CODE_MAX_LENGTH + 1];
    uint32_t profile_generation;
} nh_printer_command_t;

static nh_printer_config_t s_config;
static nh_printer_status_t s_status;
static nh_printer_snapshot_t *s_snapshot;
static QueueHandle_t s_command_queue;
static SemaphoreHandle_t s_state_mutex;
static esp_mqtt_client_handle_t s_mqtt;
static bool s_initialized;
static atomic_bool s_connected;
static atomic_bool s_configured;
static atomic_bool s_chamber_light_on;
static atomic_bool s_profile_save_pending;
static atomic_uint_fast32_t s_profile_generation;
static atomic_int s_job_state;
static atomic_int s_transport_state;
static bool s_have_verified_profile;
static bool s_backup_profile_valid;
static atomic_uint_fast32_t s_sequence;

static char s_ip_address[NH_PRINTER_IP_MAX_LENGTH + 1];
static char s_serial[NH_PRINTER_SERIAL_MAX_LENGTH + 1];
static char s_access_code[NH_PRINTER_ACCESS_CODE_MAX_LENGTH + 1];
static char s_backup_ip_address[NH_PRINTER_IP_MAX_LENGTH + 1];
static char s_backup_serial[NH_PRINTER_SERIAL_MAX_LENGTH + 1];
static char s_backup_access_code[NH_PRINTER_ACCESS_CODE_MAX_LENGTH + 1];
static char s_mqtt_uri[48];
static char s_report_topic[80];
static char s_request_topic[80];
static char s_client_id[48];

static char s_printer_name[48] = "Bambu Lab P1S";
static char s_job_name[96] = "No active print";
static char s_job_layer[48] = "Layer -- / --";
static char s_remaining[24] = "--h --m";
static nh_printer_protocol_t s_protocol;

static char *s_report_buffer;
static size_t s_report_buffer_size;
static size_t s_report_received_size;

static bool system_clock_ready(void)
{
    /*
     * Certificate validity errors before SNTP completes are transient network
     * startup conditions, not proof that a newly entered printer identity is
     * wrong. This threshold is deliberately well before the product build.
     */
    return time(NULL) >= 1700000000;
}

static void state_lock(void)
{
    if (s_state_mutex) {
        (void)xSemaphoreTake(s_state_mutex, portMAX_DELAY);
    }
}

static void state_unlock(void)
{
    if (s_state_mutex) {
        (void)xSemaphoreGive(s_state_mutex);
    }
}

static void notify_update(void)
{
    if (!s_config.update_cb || !s_snapshot) {
        return;
    }

    /*
     * MQTT callbacks and the profile worker run in different tasks. Publish a
     * coherent, deep-copied view instead of exposing pointers into mutable
     * shared strings while either task may be changing the active session.
     */
    nh_printer_snapshot_t snapshot_copy;
    nh_printer_status_t status_copy;
    char printer_name[sizeof(s_printer_name)];
    char job_name[sizeof(s_job_name)];
    char job_layer[sizeof(s_job_layer)];
    char remaining[sizeof(s_remaining)];

    state_lock();
    snapshot_copy = *s_snapshot;
    status_copy = s_status;
    strlcpy(printer_name,
            s_snapshot->printer_name ? s_snapshot->printer_name : "",
            sizeof(printer_name));
    strlcpy(job_name, s_snapshot->job_name ? s_snapshot->job_name : "",
            sizeof(job_name));
    strlcpy(job_layer, s_snapshot->job_layer ? s_snapshot->job_layer : "",
            sizeof(job_layer));
    strlcpy(remaining, s_snapshot->remaining ? s_snapshot->remaining : "",
            sizeof(remaining));
    snapshot_copy.printer_name = printer_name;
    snapshot_copy.job_name = job_name;
    snapshot_copy.job_layer = job_layer;
    snapshot_copy.remaining = remaining;
    state_unlock();

    s_config.update_cb(&snapshot_copy, &status_copy, s_config.update_ctx);
}

static void update_state(nh_printer_state_t state, esp_err_t error)
{
    atomic_store(&s_transport_state, state);
    state_lock();
    s_status.state = state;
    s_status.last_error = error;
    if (s_snapshot) {
        switch (state) {
        case NH_PRINTER_UNCONFIGURED:
            s_snapshot->connection = NH_CONNECTION_UNCONFIGURED;
            break;
        case NH_PRINTER_CONNECTING:
            s_snapshot->connection = NH_CONNECTION_CONNECTING;
            break;
        case NH_PRINTER_ONLINE:
            s_snapshot->connection = NH_CONNECTION_ONLINE;
            break;
        case NH_PRINTER_OFFLINE:
            s_snapshot->connection = NH_CONNECTION_OFFLINE;
            break;
        case NH_PRINTER_AUTH_ERROR:
        case NH_PRINTER_TLS_ERROR:
        case NH_PRINTER_ERROR:
        default:
            s_snapshot->connection = NH_CONNECTION_ERROR;
            break;
        }
    }
    state_unlock();
    notify_update();
}

static void set_profile_status(const char *ip_address, const char *serial,
                               bool configured, bool profile_ready)
{
    state_lock();
    if (ip_address) {
        strlcpy(s_status.ip_address, ip_address,
                sizeof(s_status.ip_address));
    } else {
        s_status.ip_address[0] = '\0';
    }
    if (serial) {
        strlcpy(s_status.serial, serial, sizeof(s_status.serial));
    } else {
        s_status.serial[0] = '\0';
    }
    s_status.configured = configured;
    s_status.profile_ready = profile_ready;
    state_unlock();
}

static void set_profile_ready(bool profile_ready)
{
    state_lock();
    s_status.profile_ready = profile_ready;
    state_unlock();
}

const char *nh_printer_state_label(nh_printer_state_t state)
{
    switch (state) {
    case NH_PRINTER_UNCONFIGURED:
        return "SETUP REQUIRED";
    case NH_PRINTER_CONNECTING:
        return "CONNECTING";
    case NH_PRINTER_ONLINE:
        return "ONLINE";
    case NH_PRINTER_OFFLINE:
        return "OFFLINE";
    case NH_PRINTER_AUTH_ERROR:
        return "ACCESS CODE REJECTED";
    case NH_PRINTER_TLS_ERROR:
        return "IDENTITY CHECK FAILED";
    case NH_PRINTER_ERROR:
    default:
        return "CONNECTION ERROR";
    }
}

bool nh_printer_action_supported(nh_action_t action)
{
    switch (action) {
    case NH_ACTION_CONNECT:
    case NH_ACTION_PAUSE:
    case NH_ACTION_RESUME:
    case NH_ACTION_CANCEL:
    case NH_ACTION_LIGHT_TOGGLE:
        return true;
    default:
        return false;
    }
}

bool nh_printer_action_available(
    nh_action_t action, const nh_printer_snapshot_t *snapshot)
{
    if (!nh_printer_action_supported(action)) {
        return false;
    }
    if (action == NH_ACTION_CONNECT) {
        return true;
    }
    if (!snapshot || snapshot->connection != NH_CONNECTION_ONLINE) {
        return false;
    }

    switch (action) {
    case NH_ACTION_PAUSE:
        return snapshot->job == NH_JOB_PRINTING;
    case NH_ACTION_RESUME:
        return snapshot->job == NH_JOB_PAUSED;
    case NH_ACTION_CANCEL:
        return snapshot->job == NH_JOB_PREPARING ||
               snapshot->job == NH_JOB_PRINTING ||
               snapshot->job == NH_JOB_PAUSED;
    case NH_ACTION_LIGHT_TOGGLE:
        return true;
    default:
        return false;
    }
}

static void clear_report_buffer(void)
{
    free(s_report_buffer);
    s_report_buffer = NULL;
    s_report_buffer_size = 0;
    s_report_received_size = 0;
}

static void clear_backup_profile(void)
{
    s_backup_ip_address[0] = '\0';
    s_backup_serial[0] = '\0';
    nh_secure_zero(s_backup_access_code, sizeof(s_backup_access_code));
    s_backup_profile_valid = false;
}

static void enqueue_profile_event(nh_printer_command_type_t type)
{
    const nh_printer_command_t command = {
        .type = type,
        .profile_generation =
            (uint32_t)atomic_load(&s_profile_generation),
    };
    if (!s_command_queue ||
        xQueueSend(s_command_queue, &command, 0) != pdTRUE) {
        ESP_LOGE(TAG, "Dropped printer profile event %d: command queue full",
                 (int)type);
    }
}

static void reset_telemetry(void)
{
    state_lock();
    nh_printer_protocol_reset(&s_protocol);
    state_unlock();
    atomic_store(&s_job_state, NH_JOB_UNKNOWN);
    atomic_store(&s_chamber_light_on, false);
}

static bool valid_serial(const char *serial)
{
    size_t length = serial ? strnlen(serial, NH_PRINTER_SERIAL_MAX_LENGTH + 1) : 0;
    if (length < 10 || length > NH_PRINTER_SERIAL_MAX_LENGTH) {
        return false;
    }
    for (size_t i = 0; i < length; ++i) {
        if (!isalnum((unsigned char)serial[i])) {
            return false;
        }
    }
    return true;
}

static bool valid_pairing(const char *ip_address, const char *serial,
                          const char *access_code)
{
    ip4_addr_t parsed_address;
    size_t access_length =
        access_code ? strnlen(access_code, NH_PRINTER_ACCESS_CODE_MAX_LENGTH + 1) : 0;
    return ip_address && ip4addr_aton(ip_address, &parsed_address) &&
           valid_serial(serial) && access_length >= 8 &&
           access_length <= NH_PRINTER_ACCESS_CODE_MAX_LENGTH;
}

static esp_err_t load_profile(void)
{
    nvs_handle_t nvs;
    esp_err_t err = nvs_open("nh_p1s", NVS_READONLY, &nvs);
    if (err != ESP_OK) {
        return err;
    }

    size_t ip_length = sizeof(s_ip_address);
    size_t serial_length = sizeof(s_serial);
    size_t code_length = sizeof(s_access_code);
    err = nvs_get_str(nvs, "ip", s_ip_address, &ip_length);
    if (err == ESP_OK) {
        err = nvs_get_str(nvs, "serial", s_serial, &serial_length);
    }
    if (err == ESP_OK) {
        err = nvs_get_str(nvs, "code", s_access_code, &code_length);
    }
    nvs_close(nvs);
    if (err == ESP_OK &&
        !valid_pairing(s_ip_address, s_serial, s_access_code)) {
        return ESP_ERR_INVALID_STATE;
    }
    return err;
}

static esp_err_t save_profile(void)
{
    nvs_handle_t nvs;
    esp_err_t err = nvs_open("nh_p1s", NVS_READWRITE, &nvs);
    if (err != ESP_OK) {
        return err;
    }
    err = nvs_set_str(nvs, "ip", s_ip_address);
    if (err == ESP_OK) {
        err = nvs_set_str(nvs, "serial", s_serial);
    }
    if (err == ESP_OK) {
        err = nvs_set_str(nvs, "code", s_access_code);
    }
    if (err == ESP_OK) {
        err = nvs_commit(nvs);
    }
    nvs_close(nvs);
    return err;
}

static void receive_report_fragment(const esp_mqtt_event_t *event)
{
    if (!event->data || event->total_data_len <= 0 ||
        event->total_data_len > NH_PRINTER_MAX_REPORT ||
        event->current_data_offset < 0 || event->data_len < 0 ||
        event->current_data_offset > event->total_data_len ||
        event->data_len >
            event->total_data_len - event->current_data_offset) {
        ESP_LOGW(TAG, "Rejected invalid MQTT report fragment");
        return;
    }

    if (event->current_data_offset == 0) {
        clear_report_buffer();
        s_report_buffer = heap_caps_malloc(
            (size_t)event->total_data_len + 1,
            MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
        if (!s_report_buffer) {
            s_report_buffer = malloc((size_t)event->total_data_len + 1);
        }
        s_report_buffer_size =
            s_report_buffer ? (size_t)event->total_data_len : 0;
        s_report_received_size = 0;
    }
    if (!s_report_buffer ||
        s_report_buffer_size != (size_t)event->total_data_len ||
        s_report_received_size != (size_t)event->current_data_offset) {
        ESP_LOGW(TAG, "Dropped out-of-order MQTT report fragment");
        clear_report_buffer();
        return;
    }

    memcpy(s_report_buffer + event->current_data_offset,
           event->data, (size_t)event->data_len);
    s_report_received_size += (size_t)event->data_len;
    if (s_report_received_size == (size_t)event->total_data_len) {
        s_report_buffer[event->total_data_len] = '\0';
        state_lock();
        nh_printer_protocol_result_t result =
            nh_printer_protocol_parse(
                &s_protocol, s_report_buffer,
                (size_t)event->total_data_len);
        if (result == NH_PRINTER_PROTOCOL_INVALID) {
            ESP_LOGW(TAG, "Ignored malformed P1S report (%u bytes)",
                     (unsigned)event->total_data_len);
        } else if (result == NH_PRINTER_PROTOCOL_UPDATED) {
            atomic_store(&s_job_state, s_snapshot->job);
            atomic_store(&s_chamber_light_on,
                         s_snapshot->chamber_light_on);
        }
        state_unlock();
        if (result == NH_PRINTER_PROTOCOL_UPDATED) {
            notify_update();
        }
        clear_report_buffer();
    }
}

static int queue_payload(const char *payload)
{
    if (!s_mqtt || !atomic_load(&s_connected)) {
        return -1;
    }
    return esp_mqtt_client_enqueue(s_mqtt, s_request_topic, payload,
                                   0, 1, 0, true);
}

static void request_full_status(void)
{
    char payload[128];
    uint32_t sequence =
        (uint32_t)atomic_fetch_add(&s_sequence, 1) + 1U;
    snprintf(payload, sizeof(payload),
             "{\"pushing\":{\"sequence_id\":\"%lu\",\"command\":\"pushall\"}}",
             (unsigned long)sequence);
    if (queue_payload(payload) < 0) {
        ESP_LOGW(TAG, "Could not request initial P1S status");
    }
}

static void mqtt_event_handler(void *handler_args, esp_event_base_t base,
                               int32_t event_id, void *event_data)
{
    (void)base;
    esp_mqtt_event_t *event = event_data;
    uint32_t event_generation = (uint32_t)(uintptr_t)handler_args;
    if (!event || event->client != s_mqtt ||
        event_generation !=
            (uint32_t)atomic_load(&s_profile_generation)) {
        ESP_LOGD(TAG, "Ignored event from superseded P1S session");
        return;
    }

    switch ((esp_mqtt_event_id_t)event_id) {
    case MQTT_EVENT_CONNECTED:
        atomic_store(&s_connected, true);
        if (esp_mqtt_client_subscribe(s_mqtt, s_report_topic, 1) < 0) {
            ESP_LOGW(TAG, "Could not subscribe to P1S reports");
        }
        update_state(NH_PRINTER_ONLINE, ESP_OK);
        request_full_status();
        if (atomic_load(&s_profile_save_pending)) {
            enqueue_profile_event(NH_PRINTER_COMMAND_PROFILE_VALIDATED);
        }
        ESP_LOGI(TAG, "Authenticated P1S LAN session established");
        break;
    case MQTT_EVENT_DISCONNECTED:
        atomic_store(&s_connected, false);
        clear_report_buffer();
        reset_telemetry();
        nh_printer_state_t state =
            (nh_printer_state_t)atomic_load(&s_transport_state);
        if (atomic_load(&s_configured) &&
            state != NH_PRINTER_AUTH_ERROR &&
            state != NH_PRINTER_TLS_ERROR) {
            update_state(NH_PRINTER_OFFLINE, ESP_FAIL);
        }
        break;
    case MQTT_EVENT_ERROR:
        atomic_store(&s_connected, false);
        if (event->error_handle &&
            event->error_handle->error_type ==
                MQTT_ERROR_TYPE_CONNECTION_REFUSED &&
            (event->error_handle->connect_return_code ==
                 MQTT_CONNECTION_REFUSE_BAD_USERNAME ||
             event->error_handle->connect_return_code ==
                 MQTT_CONNECTION_REFUSE_NOT_AUTHORIZED)) {
            update_state(NH_PRINTER_AUTH_ERROR, ESP_ERR_INVALID_CRC);
            ESP_LOGW(TAG, "P1S rejected the LAN access code");
            if (atomic_load(&s_profile_save_pending)) {
                enqueue_profile_event(NH_PRINTER_COMMAND_PROFILE_RESTORE);
            }
        } else if (event->error_handle &&
                   event->error_handle->error_type ==
                       MQTT_ERROR_TYPE_TCP_TRANSPORT &&
                   !system_clock_ready()) {
            update_state(NH_PRINTER_OFFLINE, ESP_ERR_TIMEOUT);
            ESP_LOGW(TAG,
                     "P1S TLS waiting for network time synchronization");
        } else if (event->error_handle &&
                   event->error_handle->error_type ==
                       MQTT_ERROR_TYPE_TCP_TRANSPORT &&
                   (event->error_handle->esp_tls_cert_verify_flags != 0 ||
                    (event->error_handle->esp_tls_stack_err != 0 &&
                     event->error_handle->esp_transport_sock_errno == 0))) {
            update_state(NH_PRINTER_TLS_ERROR, ESP_ERR_INVALID_RESPONSE);
            ESP_LOGW(TAG, "P1S TLS certificate or handshake failed");
            if (atomic_load(&s_profile_save_pending)) {
                enqueue_profile_event(NH_PRINTER_COMMAND_PROFILE_RESTORE);
            }
        } else {
            esp_err_t transport_error =
                event->error_handle &&
                        event->error_handle->esp_tls_last_esp_err != ESP_OK
                    ? event->error_handle->esp_tls_last_esp_err
                    : ESP_FAIL;
            update_state(NH_PRINTER_OFFLINE, transport_error);
            ESP_LOGW(TAG, "P1S transport unavailable");
        }
        break;
    case MQTT_EVENT_DATA:
        receive_report_fragment(event);
        break;
    default:
        break;
    }
}

static void stop_mqtt(void)
{
    atomic_store(&s_connected, false);
    clear_report_buffer();
    if (!s_mqtt) {
        return;
    }
    (void)esp_mqtt_client_stop(s_mqtt);
    (void)esp_mqtt_client_destroy(s_mqtt);
    s_mqtt = NULL;
}

static esp_err_t start_mqtt(void)
{
    stop_mqtt();
    reset_telemetry();
    snprintf(s_mqtt_uri, sizeof(s_mqtt_uri), "mqtts://%s:8883",
             s_ip_address);
    snprintf(s_report_topic, sizeof(s_report_topic), "device/%s/report",
             s_serial);
    snprintf(s_request_topic, sizeof(s_request_topic), "device/%s/request",
             s_serial);
    snprintf(s_client_id, sizeof(s_client_id), "printdeck-%s", s_serial);

    const esp_mqtt_client_config_t mqtt_config = {
        .broker = {
            .address = {
                .uri = s_mqtt_uri,
            },
            .verification = {
                .certificate = nh_bambu_ca_pem,
                .common_name = s_serial,
            },
        },
        .credentials = {
            .username = "bblp",
            .client_id = s_client_id,
            .authentication = {
                .password = s_access_code,
            },
        },
        .session = {
            .keepalive = 30,
        },
        .network = {
            .reconnect_timeout_ms = 5000,
            .timeout_ms = 7000,
        },
        .task = {
            .priority = 5,
            .stack_size = NH_PRINTER_MQTT_STACK,
        },
        .buffer = {
            .size = NH_PRINTER_MQTT_BUFFER,
            .out_size = 4096,
        },
        .outbox = {
            .limit = 32768,
        },
    };

    s_mqtt = esp_mqtt_client_init(&mqtt_config);
    if (!s_mqtt) {
        return ESP_ERR_NO_MEM;
    }
    void *session_generation = (void *)(uintptr_t)(
        (uint32_t)atomic_load(&s_profile_generation));
    esp_err_t err = esp_mqtt_client_register_event(
        s_mqtt, ESP_EVENT_ANY_ID, mqtt_event_handler, session_generation);
    if (err == ESP_OK) {
        err = esp_mqtt_client_start(s_mqtt);
    }
    if (err != ESP_OK) {
        esp_mqtt_client_destroy(s_mqtt);
        s_mqtt = NULL;
        return err;
    }

    update_state(NH_PRINTER_CONNECTING, ESP_OK);
    ESP_LOGI(TAG, "Connecting to pinned P1S identity at %s", s_ip_address);
    return ESP_OK;
}

static esp_err_t send_action(nh_action_t action, int32_t value)
{
    (void)value;
    if (action == NH_ACTION_CONNECT) {
        if (!atomic_load(&s_configured)) {
            return ESP_ERR_INVALID_STATE;
        }
        if (atomic_load(&s_connected)) {
            request_full_status();
            return ESP_OK;
        }
        return s_mqtt ? esp_mqtt_client_reconnect(s_mqtt) : start_mqtt();
    }
    if (!atomic_load(&s_connected) || !s_mqtt) {
        return ESP_ERR_INVALID_STATE;
    }

    const char *command = NULL;
    switch (action) {
    case NH_ACTION_PAUSE:
        command = "pause";
        break;
    case NH_ACTION_RESUME:
        command = "resume";
        break;
    case NH_ACTION_CANCEL:
        command = "stop";
        break;
    case NH_ACTION_LIGHT_TOGGLE: {
        char payload[320];
        uint32_t sequence =
            (uint32_t)atomic_fetch_add(&s_sequence, 1) + 1U;
        snprintf(
            payload, sizeof(payload),
            "{\"system\":{\"sequence_id\":\"%lu\",\"command\":\"ledctrl\","
            "\"led_node\":\"chamber_light\",\"led_mode\":\"%s\","
            "\"led_on_time\":500,\"led_off_time\":500,\"loop_times\":0,"
            "\"interval_time\":0}}",
            (unsigned long)sequence,
            atomic_load(&s_chamber_light_on) ? "off" : "on");
        return queue_payload(payload) >= 0 ? ESP_OK : ESP_FAIL;
    }
    default:
        return ESP_ERR_NOT_SUPPORTED;
    }

    char payload[160];
    uint32_t sequence =
        (uint32_t)atomic_fetch_add(&s_sequence, 1) + 1U;
    snprintf(payload, sizeof(payload),
             "{\"print\":{\"sequence_id\":\"%lu\",\"command\":\"%s\"}}",
             (unsigned long)sequence, command);
    return queue_payload(payload) >= 0 ? ESP_OK : ESP_FAIL;
}

static void printer_worker_task(void *arg)
{
    (void)arg;
    nh_printer_command_t command;

    while (true) {
        if (xQueueReceive(s_command_queue, &command, portMAX_DELAY) != pdTRUE) {
            continue;
        }

        if (command.type == NH_PRINTER_COMMAND_PAIR) {
            if (!atomic_load(&s_profile_save_pending)) {
                clear_backup_profile();
                if (s_have_verified_profile) {
                    strlcpy(s_backup_ip_address, s_ip_address,
                            sizeof(s_backup_ip_address));
                    strlcpy(s_backup_serial, s_serial,
                            sizeof(s_backup_serial));
                    strlcpy(s_backup_access_code, s_access_code,
                            sizeof(s_backup_access_code));
                    s_backup_profile_valid = true;
                }
            }
            (void)atomic_fetch_add(&s_profile_generation, 1);
            strlcpy(s_ip_address, command.ip_address, sizeof(s_ip_address));
            strlcpy(s_serial, command.serial, sizeof(s_serial));
            nh_secure_zero(s_access_code, sizeof(s_access_code));
            strlcpy(s_access_code, command.access_code, sizeof(s_access_code));
            set_profile_status(s_ip_address, s_serial, true, false);
            atomic_store(&s_configured, true);
            atomic_store(&s_profile_save_pending, true);

            esp_err_t err = start_mqtt();
            if (err != ESP_OK) {
                update_state(NH_PRINTER_ERROR, err);
            }
            nh_secure_zero(command.access_code, sizeof(command.access_code));
            continue;
        }

        if (command.type == NH_PRINTER_COMMAND_PROFILE_VALIDATED) {
            if (command.profile_generation ==
                    (uint32_t)atomic_load(&s_profile_generation) &&
                atomic_load(&s_profile_save_pending) &&
                atomic_load(&s_connected)) {
                esp_err_t save_err = save_profile();
                if (save_err == ESP_OK) {
                    atomic_store(&s_profile_save_pending, false);
                    s_have_verified_profile = true;
                    set_profile_ready(true);
                    clear_backup_profile();
                    ESP_LOGI(TAG, "Validated P1S profile persisted");
                    notify_update();
                } else {
                    ESP_LOGW(TAG,
                             "Could not persist validated P1S profile: %s",
                             esp_err_to_name(save_err));
                }
            }
            continue;
        }

        if (command.type == NH_PRINTER_COMMAND_PROFILE_RESTORE) {
            if (command.profile_generation !=
                    (uint32_t)atomic_load(&s_profile_generation) ||
                !atomic_load(&s_profile_save_pending)) {
                continue;
            }

            atomic_store(&s_profile_save_pending, false);
            stop_mqtt();
            if (s_backup_profile_valid) {
                strlcpy(s_ip_address, s_backup_ip_address,
                        sizeof(s_ip_address));
                strlcpy(s_serial, s_backup_serial, sizeof(s_serial));
                nh_secure_zero(s_access_code, sizeof(s_access_code));
                strlcpy(s_access_code, s_backup_access_code,
                        sizeof(s_access_code));
                set_profile_status(s_ip_address, s_serial, true, true);
                atomic_store(&s_configured, true);
                clear_backup_profile();
                ESP_LOGW(TAG,
                         "Rejected profile rolled back to last verified P1S");
                esp_err_t restore_err = start_mqtt();
                if (restore_err != ESP_OK) {
                    update_state(NH_PRINTER_ERROR, restore_err);
                }
            } else {
                s_have_verified_profile = false;
                atomic_store(&s_configured, false);
                set_profile_status(NULL, NULL, false, false);
                s_ip_address[0] = '\0';
                s_serial[0] = '\0';
                nh_secure_zero(s_access_code, sizeof(s_access_code));
                reset_telemetry();
                update_state(NH_PRINTER_UNCONFIGURED,
                             ESP_ERR_INVALID_RESPONSE);
            }
            continue;
        }

        esp_err_t err = send_action(command.action, command.value);
        if (err != ESP_OK) {
            ESP_LOGW(TAG, "Rejected action '%s': %s",
                     nh_action_label(command.action), esp_err_to_name(err));
        }
    }
}

esp_err_t nh_printer_pair(const char *ip_address, const char *serial,
                          const char *access_code)
{
    if (!s_initialized || !s_command_queue) {
        return ESP_ERR_INVALID_STATE;
    }
    if (!valid_pairing(ip_address, serial, access_code)) {
        return ESP_ERR_INVALID_ARG;
    }

    nh_printer_command_t command = {
        .type = NH_PRINTER_COMMAND_PAIR,
    };
    strlcpy(command.ip_address, ip_address, sizeof(command.ip_address));
    strlcpy(command.serial, serial, sizeof(command.serial));
    strlcpy(command.access_code, access_code, sizeof(command.access_code));
    BaseType_t queued = xQueueSend(s_command_queue, &command, 0);
    nh_secure_zero(command.access_code, sizeof(command.access_code));
    return queued == pdTRUE ? ESP_OK : ESP_ERR_TIMEOUT;
}

esp_err_t nh_printer_action(nh_action_t action, int32_t value)
{
    if (!s_initialized || !s_command_queue) {
        return ESP_ERR_INVALID_STATE;
    }
    if (!nh_printer_action_supported(action)) {
        return ESP_ERR_NOT_SUPPORTED;
    }
    if (action == NH_ACTION_CONNECT) {
        if (!atomic_load(&s_configured)) {
            return ESP_ERR_INVALID_STATE;
        }
    } else if (!atomic_load(&s_connected)) {
        return ESP_ERR_INVALID_STATE;
    } else {
        nh_job_state_t job =
            (nh_job_state_t)atomic_load(&s_job_state);
        bool available = action == NH_ACTION_LIGHT_TOGGLE ||
                         (action == NH_ACTION_PAUSE &&
                          job == NH_JOB_PRINTING) ||
                         (action == NH_ACTION_RESUME &&
                          job == NH_JOB_PAUSED) ||
                         (action == NH_ACTION_CANCEL &&
                          (job == NH_JOB_PREPARING ||
                           job == NH_JOB_PRINTING ||
                           job == NH_JOB_PAUSED));
        if (!available) {
            return ESP_ERR_INVALID_STATE;
        }
    }
    if (action != NH_ACTION_CONNECT &&
        !atomic_load(&s_connected)) {
        return ESP_ERR_INVALID_STATE;
    }

    const nh_printer_command_t command = {
        .type = NH_PRINTER_COMMAND_ACTION,
        .action = action,
        .value = value,
    };
    return xQueueSend(s_command_queue, &command, 0) == pdTRUE
               ? ESP_OK
               : ESP_ERR_TIMEOUT;
}

esp_err_t nh_printer_init(const nh_printer_config_t *config)
{
    if (s_initialized) {
        return ESP_ERR_INVALID_STATE;
    }
    if (!config || !config->snapshot) {
        return ESP_ERR_INVALID_ARG;
    }

    s_config = *config;
    s_snapshot = config->snapshot;
    s_state_mutex = xSemaphoreCreateMutex();
    if (!s_state_mutex) {
        return ESP_ERR_NO_MEM;
    }
    s_snapshot->printer_name = s_printer_name;
    nh_printer_protocol_init(
        &s_protocol, s_snapshot,
        s_job_name, sizeof(s_job_name),
        s_job_layer, sizeof(s_job_layer),
        s_remaining, sizeof(s_remaining));
    reset_telemetry();

    memset(&s_status, 0, sizeof(s_status));
    set_profile_status(config->default_ip, config->default_serial,
                       false, false);

    s_command_queue = xQueueCreate(NH_PRINTER_QUEUE_DEPTH,
                                   sizeof(nh_printer_command_t));
    if (!s_command_queue) {
        vSemaphoreDelete(s_state_mutex);
        s_state_mutex = NULL;
        return ESP_ERR_NO_MEM;
    }
    BaseType_t task_created =
        xTaskCreate(printer_worker_task, "nh_p1s_worker",
                    NH_PRINTER_WORKER_STACK, NULL, 4, NULL);
    if (task_created != pdPASS) {
        vQueueDelete(s_command_queue);
        s_command_queue = NULL;
        vSemaphoreDelete(s_state_mutex);
        s_state_mutex = NULL;
        return ESP_ERR_NO_MEM;
    }

    s_initialized = true;
    esp_err_t err = load_profile();
    if (err == ESP_OK) {
        s_have_verified_profile = true;
        atomic_store(&s_configured, true);
        set_profile_status(s_ip_address, s_serial, true, true);
        err = start_mqtt();
        if (err != ESP_OK) {
            update_state(NH_PRINTER_ERROR, err);
            return err;
        }
    } else {
        /*
         * nvs_get_str() may have populated one or more fields before a later
         * key or validation failed. Do not retain an unusable profile,
         * especially its access code, in process memory.
         */
        s_ip_address[0] = '\0';
        s_serial[0] = '\0';
        nh_secure_zero(s_access_code, sizeof(s_access_code));
        set_profile_status(NULL, NULL, false, false);
        atomic_store(&s_configured, false);
        update_state(NH_PRINTER_UNCONFIGURED, ESP_OK);
    }
    return ESP_OK;
}
