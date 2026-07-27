#include "nh_network.h"

#include <ctype.h>
#include <stdio.h>
#include <string.h>

#include "esp_check.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "esp_netif_sntp.h"
#include "esp_timer.h"
#include "esp_wifi.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"
#include "nh_core.h"
#include "nvs.h"

static const char *TAG = "nh_network";

enum {
    NH_NETWORK_UNVERIFIED_MAX_ATTEMPTS = 3,
    NH_NETWORK_COMMAND_QUEUE_DEPTH = 8,
    NH_NETWORK_WORKER_STACK_SIZE = 8192,
    NH_NETWORK_WORKER_PRIORITY = 4,
    NH_NETWORK_RETRY_INITIAL_MS = 1000,
    NH_NETWORK_RETRY_MAX_MS = 30000,
};

typedef enum {
    NH_NETWORK_COMMAND_SCAN = 0,
    NH_NETWORK_COMMAND_CONNECT,
    NH_NETWORK_EVENT_STARTED,
    NH_NETWORK_EVENT_SCAN_DONE,
    NH_NETWORK_EVENT_DISCONNECTED,
    NH_NETWORK_EVENT_GOT_IP,
    NH_NETWORK_EVENT_RETRY,
} nh_network_command_type_t;

typedef struct {
    nh_network_command_type_t type;
    char ssid[NH_NETWORK_SSID_MAX_LENGTH + 1];
    char password[65];
    uint16_t disconnect_reason;
    esp_netif_ip_info_t ip_info;
} nh_network_command_t;

static nh_network_config_t s_config;
static nh_network_snapshot_t s_snapshot;
static esp_netif_t *s_station_netif;
static char s_pending_ssid[NH_NETWORK_SSID_MAX_LENGTH + 1];
static char s_pending_password[65];
static char s_backup_ssid[NH_NETWORK_SSID_MAX_LENGTH + 1];
static char s_backup_password[65];
static bool s_initialized;
static bool s_have_saved_credentials;
static bool s_backup_credentials_valid;
static bool s_profile_unverified;
static bool s_should_reconnect;
static bool s_connect_after_disconnect;
static bool s_scan_return_connected;
static bool s_sntp_initialized;
static uint8_t s_retry_count;
static QueueHandle_t s_command_queue;
static esp_timer_handle_t s_retry_timer;
static int64_t s_retry_deadline_us;

static bool valid_credentials(const char *ssid, const char *password)
{
    size_t ssid_length =
        ssid ? strnlen(ssid, NH_NETWORK_SSID_MAX_LENGTH + 1) : 0;
    size_t password_length = password ? strnlen(password, 65) : 0;
    if (ssid_length == 0 || ssid_length > NH_NETWORK_SSID_MAX_LENGTH) {
        return false;
    }
    if (password_length == 0) {
        return true;
    }
    if (password_length >= 8 && password_length <= 63) {
        return true;
    }
    if (password_length != 64) {
        return false;
    }
    for (size_t i = 0; i < password_length; ++i) {
        if (!isxdigit((unsigned char)password[i])) {
            return false;
        }
    }
    return true;
}

static void notify_update(void)
{
    if (s_config.update_cb) {
        s_config.update_cb(&s_snapshot, s_config.update_ctx);
    }
}

static void set_state(nh_network_state_t state, esp_err_t error)
{
    s_snapshot.state = state;
    s_snapshot.last_error = error;
    notify_update();
}

const char *nh_network_state_label(nh_network_state_t state)
{
    switch (state) {
    case NH_NETWORK_DISABLED:
        return "DISABLED";
    case NH_NETWORK_INITIALIZING:
        return "INITIALIZING";
    case NH_NETWORK_SCANNING:
        return "SCANNING";
    case NH_NETWORK_READY:
        return "READY";
    case NH_NETWORK_CONNECTING:
        return "CONNECTING";
    case NH_NETWORK_CONNECTED:
        return "CONNECTED";
    case NH_NETWORK_ERROR:
        return "ERROR";
    default:
        return "UNKNOWN";
    }
}

