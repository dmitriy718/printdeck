#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

enum {
    NH_AI_SCHEMA = 1,
    NH_AI_EVENT_MAX = 16,
    NH_AI_KEY_BYTES = 32,
    NH_AI_ID_LENGTH = 48,
    NH_AI_MODEL_LENGTH = 32,
    NH_AI_EVIDENCE_HASH_LENGTH = 64,
};

typedef enum {
    NH_AI_EVENT_UNKNOWN = 0,
    NH_AI_EVENT_SPAGHETTI,
    NH_AI_EVENT_DETACHMENT,
    NH_AI_EVENT_LAYER_SHIFT,
    NH_AI_EVENT_CAMERA_BLOCKED,
} nh_ai_event_type_t;

typedef enum {
    NH_AI_SUGGEST_NOTIFY = 0,
    NH_AI_SUGGEST_PAUSE,
} nh_ai_suggestion_t;

typedef enum {
    NH_AI_LABEL_UNREVIEWED = 0,
    NH_AI_LABEL_TRUE_POSITIVE,
    NH_AI_LABEL_FALSE_POSITIVE,
} nh_ai_label_t;

typedef struct {
    uint16_t schema;
    uint64_t sequence;
    int64_t timestamp_epoch;
    char printer_id[NH_AI_ID_LENGTH];
    char job_id[NH_AI_ID_LENGTH];
    char model_version[NH_AI_MODEL_LENGTH];
    char evidence_sha256[NH_AI_EVIDENCE_HASH_LENGTH + 1];
    uint16_t confidence_milli;
    nh_ai_event_type_t type;
    nh_ai_suggestion_t suggestion;
} nh_ai_signed_event_t;

typedef struct {
    nh_ai_signed_event_t event;
    nh_ai_label_t label;
    bool actionable;
    bool muted;
} nh_ai_audit_event_t;

typedef struct {
    nh_ai_audit_event_t events[NH_AI_EVENT_MAX];
    uint8_t event_count;
    uint8_t actionable_count;
    uint64_t last_sequence;
    bool configured;
    bool local_only;
    bool notify_only;
    bool auto_pause_enabled;
    bool camera_healthy;
} nh_ai_snapshot_t;

bool nh_ai_event_valid(const nh_ai_signed_event_t *event);
bool nh_ai_temporal_actionable(const nh_ai_signed_event_t *events,
                               size_t count);
esp_err_t nh_ai_init(const uint8_t shared_key[NH_AI_KEY_BYTES]);
esp_err_t nh_ai_ingest(const nh_ai_signed_event_t *event,
                       const uint8_t signature[NH_AI_KEY_BYTES]);
esp_err_t nh_ai_snapshot(nh_ai_snapshot_t *snapshot);
esp_err_t nh_ai_label(uint64_t sequence, nh_ai_label_t label);
esp_err_t nh_ai_mute_job(const char *job_id, bool muted);
esp_err_t nh_ai_set_camera_healthy(bool healthy);
esp_err_t nh_ai_enable_auto_pause(bool enable,
                                  bool qualified_pause_capability,
                                  const char *confirmation);
esp_err_t nh_ai_sign_for_test(const nh_ai_signed_event_t *event,
                              uint8_t signature[NH_AI_KEY_BYTES]);
void nh_ai_deinit(void);
const char *nh_ai_event_label(nh_ai_event_type_t type);

#ifdef __cplusplus
}
#endif
