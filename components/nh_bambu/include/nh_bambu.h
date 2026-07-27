#pragma once

#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * Bambu Lab's public printer CA. Local printer leaf certificates are validated
 * against this trust anchor and separately pinned to the configured serial.
 */
extern const char nh_bambu_ca_pem[];
extern const size_t nh_bambu_ca_pem_size;

#ifdef __cplusplus
}
#endif
