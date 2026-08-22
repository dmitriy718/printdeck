#include <assert.h>
#include <stdio.h>
#include <string.h>

#include "nh_printer.h"

static void test_typed_bounds(void)
{
    assert(nh_printer_typed_action_valid(NH_ACTION_FAN_SET, 0));
    assert(nh_printer_typed_action_valid(NH_ACTION_FAN_SET, 100));
    assert(!nh_printer_typed_action_valid(NH_ACTION_FAN_SET, 101));
    assert(nh_printer_typed_action_valid(NH_ACTION_JOG_X, -10));
    assert(!nh_printer_typed_action_valid(NH_ACTION_JOG_X, 0));
    assert(!nh_printer_typed_action_valid(NH_ACTION_JOG_Z, 2));
    assert(nh_printer_typed_action_valid(NH_ACTION_SPEED_PROFILE, 1));
    assert(nh_printer_typed_action_valid(NH_ACTION_SPEED_PROFILE, 4));
    assert(!nh_printer_typed_action_valid(NH_ACTION_SPEED_PROFILE, 5));
    assert(nh_printer_typed_action_valid(NH_ACTION_SKIP_OBJECT, 63));
    assert(!nh_printer_typed_action_valid(NH_ACTION_SKIP_OBJECT, 64));
}

static void test_result_vocabulary(void)
{
    assert(strcmp(nh_command_result_label(NH_COMMAND_RESULT_QUEUED),
                  "QUEUED") == 0);
    assert(strcmp(nh_command_result_label(NH_COMMAND_RESULT_SENT),
                  "SENT") == 0);
    assert(strcmp(nh_command_result_label(NH_COMMAND_RESULT_ACKNOWLEDGED),
                  "ACKNOWLEDGED") == 0);
    assert(strcmp(nh_command_result_label(NH_COMMAND_RESULT_OBSERVED),
                  "OBSERVED") == 0);
    assert(strcmp(nh_command_result_label(NH_COMMAND_RESULT_REJECTED),
                  "REJECTED") == 0);
    assert(strcmp(nh_command_result_label(NH_COMMAND_RESULT_TIMED_OUT),
                  "TIMED OUT") == 0);
}

int main(void)
{
    test_typed_bounds();
    test_result_vocabulary();
    puts("control policy tests passed (2 groups)");
    return 0;
}
