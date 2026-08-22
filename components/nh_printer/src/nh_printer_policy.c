#include "nh_printer.h"

bool nh_printer_typed_action_valid(nh_action_t action, int32_t value)
{
    switch (action) {
    case NH_ACTION_FAN_SET:
        return value >= 0 && value <= 100;
    case NH_ACTION_JOG_X:
    case NH_ACTION_JOG_Y:
        return value >= -10 && value <= 10 && value != 0;
    case NH_ACTION_JOG_Z:
        return value >= -1 && value <= 1 && value != 0;
    case NH_ACTION_SPEED_PROFILE:
        return value >= 1 && value <= 4;
    case NH_ACTION_SKIP_OBJECT:
        return value >= 0 && value < 64;
    case NH_ACTION_CONNECT:
    case NH_ACTION_PAUSE:
    case NH_ACTION_RESUME:
    case NH_ACTION_CANCEL:
    case NH_ACTION_HOME:
    case NH_ACTION_LIGHT_TOGGLE:
    case NH_ACTION_PREHEAT_PLA:
    case NH_ACTION_PREHEAT_PETG:
    case NH_ACTION_COOLDOWN:
    case NH_ACTION_CALIBRATE:
        return value == 0;
    default:
        return false;
    }
}

const char *nh_command_result_label(nh_command_result_state_t state)
{
    switch (state) {
    case NH_COMMAND_RESULT_QUEUED:
        return "QUEUED";
    case NH_COMMAND_RESULT_SENT:
        return "SENT";
    case NH_COMMAND_RESULT_ACKNOWLEDGED:
        return "ACKNOWLEDGED";
    case NH_COMMAND_RESULT_OBSERVED:
        return "OBSERVED";
    case NH_COMMAND_RESULT_REJECTED:
        return "REJECTED";
    case NH_COMMAND_RESULT_TIMED_OUT:
    default:
        return "TIMED OUT";
    }
}
