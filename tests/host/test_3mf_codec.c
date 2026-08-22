#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "nh_3mf.h"

static void test_safe_member_names(void)
{
    assert(nh_3mf_safe_member_name("3D/3dmodel.model"));
    assert(nh_3mf_safe_member_name("Metadata/plate_1.png"));
    assert(!nh_3mf_safe_member_name("../secret"));
    assert(!nh_3mf_safe_member_name("Metadata/../secret"));
    assert(!nh_3mf_safe_member_name("/absolute"));
    assert(!nh_3mf_safe_member_name("Metadata\\preview.png"));
    assert(!nh_3mf_safe_member_name("Metadata//preview.png"));
}

static void test_png_dimensions(void)
{
    uint8_t png[24] = {
        0x89, 'P', 'N', 'G', '\r', '\n', 0x1a, '\n',
        0, 0, 0, 13, 'I', 'H', 'D', 'R',
        0, 0, 2, 0, 0, 0, 1, 0,
    };
    uint16_t width = 0;
    uint16_t height = 0;
    assert(nh_3mf_png_dimensions(
        png, sizeof(png), &width, &height));
    assert(width == 512);
    assert(height == 256);
    png[18] = 0;
    assert(!nh_3mf_png_dimensions(
        png, sizeof(png), &width, &height));
}

static void test_project_settings_scalar_and_array_values(void)
{
    nh_3mf_metadata_t metadata = {0};
    nh_3mf_parse_project_settings(
        "{\"printer_model_id\":[\"BL-P001\"],"
        "\"nozzle_diameter\":[\"0.4\"],"
        "\"layer_height\":\"0.20\"}",
        &metadata);
    assert(strcmp(metadata.target_model, "BL-P001") == 0);
    assert(fabsf(metadata.nozzle_diameter_mm - 0.4f) < 0.001f);
    assert(fabsf(metadata.layer_height_mm - 0.2f) < 0.001f);

    memset(&metadata, 0, sizeof(metadata));
    nh_3mf_parse_project_settings(
        "{\"printer_model\":\"X1C\","
        "\"nozzle_diameter\":\"99\","
        "\"layer_height\":\"-4\"}",
        &metadata);
    assert(strcmp(metadata.target_model, "X1C") == 0);
    assert(metadata.nozzle_diameter_mm == 0.0f);
    assert(metadata.layer_height_mm == 0.0f);
}

int main(void)
{
    test_safe_member_names();
    test_png_dimensions();
    test_project_settings_scalar_and_array_values();
    puts("3MF codec tests passed (3 groups)");
    return 0;
}
