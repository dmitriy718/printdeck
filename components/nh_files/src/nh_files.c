#include "nh_files.h"

#include <ctype.h>
#include <dirent.h>
#include <errno.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <sys/stat.h>
#include <unistd.h>

#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "nh_3mf.h"
#include "psa/crypto.h"

enum {
    NH_FILES_STATE_MAGIC = 0x50444653u,
    NH_FILES_STATE_SCHEMA = 1,
    NH_FILES_FAVORITES_MAX = NH_FILES_MAX,
};

typedef struct {
    uint32_t magic;
    uint16_t schema;
    uint16_t size;
    uint64_t next_queue_id;
    uint64_t favorite_ids[NH_FILES_FAVORITES_MAX];
    nh_file_queue_entry_t queue[NH_FILE_QUEUE_MAX];
    uint8_t favorite_count;
    uint8_t queue_count;
    uint8_t reserved[6];
    uint32_t crc32;
} nh_files_state_record_t;

static SemaphoreHandle_t s_mutex;
static nh_files_snapshot_t s_snapshot;
static uint64_t s_favorite_ids[NH_FILES_FAVORITES_MAX];
static uint8_t s_favorite_count;
static uint64_t s_next_queue_id = 1;
static char s_files_directory[NH_FILE_PATH_LENGTH];
static char s_state_path[NH_FILE_PATH_LENGTH];
static bool s_initialized;

