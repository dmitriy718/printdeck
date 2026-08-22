#include "nh_3mf.h"

#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "miniz.h"

enum {
    ZIP_EOCD_SIGNATURE = 0x06054B50u,
    ZIP_CENTRAL_SIGNATURE = 0x02014B50u,
    ZIP_LOCAL_SIGNATURE = 0x04034B50u,
    ZIP_EOCD_MIN = 22,
    ZIP_EOCD_SEARCH_MAX = 65557,
    ZIP_ENTRY_MAX = 512,
    ZIP_METADATA_MAX = 64 * 1024,
    ZIP_COMPRESSED_MAX = 512 * 1024,
    ZIP_COMPRESSION_RATIO_MAX = 128,
};

typedef struct {
    char name[NH_3MF_MEMBER_NAME_LENGTH];
    uint32_t crc32;
    uint32_t compressed_size;
    uint32_t uncompressed_size;
    uint32_t local_offset;
    uint16_t method;
    uint16_t flags;
} zip_member_t;

typedef struct {
    FILE *file;
    uint64_t file_size;
    uint32_t central_offset;
    uint16_t member_count;
} zip_reader_t;

static uint16_t le16(const uint8_t *data)
{
    return (uint16_t)data[0] | ((uint16_t)data[1] << 8);
}

static uint32_t le32(const uint8_t *data)
{
    return (uint32_t)data[0] |
           ((uint32_t)data[1] << 8) |
           ((uint32_t)data[2] << 16) |
           ((uint32_t)data[3] << 24);
}

static uint32_t be32(const uint8_t *data)
{
    return ((uint32_t)data[0] << 24) |
           ((uint32_t)data[1] << 16) |
           ((uint32_t)data[2] << 8) |
           (uint32_t)data[3];
}

static uint32_t crc32_bytes(const uint8_t *data, size_t length)
{
    uint32_t crc = UINT32_MAX;
    for (size_t i = 0; i < length; ++i) {
        crc ^= data[i];
        for (unsigned bit = 0; bit < 8; ++bit) {
            uint32_t mask = (uint32_t)-(int32_t)(crc & 1u);
            crc = (crc >> 1) ^ (0xEDB88320u & mask);
        }
    }
    return ~crc;
}

bool nh_3mf_safe_member_name(const char *name)
{
    if (!name || !name[0] || name[0] == '/' || name[0] == '\\' ||
        strchr(name, '\\')) {
        return false;
    }
    const char *part = name;
    while (*part) {
        const char *slash = strchr(part, '/');
        size_t length = slash ? (size_t)(slash - part) : strlen(part);
        if (length == 0 ||
            (length == 1 && part[0] == '.') ||
            (length == 2 && part[0] == '.' && part[1] == '.')) {
            return false;
        }
        if (!slash) {
            break;
        }
        part = slash + 1;
    }
    return true;
}

bool nh_3mf_png_dimensions(const uint8_t *data, size_t size,
                           uint16_t *width, uint16_t *height)
{
    static const uint8_t signature[8] = {
        0x89, 'P', 'N', 'G', '\r', '\n', 0x1A, '\n',
    };
    if (!data || size < 24 || !width || !height ||
        memcmp(data, signature, sizeof(signature)) != 0 ||
        memcmp(data + 12, "IHDR", 4) != 0) {
        return false;
    }
    uint32_t parsed_width = be32(data + 16);
    uint32_t parsed_height = be32(data + 20);
    if (parsed_width == 0 || parsed_height == 0 ||
        parsed_width > 8192 || parsed_height > 8192) {
        return false;
    }
    *width = (uint16_t)parsed_width;
    *height = (uint16_t)parsed_height;
    return true;
}

static bool read_at(FILE *file, uint64_t offset, void *buffer, size_t size)
{
    return offset <= LONG_MAX &&
           fseek(file, (long)offset, SEEK_SET) == 0 &&
           fread(buffer, 1, size, file) == size;
}