static esp_err_t load_credentials(void)
{
    nvs_handle_t nvs;
    esp_err_t err = nvs_open("nh_wifi", NVS_READONLY, &nvs);
    if (err == ESP_ERR_NVS_NOT_FOUND) {
        return ESP_ERR_NOT_FOUND;
    }
    if (err != ESP_OK) {
        return err;
    }

    size_t ssid_length = sizeof(s_pending_ssid);
    size_t password_length = sizeof(s_pending_password);
    err = nvs_get_str(nvs, "ssid", s_pending_ssid, &ssid_length);
    if (err == ESP_OK) {
        err = nvs_get_str(nvs, "password", s_pending_password,
                          &password_length);
    }
    nvs_close(nvs);
    if (err == ESP_OK &&
        !valid_credentials(s_pending_ssid, s_pending_password)) {
        err = ESP_ERR_INVALID_STATE;
    }
    return err;
}

static esp_err_t save_credentials(void)
{
    nvs_handle_t nvs;
    ESP_RETURN_ON_ERROR(nvs_open("nh_wifi", NVS_READWRITE, &nvs),
                        TAG, "open Wi-Fi NVS");
    esp_err_t err = nvs_set_str(nvs, "ssid", s_pending_ssid);
    if (err == ESP_OK) {
        err = nvs_set_str(nvs, "password", s_pending_password);
    }
    if (err == ESP_OK) {
        err = nvs_commit(nvs);
    }
    nvs_close(nvs);
    return err;
}

static void cancel_retry_timer(void)
{
    if (s_retry_timer) {
        (void)esp_timer_stop(s_retry_timer);
    }
    s_retry_deadline_us = 0;
    s_snapshot.reconnect_delay_ms = 0;
}

static void clear_backup_credentials(void)
{
    s_backup_ssid[0] = '\0';
    nh_secure_zero(s_backup_password, sizeof(s_backup_password));
    s_backup_credentials_valid = false;
}

static void preserve_saved_credentials(void)
{
    if (s_backup_credentials_valid || !s_have_saved_credentials) {
        return;
    }
    strlcpy(s_backup_ssid, s_pending_ssid, sizeof(s_backup_ssid));
    strlcpy(s_backup_password, s_pending_password,
            sizeof(s_backup_password));
    s_backup_credentials_valid = true;
}

static esp_err_t connect_pending(bool reset_retry_count)
{
    cancel_retry_timer();

    wifi_config_t station = {0};
    size_t ssid_length =
        strnlen(s_pending_ssid, sizeof(s_pending_ssid));
    size_t password_length =
        strnlen(s_pending_password, sizeof(s_pending_password));
    /*
     * ESP-IDF's station fields are exactly 32 and 64 bytes. Maximum-length
     * values intentionally have no trailing NUL in the driver structure;
     * strlcpy() would truncate otherwise-valid 32-byte SSIDs and raw PSKs.
     */
    memcpy(station.sta.ssid, s_pending_ssid, ssid_length);
    memcpy(station.sta.password, s_pending_password, password_length);
    station.sta.threshold.authmode =
        s_pending_password[0] ? WIFI_AUTH_WPA2_PSK : WIFI_AUTH_OPEN;
    station.sta.pmf_cfg.capable = true;
    station.sta.pmf_cfg.required = false;

    esp_err_t err = esp_wifi_set_config(WIFI_IF_STA, &station);
    nh_secure_zero(&station, sizeof(station));
    if (err != ESP_OK) {
        return err;
    }

    if (reset_retry_count) {
        s_retry_count = 0;
    }
    s_should_reconnect = true;
    set_state(NH_NETWORK_CONNECTING, ESP_OK);
    return esp_wifi_connect();
}

static esp_err_t start_scan(void)
{
    cancel_retry_timer();
    s_scan_return_connected =
        s_snapshot.connected_ssid[0] != '\0' &&
        s_snapshot.ip_address[0] != '\0';
    if (!s_scan_return_connected) {
        s_should_reconnect = false;
    }

    wifi_scan_config_t scan = {
        .show_hidden = false,
        .scan_type = WIFI_SCAN_TYPE_ACTIVE,
    };
    s_snapshot.access_point_count = 0;
    set_state(NH_NETWORK_SCANNING, ESP_OK);
    esp_err_t err = esp_wifi_scan_start(&scan, false);
    if (err != ESP_OK) {
        set_state(s_scan_return_connected ? NH_NETWORK_CONNECTED
                                          : NH_NETWORK_ERROR,
                  err);
    }
    return err;
}

