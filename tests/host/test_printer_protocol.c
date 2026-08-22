#include <assert.h>
#include <stdio.h>
#include <string.h>

#include "nh_printer_protocol.h"

typedef struct {
    nh_printer_snapshot_t snapshot;
    nh_printer_protocol_t protocol;
    char job_name[96];
    char job_layer[48];
    char remaining[24];
} fixture_t;

static void init_fixture(fixture_t *fixture)
{
    memset(fixture, 0, sizeof(*fixture));
    nh_printer_protocol_init(
        &fixture->protocol, &fixture->snapshot,
        fixture->job_name, sizeof(fixture->job_name),
        fixture->job_layer, sizeof(fixture->job_layer),
        fixture->remaining, sizeof(fixture->remaining));
    nh_printer_protocol_reset(&fixture->protocol);
}

static nh_printer_protocol_result_t parse(
    fixture_t *fixture, const char *json)
{
    return nh_printer_protocol_parse(
        &fixture->protocol, json, strlen(json));
}

static void test_full_running_report(void)
{
    fixture_t fixture;
    init_fixture(&fixture);
    const char *report =
        "{\"print\":{"
        "\"gcode_state\":\"RUNNING\","
        "\"subtask_name\":\"Calibration fixture\","
        "\"mc_percent\":60,"
        "\"layer_num\":\"1\","
        "\"total_layer_num\":954,"
        "\"mc_remaining_time\":780,"
        "\"nozzle_temper\":220.5,"
        "\"nozzle_target_temper\":220,"
        "\"bed_temper\":55.2,"
        "\"bed_target_temper\":55,"
        "\"chamber_temper\":38,"
        "\"cooling_fan_speed\":\"15\","
        "\"sdcard\":true,"
        "\"lights_report\":["
        "{\"node\":\"chamber_light\",\"mode\":\"on\"}]"
        "}}";

    assert(parse(&fixture, report) == NH_PRINTER_PROTOCOL_UPDATED);
    assert(fixture.snapshot.telemetry_ready);
    assert(fixture.snapshot.job == NH_JOB_PRINTING);
    assert(fixture.snapshot.progress_percent == 60);
    assert(strcmp(fixture.job_name, "Calibration fixture") == 0);
    assert(strcmp(fixture.job_layer, "Layer 1 / 954") == 0);
    assert(strcmp(fixture.remaining, "13h 00m") == 0);
    assert(fixture.snapshot.printer_sd_known);
    assert(fixture.snapshot.printer_sd_present);
    assert(fixture.snapshot.part_fan_percent == 100);
    assert(fixture.snapshot.chamber_light_on);
    assert(fixture.snapshot.nozzle_current_c > 220.4f);
}

static void test_delta_preserves_total_layers(void)
{
    fixture_t fixture;
    init_fixture(&fixture);
    assert(parse(
               &fixture,
               "{\"print\":{\"gcode_state\":\"RUNNING\","
               "\"layer_num\":20,\"total_layer_num\":954}}") ==
           NH_PRINTER_PROTOCOL_UPDATED);
    assert(parse(
               &fixture,
               "{\"print\":{\"layer_num\":21,\"total_layer_num\":0}}") ==
           NH_PRINTER_PROTOCOL_UPDATED);
    assert(strcmp(fixture.job_layer, "Layer 21 / 954") == 0);
}

static void test_idle_clears_job_state(void)
{
    fixture_t fixture;
    init_fixture(&fixture);
    assert(parse(
               &fixture,
               "{\"print\":{\"gcode_state\":\"RUNNING\","
               "\"subtask_name\":\"Old job\",\"mc_percent\":99,"
               "\"layer_num\":99,\"total_layer_num\":100,"
               "\"mc_remaining_time\":1}}") ==
           NH_PRINTER_PROTOCOL_UPDATED);
    assert(parse(
               &fixture,
               "{\"print\":{\"gcode_state\":\"IDLE\","
               "\"subtask_name\":\"Old job\",\"mc_percent\":99}}") ==
           NH_PRINTER_PROTOCOL_UPDATED);
    assert(fixture.snapshot.job == NH_JOB_IDLE);
    assert(fixture.snapshot.progress_percent == 0);
    assert(strcmp(fixture.job_name, "No active print") == 0);
    assert(strcmp(fixture.job_layer, "Layer -- / --") == 0);
    assert(strcmp(fixture.remaining, "--h --m") == 0);
}