static bool zip_open(const char *path, zip_reader_t *reader)
{
    memset(reader, 0, sizeof(*reader));
    reader->file = fopen(path, "rb");
    if (!reader->file ||
        fseek(reader->file, 0, SEEK_END) != 0) {
        if (reader->file) {
            fclose(reader->file);
        }
        return false;
    }
    long end = ftell(reader->file);
    if (end < ZIP_EOCD_MIN) {
        fclose(reader->file);
        reader->file = NULL;
        return false;
    }
    reader->file_size = (uint64_t)end;
    size_t search_size =
        reader->file_size > ZIP_EOCD_SEARCH_MAX
            ? ZIP_EOCD_SEARCH_MAX
            : (size_t)reader->file_size;
    uint8_t *tail = malloc(search_size);
    if (!tail ||
        !read_at(reader->file, reader->file_size - search_size,
                 tail, search_size)) {
        free(tail);
        fclose(reader->file);
        reader->file = NULL;
        return false;
    }
    bool found = false;
    for (size_t i = search_size - ZIP_EOCD_MIN + 1; i > 0; --i) {
        size_t offset = i - 1;
        if (le32(tail + offset) != ZIP_EOCD_SIGNATURE) {
            continue;
        }
        const uint8_t *eocd = tail + offset;
        uint16_t comment_length = le16(eocd + 20);
        if (offset + ZIP_EOCD_MIN + comment_length != search_size ||
            le16(eocd + 4) != 0 || le16(eocd + 6) != 0 ||
            le16(eocd + 8) != le16(eocd + 10) ||
            le16(eocd + 10) > ZIP_ENTRY_MAX) {
            continue;
        }
        reader->member_count = le16(eocd + 10);
        uint32_t central_size = le32(eocd + 12);
        reader->central_offset = le32(eocd + 16);
        found =
            (uint64_t)reader->central_offset + central_size <=
            reader->file_size - ZIP_EOCD_MIN;
        break;
    }
    free(tail);
    if (!found) {
        fclose(reader->file);
        reader->file = NULL;
    }
    return found;
}

static void zip_close(zip_reader_t *reader)
{
    if (reader && reader->file) {
        fclose(reader->file);
        reader->file = NULL;
    }
}

static bool zip_member_at(zip_reader_t *reader, uint16_t wanted,
                          zip_member_t *member)
{
    uint64_t offset = reader->central_offset;
    for (uint16_t i = 0; i < reader->member_count; ++i) {
        uint8_t fixed[46];
        if (!read_at(reader->file, offset, fixed, sizeof(fixed)) ||
            le32(fixed) != ZIP_CENTRAL_SIGNATURE) {
            return false;
        }
        uint16_t name_length = le16(fixed + 28);
        uint16_t extra_length = le16(fixed + 30);
        uint16_t comment_length = le16(fixed + 32);
        uint64_t next = offset + sizeof(fixed) + name_length +
                        extra_length + comment_length;
        if (name_length == 0 ||
            name_length >= NH_3MF_MEMBER_NAME_LENGTH ||
            next > reader->file_size) {
            return false;
        }
        if (i == wanted) {
            memset(member, 0, sizeof(*member));
            if (!read_at(reader->file, offset + sizeof(fixed),
                         member->name, name_length)) {
                return false;
            }
            member->name[name_length] = '\0';
            member->flags = le16(fixed + 8);
            member->method = le16(fixed + 10);
            member->crc32 = le32(fixed + 16);
            member->compressed_size = le32(fixed + 20);
            member->uncompressed_size = le32(fixed + 24);
            member->local_offset = le32(fixed + 42);
            return nh_3mf_safe_member_name(member->name) &&
                   member->compressed_size != UINT32_MAX &&
                   member->uncompressed_size != UINT32_MAX;
        }
        offset = next;
    }
    return false;
}

static bool zip_find(zip_reader_t *reader, const char *name,
                     zip_member_t *member)
{
    for (uint16_t i = 0; i < reader->member_count; ++i) {
        if (!zip_member_at(reader, i, member)) {
            return false;
        }
        if (strcmp(member->name, name) == 0) {
            return true;
        }
    }
    return false;
}