static esp_err_t start_connection(const nh_network_command_t *command)
{
    /*
     * Keep the last persisted network available until the replacement has
     * obtained an address. Multiple edits to an unverified profile must not
     * overwrite that rollback point.
     */
    if (!s_profile_unverified) {
        clear_backup_credentials();
        preserve_saved_credentials();
    }
    nh_secure_zero(s_pending_password, sizeof(s_pending_password));
    strlcpy(s_pending_ssid, command->ssid, sizeof(s_pending_ssid));
    strlcpy(s_pending_password, command->password,
            sizeof(s_pending_password));
    s_profile_unverified = true;
    s_should_reconnect = true;
    cancel_retry_timer();

    bool transport_active =
        s_snapshot.state == NH_NETWORK_CONNECTED ||
        s_snapshot.state == NH_NETWORK_CONNECTING ||
        s_snapshot.connected_ssid[0] != '\0';
    if (!transport_active) {
        return connect_pending(true);
    }

    /*
     * ESP Wi-Fi disconnect is asynchronous. Wait for its event before setting
     * the new station profile; issuing connect here races the old transport.
     */
    s_connect_after_disconnect = true;
    set_state(NH_NETWORK_CONNECTING, ESP_OK);
    esp_err_t err = esp_wifi_disconnect();
    if (err == ESP_ERR_WIFI_NOT_CONNECT) {
        s_connect_after_disconnect = false;
        return connect_pending(true);
    }
    if (err != ESP_OK) {
        s_connect_after_disconnect = false;
    }
    return err;
}

static void handle_scan_complete(void)
{
    uint16_t found = 0;
    esp_err_t err = esp_wifi_scan_get_ap_num(&found);
    if (err != ESP_OK) {
        set_state(s_scan_return_connected ? NH_NETWORK_CONNECTED
                                          : NH_NETWORK_ERROR,
                  err);
        return;
    }

    uint16_t requested = found;
    if (requested > NH_NETWORK_MAX_ACCESS_POINTS) {
        requested = NH_NETWORK_MAX_ACCESS_POINTS;
    }

    wifi_ap_record_t records[NH_NETWORK_MAX_ACCESS_POINTS] = {0};
    err = esp_wifi_scan_get_ap_records(&requested, records);
    if (err != ESP_OK) {
        set_state(s_scan_return_connected ? NH_NETWORK_CONNECTED
                                          : NH_NETWORK_ERROR,
                  err);
        return;
    }

    s_snapshot.access_point_count = (uint8_t)requested;
    for (uint16_t i = 0; i < requested; ++i) {
        nh_access_point_t *access_point = &s_snapshot.access_points[i];
        strlcpy(access_point->ssid, (const char *)records[i].ssid,
                sizeof(access_point->ssid));
        access_point->rssi = records[i].rssi;
        access_point->secured = records[i].authmode != WIFI_AUTH_OPEN;
    }
    if (s_scan_return_connected) {
        s_should_reconnect = true;
        set_state(NH_NETWORK_CONNECTED, ESP_OK);
    } else {
        set_state(NH_NETWORK_READY, ESP_OK);
    }
}

static bool authentication_failure(uint16_t reason)
{
    return reason == WIFI_REASON_AUTH_FAIL ||
           reason == WIFI_REASON_4WAY_HANDSHAKE_TIMEOUT ||
           reason == WIFI_REASON_HANDSHAKE_TIMEOUT ||
           reason == WIFI_REASON_NO_AP_FOUND_W_COMPATIBLE_SECURITY ||
           reason == WIFI_REASON_NO_AP_FOUND_IN_AUTHMODE_THRESHOLD;
}

static void retry_timer_cb(void *arg)
{
    (void)arg;
    const nh_network_command_t command = {
        .type = NH_NETWORK_EVENT_RETRY,
    };
    if (xQueueSend(s_command_queue, &command, 0) != pdTRUE) {
        ESP_LOGE(TAG, "Dropped Wi-Fi retry event: command queue full");
    }
}

