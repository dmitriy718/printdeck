#include "nh_history.h"

#include <errno.h>
#include <inttypes.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <time.h>
#include <unistd.h>

#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "nh_history_codec.h"

enum {
    NH_HISTORY_FLAG_WALL_CLOCK = 1u << 0,
    NH_HISTORY_FLAG_MATERIAL_ESTIMATE = 1u << 1,
    NH_HISTORY_FLAG_ENERGY_ESTIMATE = 1u << 2,
};

static SemaphoreHandle_t s_mutex;
static nh_history_snapshot_t s_snapshot;
static nh_history_estimate_policy_t s_policy;
static char s_directory[NH_HISTORY_PATH_LENGTH];
static char s_journal_path[NH_HISTORY_PATH_LENGTH];
static uint64_t s_next_sequence = 1;
static int64_t s_active_started_monotonic_us;
static uint64_t s_active_started_epoch;
static uint8_t s_active_maximum_progress;
static char s_active_job_name[NH_HISTORY_JOB_NAME_LENGTH];
static uint64_t s_maintenance_reset_sequence;
static char s_maintenance_reset_actor[NH_HISTORY_DISK_TEXT_LENGTH];
static bool s_initialized;

static bool wall_clock_known(uint64_t epoch)
{
    return epoch >= 1704067200ULL;
}

static bool active_job(nh_job_state_t state)
{
    return state == NH_JOB_PREPARING ||
           state == NH_JOB_PRINTING ||
           state == NH_JOB_PAUSED;
}

static bool safe_text(const char *text, size_t capacity, bool allow_empty)
{
    if (!text) {
        return false;
    }
    size_t length = strnlen(text, capacity);
    if (length >= capacity || (!allow_empty && length == 0)) {
        return false;
    }
    for (size_t i = 0; i < length; ++i) {
        unsigned char c = (unsigned char)text[i];
        if (c < 0x20 || c == 0x7F) {
            return false;
        }
    }
    return true;
}

static esp_err_t errno_to_esp(void)
{
    if (errno == ENOSPC) {
        return ESP_ERR_NO_MEM;
    }
    if (errno == ENOENT) {
        return ESP_ERR_NOT_FOUND;
    }
    return ESP_FAIL;
}

static void add_recent_locked(const nh_history_job_t *job)
{
    if (s_snapshot.recent_count < NH_HISTORY_RECENT_MAX) {
        s_snapshot.recent_count++;
    }
    for (size_t i = s_snapshot.recent_count - 1; i > 0; --i) {
        s_snapshot.recent[i] = s_snapshot.recent[i - 1];
    }
    s_snapshot.recent[0] = *job;
}

static bool same_local_period(uint64_t epoch, bool month_only)
{
    if (!wall_clock_known(epoch)) {
        return false;
    }
    time_t now_value = time(NULL);
    time_t event_value = (time_t)epoch;
    struct tm now_local;
    struct tm event_local;
    if (!localtime_r(&now_value, &now_local) ||
        !localtime_r(&event_value, &event_local)) {
        return false;
    }
    if (now_local.tm_year != event_local.tm_year ||
        now_local.tm_mon != event_local.tm_mon) {
        return false;
    }
    return month_only || now_local.tm_mday == event_local.tm_mday;
}

static void update_maintenance_due_locked(void)
{
    s_snapshot.maintenance_due =
        s_snapshot.maintenance_print_seconds >= 250ULL * 3600ULL ||
        s_snapshot.maintenance_jobs >= 500;
}