static void test_new_job_does_not_reuse_old_total(void)
{
    fixture_t fixture;
    init_fixture(&fixture);
    assert(parse(
               &fixture,
               "{\"print\":{\"gcode_state\":\"RUNNING\","
               "\"layer_num\":40,\"total_layer_num\":400}}") ==
           NH_PRINTER_PROTOCOL_UPDATED);
    assert(parse(&fixture,
                 "{\"print\":{\"gcode_state\":\"IDLE\"}}") ==
           NH_PRINTER_PROTOCOL_UPDATED);
    assert(parse(
               &fixture,
               "{\"print\":{\"gcode_state\":\"PREPARE\","
               "\"layer_num\":1}}") ==
           NH_PRINTER_PROTOCOL_UPDATED);
    assert(strcmp(fixture.job_layer, "Layer 1 / --") == 0);
}

static void test_malformed_and_unrelated_payloads(void)
{
    fixture_t fixture;
    init_fixture(&fixture);
    assert(parse(&fixture, "{not-json") == NH_PRINTER_PROTOCOL_INVALID);
    assert(!fixture.snapshot.telemetry_ready);
    assert(parse(&fixture, "{\"system\":{\"command\":\"ack\"}}") ==
           NH_PRINTER_PROTOCOL_IGNORED);
    assert(!fixture.snapshot.telemetry_ready);
}

static void test_numeric_bounds(void)
{
    fixture_t fixture;
    init_fixture(&fixture);
    assert(parse(
               &fixture,
               "{\"print\":{\"gcode_state\":\"RUNNING\","
               "\"mc_percent\":150,\"cooling_fan_speed\":99,"
               "\"mc_remaining_time\":-5}}") ==
           NH_PRINTER_PROTOCOL_UPDATED);
    assert(fixture.snapshot.progress_percent == 100);
    assert(fixture.snapshot.part_fan_percent == 100);
    assert(strcmp(fixture.remaining, "--h --m") == 0);
}

static void test_first_active_delta_uses_neutral_name(void)
{
    fixture_t fixture;
    init_fixture(&fixture);
    assert(parse(&fixture,
                 "{\"print\":{\"gcode_state\":\"RUNNING\"}}") ==
           NH_PRINTER_PROTOCOL_UPDATED);
    assert(fixture.snapshot.job == NH_JOB_PRINTING);
    assert(strcmp(fixture.job_name, "Active print") == 0);
}

static void test_state_mapping(void)
{
    fixture_t fixture;
    init_fixture(&fixture);
    assert(parse(&fixture,
                 "{\"print\":{\"gcode_state\":\"PREPARE\"}}") ==
           NH_PRINTER_PROTOCOL_UPDATED);
    assert(fixture.snapshot.job == NH_JOB_PREPARING);
    assert(parse(&fixture,
                 "{\"print\":{\"gcode_state\":\"PAUSE\"}}") ==
           NH_PRINTER_PROTOCOL_UPDATED);
    assert(fixture.snapshot.job == NH_JOB_PAUSED);
    assert(parse(&fixture,
                 "{\"print\":{\"gcode_state\":\"FINISH\"}}") ==
           NH_PRINTER_PROTOCOL_UPDATED);
    assert(fixture.snapshot.job == NH_JOB_COMPLETE);
    assert(parse(&fixture,
                 "{\"print\":{\"gcode_state\":\"FAILED\"}}") ==
           NH_PRINTER_PROTOCOL_UPDATED);
    assert(fixture.snapshot.job == NH_JOB_FAILED);
}