static uint32_t crc32_bytes(const void *data, size_t length)
{
    const uint8_t *bytes = data;
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

static esp_err_t errno_to_esp(void)
{
    if (errno == ENOENT) {
        return ESP_ERR_NOT_FOUND;
    }
    if (errno == ENOSPC) {
        return ESP_ERR_NO_MEM;
    }
    return ESP_FAIL;
}

static bool bounded_text(const char *value, size_t capacity)
{
    if (!value) {
        return false;
    }
    size_t length = strnlen(value, capacity);
    if (length == 0 || length >= capacity) {
        return false;
    }
    for (size_t i = 0; i < length; ++i) {
        unsigned char c = (unsigned char)value[i];
        if (c < 0x20 || c == 0x7F) {
            return false;
        }
    }
    return true;
}

static bool has_3mf_extension(const char *name)
{
    size_t length = name ? strlen(name) : 0;
    return length > 4 &&
           name[length - 4] == '.' &&
           tolower((unsigned char)name[length - 3]) == '3' &&
           tolower((unsigned char)name[length - 2]) == 'm' &&
           tolower((unsigned char)name[length - 1]) == 'f';
}

static bool safe_leaf_name(const char *name)
{
    return bounded_text(name, NH_FILE_NAME_LENGTH) &&
           strcmp(name, ".") != 0 && strcmp(name, "..") != 0 &&
           !strchr(name, '/') && !strchr(name, '\\');
}

static bool favorite_locked(uint64_t file_id)
{
    for (uint8_t i = 0; i < s_favorite_count; ++i) {
        if (s_favorite_ids[i] == file_id) {
            return true;
        }
    }
    return false;
}

static uint64_t hash_id(const uint8_t sha256[32])
{
    uint64_t id = 0;
    for (size_t i = 0; i < 8; ++i) {
        id = (id << 8) | sha256[i];
    }
    return id ? id : 1;
}

static esp_err_t hash_file(const char *path, uint8_t output[32])
{
    FILE *file = fopen(path, "rb");
    if (!file) {
        return errno_to_esp();
    }
    psa_hash_operation_t operation = PSA_HASH_OPERATION_INIT;
    psa_status_t result = psa_crypto_init();
    if (result == PSA_SUCCESS) {
        result = psa_hash_setup(&operation, PSA_ALG_SHA_256);
    }
    uint8_t buffer[4096];
    while (result == 0 && !feof(file)) {
        size_t count = fread(buffer, 1, sizeof(buffer), file);
        if (count > 0) {
            result = psa_hash_update(&operation, buffer, count);
        }
        if (ferror(file)) {
            result = PSA_ERROR_STORAGE_FAILURE;
        }
    }
    if (result == 0) {
        size_t hash_length = 0;
        result = psa_hash_finish(
            &operation, output, 32, &hash_length);
        if (result == PSA_SUCCESS && hash_length != 32) {
            result = PSA_ERROR_DATA_INVALID;
        }
    }
    if (result != PSA_SUCCESS) {
        (void)psa_hash_abort(&operation);
    }
    bool closed = fclose(file) == 0;
    return result == PSA_SUCCESS && closed ? ESP_OK : ESP_FAIL;
}

static void apply_metadata(nh_file_entry_t *entry,
                           const nh_3mf_metadata_t *metadata)
{
    entry->metadata_known = metadata->metadata_known;
    entry->thumbnail_available = metadata->thumbnail_available;
    entry->thumbnail_width = metadata->thumbnail_width;
    entry->thumbnail_height = metadata->thumbnail_height;
    entry->nozzle_diameter_mm = metadata->nozzle_diameter_mm;
    entry->layer_height_mm = metadata->layer_height_mm;
    strlcpy(entry->target_model, metadata->target_model,
            sizeof(entry->target_model));
    if (metadata->title[0]) {
        strlcpy(entry->name, metadata->title, sizeof(entry->name));
    }
    if (!entry->target_model[0]) {
        entry->compatibility = NH_FILE_COMPATIBILITY_REVIEW;
    } else if (strstr(entry->target_model, "P1S") ||
               strstr(entry->target_model, "BL-P001")) {
        entry->compatibility = NH_FILE_COMPATIBILITY_COMPATIBLE;
    } else {
        entry->compatibility = NH_FILE_COMPATIBILITY_INCOMPATIBLE;
    }
}

static int compare_modified_desc(const void *left_value,
                                 const void *right_value)
{
    const nh_file_entry_t *left = left_value;
    const nh_file_entry_t *right = right_value;
    if (left->favorite != right->favorite) {
        return left->favorite ? -1 : 1;
    }
    if (left->modified_epoch != right->modified_epoch) {
        return left->modified_epoch > right->modified_epoch ? -1 : 1;
    }
    return strcasecmp(left->name, right->name);
}

static void scan_directory_locked(const char *directory, unsigned depth)
{
    if (s_snapshot.file_count >= NH_FILES_MAX || depth > 2) {
        return;
    }
    DIR *handle = opendir(directory);
    if (!handle) {
        s_snapshot.last_error = errno_to_esp();
        return;
    }
    struct dirent *item;
    while ((item = readdir(handle)) != NULL &&
           s_snapshot.file_count < NH_FILES_MAX) {
        if (!safe_leaf_name(item->d_name)) {
            continue;
        }
        char path[NH_FILE_PATH_LENGTH];
        if (snprintf(path, sizeof(path), "%s/%s", directory,
                     item->d_name) >= (int)sizeof(path)) {
            continue;
        }
        struct stat info;
#ifdef DT_LNK
        if (item->d_type == DT_LNK) {
            continue;
        }
#endif
        /*
         * ESP-IDF's FAT VFS does not implement lstat or symbolic links.
         * Reject a link-like dirent when a filesystem reports one, then use
         * the available stat call for the controller's FAT32 volume.
         */
        if (stat(path, &info) != 0) {
            continue;
        }
        if (S_ISDIR(info.st_mode)) {
            scan_directory_locked(path, depth + 1);
            continue;
        }
        if (!S_ISREG(info.st_mode) || !has_3mf_extension(item->d_name) ||
            info.st_size <= 0) {
            continue;
        }

        nh_file_entry_t *entry =
            &s_snapshot.files[s_snapshot.file_count];
        memset(entry, 0, sizeof(*entry));
        strlcpy(entry->name, item->d_name, sizeof(entry->name));
        strlcpy(entry->path, path, sizeof(entry->path));
        entry->size_bytes = (uint64_t)info.st_size;
        entry->modified_epoch = (uint64_t)info.st_mtime;
        entry->compatibility = NH_FILE_COMPATIBILITY_UNKNOWN;
        if (hash_file(path, entry->sha256) != ESP_OK) {
            continue;
        }
        entry->hash_known = true;
        entry->id = hash_id(entry->sha256);
        entry->favorite = favorite_locked(entry->id);

        nh_3mf_metadata_t metadata;
        if (nh_3mf_inspect(path, &metadata) == 0) {
            apply_metadata(entry, &metadata);
        }
        s_snapshot.file_count++;
    }
    closedir(handle);
}

static void detect_duplicates_locked(void)
{
    for (uint8_t i = 0; i < s_snapshot.file_count; ++i) {
        for (uint8_t j = i + 1; j < s_snapshot.file_count; ++j) {
            if (s_snapshot.files[i].size_bytes ==
                    s_snapshot.files[j].size_bytes &&
                memcmp(s_snapshot.files[i].sha256,
                       s_snapshot.files[j].sha256, 32) == 0) {
                s_snapshot.files[i].duplicate = true;
                s_snapshot.files[j].duplicate = true;
            }
        }
    }
}

static esp_err_t persist_state_locked(void)
{
    nh_files_state_record_t record = {
        .magic = NH_FILES_STATE_MAGIC,
        .schema = NH_FILES_STATE_SCHEMA,
        .size = sizeof(record),
        .next_queue_id = s_next_queue_id,
        .favorite_count = s_favorite_count,
        .queue_count = s_snapshot.queue_count,
    };
    memcpy(record.favorite_ids, s_favorite_ids,
           sizeof(record.favorite_ids));
    memcpy(record.queue, s_snapshot.queue, sizeof(record.queue));
    record.crc32 = crc32_bytes(
        &record, offsetof(nh_files_state_record_t, crc32));

    char temporary[NH_FILE_PATH_LENGTH];
    if (snprintf(temporary, sizeof(temporary), "%s.tmp",
                 s_state_path) >= (int)sizeof(temporary)) {
        return ESP_ERR_INVALID_SIZE;
    }
    FILE *file = fopen(temporary, "wb");
    if (!file) {
        return errno_to_esp();
    }
    bool ok = fwrite(&record, sizeof(record), 1, file) == 1 &&
              fflush(file) == 0 && fsync(fileno(file)) == 0;
    ok = fclose(file) == 0 && ok;
    ok = ok && rename(temporary, s_state_path) == 0;
    return ok ? ESP_OK : ESP_FAIL;
}

static esp_err_t load_state_locked(void)
{
    FILE *file = fopen(s_state_path, "rb");
    if (!file) {
        return errno == ENOENT ? ESP_OK : errno_to_esp();
    }
    nh_files_state_record_t record;
    bool ok = fread(&record, sizeof(record), 1, file) == 1 &&
              fgetc(file) == EOF && !ferror(file);
    fclose(file);
    if (!ok || record.magic != NH_FILES_STATE_MAGIC ||
        record.schema != NH_FILES_STATE_SCHEMA ||
        record.size != sizeof(record) ||
        record.favorite_count > NH_FILES_FAVORITES_MAX ||
        record.queue_count > NH_FILE_QUEUE_MAX ||
        record.crc32 != crc32_bytes(
            &record, offsetof(nh_files_state_record_t, crc32))) {
        return ESP_ERR_INVALID_CRC;
    }
    s_favorite_count = record.favorite_count;
    memcpy(s_favorite_ids, record.favorite_ids, sizeof(s_favorite_ids));
    s_snapshot.queue_count = record.queue_count;
    memcpy(s_snapshot.queue, record.queue, sizeof(s_snapshot.queue));
    s_next_queue_id = record.next_queue_id ? record.next_queue_id : 1;
    for (uint8_t i = 0; i < s_snapshot.queue_count; ++i) {
        nh_file_queue_entry_t *queue = &s_snapshot.queue[i];
        if (queue->state == NH_FILE_QUEUE_TRANSFERRING) {
            queue->state = NH_FILE_QUEUE_READY_TO_TRANSFER;
            s_snapshot.queue_recovered = true;
        } else if (queue->state == NH_FILE_QUEUE_STARTING ||
                   queue->state == NH_FILE_QUEUE_PRINTING) {
            queue->state = NH_FILE_QUEUE_FAILED;
            queue->last_error = ESP_ERR_INVALID_STATE;
            s_snapshot.queue_recovered = true;
        }
    }
    return ESP_OK;
}

esp_err_t nh_files_init(const char *storage_root)
{
    if (s_initialized) {
        return ESP_ERR_INVALID_STATE;
    }
    if (!bounded_text(storage_root, NH_FILE_PATH_LENGTH - 32)) {
        return ESP_ERR_INVALID_ARG;
    }
    char product_directory[NH_FILE_PATH_LENGTH];
    if (snprintf(product_directory, sizeof(product_directory),
                 "%s/PrintDeck", storage_root) >=
            (int)sizeof(product_directory) ||
        snprintf(s_files_directory, sizeof(s_files_directory),
                 "%s/files", product_directory) >=
            (int)sizeof(s_files_directory) ||
        snprintf(s_state_path, sizeof(s_state_path),
                 "%s/files-state.bin", product_directory) >=
            (int)sizeof(s_state_path)) {
        return ESP_ERR_INVALID_SIZE;
    }
    if ((mkdir(product_directory, 0750) != 0 && errno != EEXIST) ||
        (mkdir(s_files_directory, 0750) != 0 && errno != EEXIST)) {
        return errno_to_esp();
    }
    s_mutex = xSemaphoreCreateMutex();
    if (!s_mutex) {
        return ESP_ERR_NO_MEM;
    }
    memset(&s_snapshot, 0, sizeof(s_snapshot));
    esp_err_t err = load_state_locked();
    if (err != ESP_OK) {
        vSemaphoreDelete(s_mutex);
        s_mutex = NULL;
        return err;
    }
    s_snapshot.storage_ready = true;
    s_initialized = true;
    return nh_files_rescan();
}

esp_err_t nh_files_rescan(void)
{
    if (!s_initialized) {
        return ESP_ERR_INVALID_STATE;
    }
    (void)xSemaphoreTake(s_mutex, portMAX_DELAY);
    s_snapshot.scanning = true;
    s_snapshot.file_count = 0;
    memset(s_snapshot.files, 0, sizeof(s_snapshot.files));
    s_snapshot.last_error = ESP_OK;
    scan_directory_locked(s_files_directory, 0);
    detect_duplicates_locked();
    qsort(s_snapshot.files, s_snapshot.file_count,
          sizeof(s_snapshot.files[0]), compare_modified_desc);
    s_snapshot.scanning = false;
    s_snapshot.generation++;
    esp_err_t err = s_snapshot.last_error;
    (void)xSemaphoreGive(s_mutex);
    return err;
}

esp_err_t nh_files_snapshot(nh_files_snapshot_t *snapshot)
{
    if (!s_initialized || !snapshot) {
        return ESP_ERR_INVALID_STATE;
    }
    (void)xSemaphoreTake(s_mutex, portMAX_DELAY);
    *snapshot = s_snapshot;
    (void)xSemaphoreGive(s_mutex);
    return ESP_OK;
}

esp_err_t nh_files_set_favorite(uint64_t file_id, bool favorite)
{
    if (!s_initialized || file_id == 0) {
        return ESP_ERR_INVALID_ARG;
    }
    (void)xSemaphoreTake(s_mutex, portMAX_DELAY);
    uint64_t previous_ids[NH_FILES_FAVORITES_MAX];
    memcpy(previous_ids, s_favorite_ids, sizeof(previous_ids));
    uint8_t previous_count = s_favorite_count;
    uint8_t index = s_favorite_count;
    for (uint8_t i = 0; i < s_favorite_count; ++i) {
        if (s_favorite_ids[i] == file_id) {
            index = i;
            break;
        }
    }
    if (favorite && index == s_favorite_count) {
        if (s_favorite_count >= NH_FILES_FAVORITES_MAX) {
            (void)xSemaphoreGive(s_mutex);
            return ESP_ERR_NO_MEM;
        }
        s_favorite_ids[s_favorite_count++] = file_id;
    } else if (!favorite && index < s_favorite_count) {
        for (uint8_t i = index + 1; i < s_favorite_count; ++i) {
            s_favorite_ids[i - 1] = s_favorite_ids[i];
        }
        s_favorite_ids[--s_favorite_count] = 0;
    }
    for (uint8_t i = 0; i < s_snapshot.file_count; ++i) {
        if (s_snapshot.files[i].id == file_id) {
            s_snapshot.files[i].favorite = favorite;
        }
    }
    esp_err_t err = persist_state_locked();
    if (err != ESP_OK) {
        memcpy(s_favorite_ids, previous_ids, sizeof(s_favorite_ids));
        s_favorite_count = previous_count;
        for (uint8_t i = 0; i < s_snapshot.file_count; ++i) {
            if (s_snapshot.files[i].id == file_id) {
                s_snapshot.files[i].favorite =
                    favorite_locked(file_id);
            }
        }
    }
    (void)xSemaphoreGive(s_mutex);
    return err;
}

static bool contains_case_insensitive(const char *text, const char *query)
{
    if (!query[0]) {
        return true;
    }
    size_t query_length = strlen(query);
    for (const char *start = text; *start; ++start) {
        if (strncasecmp(start, query, query_length) == 0) {
            return true;
        }
    }
    return false;
}

esp_err_t nh_files_search(const char *query,
                          uint64_t *file_ids,
                          size_t capacity,
                          size_t *match_count)
{
    if (!s_initialized || !query || !match_count ||
        (capacity > 0 && !file_ids) ||
        strnlen(query, NH_FILE_NAME_LENGTH) >= NH_FILE_NAME_LENGTH) {
        return ESP_ERR_INVALID_ARG;
    }
    (void)xSemaphoreTake(s_mutex, portMAX_DELAY);
    size_t matches = 0;
    for (uint8_t i = 0; i < s_snapshot.file_count; ++i) {
        const nh_file_entry_t *file = &s_snapshot.files[i];
        if (contains_case_insensitive(file->name, query) ||
            contains_case_insensitive(file->target_model, query)) {
            if (matches < capacity) {
                file_ids[matches] = file->id;
            }
            matches++;
        }
    }
    *match_count = matches;
    (void)xSemaphoreGive(s_mutex);
    return matches > capacity ? ESP_ERR_INVALID_SIZE : ESP_OK;
}

static nh_file_entry_t *find_file_locked(uint64_t file_id)
{
    for (uint8_t i = 0; i < s_snapshot.file_count; ++i) {
        if (s_snapshot.files[i].id == file_id) {
            return &s_snapshot.files[i];
        }
    }
    return NULL;
}

static nh_file_queue_entry_t *find_queue_locked(uint64_t queue_id)
{
    for (uint8_t i = 0; i < s_snapshot.queue_count; ++i) {
        if (s_snapshot.queue[i].id == queue_id) {
            return &s_snapshot.queue[i];
        }
    }
    return NULL;
}

esp_err_t nh_files_thumbnail(uint64_t file_id,
                             uint8_t *buffer,
                             size_t buffer_size,
                             size_t *required_size)
{
    if (!s_initialized || !required_size) {
        return ESP_ERR_INVALID_ARG;
    }
    (void)xSemaphoreTake(s_mutex, portMAX_DELAY);
    nh_file_entry_t *file = find_file_locked(file_id);
    if (!file || !file->thumbnail_available) {
        (void)xSemaphoreGive(s_mutex);
        return ESP_ERR_NOT_FOUND;
    }
    nh_3mf_metadata_t metadata;
    int result = nh_3mf_inspect(file->path, &metadata);
    if (result == 0) {
        result = nh_3mf_extract_thumbnail(
            file->path, metadata.thumbnail_member,
            buffer, buffer_size, required_size);
    }
    (void)xSemaphoreGive(s_mutex);
    return result == 0 ? ESP_OK : ESP_FAIL;
}

esp_err_t nh_files_queue_add(uint64_t file_id, uint64_t *queue_id)
{
    if (!s_initialized || !queue_id) {
        return ESP_ERR_INVALID_ARG;
    }
    (void)xSemaphoreTake(s_mutex, portMAX_DELAY);
    nh_file_entry_t *file = find_file_locked(file_id);
    if (!file || !file->hash_known) {
        (void)xSemaphoreGive(s_mutex);
        return ESP_ERR_NOT_FOUND;
    }
    if (file->compatibility == NH_FILE_COMPATIBILITY_INCOMPATIBLE) {
        (void)xSemaphoreGive(s_mutex);
        return ESP_ERR_NOT_SUPPORTED;
    }
    if (s_snapshot.queue_count >= NH_FILE_QUEUE_MAX) {
        (void)xSemaphoreGive(s_mutex);
        return ESP_ERR_NO_MEM;
    }
    nh_file_queue_entry_t *queue =
        &s_snapshot.queue[s_snapshot.queue_count++];
    *queue = (nh_file_queue_entry_t){
        .id = s_next_queue_id++,
        .file_id = file->id,
        .file_size_bytes = file->size_bytes,
        .state = NH_FILE_QUEUE_PENDING_REVIEW,
        .last_error = ESP_OK,
        .copies = 1,
    };
    memcpy(queue->expected_sha256, file->sha256, 32);
    esp_err_t err = persist_state_locked();
    if (err == ESP_OK) {
        *queue_id = queue->id;
    } else {
        s_snapshot.queue_count--;
        s_next_queue_id--;
    }
    (void)xSemaphoreGive(s_mutex);
    return err;
}

esp_err_t nh_files_queue_add_reviewed(
    uint64_t file_id,
    const uint8_t expected_sha256[NH_FILE_HASH_LENGTH],
    uint64_t *queue_id)
{
    if (!s_initialized || !expected_sha256 || !queue_id) {
        return ESP_ERR_INVALID_ARG;
    }
    (void)xSemaphoreTake(s_mutex, portMAX_DELAY);
    nh_file_entry_t *file = find_file_locked(file_id);
    if (!file || !file->hash_known) {
        (void)xSemaphoreGive(s_mutex);
        return ESP_ERR_NOT_FOUND;
    }
    if (file->compatibility == NH_FILE_COMPATIBILITY_INCOMPATIBLE) {
        (void)xSemaphoreGive(s_mutex);
        return ESP_ERR_NOT_SUPPORTED;
    }
    if (memcmp(expected_sha256, file->sha256, NH_FILE_HASH_LENGTH) != 0) {
        (void)xSemaphoreGive(s_mutex);
        return ESP_ERR_INVALID_CRC;
    }
    if (s_snapshot.queue_count >= NH_FILE_QUEUE_MAX) {
        (void)xSemaphoreGive(s_mutex);
        return ESP_ERR_NO_MEM;
    }
    uint64_t previous_next_id = s_next_queue_id;
    nh_file_queue_entry_t *queue =
        &s_snapshot.queue[s_snapshot.queue_count++];
    *queue = (nh_file_queue_entry_t){
        .id = s_next_queue_id++,
        .file_id = file->id,
        .file_size_bytes = file->size_bytes,
        .state = NH_FILE_QUEUE_WAITING_FOR_BED_CLEAR,
        .last_error = ESP_OK,
        .copies = 1,
        .compatibility_reviewed = true,
    };
    memcpy(queue->expected_sha256, file->sha256, NH_FILE_HASH_LENGTH);
    esp_err_t err = persist_state_locked();
    if (err == ESP_OK) {
        *queue_id = queue->id;
    } else {
        memset(queue, 0, sizeof(*queue));
        s_snapshot.queue_count--;
        s_next_queue_id = previous_next_id;
    }
    (void)xSemaphoreGive(s_mutex);
    return err;
}

esp_err_t nh_files_queue_review(uint64_t queue_id,
                                const uint8_t expected_sha256[32])
{
    if (!s_initialized || !expected_sha256) {
        return ESP_ERR_INVALID_ARG;
    }
    (void)xSemaphoreTake(s_mutex, portMAX_DELAY);
    nh_file_queue_entry_t *queue = find_queue_locked(queue_id);
    nh_file_entry_t *file =
        queue ? find_file_locked(queue->file_id) : NULL;
    if (!queue || !file ||
        queue->state != NH_FILE_QUEUE_PENDING_REVIEW) {
        (void)xSemaphoreGive(s_mutex);
        return ESP_ERR_INVALID_STATE;
    }
    if (memcmp(expected_sha256, file->sha256, 32) != 0 ||
        memcmp(queue->expected_sha256, file->sha256, 32) != 0 ||
        file->compatibility == NH_FILE_COMPATIBILITY_INCOMPATIBLE) {
        (void)xSemaphoreGive(s_mutex);
        return ESP_ERR_INVALID_CRC;
    }
    nh_file_queue_entry_t previous = *queue;
    queue->compatibility_reviewed = true;
    queue->state = NH_FILE_QUEUE_WAITING_FOR_BED_CLEAR;
    esp_err_t err = persist_state_locked();
    if (err != ESP_OK) {
        *queue = previous;
    }
    (void)xSemaphoreGive(s_mutex);
    return err;
}

esp_err_t nh_files_queue_confirm_bed_clear(uint64_t queue_id,
                                           bool physical_bed_is_clear)
{
    if (!s_initialized || !physical_bed_is_clear) {
        return ESP_ERR_INVALID_ARG;
    }
    (void)xSemaphoreTake(s_mutex, portMAX_DELAY);
    nh_file_queue_entry_t *queue = find_queue_locked(queue_id);
    if (!queue ||
        queue->state != NH_FILE_QUEUE_WAITING_FOR_BED_CLEAR ||
        !queue->compatibility_reviewed) {
        (void)xSemaphoreGive(s_mutex);
        return ESP_ERR_INVALID_STATE;
    }
    nh_file_queue_entry_t previous = *queue;
    queue->bed_clear_confirmed = true;
    queue->state = NH_FILE_QUEUE_READY_TO_TRANSFER;
    esp_err_t err = persist_state_locked();
    if (err != ESP_OK) {
        *queue = previous;
    }
    (void)xSemaphoreGive(s_mutex);
    return err;
}

esp_err_t nh_files_queue_set_transfer_progress(uint64_t queue_id,
                                               uint64_t offset_bytes,
                                               esp_err_t transfer_error)
{
    if (!s_initialized) {
        return ESP_ERR_INVALID_STATE;
    }
    (void)xSemaphoreTake(s_mutex, portMAX_DELAY);
    nh_file_queue_entry_t *queue = find_queue_locked(queue_id);
    if (!queue || offset_bytes > queue->file_size_bytes ||
        (queue->state != NH_FILE_QUEUE_READY_TO_TRANSFER &&
         queue->state != NH_FILE_QUEUE_TRANSFERRING)) {
        (void)xSemaphoreGive(s_mutex);
        return ESP_ERR_INVALID_STATE;
    }
    nh_file_queue_entry_t previous = *queue;
    queue->resume_offset_bytes = offset_bytes;
    queue->last_error = transfer_error;
    queue->state = transfer_error == ESP_OK
                       ? (offset_bytes == queue->file_size_bytes
                              ? NH_FILE_QUEUE_READY_TO_START
                              : NH_FILE_QUEUE_TRANSFERRING)
                       : NH_FILE_QUEUE_READY_TO_TRANSFER;
    esp_err_t err = persist_state_locked();
    if (err != ESP_OK) {
        *queue = previous;
    }
    (void)xSemaphoreGive(s_mutex);
    return err;
}

static bool allowed_transition(nh_file_queue_state_t from,
                               nh_file_queue_state_t to)
{
    return (from == NH_FILE_QUEUE_READY_TO_START &&
            to == NH_FILE_QUEUE_STARTING) ||
           (from == NH_FILE_QUEUE_STARTING &&
            (to == NH_FILE_QUEUE_PRINTING ||
             to == NH_FILE_QUEUE_FAILED)) ||
           (from == NH_FILE_QUEUE_PRINTING &&
            (to == NH_FILE_QUEUE_COMPLETE ||
             to == NH_FILE_QUEUE_FAILED));
}

static bool terminal_queue_state(nh_file_queue_state_t state)
{
    return state == NH_FILE_QUEUE_COMPLETE ||
           state == NH_FILE_QUEUE_FAILED ||
           state == NH_FILE_QUEUE_CANCELLED;
}

esp_err_t nh_files_queue_set_state(uint64_t queue_id,
                                   nh_file_queue_state_t state)
{
    if (!s_initialized) {
        return ESP_ERR_INVALID_STATE;
    }
    (void)xSemaphoreTake(s_mutex, portMAX_DELAY);
    nh_file_queue_entry_t *queue = find_queue_locked(queue_id);
    if (!queue || !allowed_transition(queue->state, state)) {
        (void)xSemaphoreGive(s_mutex);
        return ESP_ERR_INVALID_STATE;
    }
    nh_file_queue_entry_t previous = *queue;
    queue->state = state;
    esp_err_t err = persist_state_locked();
    if (err != ESP_OK) {
        *queue = previous;
    }
    (void)xSemaphoreGive(s_mutex);
    return err;
}

esp_err_t nh_files_queue_set_priority_copies(uint64_t queue_id,
                                             uint8_t priority,
                                             uint8_t copies)
{
    if (!s_initialized || priority > 3 || copies == 0 || copies > 99) {
        return ESP_ERR_INVALID_ARG;
    }
    (void)xSemaphoreTake(s_mutex, portMAX_DELAY);
    nh_file_queue_entry_t *queue = find_queue_locked(queue_id);
    if (!queue || terminal_queue_state(queue->state) ||
        queue->state == NH_FILE_QUEUE_STARTING ||
        queue->state == NH_FILE_QUEUE_PRINTING) {
        (void)xSemaphoreGive(s_mutex);
        return ESP_ERR_INVALID_STATE;
    }
    nh_file_queue_entry_t previous = *queue;
    queue->priority = priority;
    queue->copies = copies;
    esp_err_t err = persist_state_locked();
    if (err != ESP_OK) {
        *queue = previous;
    }
    (void)xSemaphoreGive(s_mutex);
    return err;
}

esp_err_t nh_files_queue_cancel(uint64_t queue_id)
{
    if (!s_initialized) {
        return ESP_ERR_INVALID_STATE;
    }
    (void)xSemaphoreTake(s_mutex, portMAX_DELAY);
    nh_file_queue_entry_t *queue = find_queue_locked(queue_id);
    if (!queue || terminal_queue_state(queue->state) ||
        queue->state == NH_FILE_QUEUE_PRINTING) {
        (void)xSemaphoreGive(s_mutex);
        return ESP_ERR_INVALID_STATE;
    }
    nh_file_queue_entry_t previous = *queue;
    queue->state = NH_FILE_QUEUE_CANCELLED;
    queue->last_error = ESP_OK;
    esp_err_t err = persist_state_locked();
    if (err != ESP_OK) {
        *queue = previous;
    }
    (void)xSemaphoreGive(s_mutex);
    return err;
}

const char *nh_file_compatibility_label(nh_file_compatibility_t compatibility)
{
    switch (compatibility) {
    case NH_FILE_COMPATIBILITY_COMPATIBLE:
        return "P1S compatible";
    case NH_FILE_COMPATIBILITY_INCOMPATIBLE:
        return "Different printer";
    case NH_FILE_COMPATIBILITY_REVIEW:
        return "Review required";
    case NH_FILE_COMPATIBILITY_UNKNOWN:
    default:
        return "Unknown";
    }
}

const char *nh_file_queue_state_label(nh_file_queue_state_t state)
{
    switch (state) {
    case NH_FILE_QUEUE_PENDING_REVIEW:
        return "Review file";
    case NH_FILE_QUEUE_WAITING_FOR_BED_CLEAR:
        return "Waiting for bed clear";
    case NH_FILE_QUEUE_READY_TO_TRANSFER:
        return "Ready to transfer";
    case NH_FILE_QUEUE_TRANSFERRING:
        return "Transferring";
    case NH_FILE_QUEUE_READY_TO_START:
        return "Ready to start";
    case NH_FILE_QUEUE_STARTING:
        return "Starting";
    case NH_FILE_QUEUE_PRINTING:
        return "Printing";
    case NH_FILE_QUEUE_COMPLETE:
        return "Complete";
    case NH_FILE_QUEUE_FAILED:
        return "Failed";
    case NH_FILE_QUEUE_CANCELLED:
        return "Cancelled";
    default:
        return "Unknown";
    }
}
