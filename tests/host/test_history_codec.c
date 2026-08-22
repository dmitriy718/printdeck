#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "nh_history_codec.h"

static void test_seal_and_validate(void)
{
    nh_history_disk_record_t record = {
        .sequence = 7,
        .timestamp_epoch = 1770000000,
        .duration_seconds = 3600,
        .event_type = NH_HISTORY_EVENT_FINISH,
        .outcome = 1,
        .maximum_progress_percent = 100,
    };
    strcpy(record.text, "Calibration cube");
    nh_history_record_seal(&record);
    assert(record.magic == NH_HISTORY_DISK_MAGIC);
    assert(record.schema == NH_HISTORY_DISK_SCHEMA);
    assert(record.record_size == sizeof(record));
    assert(nh_history_record_valid(&record));
}

static void test_corruption_fails_closed(void)
{
    nh_history_disk_record_t record = {
        .sequence = 1,
        .event_type = NH_HISTORY_EVENT_START,
    };
    strcpy(record.text, "Bracket");
    nh_history_record_seal(&record);
    record.text[2] ^= 0x20;
    assert(!nh_history_record_valid(&record));

    record.text[2] ^= 0x20;
    assert(nh_history_record_valid(&record));
    record.schema++;
    assert(!nh_history_record_valid(&record));
}

static void test_invalid_structure_is_rejected(void)
{
    nh_history_disk_record_t record = {
        .sequence = 0,
        .event_type = NH_HISTORY_EVENT_FINISH,
    };
    nh_history_record_seal(&record);
    assert(!nh_history_record_valid(&record));

    record.sequence = 1;
    record.event_type = 99;
    nh_history_record_seal(&record);
    assert(!nh_history_record_valid(&record));

    record.event_type = NH_HISTORY_EVENT_FINISH;
    memset(record.text, 'A', sizeof(record.text));
    nh_history_record_seal(&record);
    assert(!nh_history_record_valid(&record));
}

int main(void)
{
    test_seal_and_validate();
    test_corruption_fails_closed();
    test_invalid_structure_is_rejected();
    puts("nh_history_codec host tests: PASS (3 cases)");
    return 0;
}