static void apply_record_locked(const nh_history_disk_record_t *record)
{
    if (record->sequence >= s_next_sequence) {
        s_next_sequence = record->sequence + 1;
    }
    if (record->event_type == NH_HISTORY_EVENT_FINISH) {
        nh_history_job_t job = {
            .sequence = record->sequence,
            .started_epoch =
                record->timestamp_epoch >= record->duration_seconds
                    ? record->timestamp_epoch - record->duration_seconds
                    : 0,
            .ended_epoch = record->timestamp_epoch,
            .duration_seconds = record->duration_seconds,
            .material_grams_estimate = record->material_grams_estimate,
            .energy_wh_estimate = record->energy_wh_estimate,
            .material_cost_micros_estimate =
                record->material_cost_micros_estimate,
            .energy_cost_micros_estimate =
                record->energy_cost_micros_estimate,
            .maximum_progress_percent = record->maximum_progress_percent,
            .outcome = (nh_history_outcome_t)record->outcome,
            .wall_clock_known =
                (record->flags & NH_HISTORY_FLAG_WALL_CLOCK) != 0,
            .material_estimated =
                (record->flags & NH_HISTORY_FLAG_MATERIAL_ESTIMATE) != 0,
            .energy_estimated =
                (record->flags & NH_HISTORY_FLAG_ENERGY_ESTIMATE) != 0,
        };
        strlcpy(job.job_name, record->text, sizeof(job.job_name));
        add_recent_locked(&job);
        s_snapshot.total_jobs++;
        s_snapshot.total_print_seconds += record->duration_seconds;
        s_snapshot.maintenance_print_seconds += record->duration_seconds;
        s_snapshot.maintenance_jobs++;
        if (same_local_period(record->timestamp_epoch, false)) {
            s_snapshot.daily_jobs++;
            s_snapshot.daily_print_seconds += record->duration_seconds;
        }
        if (same_local_period(record->timestamp_epoch, true)) {
            s_snapshot.monthly_jobs++;
            s_snapshot.monthly_print_seconds += record->duration_seconds;
        }
        if (job.outcome == NH_HISTORY_OUTCOME_COMPLETE) {
            s_snapshot.completed_jobs++;
        } else if (job.outcome == NH_HISTORY_OUTCOME_FAILED) {
            s_snapshot.failed_jobs++;
        }
    } else if (record->event_type == NH_HISTORY_EVENT_MAINTENANCE_RESET) {
        s_snapshot.maintenance_print_seconds = 0;
        s_snapshot.maintenance_jobs = 0;
        s_snapshot.maintenance_reset_epoch = record->timestamp_epoch;
        s_maintenance_reset_sequence = record->sequence;
        strlcpy(s_maintenance_reset_actor, record->text,
                sizeof(s_maintenance_reset_actor));
    }
    update_maintenance_due_locked();
}

static esp_err_t append_record_locked(nh_history_disk_record_t *record)
{
    record->sequence = s_next_sequence++;
    nh_history_record_seal(record);
    FILE *file = fopen(s_journal_path, "ab+");
    if (!file) {
        s_next_sequence--;
        return errno_to_esp();
    }
    if (fseek(file, 0, SEEK_END) != 0) {
        fclose(file);
        s_next_sequence--;
        return ESP_FAIL;
    }
    long original_end = ftell(file);
    if (original_end < 0) {
        fclose(file);
        s_next_sequence--;
        return ESP_FAIL;
    }
    bool written = fwrite(record, sizeof(*record), 1, file) == 1;
    bool flushed = written && fflush(file) == 0;
    bool synced = flushed && fsync(fileno(file)) == 0;
    if (!written || !flushed || !synced) {
        clearerr(file);
        (void)ftruncate(fileno(file), original_end);
        (void)fsync(fileno(file));
    }
    bool closed = fclose(file) == 0;
    if (!written || !flushed || !synced) {
        s_next_sequence--;
        s_snapshot.last_error = errno_to_esp();
        return s_snapshot.last_error;
    }
    if (!closed) {
        s_snapshot.last_error = ESP_FAIL;
        return ESP_FAIL;
    }
    apply_record_locked(record);
    s_snapshot.last_error = ESP_OK;
    return ESP_OK;
}

static esp_err_t load_journal_locked(void)
{
    FILE *file = fopen(s_journal_path, "ab+");
    if (!file) {
        return errno_to_esp();
    }
    if (fseek(file, 0, SEEK_SET) != 0) {
        fclose(file);
        return ESP_FAIL;
    }

    long valid_end = 0;
    bool invalid_tail = false;
    nh_history_disk_record_t record;
    while (true) {
        size_t bytes = fread(&record, 1, sizeof(record), file);
        if (bytes == 0) {
            if (ferror(file)) {
                fclose(file);
                return ESP_FAIL;
            }
            break;
        }
        if (bytes != sizeof(record) || !nh_history_record_valid(&record)) {
            invalid_tail = true;
            break;
        }
        apply_record_locked(&record);
        valid_end += (long)sizeof(record);
    }
    if (invalid_tail) {
        if (fflush(file) != 0 || ftruncate(fileno(file), valid_end) != 0 ||
            fsync(fileno(file)) != 0) {
            fclose(file);
            return ESP_FAIL;
        }
        s_snapshot.recovered_invalid_tail = true;
    }
    if (fclose(file) != 0) {
        return ESP_FAIL;
    }
    return ESP_OK;
}