static void schedule_retry(uint16_t reason)
{
    cancel_retry_timer();
    if (!s_should_reconnect) {
        set_state(NH_NETWORK_READY, ESP_FAIL);
        return;
    }

    if (s_profile_unverified &&
        s_retry_count + 1U >= NH_NETWORK_UNVERIFIED_MAX_ATTEMPTS) {
        if (s_backup_credentials_valid) {
            strlcpy(s_pending_ssid, s_backup_ssid,
                    sizeof(s_pending_ssid));
            nh_secure_zero(s_pending_password, sizeof(s_pending_password));
            strlcpy(s_pending_password, s_backup_password,
                    sizeof(s_pending_password));
            s_profile_unverified = false;
            clear_backup_credentials();
            ESP_LOGW(TAG,
                     "Unverified Wi-Fi profile rejected; restoring saved network");
            esp_err_t restore_err = connect_pending(true);
            if (restore_err != ESP_OK) {
                set_state(NH_NETWORK_ERROR, restore_err);
            }
            return;
        }
        s_should_reconnect = false;
        set_state(NH_NETWORK_READY,
                  authentication_failure(reason)
                      ? ESP_ERR_WIFI_PASSWORD
                      : ESP_FAIL);
        ESP_LOGW(TAG, "Unverified Wi-Fi profile stopped after %u attempts",
                 NH_NETWORK_UNVERIFIED_MAX_ATTEMPTS);
        return;
    }

    uint32_t shift = s_retry_count < 5 ? s_retry_count : 5;
    uint32_t delay_ms = NH_NETWORK_RETRY_INITIAL_MS << shift;
    if (delay_ms > NH_NETWORK_RETRY_MAX_MS) {
        delay_ms = NH_NETWORK_RETRY_MAX_MS;
    }
    if (s_retry_count < UINT8_MAX) {
        ++s_retry_count;
    }

    s_snapshot.reconnect_delay_ms = delay_ms;
    set_state(NH_NETWORK_CONNECTING, ESP_OK);
    s_retry_deadline_us =
        esp_timer_get_time() + (int64_t)delay_ms * 1000;
    esp_err_t err =
        esp_timer_start_once(s_retry_timer, (uint64_t)delay_ms * 1000U);
    if (err != ESP_OK) {
        s_retry_deadline_us = 0;
        s_snapshot.reconnect_delay_ms = 0;
        set_state(NH_NETWORK_ERROR, err);
    }
}

static void clear_connection_snapshot(uint16_t reason)
{
    s_snapshot.connected_ssid[0] = '\0';
    s_snapshot.ip_address[0] = '\0';
    s_snapshot.rssi = 0;
    s_snapshot.last_disconnect_reason = reason;
}

static void handle_disconnected(uint16_t reason)
{
    clear_connection_snapshot(reason);
    if (s_connect_after_disconnect) {
        s_connect_after_disconnect = false;
        esp_err_t err = connect_pending(true);
        if (err != ESP_OK) {
            set_state(NH_NETWORK_ERROR, err);
        }
        return;
    }
    schedule_retry(reason);
}

static void handle_got_ip(const nh_network_command_t *command)
{
    if (s_connect_after_disconnect) {
        ESP_LOGW(TAG, "Ignoring address from superseded Wi-Fi profile");
        return;
    }

    strlcpy(s_snapshot.connected_ssid, s_pending_ssid,
            sizeof(s_snapshot.connected_ssid));
    snprintf(s_snapshot.ip_address, sizeof(s_snapshot.ip_address),
             IPSTR, IP2STR(&command->ip_info.ip));

    wifi_ap_record_t current = {0};
    if (esp_wifi_sta_get_ap_info(&current) == ESP_OK) {
        s_snapshot.rssi = current.rssi;
    }

    cancel_retry_timer();
    s_retry_count = 0;
    s_should_reconnect = true;
    s_snapshot.last_disconnect_reason = 0;
    if (s_sntp_initialized) {
        esp_err_t time_err = esp_netif_sntp_start();
        if (time_err != ESP_OK) {
            ESP_LOGW(TAG, "Could not start network time sync: %s",
                     esp_err_to_name(time_err));
        }
    }
    if (s_profile_unverified) {
        esp_err_t err = save_credentials();
        if (err == ESP_OK) {
            s_have_saved_credentials = true;
            clear_backup_credentials();
            ESP_LOGI(TAG, "Validated Wi-Fi profile persisted");
        } else {
            ESP_LOGW(TAG, "Could not persist validated Wi-Fi profile: %s",
                     esp_err_to_name(err));
        }
        s_profile_unverified = false;
    }

    ESP_LOGI(TAG, "Wi-Fi connected: %s at %s",
             s_snapshot.connected_ssid, s_snapshot.ip_address);
    set_state(NH_NETWORK_CONNECTED, ESP_OK);
}

