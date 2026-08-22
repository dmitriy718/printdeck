#include "nh_core.h"

#include <inttypes.h>

#include "esp_log.h"

static const char *TAG = "nh_core";

const char *nh_connection_label(nh_connection_state_t state)
{
    switch (state) {
    case NH_CONNECTION_UNCONFIGURED:
        return "SETUP REQUIRED";
    case NH_CONNECTION_CONNECTING:
        return "CONNECTING";
    case NH_CONNECTION_ONLINE:
        return "ONLINE";
    case NH_CONNECTION_OFFLINE:
        return "OFFLINE";
    case NH_CONNECTION_ERROR:
        return "CONNECTION ERROR";
    default:
        return "UNKNOWN";
    }
}

const char *nh_job_label(nh_job_state_t state)
{
    switch (state) {
    case NH_JOB_UNKNOWN:
        return "SYNCING";
    case NH_JOB_IDLE:
        return "READY";
    case NH_JOB_PREPARING:
        return "PREPARING";
    case NH_JOB_PRINTING:
        return "PRINTING";
    case NH_JOB_PAUSED:
        return "PAUSED";
    case NH_JOB_COMPLETE:
        return "COMPLETE";
    case NH_JOB_FAILED:
        return "FAILED";
    default:
        return "UNKNOWN";
    }
}

const char *nh_action_label(nh_action_t action)
{
    switch (action) {
    case NH_ACTION_CONNECT:
        return "connect";
    case NH_ACTION_PAUSE:
        return "pause print";
    case NH_ACTION_RESUME:
        return "resume print";
    case NH_ACTION_CANCEL:
        return "cancel print";
    case NH_ACTION_HOME:
        return "home axes";
    case NH_ACTION_JOG_X:
        return "jog X";
    case NH_ACTION_JOG_Y:
        return "jog Y";
    case NH_ACTION_JOG_Z:
        return "jog Z";
    case NH_ACTION_LIGHT_TOGGLE:
        return "toggle chamber light";
    case NH_ACTION_FAN_SET:
        return "set part fan";
    case NH_ACTION_PREHEAT_PLA:
        return "preheat PLA";
    case NH_ACTION_PREHEAT_PETG:
        return "preheat PETG";
    case NH_ACTION_COOLDOWN:
        return "cool down";
    case NH_ACTION_OPEN_FILE:
        return "open print file";
    case NH_ACTION_BRIGHTNESS_SET:
        return "set display brightness";
    case NH_ACTION_SD_RESCAN:
        return "refresh controller SD";
    case NH_ACTION_SPEED_PROFILE:
        return "set speed profile";
    case NH_ACTION_CALIBRATE:
        return "run calibration";
    case NH_ACTION_SKIP_OBJECT:
        return "skip object";
    case NH_ACTION_NONE:
    default:
        return "none";
    }
}

bool nh_action_requires_online(nh_action_t action)
{
    switch (action) {
    case NH_ACTION_CONNECT:
    case NH_ACTION_BRIGHTNESS_SET:
    case NH_ACTION_SD_RESCAN:
    case NH_ACTION_NONE:
        return false;
    default:
        return true;
    }
}

void nh_secure_zero(void *buffer, size_t length)
{
    volatile uint8_t *byte = (volatile uint8_t *)buffer;
    while (byte && length > 0) {
        *byte++ = 0;
        --length;
    }
}

bool nh_action_requires_confirmation(nh_action_t action)
{
    return action == NH_ACTION_CANCEL;
}

esp_err_t nh_demo_action_handler(nh_action_t action, int32_t value, void *ctx)
{
    const nh_printer_snapshot_t *snapshot = (const nh_printer_snapshot_t *)ctx;
    if (nh_action_requires_online(action) &&
        (!snapshot || snapshot->connection != NH_CONNECTION_ONLINE)) {
        ESP_LOGW(TAG, "Blocked '%s': printer is not online", nh_action_label(action));
        return ESP_ERR_INVALID_STATE;
    }

    ESP_LOGI(TAG, "Demo transport accepted action='%s' value=%" PRId32,
             nh_action_label(action), value);
    return ESP_OK;
}