esp_err_t nh_history_init(const char *storage_root)
{
    if (s_initialized) {
        return ESP_ERR_INVALID_STATE;
    }
    if (!safe_text(storage_root, NH_HISTORY_PATH_LENGTH - 32, false)) {
        return ESP_ERR_INVALID_ARG;
    }
    if (snprintf(s_directory, sizeof(s_directory), "%s/PrintDeck",
                 storage_root) >= (int)sizeof(s_directory) ||
        snprintf(s_journal_path, sizeof(s_journal_path), "%s/history.journal",
                 s_directory) >= (int)sizeof(s_journal_path)) {
        return ESP_ERR_INVALID_SIZE;
    }
    if (mkdir(s_directory, 0750) != 0 && errno != EEXIST) {
        return errno_to_esp();
    }
    s_mutex = xSemaphoreCreateMutex();
    if (!s_mutex) {
        return ESP_ERR_NO_MEM;
    }
    memset(&s_snapshot, 0, sizeof(s_snapshot));
    esp_err_t err = load_journal_locked();
    if (err != ESP_OK) {
        vSemaphoreDelete(s_mutex);
        s_mutex = NULL;
        return err;
    }
    s_snapshot.storage_ready = true;
    s_snapshot.last_error = ESP_OK;
    s_initialized = true;
    return ESP_OK;
}

static esp_err_t begin_session_locked(const nh_printer_snapshot_t *printer)
{
    uint64_t now = (uint64_t)time(NULL);
    s_active_started_epoch = wall_clock_known(now) ? now : 0;
    s_active_started_monotonic_us = esp_timer_get_time();
    s_active_maximum_progress = printer->progress_percent;
    strlcpy(s_active_job_name,
            printer->job_name && printer->job_name[0]
                ? printer->job_name
                : "Unnamed print",
            sizeof(s_active_job_name));
    s_snapshot.active_session = true;

    nh_history_disk_record_t record = {
        .timestamp_epoch = s_active_started_epoch,
        .event_type = NH_HISTORY_EVENT_START,
        .maximum_progress_percent = s_active_maximum_progress,
        .flags = s_active_started_epoch ? NH_HISTORY_FLAG_WALL_CLOCK : 0,
    };
    strlcpy(record.text, s_active_job_name, sizeof(record.text));
    return append_record_locked(&record);
}

static esp_err_t finish_session_locked(nh_history_outcome_t outcome)
{
    uint64_t now = (uint64_t)time(NULL);
    bool known_now = wall_clock_known(now);
    int64_t elapsed_us = esp_timer_get_time() - s_active_started_monotonic_us;
    uint64_t duration = elapsed_us > 0 ? (uint64_t)elapsed_us / 1000000ULL : 0;
    if (duration > UINT32_MAX) {
        duration = UINT32_MAX;
    }

    nh_history_disk_record_t record = {
        .timestamp_epoch = known_now ? now : 0,
        .duration_seconds = (uint32_t)duration,
        .event_type = NH_HISTORY_EVENT_FINISH,
        .outcome = (uint8_t)outcome,
        .maximum_progress_percent = s_active_maximum_progress,
        .flags = known_now && s_active_started_epoch
                     ? NH_HISTORY_FLAG_WALL_CLOCK
                     : 0,
    };
    if (s_policy.material_grams_per_hour > 0) {
        uint64_t grams =
            duration * s_policy.material_grams_per_hour / 3600ULL;
        record.material_grams_estimate =
            grams > UINT32_MAX ? UINT32_MAX : (uint32_t)grams;
        record.material_cost_micros_estimate =
            grams * s_policy.material_cost_micros_per_kg / 1000ULL;
        record.flags |= NH_HISTORY_FLAG_MATERIAL_ESTIMATE;
    }
    if (s_policy.printer_watts > 0) {
        uint64_t wh = duration * s_policy.printer_watts / 3600ULL;
        record.energy_wh_estimate =
            wh > UINT32_MAX ? UINT32_MAX : (uint32_t)wh;
        record.energy_cost_micros_estimate =
            wh * s_policy.energy_cost_micros_per_kwh / 1000ULL;
        record.flags |= NH_HISTORY_FLAG_ENERGY_ESTIMATE;
    }
    strlcpy(record.text, s_active_job_name, sizeof(record.text));
    esp_err_t err = append_record_locked(&record);
    s_snapshot.active_session = false;
    memset(s_active_job_name, 0, sizeof(s_active_job_name));
    return err;
}