static void network_worker_task(void *arg)
{
    (void)arg;
    nh_network_command_t command;

    while (true) {
        if (xQueueReceive(s_command_queue, &command, portMAX_DELAY) != pdTRUE) {
            continue;
        }

        esp_err_t err = ESP_OK;
        switch (command.type) {
        case NH_NETWORK_COMMAND_SCAN:
            err = start_scan();
            break;
        case NH_NETWORK_COMMAND_CONNECT:
            err = start_connection(&command);
            break;
        case NH_NETWORK_EVENT_STARTED:
            if (s_have_saved_credentials) {
                s_profile_unverified = false;
                err = connect_pending(true);
            } else {
                err = start_scan();
            }
            break;
        case NH_NETWORK_EVENT_SCAN_DONE:
            handle_scan_complete();
            break;
        case NH_NETWORK_EVENT_DISCONNECTED:
            handle_disconnected(command.disconnect_reason);
            break;
        case NH_NETWORK_EVENT_GOT_IP:
            handle_got_ip(&command);
            break;
        case NH_NETWORK_EVENT_RETRY:
            /*
             * esp_timer_stop() cannot retract a callback that has already
             * queued its event. A cancelled retry must never connect an old
             * profile or prematurely fire a newer backoff interval.
             */
            if (s_retry_deadline_us == 0 ||
                esp_timer_get_time() < s_retry_deadline_us) {
                ESP_LOGD(TAG, "Ignored stale Wi-Fi retry event");
                break;
            }
            s_retry_deadline_us = 0;
            s_snapshot.reconnect_delay_ms = 0;
            set_state(NH_NETWORK_CONNECTING, ESP_OK);
            err = esp_wifi_connect();
            break;
        default:
            err = ESP_ERR_INVALID_ARG;
            break;
        }

        nh_secure_zero(command.password, sizeof(command.password));
        if (err != ESP_OK) {
            set_state(NH_NETWORK_ERROR, err);
        }
    }
}

static void enqueue_driver_event(nh_network_command_type_t type,
                                 const void *event_data)
{
    nh_network_command_t command = {
        .type = type,
    };
    if (type == NH_NETWORK_EVENT_DISCONNECTED && event_data) {
        const wifi_event_sta_disconnected_t *disconnected = event_data;
        command.disconnect_reason = disconnected->reason;
    } else if (type == NH_NETWORK_EVENT_GOT_IP && event_data) {
        const ip_event_got_ip_t *got_ip = event_data;
        command.ip_info = got_ip->ip_info;
    }
    if (xQueueSend(s_command_queue, &command, 0) != pdTRUE) {
        ESP_LOGE(TAG, "Dropped Wi-Fi driver event %d: command queue full",
                 (int)type);
    }
}

static void network_event_handler(void *arg, esp_event_base_t event_base,
                                  int32_t event_id, void *event_data)
{
    (void)arg;
    if (event_base == WIFI_EVENT) {
        switch (event_id) {
        case WIFI_EVENT_STA_START:
            enqueue_driver_event(NH_NETWORK_EVENT_STARTED, NULL);
            break;
        case WIFI_EVENT_SCAN_DONE:
            enqueue_driver_event(NH_NETWORK_EVENT_SCAN_DONE, NULL);
            break;
        case WIFI_EVENT_STA_DISCONNECTED:
            enqueue_driver_event(NH_NETWORK_EVENT_DISCONNECTED, event_data);
            break;
        default:
            break;
        }
    } else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP) {
        enqueue_driver_event(NH_NETWORK_EVENT_GOT_IP, event_data);
    }
}

esp_err_t nh_network_scan(void)
{
    if (!s_initialized || !s_command_queue) {
        return ESP_ERR_INVALID_STATE;
    }

    const nh_network_command_t command = {
        .type = NH_NETWORK_COMMAND_SCAN,
    };
    return xQueueSend(s_command_queue, &command, 0) == pdTRUE
               ? ESP_OK
               : ESP_ERR_TIMEOUT;
}

esp_err_t nh_network_connect(const char *ssid, const char *password)
{
    if (!s_initialized || !s_command_queue || !ssid || ssid[0] == '\0') {
        return ESP_ERR_INVALID_ARG;
    }

    if (!valid_credentials(ssid, password ? password : "")) {
        return ESP_ERR_INVALID_ARG;
    }

    nh_network_command_t command = {
        .type = NH_NETWORK_COMMAND_CONNECT,
    };
    strlcpy(command.ssid, ssid, sizeof(command.ssid));
    strlcpy(command.password, password ? password : "",
            sizeof(command.password));
    BaseType_t queued = xQueueSend(s_command_queue, &command, 0);
    nh_secure_zero(command.password, sizeof(command.password));
    return queued == pdTRUE ? ESP_OK : ESP_ERR_TIMEOUT;
}