static bool zip_extract(zip_reader_t *reader, const zip_member_t *member,
                        uint8_t *output, size_t output_capacity)
{
    if (!member || !output ||
        member->uncompressed_size > output_capacity ||
        member->compressed_size > ZIP_COMPRESSED_MAX ||
        (member->compressed_size == 0 && member->uncompressed_size != 0) ||
        (member->compressed_size != 0 &&
         (uint64_t)member->uncompressed_size >
             (uint64_t)member->compressed_size *
                 ZIP_COMPRESSION_RATIO_MAX) ||
        (member->flags & 1u) != 0 ||
        (member->method != 0 && member->method != 8)) {
        return false;
    }
    uint8_t local[30];
    if (!read_at(reader->file, member->local_offset, local, sizeof(local)) ||
        le32(local) != ZIP_LOCAL_SIGNATURE) {
        return false;
    }
    uint16_t name_length = le16(local + 26);
    uint16_t extra_length = le16(local + 28);
    uint64_t data_offset =
        (uint64_t)member->local_offset + sizeof(local) +
        name_length + extra_length;
    if (data_offset + member->compressed_size > reader->file_size) {
        return false;
    }

    uint8_t *compressed = malloc(member->compressed_size ?
                                 member->compressed_size : 1);
    if (!compressed ||
        !read_at(reader->file, data_offset, compressed,
                 member->compressed_size)) {
        free(compressed);
        return false;
    }
    bool ok = false;
    if (member->method == 0) {
        if (member->compressed_size == member->uncompressed_size) {
            memcpy(output, compressed, member->uncompressed_size);
            ok = true;
        }
    } else {
        size_t actual = tinfl_decompress_mem_to_mem(
            output, member->uncompressed_size,
            compressed, member->compressed_size, 0);
        ok = actual == member->uncompressed_size;
    }
    free(compressed);
    return ok &&
           crc32_bytes(output, member->uncompressed_size) == member->crc32;
}

static bool extract_text(zip_reader_t *reader, const char *member_name,
                         char **text, size_t *length)
{
    zip_member_t member;
    if (!zip_find(reader, member_name, &member) ||
        member.uncompressed_size == 0 ||
        member.uncompressed_size > ZIP_METADATA_MAX) {
        return false;
    }
    char *buffer = calloc(1, member.uncompressed_size + 1);
    if (!buffer ||
        !zip_extract(reader, &member, (uint8_t *)buffer,
                     member.uncompressed_size)) {
        free(buffer);
        return false;
    }
    *text = buffer;
    *length = member.uncompressed_size;
    return true;
}

static void copy_printable(char *destination, size_t capacity,
                           const char *source, size_t length)
{
    if (!capacity) {
        return;
    }
    size_t written = 0;
    for (size_t i = 0; i < length && written + 1 < capacity; ++i) {
        unsigned char c = (unsigned char)source[i];
        if (c >= 0x20 && c != 0x7F && c != '<' && c != '>') {
            destination[written++] = (char)c;
        }
    }
    destination[written] = '\0';
}

static void parse_xml_title(const char *text, char *title, size_t capacity)
{
    const char *markers[] = {
        "<metadata name=\"Title\">",
        "<metadata name=\"title\">",
    };
    for (size_t i = 0; i < sizeof(markers) / sizeof(markers[0]); ++i) {
        const char *start = strstr(text, markers[i]);
        if (!start) {
            continue;
        }
        start += strlen(markers[i]);
        const char *end = strstr(start, "</metadata>");
        if (end) {
            copy_printable(title, capacity, start, (size_t)(end - start));
            return;
        }
    }
}

static bool json_value(const char *json, const char *key,
                       char *value, size_t capacity)
{
    char marker[64];
    if (snprintf(marker, sizeof(marker), "\"%s\"", key) >=
        (int)sizeof(marker)) {
        return false;
    }
    const char *cursor = strstr(json, marker);
    if (!cursor) {
        return false;
    }
    cursor += strlen(marker);
    while (*cursor == ' ' || *cursor == '\t' || *cursor == ':') {
        cursor++;
    }
    if (*cursor == '[') {
        cursor++;
        while (*cursor == ' ' || *cursor == '\t') {
            cursor++;
        }
    }
    if (*cursor == '"') {
        const char *end = strchr(++cursor, '"');
        if (!end) {
            return false;
        }
        copy_printable(value, capacity, cursor, (size_t)(end - cursor));
        return value[0] != '\0';
    }
    const char *end = cursor;
    while ((*end >= '0' && *end <= '9') || *end == '.' || *end == '-') {
        end++;
    }
    copy_printable(value, capacity, cursor, (size_t)(end - cursor));
    return value[0] != '\0';
}

