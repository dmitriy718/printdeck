#pragma once

#include <stddef.h>

size_t tinfl_decompress_mem_to_mem(void *output,
                                   size_t output_length,
                                   const void *source,
                                   size_t source_length,
                                   int flags);