static void test_string_layers_and_sd_number(void)
{
    fixture_t fixture;
    init_fixture(&fixture);
    assert(parse(
               &fixture,
               "{\"print\":{\"gcode_state\":\"RUNNING\","
               "\"layer_num\":\"7\",\"total_layer_num\":\"88\","
               "\"sdcard\":0}}") ==
           NH_PRINTER_PROTOCOL_UPDATED);
    assert(strcmp(fixture.job_layer, "Layer 7 / 88") == 0);
    assert(fixture.snapshot.printer_sd_known);
    assert(!fixture.snapshot.printer_sd_present);
}

static void test_delta_without_state_preserves_active_job(void)
{
    fixture_t fixture;
    init_fixture(&fixture);
    assert(parse(
               &fixture,
               "{\"print\":{\"gcode_state\":\"RUNNING\","
               "\"subtask_name\":\"Current job\",\"mc_percent\":12}}") ==
           NH_PRINTER_PROTOCOL_UPDATED);
    assert(parse(&fixture,
                 "{\"print\":{\"mc_percent\":13,\"layer_num\":2}}") ==
           NH_PRINTER_PROTOCOL_UPDATED);
    assert(fixture.snapshot.job == NH_JOB_PRINTING);
    assert(fixture.snapshot.progress_percent == 13);
    assert(strcmp(fixture.job_name, "Current job") == 0);
}

static void test_invalid_layer_values_do_not_replace_known_values(void)
{
    fixture_t fixture;
    init_fixture(&fixture);
    assert(parse(
               &fixture,
               "{\"print\":{\"gcode_state\":\"RUNNING\","
               "\"layer_num\":8,\"total_layer_num\":90}}") ==
           NH_PRINTER_PROTOCOL_UPDATED);
    assert(parse(
               &fixture,
               "{\"print\":{\"layer_num\":-1,"
               "\"total_layer_num\":\"99999999999999999999\"}}") ==
           NH_PRINTER_PROTOCOL_UPDATED);
    assert(strcmp(fixture.job_layer, "Layer 8 / 90") == 0);
}

static void test_known_hms_alert_is_mapped_and_deduplicated(void)
{
    fixture_t fixture;
    init_fixture(&fixture);
    const char *report =
        "{\"print\":{\"hms\":[{\"attr\":50332416,\"code\":65537}]}}";
    assert(parse(&fixture, report) == NH_PRINTER_PROTOCOL_UPDATED);
    assert(fixture.snapshot.alert_count == 1);
    assert(fixture.snapshot.active_alert_count == 1);
    const nh_alert_t *alert = &fixture.snapshot.alerts[0];
    assert(strcmp(alert->raw_code, "HMS_0300-0300-0001-0001") == 0);
    assert(alert->known_code);
    assert(alert->severity == NH_ALERT_CRITICAL);
    assert(strstr(alert->title, "cooling fan") != NULL);
    assert(alert->occurrence_count == 1);

    assert(parse(&fixture, report) == NH_PRINTER_PROTOCOL_UPDATED);
    assert(fixture.snapshot.alert_count == 1);
    assert(fixture.snapshot.alerts[0].occurrence_count == 1);
}

static void test_unknown_hms_is_preserved_and_delta_does_not_clear(void)
{
    fixture_t fixture;
    init_fixture(&fixture);
    assert(parse(
               &fixture,
               "{\"print\":{\"hms\":["
               "{\"attr\":\"305419896\",\"code\":\"2596069104\"}]}}") ==
           NH_PRINTER_PROTOCOL_UPDATED);
    assert(fixture.snapshot.alert_count == 1);
    assert(strcmp(
               fixture.snapshot.alerts[0].raw_code,
               "HMS_1234-5678-9ABC-DEF0") == 0);
    assert(!fixture.snapshot.alerts[0].known_code);
    assert(parse(&fixture, "{\"print\":{\"mc_percent\":22}}") ==
           NH_PRINTER_PROTOCOL_UPDATED);
    assert(fixture.snapshot.alerts[0].active);
    assert(fixture.snapshot.active_alert_count == 1);
}

