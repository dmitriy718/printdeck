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
    puts("nh_printer_protocol host tests: PASS (11 cases)");
    return 0;
}
