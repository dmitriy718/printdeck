#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "esp_err.h"
#include "nh_core.h"

#ifdef __cplusplus
extern "C" {
#endif

enum {
    NH_HISTORY_RECENT_MAX = 24,
    NH_HISTORY_JOB_NAME_LENGTH = 96,
    NH_HISTORY_PATH_LENGTH = 160,
};

typedef enum {
    NH_HISTORY_OUTCOME_UNKNOWN = 0,
    NH_HISTORY_OUTCOME_COMPLETE,
    NH_HISTORY_OUTCOME_FAILED,
    NH_HISTORY_OUTCOME_INTERRUPTED,
} nh_history_outcome_t;

typedef enum {
    NH_HISTORY_EXPORT_CSV = 0,
    NH_HISTORY_EXPORT_JSON,
} nh_history_export_format_t;

typedef struct {
    uint32_t material_grams_per_hour;
    uint32_t printer_watts;
    uint64_t material_cost_micros_per_kg;
    uint64_t energy_cost_micros_per_kwh;
} nh_history_estimate_policy_t;

typedef struct {
    uint64_t sequence;
    char job_name[NH_HISTORY_JOB_NAME_LENGTH];
    uint64_t started_epoch;
    uint64_t ended_epoch;
    uint32_t duration_seconds;
    uint32_t material_grams_estimate;
    uint32_t energy_wh_estimate;
    uint64_t material_cost_micros_estimate;
    uint64_t energy_cost_micros_estimate;
    uint8_t maximum_progress_percent;
    nh_history_outcome_t outcome;
    bool wall_clock_known;
    bool material_estimated;
    bool energy_estimated;
} nh_history_job_t;

typedef struct {
    nh_history_job_t recent[NH_HISTORY_RECENT_MAX];
    uint8_t recent_count;
    uint32_t total_jobs;
    uint32_t completed_jobs;
    uint32_t failed_jobs;
    uint64_t total_print_seconds;
    uint32_t daily_jobs;
    uint64_t daily_print_seconds;
    uint32_t monthly_jobs;
    uint64_t monthly_print_seconds;
    uint64_t maintenance_print_seconds;
    uint32_t maintenance_jobs;
    uint64_t maintenance_reset_epoch;
    bool maintenance_due;
    bool storage_ready;
    bool recovered_invalid_tail;
    bool active_session;
    esp_err_t last_error;
} nh_history_snapshot_t;

/**
 * Opens or creates the append-only history journal beneath storage_root.
 * A partial or invalid final record is discarded; valid earlier records are
 * preserved and reported through recovered_invalid_tail.
 */
esp_err_t nh_history_init(const char *storage_root);

/**
 * Observes printer state transitions. Only state changes append records.
 * This function never sends a printer command.
 */
esp_err_t nh_history_observe(const nh_printer_snapshot_t *printer);

esp_err_t nh_history_snapshot(nh_history_snapshot_t *snapshot);

/**
 * Configures explicit estimation inputs. Zero disables that estimate. Cost and
 * energy values are never presented as measured data.
 */
esp_err_t nh_history_set_estimate_policy(
    const nh_history_estimate_policy_t *policy);

/**
 * Writes a point-in-time export. When redact_job_names is true, stable sequence
 * labels replace job names.
 */
esp_err_t nh_history_export(nh_history_export_format_t format,
                            bool redact_job_names,
                            char *written_path,
                            size_t written_path_size);

/** Creates a byte-for-byte journal backup without altering the journal. */
esp_err_t nh_history_backup(char *written_path, size_t written_path_size);

/**
 * Appends an audited maintenance reset marker. The actor is a bounded local
 * label such as "touchscreen".
 */
esp_err_t nh_history_maintenance_reset(const char *actor);

/**
 * Explicitly rewrites the journal to retain only the newest completed jobs.
 * The operation uses a temporary file and atomic rename.
 */
esp_err_t nh_history_apply_retention(uint16_t keep_completed_jobs);

/**
 * Deletes history only when confirmation exactly equals DELETE PRINT HISTORY.
 */
esp_err_t nh_history_delete_all(const char *confirmation);

const char *nh_history_outcome_label(nh_history_outcome_t outcome);

#ifdef __cplusplus
}
#endif