static void test_hms_clear_recurrence_and_local_dismissal(void)
{
    fixture_t fixture;
    init_fixture(&fixture);
    const char *active =
        "{\"print\":{\"hms\":[{\"attr\":50332416,\"code\":65537}]}}";
    assert(parse(&fixture, active) == NH_PRINTER_PROTOCOL_UPDATED);
    assert(nh_printer_protocol_dismiss_alert(
        &fixture.protocol, "HMS_0300-0300-0001-0001"));
    assert(fixture.snapshot.alerts[0].active);
    assert(fixture.snapshot.alerts[0].dismissed_locally);
    assert(fixture.snapshot.active_alert_count == 0);

    assert(parse(&fixture, active) == NH_PRINTER_PROTOCOL_UPDATED);
    assert(fixture.snapshot.alerts[0].dismissed_locally);
    assert(fixture.snapshot.alerts[0].occurrence_count == 1);

    assert(parse(&fixture, "{\"print\":{\"hms\":[]}}") ==
           NH_PRINTER_PROTOCOL_UPDATED);
    assert(!fixture.snapshot.alerts[0].active);
    assert(!fixture.snapshot.alerts[0].dismissed_locally);
    assert(fixture.snapshot.active_alert_count == 0);

    assert(parse(&fixture, active) == NH_PRINTER_PROTOCOL_UPDATED);
    assert(fixture.snapshot.alerts[0].active);
    assert(fixture.snapshot.alerts[0].occurrence_count == 2);
}

static void test_print_error_lifecycle(void)
{
    fixture_t fixture;
    init_fixture(&fixture);
    assert(parse(
               &fixture,
               "{\"print\":{\"print_error\":117473284,\"hms\":[]}}") ==
           NH_PRINTER_PROTOCOL_UPDATED);
    assert(fixture.snapshot.active_alert_count == 1);
    assert(strcmp(
               fixture.snapshot.alerts[0].raw_code,
               "PRINT_ERROR_117473284") == 0);
    assert(fixture.snapshot.alerts[0].source == NH_ALERT_SOURCE_PRINT);
    assert(parse(&fixture, "{\"print\":{\"print_error\":0}}") ==
           NH_PRINTER_PROTOCOL_UPDATED);
    assert(fixture.snapshot.active_alert_count == 0);
    assert(!fixture.snapshot.alerts[0].active);
}

static void test_ams_unit_trays_and_material_risk(void)
{
    fixture_t fixture;
    init_fixture(&fixture);
    const char *report =
        "{\"print\":{\"ams\":{\"ams\":[{"
        "\"id\":\"0\",\"humidity\":\"4\",\"temp\":\"22.7\","
        "\"tray\":["
        "{\"id\":\"0\"},"
        "{\"id\":\"1\",\"tray_type\":\"PLA\","
        "\"tray_color\":\"DFE2E3FF\",\"tray_info_idx\":\"GFA05\","
        "\"tag_uid\":\"AABBCCDDEEFF0011\",\"remain\":75,"
        "\"nozzle_temp_min\":\"190\",\"nozzle_temp_max\":\"240\"}"
        "]}]}}}";
    assert(parse(&fixture, report) == NH_PRINTER_PROTOCOL_UPDATED);
    assert(fixture.snapshot.ams.known);
    assert(fixture.snapshot.ams.unit_count == 1);
    assert(fixture.snapshot.ams.tray_count == 2);
    assert(fixture.snapshot.ams.units[0].humidity_index == 4);
    assert(fixture.snapshot.ams.units[0].material_at_risk);
    assert(fixture.snapshot.ams.units[0].temperature_c > 22.6f);
    assert(!fixture.snapshot.ams.trays[0].present);
    assert(fixture.snapshot.ams.trays[1].present);
    assert(strcmp(fixture.snapshot.ams.trays[1].material, "PLA") == 0);
    assert(strcmp(
               fixture.snapshot.ams.trays[1].color_rgba,
               "DFE2E3FF") == 0);
    assert(fixture.snapshot.ams.trays[1].remaining_percent == 75);
    assert(fixture.snapshot.ams.trays[1].rfid_present);
    assert(fixture.snapshot.active_alert_count == 1);
    assert(strstr(
               fixture.snapshot.alerts[0].raw_code,
               "MATERIAL_AMS_0_HUMIDITY_4") != NULL);
}