esp_err_t nh_history_observe(const nh_printer_snapshot_t *printer)
{
    if (!s_initialized || !printer) {
        return ESP_ERR_INVALID_STATE;
    }
    (void)xSemaphoreTake(s_mutex, portMAX_DELAY);
    bool currently_active = active_job(printer->job);
    esp_err_t err = ESP_OK;
    if (!s_snapshot.active_session && currently_active) {
        err = begin_session_locked(printer);
    } else if (s_snapshot.active_session && currently_active) {
        if (printer->progress_percent > s_active_maximum_progress) {
            s_active_maximum_progress = printer->progress_percent;
        }
        if (printer->job_name && printer->job_name[0] &&
            strcmp(printer->job_name, "No active print") != 0) {
            strlcpy(s_active_job_name, printer->job_name,
                    sizeof(s_active_job_name));
        }
    } else if (s_snapshot.active_session) {
        nh_history_outcome_t outcome = NH_HISTORY_OUTCOME_INTERRUPTED;
        if (printer->job == NH_JOB_COMPLETE) {
            outcome = NH_HISTORY_OUTCOME_COMPLETE;
        } else if (printer->job == NH_JOB_FAILED) {
            outcome = NH_HISTORY_OUTCOME_FAILED;
        }
        err = finish_session_locked(outcome);
    }
    (void)xSemaphoreGive(s_mutex);
    return err;
}

esp_err_t nh_history_snapshot(nh_history_snapshot_t *snapshot)
{
    if (!s_initialized || !snapshot) {
        return ESP_ERR_INVALID_STATE;
    }
    (void)xSemaphoreTake(s_mutex, portMAX_DELAY);
    *snapshot = s_snapshot;
    (void)xSemaphoreGive(s_mutex);
    return ESP_OK;
}

esp_err_t nh_history_set_estimate_policy(
    const nh_history_estimate_policy_t *policy)
{
    if (!s_initialized || !policy ||
        policy->material_grams_per_hour > 10000 ||
        policy->printer_watts > 5000) {
        return ESP_ERR_INVALID_ARG;
    }
    (void)xSemaphoreTake(s_mutex, portMAX_DELAY);
    s_policy = *policy;
    (void)xSemaphoreGive(s_mutex);
    return ESP_OK;
}

static void csv_cell(FILE *file, const char *text)
{
    fputc('"', file);
    for (const char *p = text; p && *p; ++p) {
        if (*p == '"') {
            fputc('"', file);
        }
        if (*p == '\r' || *p == '\n') {
            fputc(' ', file);
        } else {
            fputc(*p, file);
        }
    }
    fputc('"', file);
}

static void json_string(FILE *file, const char *text)
{
    fputc('"', file);
    for (const unsigned char *p = (const unsigned char *)text; p && *p; ++p) {
        switch (*p) {
        case '"':
            fputs("\\\"", file);
            break;
        case '\\':
            fputs("\\\\", file);
            break;
        default:
            if (*p >= 0x20) {
                fputc(*p, file);
            }
            break;
        }
    }
    fputc('"', file);
}

