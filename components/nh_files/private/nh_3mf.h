#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

enum {
    NH_3MF_MEMBER_NAME_LENGTH = 128,
    NH_3MF_TEXT_LENGTH = 32,
};

typedef struct {
    char title[96];
    char target_model[NH_3MF_TEXT_LENGTH];
    char thumbnail_member[NH_3MF_MEMBER_NAME_LENGTH];
    uint32_t thumbnail_size;
    uint16_t thumbnail_width;
    uint16_t thumbnail_height;
    float nozzle_diameter_mm;
    float layer_height_mm;
    bool metadata_known;
    bool thumbnail_available;
} nh_3mf_metadata_t;

bool nh_3mf_safe_member_name(const char *name);
bool nh_3mf_png_dimensions(const uint8_t *data, size_t size,
                           uint16_t *width, uint16_t *height);
void nh_3mf_parse_project_settings(const char *json,
                                   nh_3mf_metadata_t *metadata);
int nh_3mf_inspect(const char *path, nh_3mf_metadata_t *metadata);
int nh_3mf_extract_thumbnail(const char *path,
                             const char *member,
                             uint8_t *buffer,
                             size_t capacity,
                             size_t *required_size);
