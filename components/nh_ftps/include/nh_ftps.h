#pragma once

#include <stddef.h>
#include <stdint.h>

#include "esp_err.h"

#ifdef __cplusplus
extern "C" {
#endif

enum {
    NH_FTPS_REMOTE_NAME_LENGTH = 96,
};

typedef void (*nh_ftps_progress_cb_t)(uint64_t sent_bytes,
                                      uint64_t total_bytes,
                                      void *ctx);

typedef struct {
    const char *ip_address;
    const char *server_common_name;
    const char *access_code;
    const char *local_path;
    const char *remote_name;
    const uint8_t *expected_sha256;
    uint64_t resume_offset;
    nh_ftps_progress_cb_t progress_cb;
    void *progress_ctx;
} nh_ftps_upload_config_t;

/**
 * Performs an authenticated implicit-FTPS upload to a temporary remote name,
 * resumes only at a server-confirmed byte boundary, and renames after the full
 * payload is accepted. The server certificate is checked against Bambu's CA
 * and the configured printer identity.
 *
 * This transport does not start a print. Product code must keep its capability
 * disabled until the exact printer/firmware combination is hardware-qualified.
 */
esp_err_t nh_ftps_upload(const nh_ftps_upload_config_t *config,
                         uint64_t *uploaded_bytes);

#ifdef __cplusplus
}
#endif
