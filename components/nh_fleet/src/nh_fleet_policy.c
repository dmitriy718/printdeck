#include "nh_fleet.h"

#include <strings.h>

uint32_t nh_fleet_capabilities_for(const char *model, const char *firmware)
{
    if (!model || !firmware || !model[0] || !firmware[0]) {
        return 0;
    }
    if (strcasecmp(model, "P1S") == 0 ||
        strcasecmp(model, "BL-P001") == 0) {
        /*
         * Reads are supported across observed P1S releases. Writes require an
         * exact qualified firmware row and are deliberately absent here.
         */
        return NH_FLEET_CAP_TELEMETRY | NH_FLEET_CAP_CAMERA |
               NH_FLEET_CAP_AMS | NH_FLEET_CAP_HMS |
               NH_FLEET_CAP_FILES;
    }
    return 0;
}

nh_fleet_attention_t nh_fleet_attention(const nh_fleet_printer_t *printer)
{
    if (!printer || printer->connection != NH_PRINTER_ONLINE) {
        return NH_FLEET_ATTENTION_OFFLINE;
    }
    if (printer->active_alerts || printer->job == NH_JOB_FAILED) {
        return NH_FLEET_ATTENTION_ERROR;
    }
    if (printer->job == NH_JOB_PAUSED) {
        return NH_FLEET_ATTENTION_PAUSED;
    }
    if (printer->job == NH_JOB_PRINTING && printer->remaining_known &&
        printer->remaining_minutes <= 15) {
        return NH_FLEET_ATTENTION_FINISHING;
    }
    if (printer->job == NH_JOB_PRINTING ||
        printer->job == NH_JOB_PREPARING) {
        return NH_FLEET_ATTENTION_PRINTING;
    }
    return NH_FLEET_ATTENTION_IDLE;
}

const char *nh_fleet_attention_label(nh_fleet_attention_t attention)
{
    switch (attention) {
    case NH_FLEET_ATTENTION_ERROR:
        return "Needs attention";
    case NH_FLEET_ATTENTION_PAUSED:
        return "Paused";
    case NH_FLEET_ATTENTION_FINISHING:
        return "Finishing soon";
    case NH_FLEET_ATTENTION_PRINTING:
        return "Printing";
    case NH_FLEET_ATTENTION_IDLE:
        return "Idle";
    case NH_FLEET_ATTENTION_OFFLINE:
    default:
        return "Offline";
    }
}