static void test_ams_delta_preservation_and_explicit_clear(void)
{
    fixture_t fixture;
    init_fixture(&fixture);
    assert(parse(
               &fixture,
               "{\"print\":{\"ams\":{\"ams\":[{"
               "\"id\":\"0\",\"humidity\":\"3\",\"tray\":["
               "{\"id\":\"0\",\"tray_type\":\"PETG\"}]}]}}}") ==
           NH_PRINTER_PROTOCOL_UPDATED);
    assert(parse(&fixture, "{\"print\":{\"mc_percent\":40}}") ==
           NH_PRINTER_PROTOCOL_UPDATED);
    assert(fixture.snapshot.ams.unit_count == 1);
    assert(fixture.snapshot.ams.tray_count == 1);
    assert(strcmp(fixture.snapshot.ams.trays[0].material, "PETG") == 0);

    assert(parse(&fixture, "{\"print\":{\"ams\":{\"ams\":[]}}}") ==
           NH_PRINTER_PROTOCOL_UPDATED);
    assert(fixture.snapshot.ams.known);
    assert(fixture.snapshot.ams.unit_count == 0);
    assert(fixture.snapshot.ams.tray_count == 0);
}

static void test_multiple_ams_external_spool_and_bounds(void)
{
    fixture_t fixture;
    init_fixture(&fixture);
    const char *report =
        "{\"print\":{\"ams\":{\"ams\":["
        "{\"id\":\"0\",\"humidity\":\"1\",\"tray\":[]},"
        "{\"id\":\"1\",\"humidity\":\"2\",\"tray\":[]},"
        "{\"id\":\"2\",\"humidity\":\"3\",\"tray\":[]},"
        "{\"id\":\"3\",\"humidity\":\"4\",\"tray\":[]},"
        "{\"id\":\"4\",\"humidity\":\"5\",\"tray\":[]}"
        "]},\"vt_tray\":{\"id\":\"254\",\"tray_type\":\"TPU\","
        "\"tray_color\":\"112233FF\",\"remain\":55}}}";
    assert(parse(&fixture, report) == NH_PRINTER_PROTOCOL_UPDATED);
    assert(fixture.snapshot.ams.unit_count == NH_AMS_MAX_UNITS);
    assert(fixture.snapshot.ams.external_spool_present);
    const nh_ams_tray_t *external =
        &fixture.snapshot.ams.trays[NH_AMS_MAX_TRAYS];
    assert(external->external);
    assert(external->present);
    assert(strcmp(external->material, "TPU") == 0);
    assert(external->remaining_percent == 55);

    assert(parse(
               &fixture,
               "{\"print\":{\"vt_tray\":{\"id\":\"254\","
               "\"tray_type\":\"PLA\",\"tray_color\":\"NOTHEX!!\","
               "\"remain\":101}}}") == NH_PRINTER_PROTOCOL_UPDATED);
    external = &fixture.snapshot.ams.trays[NH_AMS_MAX_TRAYS];
    assert(external->color_rgba[0] == '\0');
    assert(!external->remaining_known);
}

int main(void)
{
    test_full_running_report();
    test_delta_preserves_total_layers();
    test_idle_clears_job_state();
    test_new_job_does_not_reuse_old_total();
    test_malformed_and_unrelated_payloads();
    test_numeric_bounds();
    test_first_active_delta_uses_neutral_name();
    test_state_mapping();
    test_string_layers_and_sd_number();
    test_delta_without_state_preserves_active_job();
    test_invalid_layer_values_do_not_replace_known_values();
    test_known_hms_alert_is_mapped_and_deduplicated();
    test_unknown_hms_is_preserved_and_delta_does_not_clear();
    test_hms_clear_recurrence_and_local_dismissal();
    test_print_error_lifecycle();
    test_ams_unit_trays_and_material_risk();
    test_ams_delta_preservation_and_explicit_clear();
    test_multiple_ams_external_spool_and_bounds();
    puts("nh_printer_protocol host tests: PASS (18 cases)");
    return 0;
}