void nh_3mf_parse_project_settings(const char *json,
                                   nh_3mf_metadata_t *metadata)
{
    const char *model_keys[] = {
        "printer_model", "printer_model_id", "printer_structure",
    };
    for (size_t i = 0;
         i < sizeof(model_keys) / sizeof(model_keys[0]); ++i) {
        if (json_value(json, model_keys[i], metadata->target_model,
                       sizeof(metadata->target_model))) {
            break;
        }
    }
    char number[24] = {0};
    if (json_value(json, "nozzle_diameter", number, sizeof(number))) {
        metadata->nozzle_diameter_mm = strtof(number, NULL);
        if (metadata->nozzle_diameter_mm < 0.1f ||
            metadata->nozzle_diameter_mm > 2.0f) {
            metadata->nozzle_diameter_mm = 0.0f;
        }
    }
    memset(number, 0, sizeof(number));
    if (json_value(json, "layer_height", number, sizeof(number))) {
        metadata->layer_height_mm = strtof(number, NULL);
        if (metadata->layer_height_mm < 0.01f ||
            metadata->layer_height_mm > 2.0f) {
            metadata->layer_height_mm = 0.0f;
        }
    }
}

static bool choose_thumbnail(zip_reader_t *reader, zip_member_t *selected)
{
    const char *preferred[] = {
        "Metadata/plate_1.png",
        "Metadata/thumbnail.png",
        "Metadata/top_1.png",
    };
    for (size_t i = 0; i < sizeof(preferred) / sizeof(preferred[0]); ++i) {
        if (zip_find(reader, preferred[i], selected) &&
            selected->uncompressed_size >= 24 &&
            selected->uncompressed_size <= 256 * 1024) {
            return true;
        }
    }
    return false;
}

int nh_3mf_inspect(const char *path, nh_3mf_metadata_t *metadata)
{
    if (!path || !metadata) {
        return -1;
    }
    memset(metadata, 0, sizeof(*metadata));
    zip_reader_t reader;
    if (!zip_open(path, &reader)) {
        return -1;
    }

    char *text = NULL;
    size_t length = 0;
    if (extract_text(&reader, "3D/3dmodel.model", &text, &length)) {
        parse_xml_title(text, metadata->title, sizeof(metadata->title));
        metadata->metadata_known = true;
        free(text);
    }
    text = NULL;
    if (extract_text(&reader, "Metadata/project_settings.config",
                     &text, &length)) {
        nh_3mf_parse_project_settings(text, metadata);
        metadata->metadata_known = true;
        free(text);
    }

    zip_member_t thumbnail;
    if (choose_thumbnail(&reader, &thumbnail)) {
        uint8_t header[32];
        if (thumbnail.uncompressed_size <= sizeof(header)) {
            if (zip_extract(&reader, &thumbnail, header, sizeof(header)) &&
                nh_3mf_png_dimensions(
                    header, thumbnail.uncompressed_size,
                    &metadata->thumbnail_width,
                    &metadata->thumbnail_height)) {
                metadata->thumbnail_available = true;
            }
        } else {
            uint8_t *png = malloc(thumbnail.uncompressed_size);
            if (png &&
                zip_extract(&reader, &thumbnail, png,
                            thumbnail.uncompressed_size) &&
                nh_3mf_png_dimensions(
                    png, thumbnail.uncompressed_size,
                    &metadata->thumbnail_width,
                    &metadata->thumbnail_height)) {
                metadata->thumbnail_available = true;
            }
            free(png);
        }
        if (metadata->thumbnail_available) {
            strlcpy(metadata->thumbnail_member, thumbnail.name,
                    sizeof(metadata->thumbnail_member));
            metadata->thumbnail_size = thumbnail.uncompressed_size;
        }
    }
    zip_close(&reader);
    return 0;
}

int nh_3mf_extract_thumbnail(const char *path,
                             const char *member_name,
                             uint8_t *buffer,
                             size_t capacity,
                             size_t *required_size)
{
    if (!path || !member_name || !required_size ||
        !nh_3mf_safe_member_name(member_name)) {
        return -1;
    }
    zip_reader_t reader;
    if (!zip_open(path, &reader)) {
        return -1;
    }
    zip_member_t member;
    bool found = zip_find(&reader, member_name, &member) &&
                 member.uncompressed_size <= 256 * 1024;
    if (!found) {
        zip_close(&reader);
        return -1;
    }
    *required_size = member.uncompressed_size;
    if (!buffer) {
        zip_close(&reader);
        return 0;
    }
    bool extracted = capacity >= member.uncompressed_size &&
                     zip_extract(&reader, &member, buffer, capacity);
    zip_close(&reader);
    return extracted ? 0 : -1;
}
