#include "nh_ui.h"

#include <inttypes.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <time.h>

#include "esp_app_desc.h"
#include "esp_check.h"
#include "esp_heap_caps.h"
#include "esp_log.h"
#include "esp_lvgl_port.h"
#include "nh_diagnostics.h"
#include "src/misc/cache/instance/lv_image_cache.h"

static const char *TAG = "nh_ui";

#define NH_COLOR_BG          lv_color_hex(0x071019)
#define NH_COLOR_SURFACE     lv_color_hex(0x0E1A27)
#define NH_COLOR_SURFACE_2   lv_color_hex(0x142434)
#define NH_COLOR_STROKE      lv_color_hex(0x22374A)
#define NH_COLOR_TEXT        lv_color_hex(0xF5FAFF)
#define NH_COLOR_MUTED       lv_color_hex(0x8FA6B8)
#define NH_COLOR_CYAN        lv_color_hex(0x42D7FF)
#define NH_COLOR_VIOLET      lv_color_hex(0x8068FF)
#define NH_COLOR_GREEN       lv_color_hex(0x55E6A5)
#define NH_COLOR_AMBER       lv_color_hex(0xFFB35B)
#define NH_COLOR_RED         lv_color_hex(0xFF687A)
#define NH_COLOR_DISABLED    lv_color_hex(0x344555)

enum {
    NH_PAGE_DASHBOARD = 0,
    NH_PAGE_JOB,
    NH_PAGE_CONTROL,
    NH_PAGE_FILES,
    NH_PAGE_CAMERA,
    NH_PAGE_SETTINGS,
    NH_PAGE_COUNT,
    NH_MAX_ACTION_BINDINGS = 48,
};

typedef struct {
    nh_action_t action;
    int32_t value;
    lv_obj_t *button;
} action_binding_t;

typedef enum {
    NH_KEYPAD_LOWER = 0,
    NH_KEYPAD_UPPER,
    NH_KEYPAD_SYMBOLS_1,
    NH_KEYPAD_SYMBOLS_2,
    NH_KEYPAD_MODE_COUNT,
} nh_keypad_mode_t;

typedef struct {
    nh_ui_config_t cfg;
    nh_printer_snapshot_t snapshot_store;
    const nh_printer_snapshot_t *snapshot;
    bool controller_sd_valid;
    char snapshot_printer_name[48];
    char snapshot_job_name[96];
    char snapshot_job_layer[48];
    char snapshot_remaining[24];
    lv_obj_t *screen;
    lv_obj_t *content;
    lv_obj_t *pages[NH_PAGE_COUNT];
    lv_obj_t *nav_buttons[NH_PAGE_COUNT];
    lv_obj_t *section_title;
    lv_obj_t *connection_pill;
    lv_obj_t *connection_label;
    lv_obj_t *clock;
    lv_obj_t *footer_status;
    lv_obj_t *dashboard_job_title;
    lv_obj_t *alert_button;
    lv_obj_t *alert_button_label;
    lv_obj_t *fleet_button_label;
    lv_obj_t *job_name;
    lv_obj_t *job_detail;
    lv_obj_t *job_progress;
    lv_obj_t *job_percent;
    lv_obj_t *job_state;
    lv_obj_t *job_page_title;
    lv_obj_t *job_page_state;
    lv_obj_t *job_page_progress;
    lv_obj_t *job_page_copy;
    lv_obj_t *history_button;
    lv_obj_t *control_motion_status;
    lv_obj_t *control_thermal_status;
    lv_obj_t *ams_environment;
    lv_obj_t *ams_trays[4];
    lv_obj_t *ams_detail_button;
    lv_obj_t *nozzle_value;
    lv_obj_t *bed_value;
    lv_obj_t *chamber_value;
    lv_obj_t *sd_value;
    lv_obj_t *sd_detail;
    lv_obj_t *sd_arc;
    lv_obj_t *sd_rescan_button;
    lv_obj_t *printer_sd_pill;
    lv_obj_t *printer_sd_label;
    lv_obj_t *files_title;
    lv_obj_t *files_list;
    lv_obj_t *files_queue_status;
    lv_obj_t *printer_identity_name;
    lv_obj_t *printer_identity_detail;
    lv_obj_t *printer_identity_pill;
    lv_obj_t *printer_identity_status;
    lv_obj_t *camera_image;
    lv_obj_t *camera_placeholder;
    lv_obj_t *camera_placeholder_copy;
    lv_obj_t *camera_status_pill;
    lv_obj_t *camera_status_label;
    lv_obj_t *ai_status_label;
    lv_obj_t *camera_detail;
    lv_obj_t *network_state;
    lv_obj_t *network_detail;
    lv_obj_t *network_setup_button;
    lv_obj_t *printer_setup_button;
    lv_obj_t *network_modal;
    lv_obj_t *network_list;
    lv_obj_t *network_status;
    lv_obj_t *network_password;
    lv_obj_t *network_keyboard;
    lv_obj_t *network_mode_button;
    lv_obj_t *printer_modal;
    lv_obj_t *printer_ip;
    lv_obj_t *printer_serial;
    lv_obj_t *printer_access_code;
    lv_obj_t *printer_keyboard;
    lv_obj_t *printer_mode_button;
    lv_obj_t *printer_active_input;
    lv_obj_t *ota_update_button;
    lv_obj_t *timezone_button_label;
    lv_obj_t *memory_value;
    lv_obj_t *modal;
    nh_network_snapshot_t network;
    bool network_valid;
    nh_printer_status_t printer;
    bool printer_valid;
    nh_camera_status_t camera;
    bool camera_valid;
    nh_ai_snapshot_t ai;
    bool ai_valid;
    nh_history_snapshot_t history;
    bool history_valid;
    nh_files_snapshot_t files;
    bool files_valid;
    nh_fleet_snapshot_t fleet;
    bool fleet_valid;
    uint8_t *file_thumbnail_data;
    lv_image_dsc_t file_thumbnail_dsc;
    uint64_t pending_queue_id;
    lv_image_dsc_t camera_frames[2];
    uint8_t camera_frame_index;
    uint32_t camera_frame_count;
    bool camera_requested_active;
    char selected_ssid[NH_NETWORK_SSID_MAX_LENGTH + 1];
    nh_action_t pending_action;
    int32_t pending_value;
    action_binding_t bindings[NH_MAX_ACTION_BINDINGS];
    size_t binding_count;
    uint8_t active_page;
    nh_keypad_mode_t keypad_mode;
} nh_ui_state_t;

static nh_ui_state_t s_ui;

static lv_obj_t *make_plain_button(
    lv_obj_t *parent, int x, int y, int w, int h,
    const char *text, lv_color_t accent);

static void store_snapshot(const nh_printer_snapshot_t *source)
{
    if (!source) {
        s_ui.snapshot = NULL;
        return;
    }

    bool keep_controller_sd = s_ui.controller_sd_valid;
    bool sd_mounted = s_ui.snapshot_store.sd_mounted;
    esp_err_t sd_mount_error = s_ui.snapshot_store.sd_mount_error;
    uint64_t sd_capacity_bytes = s_ui.snapshot_store.sd_capacity_bytes;
    uint64_t sd_free_bytes = s_ui.snapshot_store.sd_free_bytes;
    s_ui.snapshot_store = *source;
    if (keep_controller_sd) {
        s_ui.snapshot_store.sd_mounted = sd_mounted;
        s_ui.snapshot_store.sd_mount_error = sd_mount_error;
        s_ui.snapshot_store.sd_capacity_bytes = sd_capacity_bytes;
        s_ui.snapshot_store.sd_free_bytes = sd_free_bytes;
    }
    strlcpy(s_ui.snapshot_printer_name,
            source->printer_name ? source->printer_name : "Bambu Lab P1S",
            sizeof(s_ui.snapshot_printer_name));
    strlcpy(s_ui.snapshot_job_name,
            source->job_name ? source->job_name : "Waiting for printer status",
            sizeof(s_ui.snapshot_job_name));
    strlcpy(s_ui.snapshot_job_layer,
            source->job_layer ? source->job_layer : "Layer -- / --",
            sizeof(s_ui.snapshot_job_layer));
    strlcpy(s_ui.snapshot_remaining,
            source->remaining ? source->remaining : "--h --m",
            sizeof(s_ui.snapshot_remaining));
    s_ui.snapshot_store.printer_name = s_ui.snapshot_printer_name;
    s_ui.snapshot_store.job_name = s_ui.snapshot_job_name;
    s_ui.snapshot_store.job_layer = s_ui.snapshot_job_layer;
    s_ui.snapshot_store.remaining = s_ui.snapshot_remaining;
    s_ui.snapshot = &s_ui.snapshot_store;
}

static const char *s_page_titles[NH_PAGE_COUNT] = {
    "OVERVIEW", "PRINT JOB", "MANUAL CONTROL", "PRINT FILES",
    "CAMERA", "SYSTEM"
};

static const char *const s_keypad_lower[] = {
    "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "\n",
    "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z", ""
};

static const char *const s_keypad_upper[] = {
    "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "\n",
    "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z", ""
};

static const char *const s_keypad_symbols_1[] = {
    "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "-", "_", "@", "\n",
    "!", "#", "$", "%", "&", "*", "+", "=", ".", ",", "?", "/", ":", ""
};

static const char *const s_keypad_symbols_2[] = {
    ";", "<", ">", "[", "]", "{", "}", "(", ")", "^", "~", "|", "\\", "\n",
    "`", "'", "\"", "-", "_", "@", "!", "#", "$", "%", "&", "*", "+", ""
};

static const char *const *const s_keypad_maps[NH_KEYPAD_MODE_COUNT] = {
    s_keypad_lower,
    s_keypad_upper,
    s_keypad_symbols_1,
    s_keypad_symbols_2,
};

static const char *const s_keypad_mode_labels[NH_KEYPAD_MODE_COUNT] = {
    "abc", "ABC", "123", "#+="
};

static void set_obj_box(lv_obj_t *obj, lv_color_t bg, int radius, int border)
{
    lv_obj_remove_style_all(obj);
    lv_obj_set_style_bg_color(obj, bg, 0);
    lv_obj_set_style_bg_opa(obj, LV_OPA_COVER, 0);
    lv_obj_set_style_radius(obj, radius, 0);
    lv_obj_set_style_border_width(obj, border, 0);
    lv_obj_set_style_border_color(obj, NH_COLOR_STROKE, 0);
    lv_obj_set_style_pad_all(obj, 0, 0);
    lv_obj_set_style_shadow_width(obj, 0, 0);
}

static lv_obj_t *make_label(lv_obj_t *parent, const char *text,
                            const lv_font_t *font, lv_color_t color)
{
    lv_obj_t *label = lv_label_create(parent);
    lv_label_set_text(label, text);
    lv_obj_set_style_text_font(label, font, 0);
    lv_obj_set_style_text_color(label, color, 0);
    lv_obj_set_style_text_letter_space(label, 0, 0);
    return label;
}

static lv_obj_t *make_card(lv_obj_t *parent, int x, int y, int w, int h)
{
    lv_obj_t *card = lv_obj_create(parent);
    set_obj_box(card, NH_COLOR_SURFACE, 16, 1);
    lv_obj_set_pos(card, x, y);
    lv_obj_set_size(card, w, h);
    lv_obj_clear_flag(card, LV_OBJ_FLAG_SCROLLABLE);
    return card;
}

static lv_obj_t *make_pill(lv_obj_t *parent, int x, int y, int w, int h,
                           lv_color_t color, const char *text)
{
    lv_obj_t *pill = lv_obj_create(parent);
    set_obj_box(pill, lv_color_darken(color, 190), h / 2, 1);
    lv_obj_set_style_border_color(pill, color, 0);
    lv_obj_set_pos(pill, x, y);
    lv_obj_set_size(pill, w, h);
    lv_obj_clear_flag(pill, LV_OBJ_FLAG_SCROLLABLE);

    lv_obj_t *label = make_label(pill, text, &lv_font_montserrat_12, color);
    lv_obj_center(label);
    return pill;
}