esp_err_t nh_history_export(nh_history_export_format_t format,
                            bool redact_job_names,
                            char *written_path,
                            size_t written_path_size)
{
    if (!s_initialized ||
        (format != NH_HISTORY_EXPORT_CSV &&
         format != NH_HISTORY_EXPORT_JSON)) {
        return ESP_ERR_INVALID_ARG;
    }
    char path[NH_HISTORY_PATH_LENGTH];
    const char *extension =
        format == NH_HISTORY_EXPORT_CSV ? "csv" : "json";
    if (snprintf(path, sizeof(path), "%s/history-export.%s",
                 s_directory, extension) >= (int)sizeof(path)) {
        return ESP_ERR_INVALID_SIZE;
    }
    (void)xSemaphoreTake(s_mutex, portMAX_DELAY);
    FILE *file = fopen(path, "wb");
    if (!file) {
        (void)xSemaphoreGive(s_mutex);
        return errno_to_esp();
    }
    if (format == NH_HISTORY_EXPORT_CSV) {
        fprintf(
            file,
            "# daily_jobs=%" PRIu32 ",daily_print_seconds=%" PRIu64
            ",monthly_jobs=%" PRIu32 ",monthly_print_seconds=%" PRIu64
            "\n",
            s_snapshot.daily_jobs, s_snapshot.daily_print_seconds,
            s_snapshot.monthly_jobs, s_snapshot.monthly_print_seconds);
        fputs("sequence,job_name,outcome,started_epoch,ended_epoch,"
              "duration_seconds,max_progress,material_grams_estimate,"
              "energy_wh_estimate,material_cost_micros_estimate,"
              "energy_cost_micros_estimate,wall_clock_known\n", file);
        for (size_t i = s_snapshot.recent_count; i > 0; --i) {
            const nh_history_job_t *job = &s_snapshot.recent[i - 1];
            char redacted[32];
            snprintf(redacted, sizeof(redacted), "Print-%" PRIu64,
                     job->sequence);
            fprintf(file, "%" PRIu64 ",", job->sequence);
            csv_cell(file, redact_job_names ? redacted : job->job_name);
            fprintf(file,
                    ",%s,%" PRIu64 ",%" PRIu64 ",%" PRIu32 ",%u,%" PRIu32
                    ",%" PRIu32 ",%" PRIu64 ",%" PRIu64 ",%s\n",
                    nh_history_outcome_label(job->outcome),
                    job->started_epoch, job->ended_epoch,
                    job->duration_seconds,
                    (unsigned)job->maximum_progress_percent,
                    job->material_grams_estimate,
                    job->energy_wh_estimate,
                    job->material_cost_micros_estimate,
                    job->energy_cost_micros_estimate,
                    job->wall_clock_known ? "true" : "false");
        }
    } else {
        fprintf(
            file,
            "{\"schema\":1,\"estimates_are_measured\":false,"
            "\"daily_summary\":{\"jobs\":%" PRIu32
            ",\"print_seconds\":%" PRIu64 "},"
            "\"monthly_summary\":{\"jobs\":%" PRIu32
            ",\"print_seconds\":%" PRIu64 "},\"jobs\":[",
            s_snapshot.daily_jobs, s_snapshot.daily_print_seconds,
            s_snapshot.monthly_jobs, s_snapshot.monthly_print_seconds);
        for (size_t i = s_snapshot.recent_count; i > 0; --i) {
            const nh_history_job_t *job = &s_snapshot.recent[i - 1];
            char redacted[32];
            snprintf(redacted, sizeof(redacted), "Print-%" PRIu64,
                     job->sequence);
            if (i != s_snapshot.recent_count) {
                fputc(',', file);
            }
            fputs("{\"sequence\":", file);
            fprintf(file, "%" PRIu64 ",\"job_name\":", job->sequence);
            json_string(file, redact_job_names ? redacted : job->job_name);
            fputs(",\"outcome\":", file);
            json_string(file, nh_history_outcome_label(job->outcome));
            fprintf(file,
                    ",\"started_epoch\":%" PRIu64
                    ",\"ended_epoch\":%" PRIu64
                    ",\"duration_seconds\":%" PRIu32
                    ",\"max_progress\":%u"
                    ",\"material_grams_estimate\":%" PRIu32
                    ",\"energy_wh_estimate\":%" PRIu32
                    ",\"material_cost_micros_estimate\":%" PRIu64
                    ",\"energy_cost_micros_estimate\":%" PRIu64
                    ",\"wall_clock_known\":%s}",
                    job->started_epoch, job->ended_epoch,
                    job->duration_seconds,
                    (unsigned)job->maximum_progress_percent,
                    job->material_grams_estimate,
                    job->energy_wh_estimate,
                    job->material_cost_micros_estimate,
                    job->energy_cost_micros_estimate,
                    job->wall_clock_known ? "true" : "false");
        }
        fputs("]}\n", file);
    }
    bool ok = !ferror(file) && fflush(file) == 0 &&
              fsync(fileno(file)) == 0 && fclose(file) == 0;
    (void)xSemaphoreGive(s_mutex);
    if (!ok) {
        return ESP_FAIL;
    }
    if (written_path && written_path_size > 0) {
        strlcpy(written_path, path, written_path_size);
    }
    return ESP_OK;
}

