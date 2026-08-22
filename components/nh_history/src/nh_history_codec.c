#include "nh_history_codec.h"

#include <stddef.h>

uint32_t nh_history_crc32(const void *data, size_t length)
{
    const uint8_t *bytes = (const uint8_t *)data;
    uint32_t crc = UINT32_MAX;
    for (size_t i = 0; i < length; ++i) {
        crc ^= bytes[i];
        for (unsigned bit = 0; bit < 8; ++bit) {
            uint32_t mask = (uint32_t)-(int32_t)(crc & 1u);
            crc = (crc >> 1) ^ (0xEDB88320u & mask);
        }
    }
    return ~crc;
}

void nh_history_record_seal(nh_history_disk_record_t *record)
{
    if (!record) {
        return;
    }
    record->magic = NH_HISTORY_DISK_MAGIC;
    record->schema = NH_HISTORY_DISK_SCHEMA;
    record->record_size = (uint16_t)sizeof(*record);
    record->crc32 = nh_history_crc32(
        record, offsetof(nh_history_disk_record_t, crc32));
}

bool nh_history_record_valid(const nh_history_disk_record_t *record)
{
    if (!record ||
        record->magic != NH_HISTORY_DISK_MAGIC ||
        record->schema != NH_HISTORY_DISK_SCHEMA ||
        record->record_size != sizeof(*record) ||
        record->sequence == 0 ||
        record->event_type < NH_HISTORY_EVENT_START ||
        record->event_type > NH_HISTORY_EVENT_MAINTENANCE_RESET ||
        record->text[sizeof(record->text) - 1] != '\0') {
        return false;
    }
    return record->crc32 == nh_history_crc32(
        record, offsetof(nh_history_disk_record_t, crc32));
}