static lv_obj_t *make_camera_icon(lv_obj_t *parent, int x, int y,
                                  int width, int height, lv_color_t color)
{
    lv_obj_t *body = lv_obj_create(parent);
    set_obj_box(body, lv_color_darken(color, 210), height / 5, 1);
    lv_obj_set_style_border_color(body, color, 0);
    lv_obj_set_pos(body, x, y + height / 5);
    lv_obj_set_size(body, width, height - height / 5);
    lv_obj_clear_flag(body, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_clear_flag(body, LV_OBJ_FLAG_CLICKABLE);

    lv_obj_t *top = lv_obj_create(parent);
    set_obj_box(top, color, 2, 0);
    lv_obj_set_pos(top, x + width / 5, y);
    lv_obj_set_size(top, width / 3, height / 4);
    lv_obj_clear_flag(top, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_clear_flag(top, LV_OBJ_FLAG_CLICKABLE);

    lv_obj_t *lens = lv_obj_create(body);
    int lens_size = (height * 2) / 5;
    set_obj_box(lens, NH_COLOR_BG, lens_size / 2, 1);
    lv_obj_set_style_border_color(lens, color, 0);
    lv_obj_set_size(lens, lens_size, lens_size);
    lv_obj_center(lens);
    lv_obj_clear_flag(lens, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_clear_flag(lens, LV_OBJ_FLAG_CLICKABLE);
    return body;
}

static void update_footer(const char *text, lv_color_t color)
{
    if (!s_ui.footer_status) {
        return;
    }
    lv_label_set_text(s_ui.footer_status, text);
    lv_obj_set_style_text_color(s_ui.footer_status, color, 0);
}

static void clock_timer_cb(lv_timer_t *timer)
{
    (void)timer;
    if (!s_ui.clock) {
        return;
    }

    time_t now = time(NULL);
    struct tm local_time;
    if (now < 1700000000 || !localtime_r(&now, &local_time)) {
        lv_label_set_text(s_ui.clock, "--:--");
        lv_obj_set_style_text_color(s_ui.clock, NH_COLOR_MUTED, 0);
        return;
    }

    char text[20];
    int hour_12 = local_time.tm_hour % 12;
    if (hour_12 == 0) {
        hour_12 = 12;
    }
    snprintf(text, sizeof(text), "%d:%02d %s",
             hour_12, local_time.tm_min,
             local_time.tm_hour < 12 ? "AM" : "PM");
    lv_label_set_text(s_ui.clock, text);
    lv_obj_set_style_text_color(s_ui.clock, NH_COLOR_TEXT, 0);
}

static void health_timer_cb(lv_timer_t *timer)
{
    (void)timer;
    if (!s_ui.memory_value) {
        return;
    }

    nh_diagnostics_snapshot_t health;
    nh_diagnostics_snapshot(&health);
    char text[64];
    if (health.tracked_task_count > 0) {
        snprintf(text, sizeof(text), "I %u/%uK  S %uK %s",
                 (unsigned)(health.internal_free_bytes / 1024U),
                 (unsigned)(health.internal_minimum_bytes / 1024U),
                 (unsigned)(health.minimum_task_stack_bytes / 1024U),
                 health.minimum_stack_task);
    } else {
        snprintf(text, sizeof(text), "I %u/%uK  S measuring",
                 (unsigned)(health.internal_free_bytes / 1024U),
                 (unsigned)(health.internal_minimum_bytes / 1024U));
    }
    lv_label_set_text(s_ui.memory_value, text);
    lv_obj_set_style_text_color(
        s_ui.memory_value,
        health.internal_minimum_bytes < 64U * 1024U ||
                (health.tracked_task_count > 0 &&
                 health.minimum_task_stack_bytes < 1024U)
            ? NH_COLOR_RED
            : NH_COLOR_TEXT,
        0);
}

static void clear_sensitive_textarea(lv_obj_t *textarea)
{
    if (!textarea) {
        return;
    }
    const char *text = lv_textarea_get_text(textarea);
    if (text) {
        nh_secure_zero((void *)text, strlen(text));
    }
    lv_textarea_set_text(textarea, "");
}

static void dispatch_action(nh_action_t action, int32_t value)
{
    if (!s_ui.cfg.action_handler) {
        update_footer("No command transport is installed", NH_COLOR_AMBER);
        return;
    }

    esp_err_t err = s_ui.cfg.action_handler(action, value, s_ui.cfg.action_ctx);
    if (err == ESP_OK) {
        char status[96];
        snprintf(status, sizeof(status), "Command queued: %s",
                 nh_action_label(action));
        update_footer(status, NH_COLOR_GREEN);
    } else if (err == ESP_ERR_INVALID_STATE) {
        update_footer("Blocked safely: connect the P1S before using this control",
                      NH_COLOR_AMBER);
    } else if (err == ESP_ERR_NOT_SUPPORTED) {
        update_footer("This control is disabled in this firmware; no command was sent",
                      NH_COLOR_AMBER);
    } else {
        char status[96];
        snprintf(status, sizeof(status), "Command failed: %s", esp_err_to_name(err));
        update_footer(status, NH_COLOR_RED);
    }
}

static void close_modal(void)
{
    if (s_ui.file_thumbnail_dsc.header.magic == LV_IMAGE_HEADER_MAGIC) {
        lv_image_cache_drop(&s_ui.file_thumbnail_dsc);
    }
    memset(&s_ui.file_thumbnail_dsc, 0,
           sizeof(s_ui.file_thumbnail_dsc));
    free(s_ui.file_thumbnail_data);
    s_ui.file_thumbnail_data = NULL;
    if (s_ui.modal) {
        lv_obj_delete(s_ui.modal);
        s_ui.modal = NULL;
    }
    s_ui.pending_action = NH_ACTION_NONE;
    s_ui.pending_value = 0;
    s_ui.pending_queue_id = 0;
}

static void modal_cancel_cb(lv_event_t *event)
{
    (void)event;
    close_modal();
    update_footer("Cancel print dismissed", NH_COLOR_MUTED);
}

static void modal_confirm_cb(lv_event_t *event)
{
    (void)event;
    nh_action_t action = s_ui.pending_action;
    int32_t value = s_ui.pending_value;
    close_modal();
    dispatch_action(action, value);
}

static const char *alert_severity_label(nh_alert_severity_t severity)
{
    switch (severity) {
    case NH_ALERT_CRITICAL:
        return "CRITICAL";
    case NH_ALERT_ERROR:
        return "ERROR";
    case NH_ALERT_WARNING:
        return "WARNING";
    case NH_ALERT_INFO:
    default:
        return "INFO";
    }
}

static void alert_dismiss_cb(lv_event_t *event)
{
    const char *raw_code = lv_event_get_user_data(event);
    if (!raw_code || !s_ui.cfg.alert_dismiss) {
        update_footer("Local alert dismissal is unavailable", NH_COLOR_AMBER);
        return;
    }
    esp_err_t err =
        s_ui.cfg.alert_dismiss(raw_code, s_ui.cfg.printer_ctx);
    if (err == ESP_OK) {
        update_footer(
            "Alert hidden locally; printer resolution is unchanged",
            NH_COLOR_MUTED);
    } else {
        update_footer("Alert could not be dismissed", NH_COLOR_AMBER);
    }
    close_modal();
}

static void alert_modal_close_cb(lv_event_t *event)
{
    (void)event;
    close_modal();
    update_footer("Alert center closed", NH_COLOR_MUTED);
}

static void history_operation_result(esp_err_t err, const char *success)
{
    if (err == ESP_OK) {
        update_footer(success, NH_COLOR_GREEN);
    } else if (err == ESP_ERR_INVALID_STATE ||
               err == ESP_ERR_NOT_FOUND) {
        update_footer("History storage is unavailable", NH_COLOR_AMBER);
    } else {
        char message[96];
        snprintf(message, sizeof(message), "History operation failed: %s",
                 esp_err_to_name(err));
        update_footer(message, NH_COLOR_RED);
    }
}

static void history_export_csv_cb(lv_event_t *event)
{
    (void)event;
    esp_err_t err = s_ui.cfg.history_export
                        ? s_ui.cfg.history_export(
                              NH_HISTORY_EXPORT_CSV, true,
                              s_ui.cfg.history_ctx)
                        : ESP_ERR_NOT_SUPPORTED;
    history_operation_result(
        err, "Redacted CSV history exported to controller SD");
}

static void history_export_json_cb(lv_event_t *event)
{
    (void)event;
    esp_err_t err = s_ui.cfg.history_export
                        ? s_ui.cfg.history_export(
                              NH_HISTORY_EXPORT_JSON, true,
                              s_ui.cfg.history_ctx)
                        : ESP_ERR_NOT_SUPPORTED;
    history_operation_result(
        err, "Redacted JSON history exported to controller SD");
}

static void history_backup_cb(lv_event_t *event)
{
    (void)event;
    esp_err_t err = s_ui.cfg.history_backup
                        ? s_ui.cfg.history_backup(s_ui.cfg.history_ctx)
                        : ESP_ERR_NOT_SUPPORTED;
    history_operation_result(err, "History journal backup created");
}

static void history_modal_close_cb(lv_event_t *event)
{
    (void)event;
    close_modal();
    update_footer("Print history closed", NH_COLOR_MUTED);
}

static void show_history_cb(lv_event_t *event)
{
    (void)event;
    if (s_ui.modal) {
        return;
    }
    s_ui.modal = lv_obj_create(s_ui.screen);
    set_obj_box(s_ui.modal, lv_color_hex(0x020609), 0, 0);
    lv_obj_set_style_bg_opa(s_ui.modal, LV_OPA_80, 0);
    lv_obj_set_size(s_ui.modal, 800, 480);
    lv_obj_set_pos(s_ui.modal, 0, 0);
    lv_obj_move_foreground(s_ui.modal);
    lv_obj_clear_flag(s_ui.modal, LV_OBJ_FLAG_SCROLLABLE);

    lv_obj_t *dialog = make_card(s_ui.modal, 35, 24, 730, 432);
    lv_obj_set_style_border_color(dialog, NH_COLOR_VIOLET, 0);
    lv_obj_t *eyebrow = make_label(
        dialog, "LOCAL HISTORY / ESTIMATES / MAINTENANCE",
        &lv_font_montserrat_12, NH_COLOR_VIOLET);
    lv_obj_set_pos(eyebrow, 20, 14);

    char title_text[96];
    if (!s_ui.history_valid || !s_ui.history.storage_ready) {
        snprintf(title_text, sizeof(title_text),
                 "History waits for controller SD");
    } else {
        snprintf(title_text, sizeof(title_text),
                 "%lu jobs / %.1f print hours",
                 (unsigned long)s_ui.history.total_jobs,
                 (double)s_ui.history.total_print_seconds / 3600.0);
    }
    lv_obj_t *title = make_label(
        dialog, title_text, &lv_font_montserrat_20, NH_COLOR_TEXT);
    lv_obj_set_pos(title, 20, 37);

    lv_obj_t *close = make_plain_button(
        dialog, 584, 14, 126, 40, "CLOSE", NH_COLOR_MUTED);
    lv_obj_add_event_cb(
        close, history_modal_close_cb, LV_EVENT_CLICKED, NULL);

    char summary[160];
    snprintf(
        summary, sizeof(summary),
        "Today %lu / Month %lu / Maintenance %lu jobs, %.1f h%s%s",
        (unsigned long)s_ui.history.daily_jobs,
        (unsigned long)s_ui.history.monthly_jobs,
        (unsigned long)s_ui.history.maintenance_jobs,
        (double)s_ui.history.maintenance_print_seconds / 3600.0,
        s_ui.history.maintenance_due ? " / SERVICE DUE" : "",
        s_ui.history.recovered_invalid_tail
            ? " / tail recovered"
            : "");
    lv_obj_t *metrics = make_label(
        dialog, summary, &lv_font_montserrat_12, NH_COLOR_MUTED);
    lv_obj_set_pos(metrics, 20, 68);
    lv_obj_set_width(metrics, 690);
    lv_label_set_long_mode(metrics, LV_LABEL_LONG_DOT);

    lv_obj_t *list = lv_obj_create(dialog);
    set_obj_box(list, NH_COLOR_SURFACE_2, 10, 0);
    lv_obj_set_pos(list, 18, 94);
    lv_obj_set_size(list, 694, 250);
    lv_obj_set_style_pad_all(list, 8, 0);

    if (!s_ui.history_valid || s_ui.history.recent_count == 0) {
        lv_obj_t *empty = make_label(
            list,
            "No completed local sessions yet. Estimates remain unavailable "
            "until explicit rates are configured.",
            &lv_font_montserrat_14, NH_COLOR_MUTED);
        lv_obj_set_width(empty, 650);
        lv_label_set_long_mode(empty, LV_LABEL_LONG_WRAP);
    } else {
        for (uint8_t i = 0; i < s_ui.history.recent_count; ++i) {
            const nh_history_job_t *job = &s_ui.history.recent[i];
            lv_obj_t *row = lv_obj_create(list);
            set_obj_box(row, NH_COLOR_SURFACE, 8, 1);
            lv_obj_set_pos(row, 0, i * 72);
            lv_obj_set_size(row, 660, 64);
            lv_obj_clear_flag(row, LV_OBJ_FLAG_SCROLLABLE);

            lv_color_t color =
                job->outcome == NH_HISTORY_OUTCOME_COMPLETE
                    ? NH_COLOR_GREEN
                    : (job->outcome == NH_HISTORY_OUTCOME_FAILED
                           ? NH_COLOR_RED
                           : NH_COLOR_AMBER);
            lv_obj_t *name = make_label(
                row, job->job_name, &lv_font_montserrat_14, NH_COLOR_TEXT);
            lv_obj_set_pos(name, 10, 8);
            lv_obj_set_width(name, 430);
            lv_label_set_long_mode(name, LV_LABEL_LONG_DOT);

            char detail[160];
            snprintf(
                detail, sizeof(detail),
                "%s / %.1f h / max %u%%%s%s",
                nh_history_outcome_label(job->outcome),
                (double)job->duration_seconds / 3600.0,
                (unsigned)job->maximum_progress_percent,
                job->material_estimated ? " / material est." : "",
                job->energy_estimated ? " / energy est." : "");
            lv_obj_t *copy = make_label(
                row, detail, &lv_font_montserrat_12, color);
            lv_obj_set_pos(copy, 10, 34);
            lv_obj_set_width(copy, 620);
            lv_label_set_long_mode(copy, LV_LABEL_LONG_DOT);
        }
    }

    lv_obj_t *csv = make_plain_button(
        dialog, 18, 360, 208, 50, "EXPORT REDACTED CSV", NH_COLOR_CYAN);
    lv_obj_add_event_cb(
        csv, history_export_csv_cb, LV_EVENT_CLICKED, NULL);
    lv_obj_t *json = make_plain_button(
        dialog, 243, 360, 208, 50, "EXPORT REDACTED JSON", NH_COLOR_VIOLET);
    lv_obj_add_event_cb(
        json, history_export_json_cb, LV_EVENT_CLICKED, NULL);
    lv_obj_t *backup = make_plain_button(
        dialog, 468, 360, 244, 50, "BACK UP JOURNAL", NH_COLOR_GREEN);
    lv_obj_add_event_cb(
        backup, history_backup_cb, LV_EVENT_CLICKED, NULL);
}

static void show_alert_center_cb(lv_event_t *event)
{
    (void)event;
    if (s_ui.modal || !s_ui.snapshot) {
        return;
    }

    s_ui.modal = lv_obj_create(s_ui.screen);
    set_obj_box(s_ui.modal, lv_color_hex(0x020609), 0, 0);
    lv_obj_set_style_bg_opa(s_ui.modal, LV_OPA_80, 0);
    lv_obj_set_size(s_ui.modal, 800, 480);
    lv_obj_set_pos(s_ui.modal, 0, 0);
    lv_obj_move_foreground(s_ui.modal);
    lv_obj_clear_flag(s_ui.modal, LV_OBJ_FLAG_SCROLLABLE);

    lv_obj_t *dialog = make_card(s_ui.modal, 45, 30, 710, 420);
    lv_obj_set_style_border_color(
        dialog,
        s_ui.snapshot->active_alert_count ? NH_COLOR_RED : NH_COLOR_CYAN, 0);
    lv_obj_t *eyebrow = make_label(
        dialog, "LOCAL HMS / PRINT HISTORY",
        &lv_font_montserrat_12, NH_COLOR_CYAN);
    lv_obj_set_pos(eyebrow, 20, 16);
    lv_obj_t *title = make_label(
        dialog,
        s_ui.snapshot->active_alert_count
            ? "Printer needs attention"
            : "No active printer alerts",
        &lv_font_montserrat_20, NH_COLOR_TEXT);
    lv_obj_set_pos(title, 20, 40);

    lv_obj_t *close = make_plain_button(
        dialog, 560, 18, 126, 40, "CLOSE", NH_COLOR_MUTED);
    lv_obj_add_event_cb(close, alert_modal_close_cb, LV_EVENT_CLICKED, NULL);

    lv_obj_t *list = lv_obj_create(dialog);
    set_obj_box(list, NH_COLOR_SURFACE_2, 10, 0);
    lv_obj_set_pos(list, 18, 78);
    lv_obj_set_size(list, 674, 320);
    lv_obj_set_style_pad_all(list, 8, 0);

    if (s_ui.snapshot->alert_count == 0) {
        lv_obj_t *empty = make_label(
            list,
            "PrintDeck has not observed an HMS or print-error code in this session.",
            &lv_font_montserrat_14, NH_COLOR_MUTED);
        lv_obj_set_width(empty, 630);
        return;
    }

    for (uint8_t i = 0; i < s_ui.snapshot->alert_count; ++i) {
        const nh_alert_t *alert = &s_ui.snapshot->alerts[i];
        lv_obj_t *row = lv_obj_create(list);
        set_obj_box(row, NH_COLOR_SURFACE, 8, 1);
        lv_obj_set_style_border_color(
            row, alert->active ? NH_COLOR_RED : NH_COLOR_STROKE, 0);
        lv_obj_set_pos(row, 0, i * 100);
        lv_obj_set_size(row, 642, alert->active ? 92 : 66);
        lv_obj_clear_flag(row, LV_OBJ_FLAG_SCROLLABLE);

        char heading[120];
        snprintf(heading, sizeof(heading), "%s  /  %s  /  %s",
                 alert->active
                     ? (alert->dismissed_locally ? "HIDDEN LOCALLY" : "ACTIVE")
                     : "RESOLVED",
                 alert_severity_label(alert->severity), alert->raw_code);
        lv_obj_t *code = make_label(
            row, heading, &lv_font_montserrat_12,
            alert->active ? NH_COLOR_RED : NH_COLOR_MUTED);
        lv_obj_set_pos(code, 10, 8);
        lv_obj_set_width(code, 500);
        lv_label_set_long_mode(code, LV_LABEL_LONG_DOT);

        lv_obj_t *message = make_label(
            row, alert->title, &lv_font_montserrat_14, NH_COLOR_TEXT);
        lv_obj_set_pos(message, 10, 31);
        lv_obj_set_width(message, alert->active ? 470 : 610);
        lv_label_set_long_mode(message, LV_LABEL_LONG_DOT);

        if (alert->active && !alert->dismissed_locally) {
            lv_obj_t *dismiss = make_plain_button(
                row, 500, 25, 124, 42, "HIDE LOCAL", NH_COLOR_AMBER);
            lv_obj_add_event_cb(
                dismiss, alert_dismiss_cb, LV_EVENT_CLICKED,
                (void *)alert->raw_code);
            lv_obj_t *guidance = make_label(
                row, alert->guidance, &lv_font_montserrat_12, NH_COLOR_MUTED);
            lv_obj_set_pos(guidance, 10, 57);
            lv_obj_set_width(guidance, 470);
            lv_label_set_long_mode(guidance, LV_LABEL_LONG_DOT);
        }
    }
}

static void ams_modal_close_cb(lv_event_t *event)
{
    (void)event;
    close_modal();
    update_footer("Material center closed", NH_COLOR_MUTED);
}

static void show_ams_center_cb(lv_event_t *event)
{
    (void)event;
    if (s_ui.modal || !s_ui.snapshot) {
        return;
    }
    s_ui.modal = lv_obj_create(s_ui.screen);
    set_obj_box(s_ui.modal, lv_color_hex(0x020609), 0, 0);
    lv_obj_set_style_bg_opa(s_ui.modal, LV_OPA_80, 0);
    lv_obj_set_size(s_ui.modal, 800, 480);
    lv_obj_set_pos(s_ui.modal, 0, 0);
    lv_obj_move_foreground(s_ui.modal);
    lv_obj_clear_flag(s_ui.modal, LV_OBJ_FLAG_SCROLLABLE);

    lv_obj_t *dialog = make_card(s_ui.modal, 45, 30, 710, 420);
    lv_obj_set_style_border_color(dialog, NH_COLOR_VIOLET, 0);
    lv_obj_t *eyebrow = make_label(
        dialog, "READ-ONLY MATERIAL TELEMETRY",
        &lv_font_montserrat_12, NH_COLOR_CYAN);
    lv_obj_set_pos(eyebrow, 20, 16);
    lv_obj_t *title = make_label(
        dialog,
        s_ui.snapshot->ams.known ? "AMS material command center"
                                : "AMS has not been reported",
        &lv_font_montserrat_20, NH_COLOR_TEXT);
    lv_obj_set_pos(title, 20, 40);
    lv_obj_t *close = make_plain_button(
        dialog, 560, 18, 126, 40, "CLOSE", NH_COLOR_MUTED);
    lv_obj_add_event_cb(close, ams_modal_close_cb, LV_EVENT_CLICKED, NULL);

    lv_obj_t *list = lv_obj_create(dialog);
    set_obj_box(list, NH_COLOR_SURFACE_2, 10, 0);
    lv_obj_set_pos(list, 18, 78);
    lv_obj_set_size(list, 674, 320);
    lv_obj_set_style_pad_all(list, 8, 0);

    int y = 0;
    for (uint8_t i = 0; i < s_ui.snapshot->ams.unit_count; ++i) {
        const nh_ams_unit_t *unit = &s_ui.snapshot->ams.units[i];
        char line[120];
        if (unit->humidity_known && unit->temperature_known) {
            snprintf(
                line, sizeof(line),
                "AMS %u  /  HUMIDITY INDEX %u  /  %.1f C%s",
                (unsigned)unit->id, (unsigned)unit->humidity_index,
                unit->temperature_c,
                unit->material_at_risk ? "  /  CHECK MATERIAL" : "");
        } else {
            snprintf(line, sizeof(line),
                     "AMS %u  /  HUMIDITY INDEX --  /  TEMPERATURE --",
                     (unsigned)unit->id);
        }
        lv_obj_t *unit_label = make_label(
            list, line, &lv_font_montserrat_14,
            unit->material_at_risk ? NH_COLOR_AMBER : NH_COLOR_CYAN);
        lv_obj_set_pos(unit_label, 4, y);
        lv_obj_set_width(unit_label, 630);
        y += 28;

        for (uint8_t tray_index = 0;
             tray_index < s_ui.snapshot->ams.tray_count; ++tray_index) {
            const nh_ams_tray_t *tray =
                &s_ui.snapshot->ams.trays[tray_index];
            if (tray->unit_id != unit->id) {
                continue;
            }
            char tray_line[150];
            snprintf(
                tray_line, sizeof(tray_line),
                "  SLOT %u  /  %-8s  /  %s  /  %s%u%%  /  %s",
                (unsigned)tray->tray_id,
                tray->present ? tray->material : "EMPTY",
                tray->color_rgba[0] ? tray->color_rgba : "NO COLOR",
                tray->remaining_known ? "" : "--",
                tray->remaining_known
                    ? (unsigned)tray->remaining_percent : 0U,
                tray->rfid_present ? "RFID" : "MANUAL/UNKNOWN");
            lv_obj_t *tray_label = make_label(
                list, tray_line, &lv_font_montserrat_12,
                tray->present ? NH_COLOR_TEXT : NH_COLOR_MUTED);
            lv_obj_set_pos(tray_label, 4, y);
            lv_obj_set_width(tray_label, 630);
            lv_label_set_long_mode(tray_label, LV_LABEL_LONG_DOT);
            y += 24;
        }
        y += 8;
    }

    const nh_ams_tray_t *external =
        &s_ui.snapshot->ams.trays[NH_AMS_MAX_TRAYS];
    char external_line[120];
    snprintf(
        external_line, sizeof(external_line), "EXTERNAL SPOOL  /  %s  /  %s",
        external->present && external->material[0]
            ? external->material : "EMPTY OR UNKNOWN",
        external->color_rgba[0] ? external->color_rgba : "NO COLOR");
    lv_obj_t *external_label = make_label(
        list, external_line, &lv_font_montserrat_14,
        external->present ? NH_COLOR_TEXT : NH_COLOR_MUTED);
    lv_obj_set_pos(external_label, 4, y);
    lv_obj_set_width(external_label, 630);
}

static lv_obj_t *make_plain_button(lv_obj_t *parent, int x, int y, int w, int h,
                                   const char *text, lv_color_t accent)
{
    lv_obj_t *button = lv_button_create(parent);
    set_obj_box(button, NH_COLOR_SURFACE_2, 12, 1);
    lv_obj_set_style_border_color(button, NH_COLOR_STROKE, 0);
    lv_obj_set_style_bg_color(button, lv_color_darken(accent, 205), LV_STATE_PRESSED);
    lv_obj_set_style_border_color(button, accent, LV_STATE_PRESSED);
    lv_obj_set_style_bg_color(button, lv_color_hex(0x111C25), LV_STATE_DISABLED);
    lv_obj_set_style_border_color(button, NH_COLOR_DISABLED, LV_STATE_DISABLED);
    lv_obj_set_pos(button, x, y);
    lv_obj_set_size(button, w, h);

    lv_obj_t *label = make_label(button, text, &lv_font_montserrat_14, NH_COLOR_TEXT);
    lv_obj_set_style_text_color(label, NH_COLOR_DISABLED, LV_STATE_DISABLED);
    lv_obj_center(label);
    return button;
}

static void close_network_modal(void)
{
    if (s_ui.network_modal) {
        clear_sensitive_textarea(s_ui.network_password);
        lv_obj_delete(s_ui.network_modal);
    }
    s_ui.network_modal = NULL;
    s_ui.network_list = NULL;
    s_ui.network_status = NULL;
    s_ui.network_password = NULL;
    s_ui.network_keyboard = NULL;
    s_ui.network_mode_button = NULL;
}

static void network_modal_close_cb(lv_event_t *event)
{
    (void)event;
    close_network_modal();
    update_footer("Network setup closed", NH_COLOR_MUTED);
}

static void network_connect_submit_cb(lv_event_t *event)
{
    (void)event;
    if (!s_ui.cfg.network_connect || s_ui.selected_ssid[0] == '\0') {
        update_footer("Wi-Fi connection service is unavailable", NH_COLOR_RED);
        return;
    }

    const char *password = s_ui.network_password
                               ? lv_textarea_get_text(s_ui.network_password)
                               : "";
    esp_err_t err = s_ui.cfg.network_connect(
        s_ui.selected_ssid, password, s_ui.cfg.network_ctx);
    if (err == ESP_OK) {
        char message[96];
        snprintf(message, sizeof(message), "Connecting to %s", s_ui.selected_ssid);
        close_network_modal();
        update_footer(message, NH_COLOR_CYAN);
    } else {
        char message[96];
        snprintf(message, sizeof(message), "Wi-Fi connection failed: %s",
                 esp_err_to_name(err));
        update_footer(message, NH_COLOR_RED);
    }
}

static void network_keypad_cb(lv_event_t *event)
{
    if (!s_ui.network_password) {
        return;
    }

    lv_obj_t *keypad = lv_event_get_target_obj(event);
    uint32_t button = lv_buttonmatrix_get_selected_button(keypad);
    const char *text = lv_buttonmatrix_get_button_text(keypad, button);
    if (text) {
        lv_textarea_add_text(s_ui.network_password, text);
    }
}

static void network_keypad_mode_cb(lv_event_t *event)
{
    (void)event;
    if (!s_ui.network_keyboard || !s_ui.network_mode_button) {
        return;
    }

    s_ui.keypad_mode =
        (nh_keypad_mode_t)((s_ui.keypad_mode + 1) % NH_KEYPAD_MODE_COUNT);
    lv_buttonmatrix_set_map(s_ui.network_keyboard,
                            s_keypad_maps[s_ui.keypad_mode]);
    lv_obj_t *label = lv_obj_get_child(s_ui.network_mode_button, 0);
    if (label) {
        lv_label_set_text(label, s_keypad_mode_labels[s_ui.keypad_mode]);
    }
}

static void network_keypad_space_cb(lv_event_t *event)
{
    (void)event;
    if (s_ui.network_password) {
        lv_textarea_add_char(s_ui.network_password, ' ');
    }
}

static void network_keypad_delete_cb(lv_event_t *event)
{
    (void)event;
    if (s_ui.network_password) {
        lv_textarea_delete_char(s_ui.network_password);
    }
}

static void show_network_password_dialog(void)
{
    if (!s_ui.network_modal) {
        return;
    }

    lv_obj_clean(s_ui.network_modal);
    s_ui.network_list = NULL;
    s_ui.network_status = NULL;

    /*
     * Keep every control in fixed screen coordinates. In particular, the
     * keyboard must never rely on LVGL's focus scrolling on this 800x480
     * landscape display.
     */
    lv_obj_t *dialog = make_card(s_ui.network_modal, 18, 12, 764, 456);
    lv_obj_set_style_border_color(dialog, NH_COLOR_CYAN, 0);

    lv_obj_t *eyebrow = make_label(dialog, "SECURED NETWORK",
                                   &lv_font_montserrat_12, NH_COLOR_CYAN);
    lv_obj_set_pos(eyebrow, 20, 12);

    lv_obj_t *title = make_label(dialog, s_ui.selected_ssid,
                                 &lv_font_montserrat_22, NH_COLOR_TEXT);
    lv_obj_set_pos(title, 20, 31);

    s_ui.network_password = lv_textarea_create(dialog);
    lv_obj_set_pos(s_ui.network_password, 20, 64);
    lv_obj_set_size(s_ui.network_password, 530, 48);
    lv_textarea_set_one_line(s_ui.network_password, true);
    lv_textarea_set_password_mode(s_ui.network_password, true);
    lv_textarea_set_max_length(s_ui.network_password, 64);
    lv_textarea_set_placeholder_text(s_ui.network_password, "Wi-Fi password");
    lv_obj_clear_flag(s_ui.network_password, LV_OBJ_FLAG_SCROLL_ON_FOCUS);
    lv_obj_set_style_bg_color(s_ui.network_password, NH_COLOR_SURFACE_2, 0);
    lv_obj_set_style_border_color(s_ui.network_password, NH_COLOR_STROKE, 0);
    lv_obj_set_style_text_color(s_ui.network_password, NH_COLOR_TEXT, 0);
    lv_obj_add_event_cb(s_ui.network_password, network_connect_submit_cb,
                        LV_EVENT_READY, NULL);

    lv_obj_t *back = make_plain_button(dialog, 570, 116, 174, 36,
                                       "CANCEL", NH_COLOR_MUTED);
    lv_obj_add_event_cb(back, network_modal_close_cb, LV_EVENT_CLICKED, NULL);
    lv_obj_t *connect = make_plain_button(dialog, 570, 64, 174, 48,
                                          "CONNECT", NH_COLOR_CYAN);
    lv_obj_set_style_border_color(connect, NH_COLOR_CYAN, 0);
    lv_obj_add_event_cb(connect, network_connect_submit_cb,
                        LV_EVENT_CLICKED, NULL);

    s_ui.keypad_mode = NH_KEYPAD_LOWER;
    s_ui.network_keyboard = lv_buttonmatrix_create(dialog);
    set_obj_box(s_ui.network_keyboard, NH_COLOR_SURFACE_2, 12, 1);
    lv_obj_set_pos(s_ui.network_keyboard, 20, 176);
    lv_obj_set_size(s_ui.network_keyboard, 724, 112);
    lv_obj_clear_flag(s_ui.network_keyboard, LV_OBJ_FLAG_SCROLL_ON_FOCUS);
    lv_buttonmatrix_set_map(s_ui.network_keyboard,
                            s_keypad_maps[s_ui.keypad_mode]);
    lv_obj_set_style_bg_color(s_ui.network_keyboard,
                              lv_color_hex(0x183448), LV_PART_ITEMS);
    lv_obj_set_style_bg_color(s_ui.network_keyboard,
                              lv_color_hex(0x22516A),
                              LV_PART_ITEMS | LV_STATE_PRESSED);
    lv_obj_set_style_text_color(s_ui.network_keyboard,
                                NH_COLOR_TEXT, LV_PART_ITEMS);
    lv_obj_set_style_border_width(s_ui.network_keyboard, 1, LV_PART_ITEMS);
    lv_obj_set_style_border_color(s_ui.network_keyboard,
                                  NH_COLOR_STROKE, LV_PART_ITEMS);
    lv_obj_set_style_radius(s_ui.network_keyboard, 7, LV_PART_ITEMS);
    lv_obj_set_style_pad_all(s_ui.network_keyboard, 5, LV_PART_MAIN);
    lv_obj_set_style_pad_row(s_ui.network_keyboard, 5, LV_PART_MAIN);
    lv_obj_set_style_pad_column(s_ui.network_keyboard, 4, LV_PART_MAIN);
    lv_obj_add_event_cb(s_ui.network_keyboard, network_keypad_cb,
                        LV_EVENT_VALUE_CHANGED, NULL);

    s_ui.network_mode_button =
        make_plain_button(dialog, 20, 120, 140, 44, "abc", NH_COLOR_VIOLET);
    lv_obj_add_event_cb(s_ui.network_mode_button, network_keypad_mode_cb,
                        LV_EVENT_CLICKED, NULL);
    lv_obj_t *space =
        make_plain_button(dialog, 175, 120, 230, 44, "SPACE", NH_COLOR_CYAN);
    lv_obj_add_event_cb(space, network_keypad_space_cb,
                        LV_EVENT_CLICKED, NULL);
    lv_obj_t *delete_button =
        make_plain_button(dialog, 420, 120, 130, 44, "DELETE", NH_COLOR_AMBER);
    lv_obj_add_event_cb(delete_button, network_keypad_delete_cb,
                        LV_EVENT_CLICKED, NULL);
}

static void network_ap_selected_cb(lv_event_t *event)
{
    uintptr_t index = (uintptr_t)lv_event_get_user_data(event);
    if (!s_ui.network_valid ||
        index >= s_ui.network.access_point_count) {
        return;
    }

    const nh_access_point_t *access_point = &s_ui.network.access_points[index];
    strlcpy(s_ui.selected_ssid, access_point->ssid, sizeof(s_ui.selected_ssid));
    if (!access_point->secured) {
        s_ui.network_password = NULL;
        network_connect_submit_cb(NULL);
        return;
    }
    show_network_password_dialog();
}

static void close_printer_modal(void)
{
    if (s_ui.printer_modal) {
        clear_sensitive_textarea(s_ui.printer_access_code);
        lv_obj_delete(s_ui.printer_modal);
    }
    s_ui.printer_modal = NULL;
    s_ui.printer_ip = NULL;
    s_ui.printer_serial = NULL;
    s_ui.printer_access_code = NULL;
    s_ui.printer_keyboard = NULL;
    s_ui.printer_mode_button = NULL;
    s_ui.printer_active_input = NULL;
}

static void printer_modal_close_cb(lv_event_t *event)
{
    (void)event;
    close_printer_modal();
    update_footer("P1S pairing closed", NH_COLOR_MUTED);
}

static void select_printer_input(lv_obj_t *input)
{
    s_ui.printer_active_input = input;
    lv_obj_t *inputs[] = {
        s_ui.printer_ip,
        s_ui.printer_serial,
        s_ui.printer_access_code,
    };
    for (size_t i = 0; i < sizeof(inputs) / sizeof(inputs[0]); ++i) {
        if (inputs[i]) {
            lv_obj_set_style_border_color(
                inputs[i], inputs[i] == input ? NH_COLOR_CYAN : NH_COLOR_STROKE,
                0);
        }
    }
}

static void printer_input_selected_cb(lv_event_t *event)
{
    select_printer_input(lv_event_get_target_obj(event));
}

static void printer_keypad_cb(lv_event_t *event)
{
    if (!s_ui.printer_active_input) {
        return;
    }
    lv_obj_t *keypad = lv_event_get_target_obj(event);
    uint32_t button = lv_buttonmatrix_get_selected_button(keypad);
    const char *text = lv_buttonmatrix_get_button_text(keypad, button);
    if (text) {
        lv_textarea_add_text(s_ui.printer_active_input, text);
    }
}

static void printer_keypad_mode_cb(lv_event_t *event)
{
    (void)event;
    if (!s_ui.printer_keyboard || !s_ui.printer_mode_button) {
        return;
    }
    s_ui.keypad_mode =
        (nh_keypad_mode_t)((s_ui.keypad_mode + 1) % NH_KEYPAD_MODE_COUNT);
    lv_buttonmatrix_set_map(s_ui.printer_keyboard,
                            s_keypad_maps[s_ui.keypad_mode]);
    lv_obj_t *label = lv_obj_get_child(s_ui.printer_mode_button, 0);
    if (label) {
        lv_label_set_text(label, s_keypad_mode_labels[s_ui.keypad_mode]);
    }
}

static void printer_keypad_delete_cb(lv_event_t *event)
{
    (void)event;
    if (s_ui.printer_active_input) {
        lv_textarea_delete_char(s_ui.printer_active_input);
    }
}

static void printer_pair_submit_cb(lv_event_t *event)
{
    (void)event;
    if (!s_ui.cfg.printer_pair || !s_ui.printer_ip ||
        !s_ui.printer_serial || !s_ui.printer_access_code) {
        update_footer("P1S pairing service is unavailable", NH_COLOR_RED);
        return;
    }

    const char *ip_address = lv_textarea_get_text(s_ui.printer_ip);
    const char *serial = lv_textarea_get_text(s_ui.printer_serial);
    const char *access_code = lv_textarea_get_text(s_ui.printer_access_code);
    esp_err_t err = s_ui.cfg.printer_pair(
        ip_address, serial, access_code, s_ui.cfg.printer_ctx);
    if (err == ESP_OK) {
        close_printer_modal();
        update_footer("Validating P1S profile before it is saved",
                      NH_COLOR_CYAN);
    } else if (err == ESP_ERR_INVALID_ARG) {
        update_footer(
            "Check the P1S IP, device ID, and eight-character access code",
            NH_COLOR_AMBER);
    } else {
        char message[96];
        snprintf(message, sizeof(message), "Could not queue P1S pairing: %s",
                 esp_err_to_name(err));
        update_footer(message, NH_COLOR_RED);
    }
}

static lv_obj_t *make_printer_input(lv_obj_t *parent, int x, int width,
                                    const char *placeholder, int max_length,
                                    bool password)
{
    lv_obj_t *input = lv_textarea_create(parent);
    lv_obj_set_pos(input, x, 84);
    lv_obj_set_size(input, width, 48);
    lv_textarea_set_one_line(input, true);
    lv_textarea_set_password_mode(input, password);
    lv_textarea_set_max_length(input, max_length);
    lv_textarea_set_placeholder_text(input, placeholder);
    lv_obj_clear_flag(input, LV_OBJ_FLAG_SCROLL_ON_FOCUS);
    lv_obj_set_style_bg_color(input, NH_COLOR_SURFACE_2, 0);
    lv_obj_set_style_border_color(input, NH_COLOR_STROKE, 0);
    lv_obj_set_style_text_color(input, NH_COLOR_TEXT, 0);
    lv_obj_add_event_cb(input, printer_input_selected_cb,
                        LV_EVENT_CLICKED, NULL);
    return input;
}

static void show_printer_setup_cb(lv_event_t *event)
{
    (void)event;
    if (s_ui.printer_modal) {
        return;
    }
    if (!s_ui.network_valid ||
        s_ui.network.state != NH_NETWORK_CONNECTED) {
        update_footer("Connect the controller to Wi-Fi before pairing the P1S",
                      NH_COLOR_AMBER);
        return;
    }

    s_ui.printer_modal = lv_obj_create(s_ui.screen);
    set_obj_box(s_ui.printer_modal, lv_color_hex(0x020609), 0, 0);
    lv_obj_set_style_bg_opa(s_ui.printer_modal, LV_OPA_80, 0);
    lv_obj_set_size(s_ui.printer_modal, 800, 480);
    lv_obj_set_pos(s_ui.printer_modal, 0, 0);
    lv_obj_move_foreground(s_ui.printer_modal);
    lv_obj_clear_flag(s_ui.printer_modal, LV_OBJ_FLAG_SCROLLABLE);

    lv_obj_t *dialog = make_card(s_ui.printer_modal, 18, 12, 764, 456);
    lv_obj_set_style_border_color(dialog, NH_COLOR_VIOLET, 0);
    lv_obj_t *eyebrow = make_label(dialog, "PINNED LOCAL TLS / MQTT",
                                   &lv_font_montserrat_12, NH_COLOR_VIOLET);
    lv_obj_set_pos(eyebrow, 20, 12);
    lv_obj_t *title = make_label(dialog, "Pair Bambu Lab P1S",
                                 &lv_font_montserrat_22, NH_COLOR_TEXT);
    lv_obj_set_pos(title, 20, 31);

    lv_obj_t *ip_label = make_label(dialog, "PRINTER IP",
                                    &lv_font_montserrat_12, NH_COLOR_MUTED);
    lv_obj_set_pos(ip_label, 20, 66);
    lv_obj_t *serial_label = make_label(dialog, "DEVICE ID",
                                        &lv_font_montserrat_12, NH_COLOR_MUTED);
    lv_obj_set_pos(serial_label, 242, 66);
    lv_obj_t *code_label = make_label(dialog, "LAN ACCESS CODE",
                                      &lv_font_montserrat_12, NH_COLOR_MUTED);
    lv_obj_set_pos(code_label, 554, 66);

    s_ui.printer_ip = make_printer_input(
        dialog, 20, 210, "192.168.1.x", NH_PRINTER_IP_MAX_LENGTH, false);
    s_ui.printer_serial = make_printer_input(
        dialog, 242, 300, "P1S device ID", NH_PRINTER_SERIAL_MAX_LENGTH, false);
    s_ui.printer_access_code = make_printer_input(
        dialog, 554, 190, "8+ characters",
        NH_PRINTER_ACCESS_CODE_MAX_LENGTH, true);

    if (s_ui.printer_valid) {
        lv_textarea_set_text(s_ui.printer_ip, s_ui.printer.ip_address);
        lv_textarea_set_text(s_ui.printer_serial, s_ui.printer.serial);
    }

    s_ui.keypad_mode = NH_KEYPAD_UPPER;
    s_ui.printer_mode_button =
        make_plain_button(dialog, 20, 143, 140, 44, "ABC", NH_COLOR_VIOLET);
    lv_obj_add_event_cb(s_ui.printer_mode_button, printer_keypad_mode_cb,
                        LV_EVENT_CLICKED, NULL);
    lv_obj_t *delete_button =
        make_plain_button(dialog, 175, 143, 140, 44, "DELETE", NH_COLOR_AMBER);
    lv_obj_add_event_cb(delete_button, printer_keypad_delete_cb,
                        LV_EVENT_CLICKED, NULL);
    lv_obj_t *cancel =
        make_plain_button(dialog, 330, 143, 140, 44, "CANCEL", NH_COLOR_MUTED);
    lv_obj_add_event_cb(cancel, printer_modal_close_cb,
                        LV_EVENT_CLICKED, NULL);
    lv_obj_t *save = make_plain_button(
        dialog, 485, 143, 259, 44, "SAVE & CONNECT", NH_COLOR_CYAN);
    lv_obj_set_style_border_color(save, NH_COLOR_CYAN, 0);
    lv_obj_add_event_cb(save, printer_pair_submit_cb,
                        LV_EVENT_CLICKED, NULL);

    s_ui.printer_keyboard = lv_buttonmatrix_create(dialog);
    set_obj_box(s_ui.printer_keyboard, NH_COLOR_SURFACE_2, 12, 1);
    lv_obj_set_pos(s_ui.printer_keyboard, 20, 199);
    lv_obj_set_size(s_ui.printer_keyboard, 724, 112);
    lv_obj_clear_flag(s_ui.printer_keyboard, LV_OBJ_FLAG_SCROLL_ON_FOCUS);
    lv_buttonmatrix_set_map(s_ui.printer_keyboard,
                            s_keypad_maps[s_ui.keypad_mode]);
    lv_obj_set_style_bg_color(s_ui.printer_keyboard,
                              lv_color_hex(0x183448), LV_PART_ITEMS);
    lv_obj_set_style_bg_color(s_ui.printer_keyboard,
                              lv_color_hex(0x22516A),
                              LV_PART_ITEMS | LV_STATE_PRESSED);
    lv_obj_set_style_text_color(s_ui.printer_keyboard,
                                NH_COLOR_TEXT, LV_PART_ITEMS);
    lv_obj_set_style_border_width(s_ui.printer_keyboard, 1, LV_PART_ITEMS);
    lv_obj_set_style_border_color(s_ui.printer_keyboard,
                                  NH_COLOR_STROKE, LV_PART_ITEMS);
    lv_obj_set_style_radius(s_ui.printer_keyboard, 7, LV_PART_ITEMS);
    lv_obj_set_style_pad_all(s_ui.printer_keyboard, 5, LV_PART_MAIN);
    lv_obj_set_style_pad_row(s_ui.printer_keyboard, 5, LV_PART_MAIN);
    lv_obj_set_style_pad_column(s_ui.printer_keyboard, 4, LV_PART_MAIN);
    lv_obj_add_event_cb(s_ui.printer_keyboard, printer_keypad_cb,
                        LV_EVENT_VALUE_CHANGED, NULL);

    lv_obj_t *security = make_label(
        dialog,
        "The access code stays on this controller. The P1S certificate chain "
        "and device ID are verified before telemetry or controls unlock.",
        &lv_font_montserrat_12, NH_COLOR_MUTED);
    lv_label_set_long_mode(security, LV_LABEL_LONG_WRAP);
    lv_obj_set_width(security, 724);
    lv_obj_set_pos(security, 20, 330);
    select_printer_input(s_ui.printer_access_code);
}

static void rebuild_network_list(void)
{
    if (!s_ui.network_list) {
        return;
    }

    lv_obj_clean(s_ui.network_list);
    if (!s_ui.network_valid ||
        s_ui.network.state == NH_NETWORK_INITIALIZING ||
        s_ui.network.state == NH_NETWORK_SCANNING) {
        lv_obj_t *label = make_label(s_ui.network_list, "Scanning for nearby networks...",
                                     &lv_font_montserrat_14, NH_COLOR_MUTED);
        lv_obj_center(label);
        return;
    }

    if (s_ui.network.access_point_count == 0) {
        lv_obj_t *label = make_label(s_ui.network_list, "No Wi-Fi networks found",
                                     &lv_font_montserrat_14, NH_COLOR_AMBER);
        lv_obj_center(label);
        return;
    }

    for (uint8_t i = 0; i < s_ui.network.access_point_count; ++i) {
        const nh_access_point_t *access_point = &s_ui.network.access_points[i];
        char row_text[80];
        snprintf(row_text, sizeof(row_text), "%s    %d dBm%s",
                 access_point->ssid, access_point->rssi,
                 access_point->secured ? "  /  SECURED" : "");
        lv_obj_t *row = make_plain_button(
            s_ui.network_list, 8, 8 + i * 48, 548, 40,
            row_text, NH_COLOR_CYAN);
        lv_obj_add_event_cb(row, network_ap_selected_cb, LV_EVENT_CLICKED,
                            (void *)(uintptr_t)i);
    }
}

static void network_scan_cb(lv_event_t *event)
{
    (void)event;
    if (!s_ui.cfg.network_scan) {
        update_footer("Wi-Fi scanner is unavailable", NH_COLOR_RED);
        return;
    }
    if (s_ui.network_valid &&
        s_ui.network.state == NH_NETWORK_SCANNING) {
        update_footer("Wi-Fi scan already in progress", NH_COLOR_MUTED);
        return;
    }
    esp_err_t err = s_ui.cfg.network_scan(s_ui.cfg.network_ctx);
    if (err == ESP_OK) {
        update_footer("Scanning for Wi-Fi networks", NH_COLOR_CYAN);
        rebuild_network_list();
    } else {
        char message[96];
        snprintf(message, sizeof(message), "Wi-Fi scan failed: %s",
                 esp_err_to_name(err));
        update_footer(message, NH_COLOR_RED);
    }
}

static void show_network_setup_cb(lv_event_t *event)
{
    (void)event;
    if (s_ui.network_modal) {
        return;
    }

    s_ui.network_modal = lv_obj_create(s_ui.screen);
    set_obj_box(s_ui.network_modal, lv_color_hex(0x020609), 0, 0);
    lv_obj_set_style_bg_opa(s_ui.network_modal, LV_OPA_80, 0);
    lv_obj_set_size(s_ui.network_modal, 800, 480);
    lv_obj_set_pos(s_ui.network_modal, 0, 0);
    lv_obj_move_foreground(s_ui.network_modal);
    lv_obj_clear_flag(s_ui.network_modal, LV_OBJ_FLAG_SCROLLABLE);

    lv_obj_t *dialog = make_card(s_ui.network_modal, 85, 45, 630, 390);
    lv_obj_set_style_border_color(dialog, NH_COLOR_CYAN, 0);
    lv_obj_t *eyebrow = make_label(dialog, "ESP32-C6 / HOSTED WI-FI",
                                   &lv_font_montserrat_12, NH_COLOR_CYAN);
    lv_obj_set_pos(eyebrow, 22, 17);
    lv_obj_t *title = make_label(dialog, "Choose a network",
                                 &lv_font_montserrat_24, NH_COLOR_TEXT);
    lv_obj_set_pos(title, 22, 40);

    s_ui.network_list = lv_obj_create(dialog);
    set_obj_box(s_ui.network_list, NH_COLOR_SURFACE_2, 12, 1);
    lv_obj_set_pos(s_ui.network_list, 22, 80);
    lv_obj_set_size(s_ui.network_list, 586, 224);
    lv_obj_set_scroll_dir(s_ui.network_list, LV_DIR_VER);
    lv_obj_set_scrollbar_mode(s_ui.network_list, LV_SCROLLBAR_MODE_ACTIVE);

    s_ui.network_status = make_label(dialog, "Select an access point to continue",
                                     &lv_font_montserrat_12, NH_COLOR_MUTED);
    lv_obj_set_pos(s_ui.network_status, 22, 316);

    lv_obj_t *close = make_plain_button(dialog, 22, 339, 180, 40,
                                        "CLOSE", NH_COLOR_MUTED);
    lv_obj_add_event_cb(close, network_modal_close_cb, LV_EVENT_CLICKED, NULL);
    lv_obj_t *scan = make_plain_button(dialog, 428, 339, 180, 40,
                                       "SCAN AGAIN", NH_COLOR_CYAN);
    lv_obj_add_event_cb(scan, network_scan_cb, LV_EVENT_CLICKED, NULL);

    rebuild_network_list();
    if (!s_ui.network_valid ||
        (s_ui.network.access_point_count == 0 &&
         s_ui.network.state != NH_NETWORK_INITIALIZING &&
         s_ui.network.state != NH_NETWORK_SCANNING)) {
        network_scan_cb(NULL);
    }
}

static void show_confirmation(const action_binding_t *binding)
{
    if (s_ui.modal || !binding) {
        return;
    }

    s_ui.pending_action = binding->action;
    s_ui.pending_value = binding->value;

    s_ui.modal = lv_obj_create(s_ui.screen);
    set_obj_box(s_ui.modal, lv_color_hex(0x020609), 0, 0);
    lv_obj_set_style_bg_opa(s_ui.modal, LV_OPA_80, 0);
    lv_obj_set_size(s_ui.modal, 800, 480);
    lv_obj_set_pos(s_ui.modal, 0, 0);
    lv_obj_move_foreground(s_ui.modal);
    lv_obj_clear_flag(s_ui.modal, LV_OBJ_FLAG_SCROLLABLE);

    lv_obj_t *dialog = make_card(s_ui.modal, 205, 125, 390, 230);
    lv_obj_set_style_border_color(dialog, NH_COLOR_RED, 0);

    lv_obj_t *eyebrow = make_label(dialog, "DESTRUCTIVE ACTION",
                                   &lv_font_montserrat_12, NH_COLOR_RED);
    lv_obj_set_pos(eyebrow, 24, 22);

    lv_obj_t *title = make_label(dialog, "Cancel the active print?",
                                 &lv_font_montserrat_24, NH_COLOR_TEXT);
    lv_obj_set_pos(title, 24, 51);

    lv_obj_t *body = make_label(
        dialog,
        "The printer will stop and the current build cannot be resumed.",
        &lv_font_montserrat_14, NH_COLOR_MUTED);
    lv_label_set_long_mode(body, LV_LABEL_LONG_WRAP);
    lv_obj_set_width(body, 340);
    lv_obj_set_pos(body, 24, 91);

    lv_obj_t *keep = make_plain_button(dialog, 24, 160, 160, 46,
                                       "KEEP PRINTING", NH_COLOR_CYAN);
    lv_obj_add_event_cb(keep, modal_cancel_cb, LV_EVENT_CLICKED, NULL);

    lv_obj_t *cancel = make_plain_button(dialog, 202, 160, 164, 46,
                                         "CANCEL PRINT", NH_COLOR_RED);
    lv_obj_set_style_border_color(cancel, NH_COLOR_RED, 0);
    lv_obj_add_event_cb(cancel, modal_confirm_cb, LV_EVENT_CLICKED, NULL);
}

static void action_button_cb(lv_event_t *event)
{
    action_binding_t *binding = lv_event_get_user_data(event);
    if (!binding) {
        return;
    }

    if (nh_action_requires_confirmation(binding->action)) {
        show_confirmation(binding);
    } else {
        dispatch_action(binding->action, binding->value);
    }
}

static lv_obj_t *make_action_button(lv_obj_t *parent, int x, int y, int w, int h,
                                    const char *text, lv_color_t accent,
                                    nh_action_t action, int32_t value)
{
    lv_obj_t *button = make_plain_button(parent, x, y, w, h, text, accent);
    if (s_ui.binding_count >= NH_MAX_ACTION_BINDINGS) {
        ESP_LOGE(TAG, "Action binding pool exhausted");
        lv_obj_add_state(button, LV_STATE_DISABLED);
        return button;
    }

    action_binding_t *binding = &s_ui.bindings[s_ui.binding_count++];
    *binding = (action_binding_t){
        .action = action,
        .value = value,
        .button = button,
    };
    lv_obj_add_event_cb(button, action_button_cb, LV_EVENT_CLICKED, binding);
    return button;
}

static void reset_camera_view(void)
{
    if (!s_ui.camera_image) {
        return;
    }
    lv_image_set_src(s_ui.camera_image, NULL);
    for (size_t i = 0; i < 2; ++i) {
        if (s_ui.camera_frames[i].header.magic == LV_IMAGE_HEADER_MAGIC) {
            lv_image_cache_drop(&s_ui.camera_frames[i]);
        }
        memset(&s_ui.camera_frames[i], 0, sizeof(s_ui.camera_frames[i]));
    }
    s_ui.camera_frame_index = 0;
    s_ui.camera_frame_count = 0;
    lv_obj_add_flag(s_ui.camera_image, LV_OBJ_FLAG_HIDDEN);
    if (s_ui.camera_placeholder) {
        lv_obj_clear_flag(s_ui.camera_placeholder, LV_OBJ_FLAG_HIDDEN);
    }
}

static bool camera_profile_ready(void)
{
    return s_ui.printer_valid &&
           s_ui.printer.state == NH_PRINTER_ONLINE &&
           s_ui.printer.profile_ready;
}

static esp_err_t set_camera_requested(bool active)
{
    if (s_ui.camera_requested_active == active) {
        return ESP_OK;
    }
    if (!s_ui.cfg.camera_set_active) {
        return ESP_ERR_INVALID_STATE;
    }
    esp_err_t err =
        s_ui.cfg.camera_set_active(active, s_ui.cfg.camera_ctx);
    if (err == ESP_OK) {
        s_ui.camera_requested_active = active;
    }
    return err;
}

static void nav_button_cb(lv_event_t *event)
{
    uintptr_t page_index = (uintptr_t)lv_event_get_user_data(event);
    if (page_index >= NH_PAGE_COUNT) {
        return;
    }

    for (size_t i = 0; i < NH_PAGE_COUNT; ++i) {
        if (i == page_index) {
            lv_obj_clear_flag(s_ui.pages[i], LV_OBJ_FLAG_HIDDEN);
            lv_obj_set_style_bg_color(s_ui.nav_buttons[i], lv_color_hex(0x163444), 0);
            lv_obj_set_style_border_color(s_ui.nav_buttons[i], NH_COLOR_CYAN, 0);
        } else {
            lv_obj_add_flag(s_ui.pages[i], LV_OBJ_FLAG_HIDDEN);
            lv_obj_set_style_bg_color(s_ui.nav_buttons[i], NH_COLOR_SURFACE, 0);
            lv_obj_set_style_border_color(s_ui.nav_buttons[i], NH_COLOR_SURFACE, 0);
        }
    }

    s_ui.active_page = page_index;
    lv_label_set_text(s_ui.section_title, s_page_titles[page_index]);
    bool camera_ready =
        page_index == NH_PAGE_CAMERA && camera_profile_ready();
    esp_err_t camera_err = set_camera_requested(camera_ready);
    if (page_index != NH_PAGE_CAMERA) {
        reset_camera_view();
    }
    if (camera_err != ESP_OK) {
        update_footer("Camera service is not ready", NH_COLOR_AMBER);
        return;
    }
    update_footer(
        page_index == NH_PAGE_CAMERA
            ? (camera_ready
                   ? "P1S camera uses the encrypted local LAN connection"
                   : "Camera waits for an online, validated P1S profile")
            : "PrintDeck ready",
        page_index == NH_PAGE_CAMERA
            ? (camera_ready ? NH_COLOR_CYAN : NH_COLOR_AMBER)
            : NH_COLOR_MUTED);
}

static lv_obj_t *add_card_title(lv_obj_t *card, const char *eyebrow,
                                const char *title)
{
    lv_obj_t *small = make_label(card, eyebrow, &lv_font_montserrat_12, NH_COLOR_CYAN);
    lv_obj_set_pos(small, 20, 17);
    lv_obj_t *large = make_label(card, title, &lv_font_montserrat_20, NH_COLOR_TEXT);
    lv_obj_set_pos(large, 20, 42);
    return large;
}

static void fleet_modal_close_cb(lv_event_t *event)
{
    (void)event;
    close_modal();
    update_footer("Fleet overview closed", NH_COLOR_MUTED);
}

static void show_fleet_cb(lv_event_t *event)
{
    (void)event;
    if (s_ui.modal) {
        return;
    }
    s_ui.modal = lv_obj_create(s_ui.screen);
    set_obj_box(s_ui.modal, lv_color_hex(0x020609), 0, 0);
    lv_obj_set_style_bg_opa(s_ui.modal, LV_OPA_80, 0);
    lv_obj_set_size(s_ui.modal, 800, 480);
    lv_obj_clear_flag(s_ui.modal, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_move_foreground(s_ui.modal);

    lv_obj_t *dialog = make_card(s_ui.modal, 115, 55, 570, 370);
    add_card_title(dialog, "LOCAL FLEET", "Attention-first printers");
    lv_obj_t *list = lv_obj_create(dialog);
    set_obj_box(list, NH_COLOR_SURFACE_2, 10, 0);
    lv_obj_set_pos(list, 18, 82);
    lv_obj_set_size(list, 534, 222);
    lv_obj_set_style_pad_all(list, 8, 0);

    if (!s_ui.fleet_valid || s_ui.fleet.count == 0) {
        lv_obj_t *empty = make_label(
            list,
            "No observed printers. Pair a printer on the System page.",
            &lv_font_montserrat_14, NH_COLOR_MUTED);
        lv_label_set_long_mode(empty, LV_LABEL_LONG_WRAP);
        lv_obj_set_width(empty, 490);
    } else {
        for (uint8_t i = 0; i < s_ui.fleet.count; ++i) {
            const nh_fleet_printer_t *printer =
                &s_ui.fleet.printers[i];
            char row[180];
            snprintf(
                row, sizeof(row),
                "%s  /  %s\n%s  %u%%  /  %s%s",
                printer->name,
                nh_fleet_attention_label(nh_fleet_attention(printer)),
                nh_job_label(printer->job),
                (unsigned)printer->progress_percent,
                printer->identity_confirmed
                    ? "IDENTITY CONFIRMED"
                    : "OBSERVED ONLY",
                printer->active_transport ? "  /  ACTIVE" : "");
            lv_obj_t *label = make_label(
                list, row, &lv_font_montserrat_14,
                nh_fleet_attention(printer) <= NH_FLEET_ATTENTION_PAUSED
                    ? NH_COLOR_AMBER
                    : NH_COLOR_TEXT);
            lv_obj_set_pos(label, 0, (int)i * 54);
            lv_obj_set_width(label, 490);
        }
    }
    lv_obj_t *note = make_label(
        dialog,
        "Only the active transport can show live detail. Writes stay disabled "
        "unless model and firmware capabilities are qualified.",
        &lv_font_montserrat_12, NH_COLOR_MUTED);
    lv_label_set_long_mode(note, LV_LABEL_LONG_WRAP);
    lv_obj_set_width(note, 390);
    lv_obj_set_pos(note, 20, 316);
    lv_obj_t *close = make_plain_button(
        dialog, 430, 315, 120, 38, "CLOSE", NH_COLOR_CYAN);
    lv_obj_add_event_cb(
        close, fleet_modal_close_cb, LV_EVENT_CLICKED, NULL);
}

static void build_dashboard_page(lv_obj_t *page)
{
    lv_obj_t *job = make_card(page, 0, 0, 420, 205);
    s_ui.dashboard_job_title =
        add_card_title(job, "CURRENT JOB", "Waiting for P1S");
    lv_obj_set_width(s_ui.dashboard_job_title, 270);
    lv_label_set_long_mode(s_ui.dashboard_job_title, LV_LABEL_LONG_DOT);

    s_ui.job_state = make_pill(job, 20, 79, 92, 28, NH_COLOR_GREEN, "READY");
    s_ui.job_name = make_label(job, "No active print",
                               &lv_font_montserrat_16, NH_COLOR_MUTED);
    lv_obj_set_pos(s_ui.job_name, 125, 84);
    lv_obj_set_width(s_ui.job_name, 175);

    s_ui.job_progress = lv_bar_create(job);
    lv_obj_set_pos(s_ui.job_progress, 20, 140);
    lv_obj_set_size(s_ui.job_progress, 270, 12);
    lv_bar_set_range(s_ui.job_progress, 0, 100);
    lv_bar_set_value(s_ui.job_progress, 0, LV_ANIM_OFF);
    lv_obj_set_style_bg_color(s_ui.job_progress, NH_COLOR_SURFACE_2, LV_PART_MAIN);
    lv_obj_set_style_bg_color(s_ui.job_progress, NH_COLOR_CYAN, LV_PART_INDICATOR);
    lv_obj_set_style_radius(s_ui.job_progress, 6, LV_PART_MAIN);
    lv_obj_set_style_radius(s_ui.job_progress, 6, LV_PART_INDICATOR);

    s_ui.job_detail = make_label(job, "Layer -- / --  |  --h --m remaining",
                                 &lv_font_montserrat_12, NH_COLOR_MUTED);
    lv_obj_set_pos(s_ui.job_detail, 20, 165);

    lv_obj_t *progress_arc = lv_arc_create(job);
    lv_obj_set_pos(progress_arc, 308, 55);
    lv_obj_set_size(progress_arc, 88, 88);
    lv_arc_set_range(progress_arc, 0, 100);
    lv_arc_set_value(progress_arc, 0);
    lv_arc_set_rotation(progress_arc, 135);
    lv_arc_set_bg_angles(progress_arc, 0, 270);
    lv_obj_remove_style(progress_arc, NULL, LV_PART_KNOB);
    lv_obj_set_style_arc_width(progress_arc, 9, LV_PART_MAIN);
    lv_obj_set_style_arc_width(progress_arc, 9, LV_PART_INDICATOR);
    lv_obj_set_style_arc_color(progress_arc, NH_COLOR_STROKE, LV_PART_MAIN);
    lv_obj_set_style_arc_color(progress_arc, NH_COLOR_VIOLET, LV_PART_INDICATOR);

    s_ui.job_percent = make_label(job, "0%", &lv_font_montserrat_20, NH_COLOR_TEXT);
    lv_obj_align_to(s_ui.job_percent, progress_arc, LV_ALIGN_CENTER, 0, 0);

    lv_obj_t *temps = make_card(page, 432, 0, 256, 205);
    add_card_title(temps, "THERMALS", "Live temperatures");

    const char *names[] = {"NOZZLE", "BED", "CHAMBER"};
    lv_color_t colors[] = {NH_COLOR_AMBER, NH_COLOR_VIOLET, NH_COLOR_CYAN};
    lv_obj_t **values[] = {&s_ui.nozzle_value, &s_ui.bed_value, &s_ui.chamber_value};
    for (int i = 0; i < 3; ++i) {
        int y = 78 + i * 38;
        lv_obj_t *dot = lv_obj_create(temps);
        set_obj_box(dot, colors[i], 4, 0);
        lv_obj_set_pos(dot, 20, y + 4);
        lv_obj_set_size(dot, 8, 8);

        lv_obj_t *name = make_label(temps, names[i], &lv_font_montserrat_12, NH_COLOR_MUTED);
        lv_obj_set_pos(name, 39, y);

        *values[i] = make_label(temps, "-- / -- C", &lv_font_montserrat_16, NH_COLOR_TEXT);
        lv_obj_align(*values[i], LV_ALIGN_TOP_RIGHT, -19, y - 3);
    }

    lv_obj_t *quick = make_card(page, 0, 216, 688, 124);
    lv_obj_t *title = make_label(quick, "QUICK CONTROL",
                                 &lv_font_montserrat_12, NH_COLOR_CYAN);
    lv_obj_set_pos(title, 18, 14);
    s_ui.alert_button = make_plain_button(
        quick, 512, 8, 158, 32, "ALERTS 0", NH_COLOR_CYAN);
    s_ui.alert_button_label = lv_obj_get_child(s_ui.alert_button, 0);
    lv_obj_add_event_cb(
        s_ui.alert_button, show_alert_center_cb, LV_EVENT_CLICKED, NULL);

    make_action_button(quick, 18, 47, 150, 58, "PRINT FILES",
                       NH_COLOR_CYAN, NH_ACTION_OPEN_FILE, 0);
    make_action_button(quick, 184, 47, 150, 58, "CHAMBER LIGHT",
                       NH_COLOR_VIOLET, NH_ACTION_LIGHT_TOGGLE, 0);
    lv_obj_t *fleet = make_plain_button(
        quick, 350, 47, 150, 58, "FLEET 0", NH_COLOR_CYAN);
    s_ui.fleet_button_label = lv_obj_get_child(fleet, 0);
    lv_obj_add_event_cb(fleet, show_fleet_cb, LV_EVENT_CLICKED, NULL);
    make_action_button(quick, 516, 47, 154, 58, "HOME AXES",
                       NH_COLOR_AMBER, NH_ACTION_HOME, 0);
}

static void build_job_page(lv_obj_t *page)
{
    lv_obj_t *overview = make_card(page, 0, 0, 688, 210);
    s_ui.job_page_title =
        add_card_title(overview, "PRINT SESSION", "Waiting for P1S");
    lv_obj_set_width(s_ui.job_page_title, 440);
    lv_label_set_long_mode(s_ui.job_page_title, LV_LABEL_LONG_DOT);

    s_ui.job_page_state = make_pill(overview, 20, 79, 126, 30,
                                    NH_COLOR_AMBER, "NOT CONNECTED");
    s_ui.history_button = make_plain_button(
        overview, 160, 79, 192, 30, "HISTORY & COSTS", NH_COLOR_VIOLET);
    lv_obj_add_event_cb(
        s_ui.history_button, show_history_cb, LV_EVENT_CLICKED, NULL);

    s_ui.job_page_copy = make_label(
        overview,
        "Connect this controller to your P1S LAN profile to receive live layers,\n"
        "remaining time, temperatures, and local camera status.",
        &lv_font_montserrat_14, NH_COLOR_MUTED);
    lv_obj_set_pos(s_ui.job_page_copy, 20, 125);
    lv_obj_set_style_text_line_space(s_ui.job_page_copy, 8, 0);

    lv_obj_t *metric = make_card(overview, 492, 22, 174, 166);
    lv_obj_set_style_bg_color(metric, NH_COLOR_SURFACE_2, 0);
    s_ui.job_page_progress = make_label(
        metric, "--%", &lv_font_montserrat_40, NH_COLOR_TEXT);
    lv_obj_align(s_ui.job_page_progress, LV_ALIGN_CENTER, 0, -19);
    lv_obj_t *metric_label = make_label(metric, "JOB PROGRESS",
                                        &lv_font_montserrat_12, NH_COLOR_MUTED);
    lv_obj_align(metric_label, LV_ALIGN_CENTER, 0, 24);

    lv_obj_t *actions = make_card(page, 0, 221, 688, 119);
    lv_obj_t *action_title = make_label(actions, "PRINT ACTIONS",
                                        &lv_font_montserrat_12, NH_COLOR_CYAN);
    lv_obj_set_pos(action_title, 18, 14);
    make_action_button(actions, 18, 47, 205, 54, "PAUSE",
                       NH_COLOR_AMBER, NH_ACTION_PAUSE, 0);
    make_action_button(actions, 241, 47, 205, 54, "RESUME",
                       NH_COLOR_GREEN, NH_ACTION_RESUME, 0);
    lv_obj_t *cancel = make_action_button(actions, 464, 47, 206, 54, "CANCEL PRINT",
                                          NH_COLOR_RED, NH_ACTION_CANCEL, 0);
    lv_obj_set_style_border_color(cancel, NH_COLOR_RED, 0);
}

static void build_control_page(lv_obj_t *page)
{
    lv_obj_t *motion = make_card(page, 0, 0, 338, 340);
    s_ui.control_motion_status =
        add_card_title(motion, "AXIS", "Motion controls disabled");

    make_action_button(motion, 122, 78, 94, 52, "Y +",
                       NH_COLOR_CYAN, NH_ACTION_JOG_Y, 10);
    make_action_button(motion, 28, 138, 94, 52, "X -",
                       NH_COLOR_CYAN, NH_ACTION_JOG_X, -10);
    make_action_button(motion, 122, 138, 94, 52, "HOME",
                       NH_COLOR_AMBER, NH_ACTION_HOME, 0);
    make_action_button(motion, 216, 138, 94, 52, "X +",
                       NH_COLOR_CYAN, NH_ACTION_JOG_X, 10);
    make_action_button(motion, 122, 198, 94, 52, "Y -",
                       NH_COLOR_CYAN, NH_ACTION_JOG_Y, -10);

    make_action_button(motion, 28, 273, 132, 48, "Z + 1 MM",
                       NH_COLOR_VIOLET, NH_ACTION_JOG_Z, 1);
    make_action_button(motion, 178, 273, 132, 48, "Z - 1 MM",
                       NH_COLOR_VIOLET, NH_ACTION_JOG_Z, -1);

    lv_obj_t *thermal = make_card(page, 350, 0, 338, 340);
    s_ui.control_thermal_status =
        add_card_title(thermal, "MATERIAL", "AMS not reported");

    s_ui.ams_environment = make_label(
        thermal, "Humidity --  /  Temperature --",
        &lv_font_montserrat_12, NH_COLOR_MUTED);
    lv_obj_set_pos(s_ui.ams_environment, 20, 78);

    for (size_t i = 0; i < 4; ++i) {
        char text[48];
        snprintf(text, sizeof(text), "SLOT %u  /  --", (unsigned)(i + 1));
        s_ui.ams_trays[i] = make_label(
            thermal, text, &lv_font_montserrat_14, NH_COLOR_MUTED);
        lv_obj_set_pos(s_ui.ams_trays[i], 20, 108 + (int)i * 36);
        lv_obj_set_width(s_ui.ams_trays[i], 298);
        lv_label_set_long_mode(s_ui.ams_trays[i], LV_LABEL_LONG_DOT);
    }
    s_ui.ams_detail_button = make_plain_button(
        thermal, 20, 273, 298, 48, "OPEN MATERIAL CENTER", NH_COLOR_VIOLET);
    lv_obj_add_event_cb(
        s_ui.ams_detail_button, show_ams_center_cb, LV_EVENT_CLICKED, NULL);
}

static const nh_file_entry_t *find_ui_file(uint64_t file_id)
{
    if (!s_ui.files_valid) {
        return NULL;
    }
    for (uint8_t i = 0; i < s_ui.files.file_count; ++i) {
        if (s_ui.files.files[i].id == file_id) {
            return &s_ui.files.files[i];
        }
    }
    return NULL;
}

static void file_bed_clear_confirm_cb(lv_event_t *event)
{
    (void)event;
    uint64_t queue_id = s_ui.pending_queue_id;
    esp_err_t err =
        s_ui.cfg.file_bed_clear && queue_id
            ? s_ui.cfg.file_bed_clear(queue_id, s_ui.cfg.files_ctx)
            : ESP_ERR_NOT_SUPPORTED;
    close_modal();
    if (err == ESP_OK) {
        update_footer(
            "Bed-clear confirmation recorded; transfer still requires capability",
            NH_COLOR_GREEN);
    } else {
        update_footer("Could not confirm the local queue item", NH_COLOR_RED);
    }
}

static void file_modal_close_cb(lv_event_t *event)
{
    (void)event;
    close_modal();
    update_footer("Local file review closed", NH_COLOR_MUTED);
}

static void show_bed_clear_confirmation(uint64_t queue_id)
{
    if (s_ui.modal || !queue_id) {
        return;
    }
    s_ui.pending_queue_id = queue_id;
    s_ui.modal = lv_obj_create(s_ui.screen);
    set_obj_box(s_ui.modal, lv_color_hex(0x020609), 0, 0);
    lv_obj_set_style_bg_opa(s_ui.modal, LV_OPA_80, 0);
    lv_obj_set_size(s_ui.modal, 800, 480);
    lv_obj_set_pos(s_ui.modal, 0, 0);
    lv_obj_move_foreground(s_ui.modal);
    lv_obj_clear_flag(s_ui.modal, LV_OBJ_FLAG_SCROLLABLE);

    lv_obj_t *dialog = make_card(s_ui.modal, 175, 105, 450, 270);
    lv_obj_set_style_border_color(dialog, NH_COLOR_AMBER, 0);
    lv_obj_t *eyebrow = make_label(
        dialog, "PHYSICAL SAFETY CHECK",
        &lv_font_montserrat_12, NH_COLOR_AMBER);
    lv_obj_set_pos(eyebrow, 24, 20);
    lv_obj_t *title = make_label(
        dialog, "Is the build plate clear?",
        &lv_font_montserrat_20, NH_COLOR_TEXT);
    lv_obj_set_pos(title, 24, 49);
    lv_obj_t *copy = make_label(
        dialog,
        "Remove the prior print and loose material. This confirmation only "
        "advances the local queue; it does not start or transfer a print.",
        &lv_font_montserrat_14, NH_COLOR_MUTED);
    lv_obj_set_pos(copy, 24, 88);
    lv_obj_set_width(copy, 402);
    lv_label_set_long_mode(copy, LV_LABEL_LONG_WRAP);

    lv_obj_t *cancel = make_plain_button(
        dialog, 24, 197, 180, 48, "NOT CLEAR", NH_COLOR_MUTED);
    lv_obj_add_event_cb(
        cancel, file_modal_close_cb, LV_EVENT_CLICKED, NULL);
    lv_obj_t *confirm = make_plain_button(
        dialog, 220, 197, 206, 48, "BED IS CLEAR", NH_COLOR_AMBER);
    lv_obj_set_style_border_color(confirm, NH_COLOR_AMBER, 0);
    lv_obj_add_event_cb(
        confirm, file_bed_clear_confirm_cb, LV_EVENT_CLICKED, NULL);
}

static void file_review_queue_cb(lv_event_t *event)
{
    uint64_t file_id = (uint64_t)(uintptr_t)lv_event_get_user_data(event);
    uint64_t queue_id = 0;
    esp_err_t err =
        s_ui.cfg.file_review_queue
            ? s_ui.cfg.file_review_queue(
                  file_id, &queue_id, s_ui.cfg.files_ctx)
            : ESP_ERR_NOT_SUPPORTED;
    close_modal();
    if (err == ESP_OK) {
        update_footer(
            "Compatibility review recorded; physical bed check required",
            NH_COLOR_CYAN);
        show_bed_clear_confirmation(queue_id);
    } else if (err == ESP_ERR_NOT_SUPPORTED) {
        update_footer(
            "File target is incompatible or queue service is unavailable",
            NH_COLOR_AMBER);
    } else {
        update_footer("Could not add the reviewed file to the queue",
                      NH_COLOR_RED);
    }
}

static void show_file_detail_cb(lv_event_t *event)
{
    uint64_t file_id = (uint64_t)(uintptr_t)lv_event_get_user_data(event);
    const nh_file_entry_t *file = find_ui_file(file_id);
    if (!file || s_ui.modal) {
        return;
    }
    s_ui.modal = lv_obj_create(s_ui.screen);
    set_obj_box(s_ui.modal, lv_color_hex(0x020609), 0, 0);
    lv_obj_set_style_bg_opa(s_ui.modal, LV_OPA_80, 0);
    lv_obj_set_size(s_ui.modal, 800, 480);
    lv_obj_set_pos(s_ui.modal, 0, 0);
    lv_obj_move_foreground(s_ui.modal);
    lv_obj_clear_flag(s_ui.modal, LV_OBJ_FLAG_SCROLLABLE);

    lv_obj_t *dialog = make_card(s_ui.modal, 55, 35, 690, 410);
    lv_obj_set_style_border_color(dialog, NH_COLOR_CYAN, 0);
    lv_obj_t *title = make_label(
        dialog, file->name, &lv_font_montserrat_20, NH_COLOR_TEXT);
    lv_obj_set_pos(title, 22, 22);
    lv_obj_set_width(title, 470);
    lv_label_set_long_mode(title, LV_LABEL_LONG_DOT);
    lv_obj_t *close = make_plain_button(
        dialog, 540, 16, 126, 40, "CLOSE", NH_COLOR_MUTED);
    lv_obj_add_event_cb(
        close, file_modal_close_cb, LV_EVENT_CLICKED, NULL);

    char metadata[256];
    snprintf(
        metadata, sizeof(metadata),
        "SIZE  %.1f MB\nTARGET  %s\nNOZZLE  %s%.2f mm\nLAYER  %s%.2f mm\n"
        "HASH  %02x%02x%02x%02x%02x%02x%02x%02x...\n%s%s",
        (double)file->size_bytes / (1024.0 * 1024.0),
        file->target_model[0] ? file->target_model : "not declared",
        file->nozzle_diameter_mm > 0.0f ? "" : "-- / ",
        file->nozzle_diameter_mm,
        file->layer_height_mm > 0.0f ? "" : "-- / ",
        file->layer_height_mm,
        file->sha256[0], file->sha256[1], file->sha256[2],
        file->sha256[3], file->sha256[4], file->sha256[5],
        file->sha256[6], file->sha256[7],
        nh_file_compatibility_label(file->compatibility),
        file->duplicate ? " / DUPLICATE CONTENT" : "");
    lv_obj_t *copy = make_label(
        dialog, metadata, &lv_font_montserrat_14, NH_COLOR_MUTED);
    lv_obj_set_pos(copy, 22, 74);
    lv_obj_set_style_text_line_space(copy, 8, 0);

    lv_obj_t *preview = lv_obj_create(dialog);
    set_obj_box(preview, NH_COLOR_SURFACE_2, 10, 1);
    lv_obj_set_pos(preview, 446, 74);
    lv_obj_set_size(preview, 220, 220);
    lv_obj_clear_flag(preview, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_t *preview_label = make_label(
        preview,
        file->thumbnail_available ? "LOADING PREVIEW" : "NO SAFE PREVIEW",
        &lv_font_montserrat_12, NH_COLOR_MUTED);
    lv_obj_center(preview_label);

    if (file->thumbnail_available && s_ui.cfg.file_thumbnail) {
        size_t required = 0;
        if (s_ui.cfg.file_thumbnail(
                file_id, NULL, 0, &required,
                s_ui.cfg.files_ctx) == ESP_OK &&
            required >= 24 && required <= NH_FILE_THUMBNAIL_MAX_BYTES) {
            s_ui.file_thumbnail_data = heap_caps_malloc(
                required, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
            if (s_ui.file_thumbnail_data &&
                s_ui.cfg.file_thumbnail(
                    file_id, s_ui.file_thumbnail_data, required,
                    &required, s_ui.cfg.files_ctx) == ESP_OK) {
                s_ui.file_thumbnail_dsc = (lv_image_dsc_t){
                    .header = {
                        .magic = LV_IMAGE_HEADER_MAGIC,
                        .cf = LV_COLOR_FORMAT_RAW_ALPHA,
                        .w = file->thumbnail_width,
                        .h = file->thumbnail_height,
                    },
                    .data_size = required,
                    .data = s_ui.file_thumbnail_data,
                };
                lv_obj_add_flag(preview_label, LV_OBJ_FLAG_HIDDEN);
                lv_obj_t *image = lv_image_create(preview);
                lv_image_set_src(image, &s_ui.file_thumbnail_dsc);
                uint32_t scale_x =
                    file->thumbnail_width
                        ? 196U * 256U / file->thumbnail_width
                        : 256U;
                uint32_t scale_y =
                    file->thumbnail_height
                        ? 196U * 256U / file->thumbnail_height
                        : 256U;
                uint32_t scale = scale_x < scale_y ? scale_x : scale_y;
                lv_image_set_scale(image, scale < 256U ? scale : 256U);
                lv_obj_center(image);
            }
        }
    }

    lv_obj_t *queue = make_plain_button(
        dialog, 22, 326, 644, 58,
        file->compatibility == NH_FILE_COMPATIBILITY_INCOMPATIBLE
            ? "INCOMPATIBLE TARGET"
            : "REVIEW HASH & ADD TO QUEUE",
        file->compatibility == NH_FILE_COMPATIBILITY_INCOMPATIBLE
            ? NH_COLOR_RED
            : NH_COLOR_CYAN);
    if (file->compatibility == NH_FILE_COMPATIBILITY_INCOMPATIBLE) {
        lv_obj_add_state(queue, LV_STATE_DISABLED);
    } else {
        lv_obj_add_event_cb(
            queue, file_review_queue_cb, LV_EVENT_CLICKED,
            (void *)(uintptr_t)file_id);
    }
}

static void rebuild_files_list(void)
{
    if (!s_ui.files_list) {
        return;
    }
    lv_obj_clean(s_ui.files_list);
    if (s_ui.files_title) {
        char title[64];
        snprintf(
            title, sizeof(title), "%u indexed .3MF / generation %lu",
            (unsigned)s_ui.files.file_count,
            (unsigned long)s_ui.files.generation);
        lv_label_set_text(s_ui.files_title, title);
    }
    if (s_ui.files_queue_status) {
        char queue[72];
        snprintf(queue, sizeof(queue),
                 "LOCAL QUEUE  %u / %u%s",
                 (unsigned)s_ui.files.queue_count,
                 NH_FILE_QUEUE_MAX,
                 s_ui.files.queue_recovered ? " / RECOVERED" : "");
        lv_label_set_text(s_ui.files_queue_status, queue);
    }
    if (!s_ui.files_valid || s_ui.files.file_count == 0) {
        lv_obj_t *empty = make_label(
            s_ui.files_list,
            s_ui.files.storage_ready
                ? "No .3MF files in /PrintDeck/files"
                : "Controller SD file service unavailable",
            &lv_font_montserrat_14, NH_COLOR_MUTED);
        lv_obj_set_width(empty, 360);
        return;
    }
    for (uint8_t i = 0; i < s_ui.files.file_count; ++i) {
        const nh_file_entry_t *file = &s_ui.files.files[i];
        lv_obj_t *row = lv_obj_create(s_ui.files_list);
        set_obj_box(row, NH_COLOR_SURFACE, 8, 1);
        lv_obj_set_pos(row, 0, i * 66);
        lv_obj_set_size(row, 378, 58);
        lv_obj_clear_flag(row, LV_OBJ_FLAG_SCROLLABLE);
        lv_obj_add_event_cb(
            row, show_file_detail_cb, LV_EVENT_CLICKED,
            (void *)(uintptr_t)file->id);

        char name[120];
        snprintf(name, sizeof(name), "%s%s",
                 file->favorite ? "★  " : "",
                 file->name);
        lv_obj_t *title = make_label(
            row, name, &lv_font_montserrat_14, NH_COLOR_TEXT);
        lv_obj_set_pos(title, 10, 7);
        lv_obj_set_width(title, 350);
        lv_label_set_long_mode(title, LV_LABEL_LONG_DOT);
        char detail[128];
        snprintf(
            detail, sizeof(detail), "%.1f MB / %s%s%s",
            (double)file->size_bytes / (1024.0 * 1024.0),
            nh_file_compatibility_label(file->compatibility),
            file->thumbnail_available ? " / preview" : "",
            file->duplicate ? " / duplicate" : "");
        lv_obj_t *copy = make_label(
            row, detail, &lv_font_montserrat_12,
            file->compatibility == NH_FILE_COMPATIBILITY_INCOMPATIBLE
                ? NH_COLOR_RED
                : NH_COLOR_MUTED);
        lv_obj_set_pos(copy, 10, 34);
        lv_obj_set_width(copy, 350);
        lv_label_set_long_mode(copy, LV_LABEL_LONG_DOT);
    }
}

static void build_files_page(lv_obj_t *page)
{
    lv_obj_t *storage = make_card(page, 0, 0, 235, 340);
    add_card_title(storage, "CONTROLLER STORAGE", "SD card");

    lv_obj_t *disk = lv_arc_create(storage);
    lv_obj_set_pos(disk, 55, 82);
    lv_obj_set_size(disk, 125, 125);
    lv_arc_set_range(disk, 0, 100);
    lv_arc_set_value(disk, 0);
    lv_arc_set_rotation(disk, 135);
    lv_arc_set_bg_angles(disk, 0, 270);
    lv_obj_remove_style(disk, NULL, LV_PART_KNOB);
    lv_obj_set_style_arc_width(disk, 11, LV_PART_MAIN);
    lv_obj_set_style_arc_width(disk, 11, LV_PART_INDICATOR);
    lv_obj_set_style_arc_color(disk, NH_COLOR_STROKE, LV_PART_MAIN);
    lv_obj_set_style_arc_color(disk, NH_COLOR_CYAN, LV_PART_INDICATOR);
    s_ui.sd_arc = disk;

    s_ui.sd_value = make_label(storage, "SCANNING", &lv_font_montserrat_16, NH_COLOR_TEXT);
    lv_obj_align_to(s_ui.sd_value, disk, LV_ALIGN_CENTER, 0, -3);
    s_ui.sd_detail = make_label(storage, "Controller SD / FAT32",
                                &lv_font_montserrat_12, NH_COLOR_MUTED);
    lv_obj_align(s_ui.sd_detail, LV_ALIGN_BOTTOM_MID, 0, -78);

    s_ui.sd_rescan_button = make_action_button(
        storage, 31, 231, 173, 38, "RESCAN SD",
        NH_COLOR_CYAN, NH_ACTION_SD_RESCAN, 0);
    s_ui.printer_sd_pill = make_pill(storage, 31, 283, 173, 30,
                                     NH_COLOR_AMBER, "P1S SD UNKNOWN");
    s_ui.printer_sd_label = lv_obj_get_child(s_ui.printer_sd_pill, 0);

    lv_obj_t *files = make_card(page, 247, 0, 441, 340);
    s_ui.files_title =
        add_card_title(files, "LOCAL PRINT FILES", "Waiting for index");
    s_ui.files_queue_status = make_label(
        files, "LOCAL QUEUE  0 / 8",
        &lv_font_montserrat_12, NH_COLOR_VIOLET);
    lv_obj_set_pos(s_ui.files_queue_status, 20, 72);

    s_ui.files_list = lv_obj_create(files);
    set_obj_box(s_ui.files_list, NH_COLOR_SURFACE_2, 10, 0);
    lv_obj_set_pos(s_ui.files_list, 18, 96);
    lv_obj_set_size(s_ui.files_list, 405, 226);
    lv_obj_set_style_pad_all(s_ui.files_list, 8, 0);
    rebuild_files_list();
}

static void build_camera_page(lv_obj_t *page)
{
    lv_obj_t *viewport = make_card(page, 0, 0, 688, 340);
    lv_obj_set_style_bg_color(viewport, lv_color_hex(0x020609), 0);
    lv_obj_set_style_border_color(viewport, NH_COLOR_STROKE, 0);
    lv_obj_set_style_clip_corner(viewport, true, 0);

    s_ui.camera_image = lv_image_create(viewport);
    lv_obj_add_flag(s_ui.camera_image, LV_OBJ_FLAG_HIDDEN);

    s_ui.camera_placeholder = lv_obj_create(viewport);
    set_obj_box(s_ui.camera_placeholder, lv_color_hex(0x020609), 0, 0);
    lv_obj_set_size(s_ui.camera_placeholder, 400, 180);
    lv_obj_center(s_ui.camera_placeholder);
    lv_obj_clear_flag(s_ui.camera_placeholder, LV_OBJ_FLAG_SCROLLABLE);
    make_camera_icon(s_ui.camera_placeholder, 165, 12, 70, 52,
                     NH_COLOR_CYAN);
    lv_obj_t *title = make_label(
        s_ui.camera_placeholder, "P1S CAMERA",
        &lv_font_montserrat_24, NH_COLOR_TEXT);
    lv_obj_align(title, LV_ALIGN_TOP_MID, 0, 78);
    s_ui.camera_placeholder_copy = make_label(
        s_ui.camera_placeholder,
        "Opening encrypted local liveview...",
        &lv_font_montserrat_14, NH_COLOR_MUTED);
    lv_obj_align(s_ui.camera_placeholder_copy, LV_ALIGN_TOP_MID, 0, 118);

    s_ui.camera_status_pill = make_pill(
        viewport, 16, 14, 142, 30, NH_COLOR_CYAN, "CAMERA READY");
    s_ui.camera_status_label =
        lv_obj_get_child(s_ui.camera_status_pill, 0);
    lv_obj_t *ai_status = make_pill(
        viewport, 524, 14, 148, 30, NH_COLOR_VIOLET, "AI OFF / LOCAL");
    s_ui.ai_status_label = lv_obj_get_child(ai_status, 0);

    lv_obj_t *detail_bar = lv_obj_create(viewport);
    set_obj_box(detail_bar, lv_color_hex(0x071019), 10, 1);
    lv_obj_set_style_bg_opa(detail_bar, LV_OPA_80, 0);
    lv_obj_set_style_border_color(detail_bar, NH_COLOR_STROKE, 0);
    lv_obj_set_pos(detail_bar, 16, 296);
    lv_obj_set_size(detail_bar, 656, 30);
    lv_obj_clear_flag(detail_bar, LV_OBJ_FLAG_SCROLLABLE);
    s_ui.camera_detail = make_label(
        detail_bar, "LOCAL LIVEVIEW  /  WAITING FOR CAMERA",
        &lv_font_montserrat_12, NH_COLOR_MUTED);
    lv_obj_center(s_ui.camera_detail);

    lv_obj_move_foreground(s_ui.camera_status_pill);
    lv_obj_move_foreground(detail_bar);
}

static void brightness_cb(lv_event_t *event)
{
    lv_obj_t *slider = lv_event_get_target_obj(event);
    int32_t value = lv_slider_get_value(slider);
    if (s_ui.cfg.action_handler) {
        s_ui.cfg.action_handler(NH_ACTION_BRIGHTNESS_SET, value, s_ui.cfg.action_ctx);
    }
}

static void ota_enable_cb(lv_event_t *event)
{
    (void)event;
    if (!s_ui.cfg.ota_enable) {
        update_footer("OTA update service is unavailable", NH_COLOR_RED);
        return;
    }

    esp_err_t err = s_ui.cfg.ota_enable(300, s_ui.cfg.ota_ctx);
    if (err == ESP_OK) {
        update_footer(
            "OTA enabled for 5 minutes  /  POST firmware to /api/v1/ota",
            NH_COLOR_GREEN);
    } else {
        char message[96];
        snprintf(message, sizeof(message), "Could not enable OTA: %s",
                 esp_err_to_name(err));
        update_footer(message, NH_COLOR_RED);
    }
}

static void refresh_timezone_button(void)
{
    if (!s_ui.timezone_button_label || !s_ui.cfg.timezone_name) {
        return;
    }
    const char *name = s_ui.cfg.timezone_name(s_ui.cfg.timezone_ctx);
    char text[32];
    snprintf(text, sizeof(text), "TZ %s", name ? name : "UNKNOWN");
    lv_label_set_text(s_ui.timezone_button_label, text);
}

static void timezone_next_cb(lv_event_t *event)
{
    (void)event;
    if (!s_ui.cfg.timezone_next) {
        update_footer("Timezone settings are unavailable", NH_COLOR_RED);
        return;
    }

    esp_err_t err = s_ui.cfg.timezone_next(s_ui.cfg.timezone_ctx);
    if (err != ESP_OK) {
        char message[96];
        snprintf(message, sizeof(message), "Could not save timezone: %s",
                 esp_err_to_name(err));
        update_footer(message, NH_COLOR_RED);
        return;
    }

    refresh_timezone_button();
    clock_timer_cb(NULL);
    const char *name = s_ui.cfg.timezone_name
                           ? s_ui.cfg.timezone_name(s_ui.cfg.timezone_ctx)
                           : "selected preset";
    char message[96];
    snprintf(message, sizeof(message), "Timezone set to %s", name);
    update_footer(message, NH_COLOR_GREEN);
}

static void build_settings_page(lv_obj_t *page)
{
    lv_obj_t *identity = make_card(page, 0, 0, 688, 86);
    lv_obj_t *identity_eyebrow =
        make_label(identity, "CONNECTED PRINTER",
                   &lv_font_montserrat_12, NH_COLOR_CYAN);
    lv_obj_set_pos(identity_eyebrow, 20, 11);
    s_ui.printer_identity_name =
        make_label(identity, "Bambu Lab P1S",
                   &lv_font_montserrat_24, NH_COLOR_TEXT);
    lv_obj_set_pos(s_ui.printer_identity_name, 20, 29);
    s_ui.printer_identity_detail =
        make_label(identity, "MODEL  P1S  /  SERIAL  NOT CONFIGURED",
                   &lv_font_montserrat_12, NH_COLOR_MUTED);
    lv_obj_set_pos(s_ui.printer_identity_detail, 20, 62);
    s_ui.printer_identity_pill =
        make_pill(identity, 511, 29, 157, 30,
                  NH_COLOR_AMBER, "SETUP REQUIRED");
    s_ui.printer_identity_status =
        lv_obj_get_child(s_ui.printer_identity_pill, 0);

    lv_obj_t *board = make_card(page, 0, 96, 335, 244);
    add_card_title(board, "CONTROLLER HARDWARE", "JC4880P443");

    const char *labels[] = {"COMPUTE", "MEMORY FREE", "DISPLAY", "WIRELESS"};
    const char *values[] = {
        "ESP32-P4NRW32",
        "MEASURING",
        "ST7701S + GT911 / 800x480 UI",
        "ESP32-C6 coprocessor",
    };
    for (int i = 0; i < 4; ++i) {
        int y = 79 + i * 34;
        lv_obj_t *name = make_label(board, labels[i],
                                    &lv_font_montserrat_12, NH_COLOR_MUTED);
        lv_obj_set_pos(name, 20, y);
        lv_obj_t *value = make_label(board, values[i],
                                     &lv_font_montserrat_12, NH_COLOR_TEXT);
        lv_obj_align(value, LV_ALIGN_TOP_RIGHT, -20, y);
        if (i == 1) {
            s_ui.memory_value = value;
        }
    }

    const esp_app_desc_t *app = esp_app_get_description();
    char firmware_text[64];
    snprintf(firmware_text, sizeof(firmware_text),
             "FIRMWARE %s  /  LOCAL-FIRST",
             app ? app->version : "UNKNOWN");
    lv_obj_t *version = make_pill(board, 20, 207, 295, 25,
                                  NH_COLOR_GREEN, firmware_text);
    (void)version;
    if (!lv_timer_create(health_timer_cb, 5000, NULL)) {
        ESP_LOGW(TAG, "Memory health timer could not be allocated");
    }
    health_timer_cb(NULL);

    lv_obj_t *system = make_card(page, 347, 96, 341, 244);
    add_card_title(system, "CONTROLLER", "System settings");

    lv_obj_t *brightness_title = make_label(system, "DISPLAY BRIGHTNESS",
                                            &lv_font_montserrat_12, NH_COLOR_MUTED);
    lv_obj_set_pos(brightness_title, 20, 75);
    lv_obj_t *timezone_button = make_plain_button(
        system, 174, 65, 147, 27, "TZ NEW YORK", NH_COLOR_CYAN);
    lv_obj_set_style_border_color(timezone_button, NH_COLOR_CYAN, 0);
    s_ui.timezone_button_label = lv_obj_get_child(timezone_button, 0);
    lv_obj_add_event_cb(timezone_button, timezone_next_cb,
                        LV_EVENT_CLICKED, NULL);
    refresh_timezone_button();
    lv_obj_t *slider = lv_slider_create(system);
    lv_obj_set_pos(slider, 20, 99);
    lv_obj_set_size(slider, 301, 12);
    lv_slider_set_range(slider, 10, 100);
    lv_slider_set_value(slider, 82, LV_ANIM_OFF);
    lv_obj_set_style_bg_color(slider, NH_COLOR_SURFACE_2, LV_PART_MAIN);
    lv_obj_set_style_bg_color(slider, NH_COLOR_CYAN, LV_PART_INDICATOR);
    lv_obj_set_style_bg_color(slider, NH_COLOR_TEXT, LV_PART_KNOB);
    lv_obj_add_event_cb(slider, brightness_cb, LV_EVENT_VALUE_CHANGED, NULL);

    lv_obj_t *network_box = lv_obj_create(system);
    set_obj_box(network_box, NH_COLOR_SURFACE_2, 12, 1);
    lv_obj_set_pos(network_box, 20, 119);
    lv_obj_set_size(network_box, 301, 65);
    lv_obj_clear_flag(network_box, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_t *network_title = make_label(network_box, "CONTROLLER NETWORK",
                                         &lv_font_montserrat_12, NH_COLOR_CYAN);
    lv_obj_set_pos(network_title, 14, 7);
    s_ui.network_state = make_label(network_box, "ESP32-C6 initializing",
                                    &lv_font_montserrat_14, NH_COLOR_TEXT);
    lv_obj_set_pos(s_ui.network_state, 14, 26);
    s_ui.network_detail = make_label(network_box, "P1S profile waits for Wi-Fi",
                                     &lv_font_montserrat_12, NH_COLOR_MUTED);
    lv_obj_set_pos(s_ui.network_detail, 14, 46);

    s_ui.network_setup_button = make_plain_button(
        system, 20, 193, 92, 38, "WI-FI", NH_COLOR_CYAN);
    lv_obj_set_style_border_color(s_ui.network_setup_button, NH_COLOR_CYAN, 0);
    lv_obj_add_event_cb(s_ui.network_setup_button, show_network_setup_cb,
                        LV_EVENT_CLICKED, NULL);

    s_ui.printer_setup_button = make_plain_button(
        system, 122, 193, 92, 38, "PAIR P1S", NH_COLOR_VIOLET);
    lv_obj_set_style_border_color(s_ui.printer_setup_button,
                                  NH_COLOR_VIOLET, 0);
    lv_obj_add_event_cb(s_ui.printer_setup_button, show_printer_setup_cb,
                        LV_EVENT_CLICKED, NULL);
    lv_obj_add_state(s_ui.printer_setup_button, LV_STATE_DISABLED);

    s_ui.ota_update_button = make_plain_button(
        system, 224, 193, 97, 38, "ENABLE OTA", NH_COLOR_VIOLET);
    lv_obj_set_style_border_color(s_ui.ota_update_button,
                                  NH_COLOR_VIOLET, 0);
    lv_obj_add_event_cb(s_ui.ota_update_button, ota_enable_cb,
                        LV_EVENT_CLICKED, NULL);
    lv_obj_add_state(s_ui.ota_update_button, LV_STATE_DISABLED);
}

static void build_chrome(void)
{
    lv_obj_t *sidebar = lv_obj_create(s_ui.screen);
    set_obj_box(sidebar, NH_COLOR_SURFACE, 0, 0);
    lv_obj_set_pos(sidebar, 0, 0);
    lv_obj_set_size(sidebar, 80, 480);
    lv_obj_clear_flag(sidebar, LV_OBJ_FLAG_SCROLLABLE);

    lv_obj_t *logo = lv_obj_create(sidebar);
    set_obj_box(logo, lv_color_hex(0x122D3A), 13, 1);
    lv_obj_set_style_border_color(logo, NH_COLOR_CYAN, 0);
    lv_obj_set_pos(logo, 15, 14);
    lv_obj_set_size(logo, 50, 50);
    lv_obj_clear_flag(logo, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_t *logo_text = make_label(logo, "NH", &lv_font_montserrat_20, NH_COLOR_CYAN);
    lv_obj_center(logo_text);

    const char *nav_text[] = {
        "D\nDASH", "J\nJOB", "C\nCTRL", "F\nFILES", NULL, "S\nSYS"
    };
    for (size_t i = 0; i < NH_PAGE_COUNT; ++i) {
        lv_obj_t *button = lv_button_create(sidebar);
        set_obj_box(button, NH_COLOR_SURFACE, 11, 1);
        lv_obj_set_pos(button, 11, 70 + i * 59);
        lv_obj_set_size(button, 58, 50);
        lv_obj_set_style_bg_color(button, lv_color_hex(0x163444), LV_STATE_PRESSED);
        lv_obj_set_style_border_color(button, NH_COLOR_CYAN, LV_STATE_PRESSED);
        lv_obj_add_event_cb(button, nav_button_cb, LV_EVENT_CLICKED, (void *)i);
        s_ui.nav_buttons[i] = button;

        if (i == NH_PAGE_CAMERA) {
            make_camera_icon(button, 16, 5, 26, 19, NH_COLOR_MUTED);
            lv_obj_t *label = make_label(
                button, "CAM", &lv_font_montserrat_12, NH_COLOR_MUTED);
            lv_obj_align(label, LV_ALIGN_BOTTOM_MID, 0, -4);
        } else {
            lv_obj_t *label = make_label(
                button, nav_text[i], &lv_font_montserrat_12, NH_COLOR_MUTED);
            lv_obj_set_style_text_align(label, LV_TEXT_ALIGN_CENTER, 0);
            lv_obj_center(label);
        }
    }

    lv_obj_t *side_status = lv_obj_create(sidebar);
    set_obj_box(side_status, NH_COLOR_GREEN, 4, 0);
    lv_obj_set_pos(side_status, 35, 447);
    lv_obj_set_size(side_status, 10, 10);

    lv_obj_t *brand = make_label(s_ui.screen, "PRINTDECK",
                                 &lv_font_montserrat_20, NH_COLOR_TEXT);
    lv_obj_set_pos(brand, 98, 15);
    lv_obj_t *sub = make_label(s_ui.screen, "P1S CONTROL NODE",
                               &lv_font_montserrat_12, NH_COLOR_CYAN);
    lv_obj_set_pos(sub, 99, 43);

    s_ui.section_title = make_label(s_ui.screen, s_page_titles[0],
                                    &lv_font_montserrat_12, NH_COLOR_MUTED);
    lv_obj_align(s_ui.section_title, LV_ALIGN_TOP_MID, 10, 26);

    s_ui.connection_pill = make_pill(s_ui.screen, 610, 18, 118, 30,
                                     NH_COLOR_AMBER, "SETUP REQUIRED");
    s_ui.connection_label = lv_obj_get_child(s_ui.connection_pill, 0);

    s_ui.clock = make_label(s_ui.screen, "--:--",
                            &lv_font_montserrat_16, NH_COLOR_MUTED);
    lv_obj_align(s_ui.clock, LV_ALIGN_TOP_RIGHT, -15, 24);
    if (!lv_timer_create(clock_timer_cb, 1000, NULL)) {
        ESP_LOGW(TAG, "Clock timer could not be allocated");
    }
    clock_timer_cb(NULL);

    lv_obj_t *divider = lv_obj_create(s_ui.screen);
    set_obj_box(divider, NH_COLOR_STROKE, 0, 0);
    lv_obj_set_pos(divider, 98, 65);
    lv_obj_set_size(divider, 680, 1);

    s_ui.content = lv_obj_create(s_ui.screen);
    set_obj_box(s_ui.content, NH_COLOR_BG, 0, 0);
    lv_obj_set_pos(s_ui.content, 98, 78);
    lv_obj_set_size(s_ui.content, 688, 340);
    lv_obj_clear_flag(s_ui.content, LV_OBJ_FLAG_SCROLLABLE);

    s_ui.footer_status = make_label(s_ui.screen, "PrintDeck ready",
                                    &lv_font_montserrat_12, NH_COLOR_MUTED);
    lv_obj_set_pos(s_ui.footer_status, 99, 443);

    const esp_app_desc_t *app = esp_app_get_description();
    char build_text[48];
    snprintf(build_text, sizeof(build_text), "PRINTDECK  /  v%s",
             app ? app->version : "UNKNOWN");
    lv_obj_t *build = make_label(s_ui.screen, build_text,
                                 &lv_font_montserrat_12, NH_COLOR_MUTED);
    lv_obj_align(build, LV_ALIGN_BOTTOM_RIGHT, -15, -24);
}

static void set_online_gating(void)
{
    for (size_t i = 0; i < s_ui.binding_count; ++i) {
        action_binding_t *binding = &s_ui.bindings[i];
        if (!binding->button) {
            continue;
        }

        bool available;
        if (binding->action == NH_ACTION_SD_RESCAN ||
            binding->action == NH_ACTION_BRIGHTNESS_SET) {
            available = true;
        } else if (!nh_action_requires_online(binding->action)) {
            available = nh_printer_action_supported(binding->action);
        } else {
            available = nh_printer_action_available(
                binding->action, s_ui.snapshot);
        }

        if (available) {
            lv_obj_clear_state(binding->button, LV_STATE_DISABLED);
        } else {
            lv_obj_add_state(binding->button, LV_STATE_DISABLED);
        }
    }
}

static void update_pill(lv_obj_t *pill, lv_obj_t *label,
                        lv_color_t color, const char *text)
{
    if (!pill || !label) {
        return;
    }
    lv_label_set_text(label, text);
    lv_obj_set_style_text_color(label, color, 0);
    lv_obj_set_style_border_color(pill, color, 0);
    lv_obj_set_style_bg_color(pill, lv_color_darken(color, 190), 0);
}

static void refresh_network_widgets(void)
{
    if (!s_ui.network_state || !s_ui.network_detail) {
        return;
    }

    const char *state_text = "ESP32-C6 not started";
    char detail[96] = "P1S profile waits for Wi-Fi";
    lv_color_t state_color = NH_COLOR_MUTED;

    if (s_ui.network_valid) {
        switch (s_ui.network.state) {
        case NH_NETWORK_INITIALIZING:
            state_text = "Starting ESP32-C6";
            state_color = NH_COLOR_CYAN;
            strlcpy(detail, "Bringing up the SDIO transport", sizeof(detail));
            break;
        case NH_NETWORK_SCANNING:
            state_text = "Scanning for Wi-Fi";
            state_color = NH_COLOR_CYAN;
            strlcpy(detail, "Searching for nearby access points", sizeof(detail));
            break;
        case NH_NETWORK_READY:
            state_text = "Wi-Fi setup required";
            state_color = NH_COLOR_AMBER;
            snprintf(detail, sizeof(detail), "%u networks found / P1S locked",
                     s_ui.network.access_point_count);
            break;
        case NH_NETWORK_CONNECTING:
            state_text = "Connecting to Wi-Fi";
            state_color = NH_COLOR_CYAN;
            if (s_ui.network.reconnect_delay_ms > 0) {
                snprintf(detail, sizeof(detail),
                         "Automatic retry in %lu seconds",
                         (unsigned long)(
                             (s_ui.network.reconnect_delay_ms + 999U) / 1000U));
            } else {
                snprintf(detail, sizeof(detail), "%s / waiting for address",
                         s_ui.selected_ssid[0]
                             ? s_ui.selected_ssid
                             : "Saved network");
            }
            break;
        case NH_NETWORK_CONNECTED:
            state_text = s_ui.network.connected_ssid[0]
                             ? s_ui.network.connected_ssid
                             : "Wi-Fi connected";
            state_color = NH_COLOR_GREEN;
            snprintf(detail, sizeof(detail), "%s / %d dBm",
                     s_ui.network.ip_address, s_ui.network.rssi);
            break;
        case NH_NETWORK_ERROR:
            state_text = "ESP32-C6 network error";
            state_color = NH_COLOR_RED;
            snprintf(detail, sizeof(detail), "%s",
                     esp_err_to_name(s_ui.network.last_error));
            break;
        case NH_NETWORK_DISABLED:
        default:
            break;
        }
    }

    lv_label_set_text(s_ui.network_state, state_text);
    lv_obj_set_style_text_color(s_ui.network_state, state_color, 0);
    lv_label_set_text(s_ui.network_detail, detail);

    if (s_ui.network_setup_button) {
        lv_obj_t *label = lv_obj_get_child(s_ui.network_setup_button, 0);
        if (label) {
            lv_label_set_text(
                label,
                s_ui.network_valid &&
                        s_ui.network.state == NH_NETWORK_CONNECTED
                    ? "CHANGE WI-FI"
                    : "CONNECT WI-FI");
        }
    }

    if (s_ui.printer_setup_button) {
        bool network_connected =
            s_ui.network_valid &&
            s_ui.network.state == NH_NETWORK_CONNECTED;
        if (network_connected) {
            lv_obj_clear_state(s_ui.printer_setup_button, LV_STATE_DISABLED);
        } else {
            lv_obj_add_state(s_ui.printer_setup_button, LV_STATE_DISABLED);
        }

        lv_obj_t *label = lv_obj_get_child(s_ui.printer_setup_button, 0);
        if (label) {
            const char *text = "PAIR P1S";
            if (s_ui.printer_valid) {
                switch (s_ui.printer.state) {
                case NH_PRINTER_CONNECTING:
                    text = "CONNECTING";
                    break;
                case NH_PRINTER_ONLINE:
                    text = "P1S ONLINE";
                    break;
                case NH_PRINTER_AUTH_ERROR:
                    text = "ACCESS CODE";
                    break;
                case NH_PRINTER_TLS_ERROR:
                    text = "CHECK ID";
                    break;
                case NH_PRINTER_OFFLINE:
                    text = "RECONNECT";
                    break;
                case NH_PRINTER_ERROR:
                    text = "SETUP ERROR";
                    break;
                case NH_PRINTER_UNCONFIGURED:
                default:
                    break;
                }
            }
            lv_label_set_text(label, text);
        }
    }

    if (s_ui.printer_identity_name) {
        lv_label_set_text(
            s_ui.printer_identity_name,
            s_ui.snapshot && s_ui.snapshot->printer_name
                ? s_ui.snapshot->printer_name
                : "Bambu Lab P1S");
    }
    if (s_ui.printer_identity_detail) {
        char identity[96];
        if (s_ui.printer_valid && s_ui.printer.serial[0]) {
            snprintf(identity, sizeof(identity), "MODEL  P1S  /  SERIAL  %s",
                     s_ui.printer.serial);
        } else {
            strlcpy(identity, "MODEL  P1S  /  SERIAL  NOT CONFIGURED",
                    sizeof(identity));
        }
        lv_label_set_text(s_ui.printer_identity_detail, identity);
    }
    if (s_ui.printer_identity_pill && s_ui.printer_identity_status) {
        const char *identity_state = "SETUP REQUIRED";
        lv_color_t identity_color = NH_COLOR_AMBER;
        if (s_ui.printer_valid) {
            switch (s_ui.printer.state) {
            case NH_PRINTER_CONNECTING:
                identity_state = "CONNECTING";
                identity_color = NH_COLOR_CYAN;
                break;
            case NH_PRINTER_ONLINE:
                identity_state = "ONLINE";
                identity_color = NH_COLOR_GREEN;
                break;
            case NH_PRINTER_OFFLINE:
                identity_state = "OFFLINE";
                identity_color = NH_COLOR_AMBER;
                break;
            case NH_PRINTER_AUTH_ERROR:
                identity_state = "ACCESS CODE";
                identity_color = NH_COLOR_RED;
                break;
            case NH_PRINTER_TLS_ERROR:
                identity_state = "IDENTITY ERROR";
                identity_color = NH_COLOR_RED;
                break;
            case NH_PRINTER_ERROR:
                identity_state = "SETUP ERROR";
                identity_color = NH_COLOR_RED;
                break;
            case NH_PRINTER_UNCONFIGURED:
            default:
                break;
            }
        }
        update_pill(s_ui.printer_identity_pill,
                    s_ui.printer_identity_status,
                    identity_color, identity_state);
    }

    if (s_ui.ota_update_button) {
        if (s_ui.network_valid &&
            s_ui.network.state == NH_NETWORK_CONNECTED) {
            lv_obj_clear_state(s_ui.ota_update_button, LV_STATE_DISABLED);
        } else {
            lv_obj_add_state(s_ui.ota_update_button, LV_STATE_DISABLED);
        }
    }
}

static void refresh_snapshot(void)
{
    const nh_printer_snapshot_t *snapshot = s_ui.snapshot;
    if (!snapshot) {
        return;
    }

    const char *connection = nh_connection_label(snapshot->connection);
    lv_label_set_text(s_ui.connection_label, connection);

    lv_color_t connection_color = NH_COLOR_AMBER;
    if (snapshot->connection == NH_CONNECTION_ONLINE) {
        connection_color = NH_COLOR_GREEN;
    } else if (snapshot->connection == NH_CONNECTION_ERROR) {
        connection_color = NH_COLOR_RED;
    } else if (snapshot->connection == NH_CONNECTION_CONNECTING) {
        connection_color = NH_COLOR_CYAN;
    }
    lv_obj_set_style_border_color(s_ui.connection_pill, connection_color, 0);
    lv_obj_set_style_bg_color(s_ui.connection_pill,
                              lv_color_darken(connection_color, 190), 0);
    lv_obj_set_style_text_color(s_ui.connection_label, connection_color, 0);

    const char *job_heading = "Waiting for P1S";
    if (snapshot->connection == NH_CONNECTION_ONLINE) {
        if (!snapshot->telemetry_ready) {
            job_heading = "Syncing printer status";
        } else {
            switch (snapshot->job) {
            case NH_JOB_UNKNOWN:
                job_heading = "Syncing printer status";
                break;
            case NH_JOB_PREPARING:
                job_heading = "P1S is preparing";
                break;
            case NH_JOB_PRINTING:
                job_heading = "P1S is printing";
                break;
            case NH_JOB_PAUSED:
                job_heading = "Print is paused";
                break;
            case NH_JOB_COMPLETE:
                job_heading = "Print complete";
                break;
            case NH_JOB_FAILED:
                job_heading = "Print needs attention";
                break;
            case NH_JOB_IDLE:
            default:
                job_heading = "P1S is ready";
                break;
            }
        }
    }
    if (s_ui.dashboard_job_title) {
        lv_label_set_text(s_ui.dashboard_job_title, job_heading);
    }
    if (s_ui.alert_button && s_ui.alert_button_label) {
        char alert_text[24];
        snprintf(alert_text, sizeof(alert_text), "ALERTS %u",
                 (unsigned)snapshot->active_alert_count);
        lv_label_set_text(s_ui.alert_button_label, alert_text);
        lv_obj_set_style_border_color(
            s_ui.alert_button,
            snapshot->active_alert_count ? NH_COLOR_RED : NH_COLOR_STROKE, 0);
        lv_obj_set_style_text_color(
            s_ui.alert_button_label,
            snapshot->active_alert_count ? NH_COLOR_RED : NH_COLOR_TEXT, 0);
    }

    bool active_job = snapshot->telemetry_ready &&
                      (snapshot->job == NH_JOB_PREPARING ||
                       snapshot->job == NH_JOB_PRINTING ||
                       snapshot->job == NH_JOB_PAUSED);
    if (s_ui.control_motion_status) {
        const char *motion_status = "Motion controls disabled";
        if (snapshot->job == NH_JOB_PRINTING ||
            snapshot->job == NH_JOB_PREPARING) {
            motion_status = "Locked during active print";
        } else if (snapshot->job == NH_JOB_PAUSED) {
            motion_status = "Locked while print paused";
        }
        lv_label_set_text(s_ui.control_motion_status, motion_status);
    }
    if (s_ui.control_thermal_status) {
        char material_status[48];
        if (snapshot->ams.known) {
            snprintf(material_status, sizeof(material_status),
                     "%u AMS  /  %u trays",
                     (unsigned)snapshot->ams.unit_count,
                     (unsigned)snapshot->ams.tray_count);
        } else {
            strlcpy(material_status, "AMS not reported",
                    sizeof(material_status));
        }
        lv_label_set_text(s_ui.control_thermal_status, material_status);
    }
    if (s_ui.ams_environment) {
        const nh_ams_unit_t *unit =
            snapshot->ams.unit_count ? &snapshot->ams.units[0] : NULL;
        char environment[80];
        if (unit) {
            if (unit->humidity_known && unit->temperature_known) {
                snprintf(
                    environment, sizeof(environment),
                    "Humidity index %u  /  %.1f C%s",
                    (unsigned)unit->humidity_index, unit->temperature_c,
                    unit->material_at_risk ? "  /  CHECK" : "");
            } else {
                strlcpy(environment, "Humidity --  /  Temperature --",
                        sizeof(environment));
            }
        } else {
            strlcpy(environment, "Humidity --  /  Temperature --",
                    sizeof(environment));
        }
        lv_label_set_text(s_ui.ams_environment, environment);
        lv_obj_set_style_text_color(
            s_ui.ams_environment,
            unit && unit->material_at_risk ? NH_COLOR_AMBER : NH_COLOR_MUTED,
            0);
    }
    for (size_t i = 0; i < 4; ++i) {
        if (!s_ui.ams_trays[i]) {
            continue;
        }
        char tray_text[72];
        if (i < snapshot->ams.tray_count) {
            const nh_ams_tray_t *tray = &snapshot->ams.trays[i];
            snprintf(
                tray_text, sizeof(tray_text), "SLOT %u  /  %s  /  %s%u%%",
                (unsigned)(tray->tray_id + 1),
                tray->present ? tray->material : "EMPTY",
                tray->remaining_known ? "" : "--",
                tray->remaining_known
                    ? (unsigned)tray->remaining_percent : 0U);
        } else {
            snprintf(tray_text, sizeof(tray_text), "SLOT %u  /  --",
                     (unsigned)(i + 1));
        }
        lv_label_set_text(s_ui.ams_trays[i], tray_text);
    }
    const char *job_name =
        snapshot->job_name && snapshot->job_name[0]
            ? snapshot->job_name
            : (active_job ? "Active print" : "No active print");
    if (active_job && strcmp(job_name, "No active print") == 0) {
        job_name = "Active print";
    }
    lv_label_set_text(s_ui.job_name, job_name);
    if (s_ui.job_page_title) {
        lv_label_set_text(s_ui.job_page_title,
                          active_job ? job_name : job_heading);
    }

    char detail[96];
    snprintf(detail, sizeof(detail), "%s  |  %s remaining",
             snapshot->job_layer ? snapshot->job_layer : "Layer -- / --",
             snapshot->remaining ? snapshot->remaining : "--h --m");
    lv_label_set_text(s_ui.job_detail, detail);
    lv_bar_set_value(s_ui.job_progress,
                     snapshot->telemetry_ready
                         ? snapshot->progress_percent
                         : 0,
                     LV_ANIM_ON);

    char percent[12];
    if (snapshot->telemetry_ready) {
        snprintf(percent, sizeof(percent), "%u%%",
                 snapshot->progress_percent);
    } else {
        strlcpy(percent, "--%", sizeof(percent));
    }
    lv_label_set_text(s_ui.job_percent, percent);
    if (s_ui.job_page_progress) {
        lv_label_set_text(s_ui.job_page_progress, percent);
    }

    lv_color_t job_color =
        snapshot->telemetry_ready ? NH_COLOR_GREEN : NH_COLOR_CYAN;
    if (!snapshot->telemetry_ready ||
        snapshot->job == NH_JOB_UNKNOWN) {
        job_color = NH_COLOR_CYAN;
    } else if (snapshot->job == NH_JOB_PRINTING) {
        job_color = NH_COLOR_CYAN;
    } else if (snapshot->job == NH_JOB_PAUSED ||
               snapshot->job == NH_JOB_PREPARING) {
        job_color = NH_COLOR_AMBER;
    } else if (snapshot->job == NH_JOB_FAILED) {
        job_color = NH_COLOR_RED;
    } else if (snapshot->job == NH_JOB_COMPLETE) {
        job_color = NH_COLOR_VIOLET;
    }
    lv_obj_t *job_state_label = lv_obj_get_child(s_ui.job_state, 0);
    if (job_state_label) {
        lv_label_set_text(job_state_label, nh_job_label(snapshot->job));
        lv_obj_set_style_text_color(job_state_label, job_color, 0);
    }
    lv_obj_set_style_border_color(s_ui.job_state, job_color, 0);
    lv_obj_set_style_bg_color(s_ui.job_state,
                              lv_color_darken(job_color, 190), 0);

    if (s_ui.job_page_state) {
        lv_obj_t *page_state_label =
            lv_obj_get_child(s_ui.job_page_state, 0);
        const char *page_state =
            snapshot->connection == NH_CONNECTION_ONLINE
                ? nh_job_label(snapshot->job)
                : nh_connection_label(snapshot->connection);
        if (page_state_label) {
            lv_label_set_text(page_state_label, page_state);
            lv_obj_set_style_text_color(page_state_label,
                                        snapshot->connection ==
                                                NH_CONNECTION_ONLINE
                                            ? job_color
                                            : connection_color,
                                        0);
        }
        lv_obj_set_style_border_color(s_ui.job_page_state,
                                      snapshot->connection ==
                                              NH_CONNECTION_ONLINE
                                          ? job_color
                                          : connection_color,
                                      0);
        lv_obj_set_style_bg_color(
            s_ui.job_page_state,
            lv_color_darken(
                snapshot->connection == NH_CONNECTION_ONLINE
                    ? job_color
                    : connection_color,
                190),
            0);
    }
    if (s_ui.job_page_copy) {
        char job_copy[160];
        if (snapshot->connection == NH_CONNECTION_ONLINE &&
            snapshot->telemetry_ready) {
            snprintf(job_copy, sizeof(job_copy), "%s\n%s  /  %s remaining",
                     job_name,
                     snapshot->job_layer ? snapshot->job_layer : "Layer -- / --",
                     snapshot->remaining ? snapshot->remaining : "--h --m");
        } else if (snapshot->connection == NH_CONNECTION_ONLINE) {
            strlcpy(job_copy,
                    "Waiting for a fresh status report from the P1S.",
                    sizeof(job_copy));
        } else {
            snprintf(job_copy, sizeof(job_copy),
                     "Pair the controller with the P1S LAN profile to receive "
                     "live job telemetry.");
        }
        lv_label_set_text(s_ui.job_page_copy, job_copy);
    }

    char temperature[32];
    if (snapshot->connection == NH_CONNECTION_ONLINE &&
        snapshot->telemetry_ready) {
        snprintf(temperature, sizeof(temperature), "%.0f / %.0f C",
                 snapshot->nozzle_current_c, snapshot->nozzle_target_c);
        lv_label_set_text(s_ui.nozzle_value, temperature);
        snprintf(temperature, sizeof(temperature), "%.0f / %.0f C",
                 snapshot->bed_current_c, snapshot->bed_target_c);
        lv_label_set_text(s_ui.bed_value, temperature);
        snprintf(temperature, sizeof(temperature), "%.0f C",
                 snapshot->chamber_current_c);
        lv_label_set_text(s_ui.chamber_value, temperature);
    } else {
        lv_label_set_text(s_ui.nozzle_value, "-- / -- C");
        lv_label_set_text(s_ui.bed_value, "-- / -- C");
        lv_label_set_text(s_ui.chamber_value, "-- C");
    }

    if (snapshot->sd_mounted) {
        char capacity[32];
        double gib = (double)snapshot->sd_capacity_bytes / (1024.0 * 1024.0 * 1024.0);
        snprintf(capacity, sizeof(capacity), "%.0f GB", gib);
        lv_label_set_text(s_ui.sd_value, capacity);
        unsigned used_percent = 0;
        if (snapshot->sd_capacity_bytes > 0 &&
            snapshot->sd_free_bytes <= snapshot->sd_capacity_bytes) {
            used_percent = (unsigned)(
                ((snapshot->sd_capacity_bytes - snapshot->sd_free_bytes) *
                 100U) /
                snapshot->sd_capacity_bytes);
        }
        char storage_detail[48];
        snprintf(storage_detail, sizeof(storage_detail),
                 "Controller SD / %u%% used", used_percent);
        lv_label_set_text(s_ui.sd_detail, storage_detail);
        if (s_ui.sd_arc) {
            lv_arc_set_value(s_ui.sd_arc, (int32_t)used_percent);
        }
        lv_obj_set_style_text_color(s_ui.sd_value, NH_COLOR_GREEN, 0);
    } else {
        lv_label_set_text(s_ui.sd_value, "NOT MOUNTED");
        lv_label_set_text(s_ui.sd_detail, "Controller SD / FAT32 needed");
        if (s_ui.sd_arc) {
            lv_arc_set_value(s_ui.sd_arc, 0);
        }
        lv_obj_set_style_text_color(s_ui.sd_value, NH_COLOR_AMBER, 0);
    }
    if (s_ui.sd_rescan_button) {
        lv_obj_t *label = lv_obj_get_child(s_ui.sd_rescan_button, 0);
        if (label) {
            lv_label_set_text(label,
                              snapshot->sd_mounted
                                  ? "REFRESH SD"
                                  : "RETRY SD");
        }
    }

    if (!snapshot->printer_sd_known ||
        snapshot->connection != NH_CONNECTION_ONLINE) {
        update_pill(s_ui.printer_sd_pill, s_ui.printer_sd_label,
                    NH_COLOR_AMBER, "P1S SD UNKNOWN");
    } else if (snapshot->printer_sd_present) {
        update_pill(s_ui.printer_sd_pill, s_ui.printer_sd_label,
                    NH_COLOR_GREEN, "P1S SD READY");
    } else {
        update_pill(s_ui.printer_sd_pill, s_ui.printer_sd_label,
                    NH_COLOR_RED, "P1S SD MISSING");
    }

    set_online_gating();
    refresh_network_widgets();
}

esp_err_t nh_ui_create(const nh_ui_config_t *config)
{
    ESP_RETURN_ON_FALSE(config && config->display && config->snapshot,
                        ESP_ERR_INVALID_ARG, TAG, "invalid UI config");
    memset(&s_ui, 0, sizeof(s_ui));
    s_ui.cfg = *config;
    store_snapshot(config->snapshot);
    s_ui.controller_sd_valid = true;

    ESP_RETURN_ON_FALSE(lvgl_port_lock(5000), ESP_ERR_TIMEOUT, TAG, "LVGL lock");

    s_ui.screen = lv_screen_active();
    set_obj_box(s_ui.screen, NH_COLOR_BG, 0, 0);
    lv_obj_set_style_text_font(s_ui.screen, &lv_font_montserrat_14, 0);
    lv_obj_clear_flag(s_ui.screen, LV_OBJ_FLAG_SCROLLABLE);

    build_chrome();
    for (size_t i = 0; i < NH_PAGE_COUNT; ++i) {
        s_ui.pages[i] = lv_obj_create(s_ui.content);
        set_obj_box(s_ui.pages[i], NH_COLOR_BG, 0, 0);
        lv_obj_set_size(s_ui.pages[i], 688, 340);
        lv_obj_set_pos(s_ui.pages[i], 0, 0);
        lv_obj_clear_flag(s_ui.pages[i], LV_OBJ_FLAG_SCROLLABLE);
        if (i != NH_PAGE_DASHBOARD) {
            lv_obj_add_flag(s_ui.pages[i], LV_OBJ_FLAG_HIDDEN);
        }
    }

    build_dashboard_page(s_ui.pages[NH_PAGE_DASHBOARD]);
    build_job_page(s_ui.pages[NH_PAGE_JOB]);
    build_control_page(s_ui.pages[NH_PAGE_CONTROL]);
    build_files_page(s_ui.pages[NH_PAGE_FILES]);
    build_camera_page(s_ui.pages[NH_PAGE_CAMERA]);
    build_settings_page(s_ui.pages[NH_PAGE_SETTINGS]);

    lv_obj_set_style_bg_color(s_ui.nav_buttons[NH_PAGE_DASHBOARD],
                              lv_color_hex(0x163444), 0);
    lv_obj_set_style_border_color(s_ui.nav_buttons[NH_PAGE_DASHBOARD],
                                  NH_COLOR_CYAN, 0);

    refresh_snapshot();
    lvgl_port_unlock();

    ESP_LOGI(TAG, "PrintDeck UI created (%u bound actions)",
             (unsigned)s_ui.binding_count);
    return ESP_OK;
}

esp_err_t nh_ui_update(const nh_printer_snapshot_t *snapshot)
{
    ESP_RETURN_ON_FALSE(snapshot, ESP_ERR_INVALID_ARG, TAG, "snapshot required");
    ESP_RETURN_ON_FALSE(s_ui.screen, ESP_ERR_INVALID_STATE, TAG, "UI not created");
    ESP_RETURN_ON_FALSE(lvgl_port_lock(1000), ESP_ERR_TIMEOUT, TAG, "LVGL lock");
    store_snapshot(snapshot);
    refresh_snapshot();
    lvgl_port_unlock();
    return ESP_OK;
}

esp_err_t nh_ui_storage_update(bool mounted, esp_err_t mount_error,
                               uint64_t capacity_bytes, uint64_t free_bytes)
{
    ESP_RETURN_ON_FALSE(s_ui.screen, ESP_ERR_INVALID_STATE, TAG,
                        "UI not created");
    ESP_RETURN_ON_FALSE(lvgl_port_lock(1000), ESP_ERR_TIMEOUT, TAG,
                        "LVGL lock");
    s_ui.snapshot_store.sd_mounted = mounted;
    s_ui.snapshot_store.sd_mount_error = mount_error;
    s_ui.snapshot_store.sd_capacity_bytes =
        mounted ? capacity_bytes : 0;
    s_ui.snapshot_store.sd_free_bytes = mounted ? free_bytes : 0;
    s_ui.controller_sd_valid = true;
    refresh_snapshot();
    lvgl_port_unlock();
    return ESP_OK;
}

esp_err_t nh_ui_history_update(const nh_history_snapshot_t *snapshot)
{
    ESP_RETURN_ON_FALSE(snapshot, ESP_ERR_INVALID_ARG, TAG,
                        "history snapshot required");
    ESP_RETURN_ON_FALSE(s_ui.screen, ESP_ERR_INVALID_STATE, TAG,
                        "UI not created");
    ESP_RETURN_ON_FALSE(lvgl_port_lock(1000), ESP_ERR_TIMEOUT, TAG,
                        "LVGL lock");
    s_ui.history = *snapshot;
    s_ui.history_valid = true;
    lvgl_port_unlock();
    return ESP_OK;
}

esp_err_t nh_ui_files_update(const nh_files_snapshot_t *snapshot)
{
    ESP_RETURN_ON_FALSE(snapshot, ESP_ERR_INVALID_ARG, TAG,
                        "files snapshot required");
    ESP_RETURN_ON_FALSE(s_ui.screen, ESP_ERR_INVALID_STATE, TAG,
                        "UI not created");
    ESP_RETURN_ON_FALSE(lvgl_port_lock(1000), ESP_ERR_TIMEOUT, TAG,
                        "LVGL lock");
    s_ui.files = *snapshot;
    s_ui.files_valid = true;
    rebuild_files_list();
    lvgl_port_unlock();
    return ESP_OK;
}

esp_err_t nh_ui_fleet_update(const nh_fleet_snapshot_t *snapshot)
{
    ESP_RETURN_ON_FALSE(snapshot, ESP_ERR_INVALID_ARG, TAG,
                        "fleet snapshot required");
    ESP_RETURN_ON_FALSE(s_ui.screen, ESP_ERR_INVALID_STATE, TAG,
                        "UI not created");
    ESP_RETURN_ON_FALSE(lvgl_port_lock(1000), ESP_ERR_TIMEOUT, TAG,
                        "LVGL lock");
    s_ui.fleet = *snapshot;
    s_ui.fleet_valid = true;
    if (s_ui.fleet_button_label) {
        char label[32];
        snprintf(label, sizeof(label), "FLEET %u%s",
                 (unsigned)snapshot->count,
                 snapshot->attention_count ? " !" : "");
        lv_label_set_text(s_ui.fleet_button_label, label);
    }
    lvgl_port_unlock();
    return ESP_OK;
}

esp_err_t nh_ui_command_result_update(const nh_command_result_t *result)
{
    ESP_RETURN_ON_FALSE(result, ESP_ERR_INVALID_ARG, TAG,
                        "command result required");
    ESP_RETURN_ON_FALSE(s_ui.screen, ESP_ERR_INVALID_STATE, TAG,
                        "UI not created");
    ESP_RETURN_ON_FALSE(lvgl_port_lock(1000), ESP_ERR_TIMEOUT, TAG,
                        "LVGL lock");
    char status[112];
    snprintf(status, sizeof(status), "Command #%lu %s: %s",
             (unsigned long)result->sequence_id,
             nh_action_label(result->action),
             nh_command_result_label(result->state));
    update_footer(
        status,
        result->state == NH_COMMAND_RESULT_REJECTED ||
                result->state == NH_COMMAND_RESULT_TIMED_OUT
            ? NH_COLOR_RED
            : NH_COLOR_GREEN);
    lvgl_port_unlock();
    return ESP_OK;
}

esp_err_t nh_ui_ai_update(const nh_ai_snapshot_t *snapshot)
{
    ESP_RETURN_ON_FALSE(snapshot, ESP_ERR_INVALID_ARG, TAG,
                        "AI snapshot required");
    ESP_RETURN_ON_FALSE(s_ui.screen, ESP_ERR_INVALID_STATE, TAG,
                        "UI not created");
    ESP_RETURN_ON_FALSE(lvgl_port_lock(1000), ESP_ERR_TIMEOUT, TAG,
                        "LVGL lock");
    s_ui.ai = *snapshot;
    s_ui.ai_valid = true;
    if (s_ui.ai_status_label) {
        char label[40];
        if (!snapshot->configured) {
            strlcpy(label, "AI OFF / LOCAL", sizeof(label));
        } else if (snapshot->actionable_count) {
            snprintf(label, sizeof(label), "AI ALERTS %u",
                     (unsigned)snapshot->actionable_count);
        } else {
            strlcpy(label,
                    snapshot->notify_only ? "AI WATCH / NOTIFY"
                                          : "AI WATCH / PAUSE",
                    sizeof(label));
        }
        lv_label_set_text(s_ui.ai_status_label, label);
    }
    lvgl_port_unlock();
    return ESP_OK;
}

esp_err_t nh_ui_network_update(const nh_network_snapshot_t *snapshot)
{
    ESP_RETURN_ON_FALSE(snapshot, ESP_ERR_INVALID_ARG, TAG,
                        "network snapshot required");
    ESP_RETURN_ON_FALSE(s_ui.screen, ESP_ERR_INVALID_STATE, TAG,
                        "UI not created");
    ESP_RETURN_ON_FALSE(lvgl_port_lock(1000), ESP_ERR_TIMEOUT, TAG,
                        "LVGL lock");
    s_ui.network = *snapshot;
    s_ui.network_valid = true;
    refresh_network_widgets();
    rebuild_network_list();
    lvgl_port_unlock();
    return ESP_OK;
}

esp_err_t nh_ui_printer_update(const nh_printer_status_t *status)
{
    ESP_RETURN_ON_FALSE(status, ESP_ERR_INVALID_ARG, TAG,
                        "printer status required");
    ESP_RETURN_ON_FALSE(s_ui.screen, ESP_ERR_INVALID_STATE, TAG,
                        "UI not created");
    ESP_RETURN_ON_FALSE(lvgl_port_lock(1000), ESP_ERR_TIMEOUT, TAG,
                        "LVGL lock");
    s_ui.printer = *status;
    s_ui.printer_valid = true;
    if (s_ui.active_page == NH_PAGE_CAMERA) {
        bool camera_ready = camera_profile_ready();
        esp_err_t camera_err = set_camera_requested(camera_ready);
        if (!camera_ready) {
            reset_camera_view();
        }
        if (camera_err != ESP_OK) {
            ESP_LOGW(TAG, "Camera activation update failed: %s",
                     esp_err_to_name(camera_err));
        }
    }
    refresh_network_widgets();
    lvgl_port_unlock();
    return ESP_OK;
}

esp_err_t nh_ui_camera_status_update(const nh_camera_status_t *status)
{
    ESP_RETURN_ON_FALSE(status, ESP_ERR_INVALID_ARG, TAG,
                        "camera status required");
    ESP_RETURN_ON_FALSE(s_ui.screen, ESP_ERR_INVALID_STATE, TAG,
                        "UI not created");
    ESP_RETURN_ON_FALSE(lvgl_port_lock(1000), ESP_ERR_TIMEOUT, TAG,
                        "LVGL lock");

    s_ui.camera = *status;
    s_ui.camera_valid = true;
    const char *pill_text = nh_camera_state_label(status->state);
    const char *detail = "LOCAL LIVEVIEW  /  CAMERA READY";
    const char *placeholder = "Opening encrypted local liveview...";
    lv_color_t color = NH_COLOR_CYAN;
    bool show_placeholder = false;

    switch (status->state) {
    case NH_CAMERA_STOPPED:
        detail = "LOCAL LIVEVIEW  /  OPENS ONLY ON THIS TAB";
        placeholder = "Camera starts when this tab is open";
        show_placeholder = true;
        break;
    case NH_CAMERA_NO_PROFILE:
        color = NH_COLOR_AMBER;
        detail = "PAIR THE P1S ON THE SYSTEM PAGE";
        placeholder = "P1S LAN profile is required";
        show_placeholder = true;
        break;
    case NH_CAMERA_CONNECTING:
        detail = "ENCRYPTED LAN SESSION  /  CONNECTING TO P1S";
        placeholder = "Connecting directly to the P1S...";
        show_placeholder = s_ui.camera_frame_count == 0;
        break;
    case NH_CAMERA_LIVE:
        color = NH_COLOR_GREEN;
        detail = "LOCAL LIVEVIEW  /  WAITING FOR NEXT FRAME";
        break;
    case NH_CAMERA_RECONNECTING:
        color = NH_COLOR_AMBER;
        detail = s_ui.camera_frame_count
                     ? "RECONNECTING  /  LAST FRAME SHOWN"
                     : "RECONNECTING TO P1S CAMERA";
        placeholder = "P1S camera is reconnecting...";
        show_placeholder = s_ui.camera_frame_count == 0;
        break;
    case NH_CAMERA_ERROR:
    default:
        color = NH_COLOR_RED;
        detail = "CAMERA UNAVAILABLE  /  CHECK LOCAL NETWORK";
        placeholder = "Camera feed is currently unavailable";
        show_placeholder = true;
        break;
    }

    update_pill(s_ui.camera_status_pill, s_ui.camera_status_label,
                color, pill_text);
    if (s_ui.camera_detail) {
        lv_label_set_text(s_ui.camera_detail, detail);
    }
    if (s_ui.camera_placeholder_copy) {
        lv_label_set_text(s_ui.camera_placeholder_copy, placeholder);
    }
    if (show_placeholder) {
        lv_obj_clear_flag(s_ui.camera_placeholder, LV_OBJ_FLAG_HIDDEN);
        lv_obj_add_flag(s_ui.camera_image, LV_OBJ_FLAG_HIDDEN);
    } else if (s_ui.camera_frame_count) {
        lv_obj_add_flag(s_ui.camera_placeholder, LV_OBJ_FLAG_HIDDEN);
        lv_obj_clear_flag(s_ui.camera_image, LV_OBJ_FLAG_HIDDEN);
    }

    lvgl_port_unlock();
    return ESP_OK;
}

esp_err_t nh_ui_camera_frame(const uint8_t *rgb565,
                             uint16_t width,
                             uint16_t height,
                             uint16_t source_width,
                             uint16_t source_height)
{
    ESP_RETURN_ON_FALSE(rgb565 && width && height,
                        ESP_ERR_INVALID_ARG, TAG, "camera frame required");
    ESP_RETURN_ON_FALSE(s_ui.screen && s_ui.camera_image,
                        ESP_ERR_INVALID_STATE, TAG, "camera UI not created");
    ESP_RETURN_ON_FALSE(lvgl_port_lock(1000), ESP_ERR_TIMEOUT, TAG,
                        "LVGL lock");
    if (s_ui.active_page != NH_PAGE_CAMERA ||
        !s_ui.camera_requested_active) {
        lvgl_port_unlock();
        return ESP_ERR_INVALID_STATE;
    }

    uint8_t index = s_ui.camera_frame_index ^ 1U;
    lv_image_dsc_t *frame = &s_ui.camera_frames[index];
    if (frame->header.magic == LV_IMAGE_HEADER_MAGIC) {
        lv_image_cache_drop(frame);
    }
    *frame = (lv_image_dsc_t){
        .header = {
            .magic = LV_IMAGE_HEADER_MAGIC,
            .cf = LV_COLOR_FORMAT_RGB565,
            .flags = LV_IMAGE_FLAGS_MODIFIABLE,
            .w = width,
            .h = height,
            .stride = width * 2U,
        },
        .data_size = (uint32_t)width * height * 2U,
        .data = rgb565,
    };

    lv_image_set_src(s_ui.camera_image, frame);
    lv_obj_align(s_ui.camera_image, LV_ALIGN_CENTER, 0, 0);
    lv_obj_add_flag(s_ui.camera_placeholder, LV_OBJ_FLAG_HIDDEN);
    lv_obj_clear_flag(s_ui.camera_image, LV_OBJ_FLAG_HIDDEN);
    lv_obj_move_foreground(s_ui.camera_status_pill);
    if (s_ui.camera_detail) {
        lv_obj_t *detail_bar = lv_obj_get_parent(s_ui.camera_detail);
        lv_obj_move_foreground(detail_bar);
        char detail[112];
        snprintf(detail, sizeof(detail),
                 "LOCAL LIVEVIEW  /  SOURCE %u x %u  /  FRAME %lu",
                 source_width, source_height,
                 (unsigned long)(s_ui.camera_frame_count + 1U));
        lv_label_set_text(s_ui.camera_detail, detail);
    }

    s_ui.camera_frame_index = index;
    s_ui.camera_frame_count++;
    update_pill(s_ui.camera_status_pill, s_ui.camera_status_label,
                NH_COLOR_GREEN, "LIVE");

    lvgl_port_unlock();
    return ESP_OK;
}
