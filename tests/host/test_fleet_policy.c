#include <assert.h>
#include <stdio.h>
#include <string.h>

#include "nh_fleet.h"

static void test_capabilities_fail_closed(void)
{
    assert(nh_fleet_capabilities_for(NULL, "1") == 0);
    assert(nh_fleet_capabilities_for("P1S", "") == 0);
    assert(nh_fleet_capabilities_for("X1C", "01.00") == 0);
    uint32_t p1s = nh_fleet_capabilities_for("P1S", "01.06.00");
    assert((p1s & NH_FLEET_CAP_TELEMETRY) != 0);
    assert((p1s & NH_FLEET_CAP_CAMERA) != 0);
    assert((p1s & NH_FLEET_CAP_BASIC_COMMANDS) == 0);
    assert((p1s & NH_FLEET_CAP_MOTION) == 0);
}

static void test_attention_order(void)
{
    nh_fleet_printer_t printer = {
        .connection = NH_PRINTER_OFFLINE,
        .job = NH_JOB_IDLE,
    };
    assert(nh_fleet_attention(&printer) == NH_FLEET_ATTENTION_OFFLINE);
    printer.connection = NH_PRINTER_ONLINE;
    assert(nh_fleet_attention(&printer) == NH_FLEET_ATTENTION_IDLE);
    printer.job = NH_JOB_PRINTING;
    printer.remaining_minutes = 90;
    printer.remaining_known = true;
    assert(nh_fleet_attention(&printer) == NH_FLEET_ATTENTION_PRINTING);
    printer.remaining_minutes = 15;
    assert(nh_fleet_attention(&printer) == NH_FLEET_ATTENTION_FINISHING);
    printer.job = NH_JOB_PAUSED;
    assert(nh_fleet_attention(&printer) == NH_FLEET_ATTENTION_PAUSED);
    printer.active_alerts = 1;
    assert(nh_fleet_attention(&printer) == NH_FLEET_ATTENTION_ERROR);

    printer.active_alerts = 0;
    printer.job = NH_JOB_PRINTING;
    printer.remaining_known = false;
    printer.remaining_minutes = 0;
    assert(nh_fleet_attention(&printer) == NH_FLEET_ATTENTION_PRINTING);
}

int main(void)
{
    test_capabilities_fail_closed();
    test_attention_order();
    puts("fleet policy tests passed (2 groups)");
    return 0;
}
