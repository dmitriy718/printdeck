#include <assert.h>
#include <stdio.h>
#include <string.h>

#include "nh_ai.h"

static nh_ai_signed_event_t event(uint64_t sequence, uint16_t confidence)
{
    nh_ai_signed_event_t value = {
        .schema = NH_AI_SCHEMA,
        .sequence = sequence,
        .timestamp_epoch = 1800000000,
        .confidence_milli = confidence,
        .type = NH_AI_EVENT_SPAGHETTI,
        .suggestion = NH_AI_SUGGEST_NOTIFY,
    };
    strcpy(value.printer_id, "printer-1");
    strcpy(value.job_id, "job-1");
    strcpy(value.model_version, "local-test-v1");
    memset(value.evidence_sha256, 'a', NH_AI_EVIDENCE_HASH_LENGTH);
    value.evidence_sha256[NH_AI_EVIDENCE_HASH_LENGTH] = '\0';
    return value;
}

static void test_event_validation(void)
{
    nh_ai_signed_event_t value = event(1, 900);
    assert(nh_ai_event_valid(&value));
    value.confidence_milli = 1001;
    assert(!nh_ai_event_valid(&value));
    value = event(0, 900);
    assert(!nh_ai_event_valid(&value));
    value = event(1, 900);
    value.evidence_sha256[4] = 'z';
    assert(!nh_ai_event_valid(&value));
    value = event(1, 900);
    value.job_id[3] = '|';
    assert(!nh_ai_event_valid(&value));
}

static void test_temporal_smoothing(void)
{
    nh_ai_signed_event_t values[3] = {
        event(1, 850), event(2, 900), event(3, 950),
    };
    assert(!nh_ai_temporal_actionable(values, 2));
    assert(nh_ai_temporal_actionable(values, 3));
    values[1].type = NH_AI_EVENT_DETACHMENT;
    assert(!nh_ai_temporal_actionable(values, 3));
    values[1] = event(2, 600);
    assert(!nh_ai_temporal_actionable(values, 3));
}

int main(void)
{
    test_event_validation();
    test_temporal_smoothing();
    puts("AI policy tests passed (2 groups)");
    return 0;
}
