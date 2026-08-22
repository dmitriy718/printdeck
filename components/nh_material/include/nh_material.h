#pragma once

#include <stdbool.h>
#include <stdint.h>

#include "esp_err.h"
#include "nh_core.h"

#ifdef __cplusplus
extern "C" {
#endif

enum {
    NH_MATERIAL_CATALOG_MAX = 16,
    NH_MATERIAL_ID_LENGTH = 33,
    NH_MATERIAL_LABEL_LENGTH = 32,
};

typedef struct {
    char id[NH_MATERIAL_ID_LENGTH];
    char label[NH_MATERIAL_LABEL_LENGTH];
    char material[NH_AMS_MATERIAL_LENGTH];
    char color_rgba[NH_AMS_COLOR_LENGTH];
    uint32_t nominal_weight_grams;
    uint64_t cost_micros_per_kg;
    uint64_t dry_state_epoch;
    bool ams_compatible;
} nh_material_entry_t;

typedef struct {
    nh_material_entry_t entries[NH_MATERIAL_CATALOG_MAX];
    uint8_t count;
} nh_material_catalog_t;

esp_err_t nh_material_init(void);
esp_err_t nh_material_snapshot(nh_material_catalog_t *catalog);
esp_err_t nh_material_upsert(const nh_material_entry_t *entry);
esp_err_t nh_material_remove(const char *id);

#ifdef __cplusplus
}
#endif

