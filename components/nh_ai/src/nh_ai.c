#include "nh_ai.h"

#include <inttypes.h>
#include <stdio.h>
#include <string.h>
#include <time.h>

#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "nh_core.h"
#include "psa/crypto.h"

enum {
    NH_AI_CLOCK_SKEW_SECONDS = 120,
    NH_AI_COOLDOWN_SECONDS = 300,
};

static SemaphoreHandle_t s_mutex;
static uint8_t s_key[NH_AI_KEY_BYTES];
static nh_ai_snapshot_t s_state;
static char s_muted_job[NH_AI_ID_LENGTH];
static int64_t s_last_action_epoch;
static bool s_initialized;

static bool canonical(const nh_ai_signed_event_t *event,
                      char *output, size_t capacity)
{
    int length = snprintf(
        output, capacity,
        "%u|%" PRIu64 "|%" PRId64 "|%s|%s|%s|%s|%u|%u|%u",
        (unsigned)event->schema, event->sequence, event->timestamp_epoch,
        event->printer_id, event->job_id, event->model_version,
        event->evidence_sha256, (unsigned)event->confidence_milli,
        (unsigned)event->type, (unsigned)event->suggestion);
    return length > 0 && length < (int)capacity;
}

static esp_err_t sign_event(const nh_ai_signed_event_t *event,
                            uint8_t signature[NH_AI_KEY_BYTES])
{
    char message[320];
    if (!nh_ai_event_valid(event) ||
        !canonical(event, message, sizeof(message))) {
        return ESP_ERR_INVALID_ARG;
    }
    psa_key_attributes_t attributes = PSA_KEY_ATTRIBUTES_INIT;
    psa_set_key_usage_flags(
        &attributes, PSA_KEY_USAGE_SIGN_MESSAGE);
    psa_set_key_algorithm(
        &attributes, PSA_ALG_HMAC(PSA_ALG_SHA_256));
    psa_set_key_type(&attributes, PSA_KEY_TYPE_HMAC);
    psa_set_key_bits(&attributes, NH_AI_KEY_BYTES * 8);
    psa_key_id_t key_id = 0;
    psa_status_t status = psa_crypto_init();
    if (status == PSA_SUCCESS) {
        status = psa_import_key(
            &attributes, s_key, sizeof(s_key), &key_id);
    }
    psa_reset_key_attributes(&attributes);
    size_t signature_length = 0;
    if (status == PSA_SUCCESS) {
        status = psa_mac_compute(
            key_id, PSA_ALG_HMAC(PSA_ALG_SHA_256),
            (const uint8_t *)message, strlen(message),
            signature, NH_AI_KEY_BYTES, &signature_length);
    }
    if (key_id != 0) {
        (void)psa_destroy_key(key_id);
    }
    if (status != PSA_SUCCESS ||
        signature_length != NH_AI_KEY_BYTES) {
        nh_secure_zero(message, sizeof(message));
        return ESP_FAIL;
    }
    nh_secure_zero(message, sizeof(message));
    return ESP_OK;
}

esp_err_t nh_ai_init(const uint8_t shared_key[NH_AI_KEY_BYTES])
{
    if (s_initialized || !shared_key) {
        return ESP_ERR_INVALID_ARG;
    }
    uint8_t aggregate = 0;
    for (size_t i = 0; i < NH_AI_KEY_BYTES; ++i) {
        aggregate |= shared_key[i];
    }
    if (aggregate == 0) {
        return ESP_ERR_INVALID_ARG;
    }
    s_mutex = xSemaphoreCreateMutex();
    if (!s_mutex) {
        return ESP_ERR_NO_MEM;
    }
    memcpy(s_key, shared_key, sizeof(s_key));
    memset(&s_state, 0, sizeof(s_state));
    s_state.configured = true;
    s_state.local_only = true;
    s_state.notify_only = true;
    s_initialized = true;
    return ESP_OK;
}

esp_err_t nh_ai_sign_for_test(const nh_ai_signed_event_t *event,
                              uint8_t signature[NH_AI_KEY_BYTES])
{
    if (!s_initialized || !signature) {
        return ESP_ERR_INVALID_STATE;
    }
    return sign_event(event, signature);
}