esp_err_t nh_history_backup(char *written_path, size_t written_path_size)
{
    if (!s_initialized) {
        return ESP_ERR_INVALID_STATE;
    }
    char path[NH_HISTORY_PATH_LENGTH];
    if (snprintf(path, sizeof(path), "%s/history.backup",
                 s_directory) >= (int)sizeof(path)) {
        return ESP_ERR_INVALID_SIZE;
    }
    (void)xSemaphoreTake(s_mutex, portMAX_DELAY);
    FILE *source = fopen(s_journal_path, "rb");
    FILE *target = source ? fopen(path, "wb") : NULL;
    if (!source || !target) {
        if (source) {
            fclose(source);
        }
        if (target) {
            fclose(target);
        }
        (void)xSemaphoreGive(s_mutex);
        return errno_to_esp();
    }
    uint8_t buffer[1024];
    bool ok = true;
    while (!feof(source)) {
        size_t got = fread(buffer, 1, sizeof(buffer), source);
        if (got > 0 && fwrite(buffer, 1, got, target) != got) {
            ok = false;
            break;
        }
        if (ferror(source)) {
            ok = false;
            break;
        }
    }
    ok = ok && fflush(target) == 0 && fsync(fileno(target)) == 0;
    ok = fclose(source) == 0 && ok;
    ok = fclose(target) == 0 && ok;
    (void)xSemaphoreGive(s_mutex);
    if (!ok) {
        return ESP_FAIL;
    }
    if (written_path && written_path_size > 0) {
        strlcpy(written_path, path, written_path_size);
    }
    return ESP_OK;
}

esp_err_t nh_history_maintenance_reset(const char *actor)
{
    if (!s_initialized ||
        !safe_text(actor, NH_HISTORY_DISK_TEXT_LENGTH, false)) {
        return ESP_ERR_INVALID_ARG;
    }
    (void)xSemaphoreTake(s_mutex, portMAX_DELAY);
    uint64_t now = (uint64_t)time(NULL);
    nh_history_disk_record_t record = {
        .timestamp_epoch = wall_clock_known(now) ? now : 0,
        .event_type = NH_HISTORY_EVENT_MAINTENANCE_RESET,
        .flags = wall_clock_known(now) ? NH_HISTORY_FLAG_WALL_CLOCK : 0,
    };
    strlcpy(record.text, actor, sizeof(record.text));
    esp_err_t err = append_record_locked(&record);
    (void)xSemaphoreGive(s_mutex);
    return err;
}

static esp_err_t rebuild_from_file_locked(void)
{
    bool recovered = s_snapshot.recovered_invalid_tail;
    memset(&s_snapshot, 0, sizeof(s_snapshot));
    s_snapshot.recovered_invalid_tail = recovered;
    s_snapshot.storage_ready = true;
    s_next_sequence = 1;
    s_maintenance_reset_sequence = 0;
    memset(s_maintenance_reset_actor, 0, sizeof(s_maintenance_reset_actor));
    return load_journal_locked();
}

