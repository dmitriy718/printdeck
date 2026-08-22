#include "nh_ai.h"

#include <ctype.h>
#include <string.h>

static bool bounded_text(const char *text, size_t capacity)
{
    if (!text) {
        return false;
    }
    size_t length = 0;
    while (length < capacity && text[length]) {
        length++;
    }
    if (length == 0 || length >= capacity) {
        return false;
    }
    for (size_t i = 0; i < length; ++i) {
        unsigned char value = (unsigned char)text[i];
        if (value < 0x20 || value == 0x7f || value == '|') {
            return false;
        }
    }
    return true;
}

bool nh_ai_event_valid(const nh_ai_signed_event_t *event)
{
    if (!event || event->schema != NH_AI_SCHEMA ||
        event->sequence == 0 ||
        event->timestamp_epoch < 1700000000 ||
        event->confidence_milli > 1000 ||
        event->type <= NH_AI_EVENT_UNKNOWN ||
        event->type > NH_AI_EVENT_CAMERA_BLOCKED ||
        event->suggestion > NH_AI_SUGGEST_PAUSE ||
        !bounded_text(event->printer_id, sizeof(event->printer_id)) ||
        !bounded_text(event->job_id, sizeof(event->job_id)) ||
        !bounded_text(event->model_version, sizeof(event->model_version)) ||
        strlen(event->evidence_sha256) != NH_AI_EVIDENCE_HASH_LENGTH) {
        return false;
    }
    for (size_t i = 0; i < NH_AI_EVIDENCE_HASH_LENGTH; ++i) {
        if (!isxdigit((unsigned char)event->evidence_sha256[i])) {
            return false;
        }
    }
    return true;
}

bool nh_ai_temporal_actionable(const nh_ai_signed_event_t *events,
                               size_t count)
{
    if (!events || count < 3) {
        return false;
    }
    const nh_ai_signed_event_t *last = &events[count - 1];
    uint32_t confidence = 0;
    for (size_t i = count - 3; i < count; ++i) {
        if (events[i].type != last->type ||
            strcmp(events[i].job_id, last->job_id) != 0) {
            return false;
        }
        confidence += events[i].confidence_milli;
    }
    return confidence >= 3u * 850u;
}

const char *nh_ai_event_label(nh_ai_event_type_t type)
{
    switch (type) {
    case NH_AI_EVENT_SPAGHETTI:
        return "Spaghetti";
    case NH_AI_EVENT_DETACHMENT:
        return "Part detachment";
    case NH_AI_EVENT_LAYER_SHIFT:
        return "Layer shift";
    case NH_AI_EVENT_CAMERA_BLOCKED:
        return "Camera blocked";
    case NH_AI_EVENT_UNKNOWN:
    default:
        return "Unknown";
    }
}