esp_err_t nh_ai_ingest(const nh_ai_signed_event_t *event,
                       const uint8_t signature[NH_AI_KEY_BYTES])
{
    if (!s_initialized || !event || !signature ||
        !nh_ai_event_valid(event)) {
        return ESP_ERR_INVALID_ARG;
    }
    uint8_t expected[NH_AI_KEY_BYTES];
    esp_err_t err = sign_event(event, expected);
    unsigned difference = 0;
    for (size_t i = 0; i < sizeof(expected); ++i) {
        difference |= expected[i] ^ signature[i];
    }
    nh_secure_zero(expected, sizeof(expected));
    if (err != ESP_OK || difference != 0) {
        return ESP_ERR_INVALID_CRC;
    }
    time_t now = time(NULL);
    if (now >= 1700000000 &&
        (event->timestamp_epoch < now - NH_AI_CLOCK_SKEW_SECONDS ||
         event->timestamp_epoch > now + NH_AI_CLOCK_SKEW_SECONDS)) {
        return ESP_ERR_INVALID_STATE;
    }

    (void)xSemaphoreTake(s_mutex, portMAX_DELAY);
    if (event->sequence <= s_state.last_sequence) {
        (void)xSemaphoreGive(s_mutex);
        return ESP_ERR_INVALID_STATE;
    }
    if (s_state.event_count == NH_AI_EVENT_MAX) {
        memmove(&s_state.events[0], &s_state.events[1],
                sizeof(s_state.events[0]) * (NH_AI_EVENT_MAX - 1));
        s_state.event_count--;
    }
    nh_ai_audit_event_t *audit =
        &s_state.events[s_state.event_count++];
    *audit = (nh_ai_audit_event_t){
        .event = *event,
        .label = NH_AI_LABEL_UNREVIEWED,
        .muted = strcmp(event->job_id, s_muted_job) == 0,
    };
    nh_ai_signed_event_t recent[3];
    size_t recent_count = s_state.event_count < 3 ? s_state.event_count : 3;
    for (size_t i = 0; i < recent_count; ++i) {
        recent[i] =
            s_state.events[s_state.event_count - recent_count + i].event;
    }
    bool cooldown_ready =
        event->timestamp_epoch >=
        s_last_action_epoch + NH_AI_COOLDOWN_SECONDS;
    audit->actionable =
        !audit->muted && s_state.camera_healthy && cooldown_ready &&
        nh_ai_temporal_actionable(recent, recent_count);
    if (audit->actionable) {
        s_state.actionable_count++;
        s_last_action_epoch = event->timestamp_epoch;
    }
    s_state.last_sequence = event->sequence;
    (void)xSemaphoreGive(s_mutex);
    return ESP_OK;
}

esp_err_t nh_ai_snapshot(nh_ai_snapshot_t *snapshot)
{
    if (!s_initialized || !snapshot) {
        return ESP_ERR_INVALID_STATE;
    }
    (void)xSemaphoreTake(s_mutex, portMAX_DELAY);
    *snapshot = s_state;
    (void)xSemaphoreGive(s_mutex);
    return ESP_OK;
}

esp_err_t nh_ai_label(uint64_t sequence, nh_ai_label_t label)
{
    if (!s_initialized || sequence == 0 ||
        label == NH_AI_LABEL_UNREVIEWED ||
        label > NH_AI_LABEL_FALSE_POSITIVE) {
        return ESP_ERR_INVALID_ARG;
    }
    (void)xSemaphoreTake(s_mutex, portMAX_DELAY);
    for (uint8_t i = 0; i < s_state.event_count; ++i) {
        if (s_state.events[i].event.sequence == sequence) {
            s_state.events[i].label = label;
            (void)xSemaphoreGive(s_mutex);
            return ESP_OK;
        }
    }
    (void)xSemaphoreGive(s_mutex);
    return ESP_ERR_NOT_FOUND;
}

esp_err_t nh_ai_mute_job(const char *job_id, bool muted)
{
    if (!s_initialized || !job_id ||
        job_id[0] == '\0' ||
        strnlen(job_id, sizeof(s_muted_job)) >= sizeof(s_muted_job)) {
        return ESP_ERR_INVALID_ARG;
    }
    (void)xSemaphoreTake(s_mutex, portMAX_DELAY);
    if (muted) {
        strlcpy(s_muted_job, job_id, sizeof(s_muted_job));
    } else if (strcmp(s_muted_job, job_id) == 0) {
        s_muted_job[0] = '\0';
    }
    (void)xSemaphoreGive(s_mutex);
    return ESP_OK;
}

esp_err_t nh_ai_set_camera_healthy(bool healthy)
{
    if (!s_initialized) {
        return ESP_ERR_INVALID_STATE;
    }
    (void)xSemaphoreTake(s_mutex, portMAX_DELAY);
    s_state.camera_healthy = healthy;
    (void)xSemaphoreGive(s_mutex);
    return ESP_OK;
}

esp_err_t nh_ai_enable_auto_pause(bool enable,
                                  bool qualified_pause_capability,
                                  const char *confirmation)
{
    if (!s_initialized) {
        return ESP_ERR_INVALID_STATE;
    }
    if (enable &&
        (!qualified_pause_capability || !confirmation ||
         strcmp(confirmation, "ENABLE AUTO PAUSE") != 0)) {
        return ESP_ERR_NOT_SUPPORTED;
    }
    (void)xSemaphoreTake(s_mutex, portMAX_DELAY);
    s_state.auto_pause_enabled = enable;
    s_state.notify_only = !enable;
    (void)xSemaphoreGive(s_mutex);
    return ESP_OK;
}

void nh_ai_deinit(void)
{
    if (!s_initialized) {
        return;
    }
    nh_secure_zero(s_key, sizeof(s_key));
    memset(&s_state, 0, sizeof(s_state));
    memset(s_muted_job, 0, sizeof(s_muted_job));
    vSemaphoreDelete(s_mutex);
    s_mutex = NULL;
    s_initialized = false;
}
