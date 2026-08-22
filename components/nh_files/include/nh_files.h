#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

enum {
    NH_FILES_MAX = 48,
    NH_FILE_QUEUE_MAX = 8,
    NH_FILE_NAME_LENGTH = 96,
    NH_FILE_PATH_LENGTH = 192,
    NH_FILE_MODEL_LENGTH = 32,
    NH_FILE_HASH_LENGTH = 32,
    NH_FILE_THUMBNAIL_MAX_BYTES = 256 * 1024,
};

typedef enum {
    NH_FILE_COMPATIBILITY_UNKNOWN = 0,
    NH_FILE_COMPATIBILITY_REVIEW,
    NH_FILE_COMPATIBILITY_COMPATIBLE,
    NH_FILE_COMPATIBILITY_INCOMPATIBLE,
} nh_file_compatibility_t;

typedef enum {
    NH_FILE_QUEUE_PENDING_REVIEW = 0,
    NH_FILE_QUEUE_WAITING_FOR_BED_CLEAR,
    NH_FILE_QUEUE_READY_TO_TRANSFER,
    NH_FILE_QUEUE_TRANSFERRING,
    NH_FILE_QUEUE_READY_TO_START,
    NH_FILE_QUEUE_STARTING,
    NH_FILE_QUEUE_PRINTING,
    NH_FILE_QUEUE_COMPLETE,
    NH_FILE_QUEUE_FAILED,
    NH_FILE_QUEUE_CANCELLED,
} nh_file_queue_state_t;

typedef struct {
    uint64_t id;
    char name[NH_FILE_NAME_LENGTH];
    char path[NH_FILE_PATH_LENGTH];
    char target_model[NH_FILE_MODEL_LENGTH];
    uint64_t size_bytes;
    uint64_t modified_epoch;
    uint8_t sha256[NH_FILE_HASH_LENGTH];
    uint16_t thumbnail_width;
    uint16_t thumbnail_height;
    float nozzle_diameter_mm;
    float layer_height_mm;
    nh_file_compatibility_t compatibility;
    bool hash_known;
    bool metadata_known;
    bool thumbnail_available;
    bool favorite;
    bool duplicate;
} nh_file_entry_t;

typedef struct {
    uint64_t id;
    uint64_t file_id;
    uint64_t file_size_bytes;
    uint64_t resume_offset_bytes;
    uint8_t expected_sha256[NH_FILE_HASH_LENGTH];
    nh_file_queue_state_t state;
    esp_err_t last_error;
    uint8_t priority;
    uint8_t copies;
    bool compatibility_reviewed;
    bool bed_clear_confirmed;
} nh_file_queue_entry_t;

typedef struct {
    nh_file_entry_t files[NH_FILES_MAX];
    nh_file_queue_entry_t queue[NH_FILE_QUEUE_MAX];
    uint8_t file_count;
    uint8_t queue_count;
    uint32_t generation;
    bool storage_ready;
    bool scanning;
    bool queue_recovered;
    esp_err_t last_error;
} nh_files_snapshot_t;

esp_err_t nh_files_init(const char *storage_root);
esp_err_t nh_files_rescan(void);
esp_err_t nh_files_snapshot(nh_files_snapshot_t *snapshot);
esp_err_t nh_files_set_favorite(uint64_t file_id, bool favorite);
esp_err_t nh_files_search(const char *query,
                          uint64_t *file_ids,
                          size_t capacity,
                          size_t *match_count);

/**
 * Extracts the bounded PNG preview embedded in a 3MF. Passing a NULL buffer
 * reports required_size without extracting. The caller owns the buffer.
 */
esp_err_t nh_files_thumbnail(uint64_t file_id,
                             uint8_t *buffer,
                             size_t buffer_size,
                             size_t *required_size);

esp_err_t nh_files_queue_add(uint64_t file_id, uint64_t *queue_id);
/**
 * Atomically adds and compatibility-reviews one queue item. No orphaned
 * pending item is retained if validation or persistence fails.
 */
esp_err_t nh_files_queue_add_reviewed(
    uint64_t file_id,
    const uint8_t expected_sha256[NH_FILE_HASH_LENGTH],
    uint64_t *queue_id);
esp_err_t nh_files_queue_review(uint64_t queue_id,
                                const uint8_t expected_sha256[32]);
esp_err_t nh_files_queue_confirm_bed_clear(uint64_t queue_id,
                                           bool physical_bed_is_clear);
esp_err_t nh_files_queue_set_transfer_progress(uint64_t queue_id,
                                               uint64_t offset_bytes,
                                               esp_err_t transfer_error);
esp_err_t nh_files_queue_set_state(uint64_t queue_id,
                                   nh_file_queue_state_t state);
esp_err_t nh_files_queue_set_priority_copies(uint64_t queue_id,
                                             uint8_t priority,
                                             uint8_t copies);
esp_err_t nh_files_queue_cancel(uint64_t queue_id);

const char *nh_file_compatibility_label(nh_file_compatibility_t compatibility);
const char *nh_file_queue_state_label(nh_file_queue_state_t state);

#ifdef __cplusplus
}
#endif
