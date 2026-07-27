#include "compat.h"

#include <string.h>

size_t strlcpy(char *destination, const char *source, size_t size)
{
    size_t source_length = strlen(source);
    if (size > 0) {
        size_t copied = source_length < size - 1 ? source_length : size - 1;
        memcpy(destination, source, copied);
        destination[copied] = '\0';
    }
    return source_length;
}