esp_err_t nh_history_apply_retention(uint16_t keep_completed_jobs)
{
    if (!s_initialized || keep_completed_jobs > NH_HISTORY_RECENT_MAX) {
        return ESP_ERR_INVALID_ARG;
    }
    char temporary[NH_HISTORY_PATH_LENGTH];
    if (snprintf(temporary, sizeof(temporary), "%s/history.tmp",
                 s_directory) >= (int)sizeof(temporary)) {
        return ESP_ERR_INVALID_SIZE;
    }
    (void)xSemaphoreTake(s_mutex, portMAX_DELAY);
    FILE *target = fopen(temporary, "wb");
    if (!target) {
        (void)xSemaphoreGive(s_mutex);
        return errno_to_esp();
    }
    size_t keep = keep_completed_jobs;
    if (keep > s_snapshot.recent_count) {
        keep = s_snapshot.recent_count;
    }
    bool ok = true;
    bool reset_written = false;
    for (size_t i = keep; i > 0; --i) {
        const nh_history_job_t *job = &s_snapshot.recent[i - 1];
        if (!reset_written && s_maintenance_reset_sequence > 0 &&
            s_maintenance_reset_sequence < job->sequence) {
            nh_history_disk_record_t reset = {
                .sequence = s_maintenance_reset_sequence,
                .timestamp_epoch = s_snapshot.maintenance_reset_epoch,
                .event_type = NH_HISTORY_EVENT_MAINTENANCE_RESET,
                .flags = wall_clock_known(s_snapshot.maintenance_reset_epoch)
                             ? NH_HISTORY_FLAG_WALL_CLOCK
                             : 0,
            };
            strlcpy(reset.text, s_maintenance_reset_actor,
                    sizeof(reset.text));
            nh_history_record_seal(&reset);
            if (fwrite(&reset, sizeof(reset), 1, target) != 1) {
                ok = false;
                break;
            }
            reset_written = true;
        }
        nh_history_disk_record_t record = {
            .sequence = job->sequence,
            .timestamp_epoch = job->ended_epoch,
            .duration_seconds = job->duration_seconds,
            .material_grams_estimate = job->material_grams_estimate,
            .energy_wh_estimate = job->energy_wh_estimate,
            .material_cost_micros_estimate =
                job->material_cost_micros_estimate,
            .energy_cost_micros_estimate =
                job->energy_cost_micros_estimate,
            .event_type = NH_HISTORY_EVENT_FINISH,
            .outcome = (uint8_t)job->outcome,
            .maximum_progress_percent = job->maximum_progress_percent,
            .flags =
                (job->wall_clock_known ? NH_HISTORY_FLAG_WALL_CLOCK : 0) |
                (job->material_estimated
                     ? NH_HISTORY_FLAG_MATERIAL_ESTIMATE
                     : 0) |
                (job->energy_estimated ? NH_HISTORY_FLAG_ENERGY_ESTIMATE : 0),
        };
        strlcpy(record.text, job->job_name, sizeof(record.text));
        nh_history_record_seal(&record);
        if (fwrite(&record, sizeof(record), 1, target) != 1) {
            ok = false;
            break;
        }
    }
    if (ok && !reset_written && s_maintenance_reset_sequence > 0) {
        nh_history_disk_record_t reset = {
            .sequence = s_maintenance_reset_sequence,
            .timestamp_epoch = s_snapshot.maintenance_reset_epoch,
            .event_type = NH_HISTORY_EVENT_MAINTENANCE_RESET,
            .flags = wall_clock_known(s_snapshot.maintenance_reset_epoch)
                         ? NH_HISTORY_FLAG_WALL_CLOCK
                         : 0,
        };
        strlcpy(reset.text, s_maintenance_reset_actor, sizeof(reset.text));
        nh_history_record_seal(&reset);
        ok = fwrite(&reset, sizeof(reset), 1, target) == 1;
    }
    ok = ok && fflush(target) == 0 && fsync(fileno(target)) == 0;
    ok = fclose(target) == 0 && ok;
    if (ok) {
        ok = rename(temporary, s_journal_path) == 0;
    }
    esp_err_t err = ok ? rebuild_from_file_locked() : ESP_FAIL;
    (void)xSemaphoreGive(s_mutex);
    return err;
}

esp_err_t nh_history_delete_all(const char *confirmation)
{
    if (!s_initialized || !confirmation ||
        strcmp(confirmation, "DELETE PRINT HISTORY") != 0) {
        return ESP_ERR_INVALID_ARG;
    }
    (void)xSemaphoreTake(s_mutex, portMAX_DELAY);
    char temporary[NH_HISTORY_PATH_LENGTH];
    if (snprintf(temporary, sizeof(temporary), "%s/history.empty",
                 s_directory) >= (int)sizeof(temporary)) {
        (void)xSemaphoreGive(s_mutex);
        return ESP_ERR_INVALID_SIZE;
    }
    FILE *file = fopen(temporary, "wb");
    bool ok = false;
    if (file) {
        ok = fflush(file) == 0 && fsync(fileno(file)) == 0;
        ok = fclose(file) == 0 && ok;
        ok = ok && rename(temporary, s_journal_path) == 0;
    }
    if (ok) {
        memset(&s_snapshot, 0, sizeof(s_snapshot));
        s_snapshot.storage_ready = true;
        s_next_sequence = 1;
        s_maintenance_reset_sequence = 0;
        memset(s_maintenance_reset_actor, 0,
               sizeof(s_maintenance_reset_actor));
    }
    (void)xSemaphoreGive(s_mutex);
    return ok ? ESP_OK : ESP_FAIL;
}

const char *nh_history_outcome_label(nh_history_outcome_t outcome)
{
    switch (outcome) {
    case NH_HISTORY_OUTCOME_COMPLETE:
        return "complete";
    case NH_HISTORY_OUTCOME_FAILED:
        return "failed";
    case NH_HISTORY_OUTCOME_INTERRUPTED:
        return "interrupted";
    case NH_HISTORY_OUTCOME_UNKNOWN:
    default:
        return "unknown";
    }
}