esp_err_t nh_network_init(const nh_network_config_t *config)
{
    if (s_initialized) {
        return ESP_ERR_INVALID_STATE;
    }

    memset(&s_snapshot, 0, sizeof(s_snapshot));
    if (config) {
        s_config = *config;
    }
    set_state(NH_NETWORK_INITIALIZING, ESP_OK);

    ESP_RETURN_ON_ERROR(esp_netif_init(), TAG, "network interface init");
    esp_err_t err = esp_event_loop_create_default();
    if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) {
        return err;
    }

    s_station_netif = esp_netif_create_default_wifi_sta();
    ESP_RETURN_ON_FALSE(s_station_netif, ESP_ERR_NO_MEM, TAG,
                        "station network interface");

    /*
     * The printer presents a CA-signed local certificate. Start time sync
     * before MQTT begins so certificate validity is never intentionally
     * bypassed.
     */
    esp_sntp_config_t time_config =
        ESP_NETIF_SNTP_DEFAULT_CONFIG("pool.ntp.org");
    /*
     * Starting SNTP before DHCP can leave the header clock unsynchronized for
     * an entire retry interval. Initialize it now and start/restart it on each
     * GOT_IP event, when DNS and the default route are actually available.
     */
    time_config.start = false;
    err = esp_netif_sntp_init(&time_config);
    if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) {
        ESP_LOGW(TAG, "Could not start network time sync: %s",
                 esp_err_to_name(err));
    } else {
        s_sntp_initialized = true;
    }

    s_command_queue =
        xQueueCreate(NH_NETWORK_COMMAND_QUEUE_DEPTH,
                     sizeof(nh_network_command_t));
    ESP_RETURN_ON_FALSE(s_command_queue, ESP_ERR_NO_MEM, TAG,
                        "network command queue");

    const esp_timer_create_args_t retry_timer_config = {
        .callback = retry_timer_cb,
        .name = "nh_wifi_retry",
    };
    ESP_RETURN_ON_ERROR(esp_timer_create(&retry_timer_config, &s_retry_timer),
                        TAG, "Wi-Fi retry timer");

    BaseType_t task_created =
        xTaskCreate(network_worker_task, "nh_wifi_worker",
                    NH_NETWORK_WORKER_STACK_SIZE, NULL,
                    NH_NETWORK_WORKER_PRIORITY, NULL);
    ESP_RETURN_ON_FALSE(task_created == pdPASS, ESP_ERR_NO_MEM, TAG,
                        "network worker task");

    wifi_init_config_t wifi_config = WIFI_INIT_CONFIG_DEFAULT();
    ESP_RETURN_ON_ERROR(esp_wifi_init(&wifi_config), TAG, "hosted Wi-Fi init");
    ESP_RETURN_ON_ERROR(
        esp_event_handler_register(WIFI_EVENT, ESP_EVENT_ANY_ID,
                                   network_event_handler, NULL),
        TAG, "Wi-Fi event handler");
    ESP_RETURN_ON_ERROR(
        esp_event_handler_register(IP_EVENT, IP_EVENT_STA_GOT_IP,
                                   network_event_handler, NULL),
        TAG, "IP event handler");
    ESP_RETURN_ON_ERROR(esp_wifi_set_storage(WIFI_STORAGE_RAM),
                        TAG, "Wi-Fi storage");
    ESP_RETURN_ON_ERROR(esp_wifi_set_mode(WIFI_MODE_STA), TAG, "station mode");

    err = load_credentials();
    s_have_saved_credentials = err == ESP_OK;
    if (err != ESP_OK && err != ESP_ERR_NOT_FOUND &&
        err != ESP_ERR_NVS_NOT_FOUND) {
        ESP_LOGW(TAG, "Could not load saved Wi-Fi profile: %s",
                 esp_err_to_name(err));
        nh_secure_zero(s_pending_password, sizeof(s_pending_password));
        s_pending_ssid[0] = '\0';
    }

    s_initialized = true;
    err = esp_wifi_start();
    if (err != ESP_OK) {
        s_initialized = false;
        set_state(NH_NETWORK_ERROR, err);
        return err;
    }

    ESP_LOGI(TAG, "ESP32-C6 hosted Wi-Fi starting over SDIO");
    return ESP_OK;
}
