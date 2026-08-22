#include "nh_ftps.h"

#include <ctype.h>
#include <errno.h>
#include <inttypes.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#include "esp_tls.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "nh_bambu.h"
#include "nh_core.h"
#include "lwip/ip4_addr.h"
#include "psa/crypto.h"

enum {
    NH_FTPS_PORT = 990,
    NH_FTPS_LINE_MAX = 512,
    NH_FTPS_IO_BUFFER = 16 * 1024,
};

typedef struct {
    esp_tls_t *tls;
    char line[NH_FTPS_LINE_MAX];
} ftps_control_t;

static bool valid_text(const char *value, size_t maximum, size_t minimum)
{
    size_t length = value ? strnlen(value, maximum) : 0;
    if (length < minimum || length >= maximum) {
        return false;
    }
    for (size_t i = 0; i < length; ++i) {
        unsigned char c = (unsigned char)value[i];
        if (c < 0x20 || c == 0x7F) {
            return false;
        }
    }
    return true;
}

static bool valid_remote_name(const char *name)
{
    if (!valid_text(name, NH_FTPS_REMOTE_NAME_LENGTH, 5) ||
        name[0] == '.' || strchr(name, '/') || strchr(name, '\\') ||
        strstr(name, "..")) {
        return false;
    }
    for (const unsigned char *p = (const unsigned char *)name; *p; ++p) {
        if (!(isalnum(*p) || *p == '.' || *p == '-' || *p == '_' ||
              *p == ' ')) {
            return false;
        }
    }
    return true;
}

static bool valid_private_ipv4(const char *text)
{
    ip4_addr_t address;
    if (!ip4addr_aton(text, &address)) {
        return false;
    }
    uint8_t first = ip4_addr1(&address);
    uint8_t second = ip4_addr2(&address);
    return first == 10 ||
           (first == 172 && second >= 16 && second <= 31) ||
           (first == 192 && second == 168);
}

static bool hash_matches(const char *path, const uint8_t expected[32])
{
    FILE *file = fopen(path, "rb");
    if (!file) {
        return false;
    }
    psa_hash_operation_t operation = PSA_HASH_OPERATION_INIT;
    psa_status_t status = psa_crypto_init();
    if (status == PSA_SUCCESS) {
        status = psa_hash_setup(&operation, PSA_ALG_SHA_256);
    }
    uint8_t buffer[4096];
    while (status == PSA_SUCCESS && !feof(file)) {
        size_t count = fread(buffer, 1, sizeof(buffer), file);
        if (count > 0) {
            status = psa_hash_update(&operation, buffer, count);
        }
        if (ferror(file)) {
            status = PSA_ERROR_STORAGE_FAILURE;
        }
    }
    uint8_t actual[32];
    size_t actual_length = 0;
    if (status == PSA_SUCCESS) {
        status = psa_hash_finish(
            &operation, actual, sizeof(actual), &actual_length);
    } else {
        (void)psa_hash_abort(&operation);
    }
    bool closed = fclose(file) == 0;
    bool matches = status == PSA_SUCCESS &&
                   actual_length == sizeof(actual) && closed &&
                   memcmp(actual, expected, sizeof(actual)) == 0;
    nh_secure_zero(actual, sizeof(actual));
    nh_secure_zero(buffer, sizeof(buffer));
    return matches;
}

static esp_tls_t *open_tls(const nh_ftps_upload_config_t *config,
                           uint16_t port)
{
    esp_tls_t *tls = esp_tls_init();
    if (!tls) {
        return NULL;
    }
    const esp_tls_cfg_t tls_config = {
        .cacert_buf = (const unsigned char *)nh_bambu_ca_pem,
        .cacert_bytes = nh_bambu_ca_pem_size,
        .timeout_ms = 10000,
        .common_name = config->server_common_name,
    };
    int connected = esp_tls_conn_new_sync(
        config->ip_address, strlen(config->ip_address),
        port, &tls_config, tls);
    if (connected != 1) {
        esp_tls_conn_destroy(tls);
        return NULL;
    }
    return tls;
}

static bool tls_write_all(esp_tls_t *tls, const void *data, size_t length)
{
    const uint8_t *bytes = data;
    size_t sent = 0;
    while (sent < length) {
        ssize_t result =
            esp_tls_conn_write(tls, bytes + sent, length - sent);
        if (result > 0) {
            sent += (size_t)result;
        } else if (result == ESP_TLS_ERR_SSL_WANT_READ ||
                   result == ESP_TLS_ERR_SSL_WANT_WRITE) {
            vTaskDelay(1);
        } else {
            return false;
        }
    }
    return true;
}

static bool read_line(ftps_control_t *control)
{
    size_t length = 0;
    while (length + 1 < sizeof(control->line)) {
        uint8_t value;
        ssize_t result = esp_tls_conn_read(control->tls, &value, 1);
        if (result == 1) {
            if (value == '\n') {
                control->line[length] = '\0';
                return true;
            }
            if (value != '\r') {
                control->line[length++] = (char)value;
            }
        } else if (result == ESP_TLS_ERR_SSL_WANT_READ ||
                   result == ESP_TLS_ERR_SSL_WANT_WRITE) {
            vTaskDelay(1);
        } else {
            return false;
        }
    }
    return false;
}

static int read_reply(ftps_control_t *control)
{
    if (!read_line(control) ||
        !isdigit((unsigned char)control->line[0]) ||
        !isdigit((unsigned char)control->line[1]) ||
        !isdigit((unsigned char)control->line[2])) {
        return -1;
    }
    char code_text[4] = {
        control->line[0], control->line[1], control->line[2], '\0',
    };
    int code = atoi(code_text);
    if (control->line[3] != '-') {
        return code;
    }
    while (read_line(control)) {
        if (strncmp(control->line, code_text, 3) == 0 &&
            control->line[3] == ' ') {
            return code;
        }
    }
    return -1;
}

static int command(ftps_control_t *control, const char *format,
                   const char *argument)
{
    char request[NH_FTPS_LINE_MAX];
    int length = argument
                     ? snprintf(request, sizeof(request), format, argument)
                     : snprintf(request, sizeof(request), "%s", format);
    if (length <= 0 || length >= (int)sizeof(request) ||
        !tls_write_all(control->tls, request, (size_t)length)) {
        return -1;
    }
    return read_reply(control);
}

static bool expected(int actual, int first, int second)
{
    return actual == first || actual == second;
}

static bool parse_epsv_port(const char *line, uint16_t *port)
{
    const char *open = strchr(line, '(');
    const char *close = open ? strchr(open, ')') : NULL;
    if (!open || !close || close - open < 6) {
        return false;
    }
    char delimiter = open[1];
    const char *cursor = open + 2;
    for (int field = 0; field < 2; ++field) {
        cursor = strchr(cursor, delimiter);
        if (!cursor || cursor >= close) {
            return false;
        }
        cursor++;
    }
    const char *end = strchr(cursor, delimiter);
    if (!end || end >= close || end == cursor || end - cursor > 5) {
        return false;
    }
    char number[6] = {0};
    memcpy(number, cursor, (size_t)(end - cursor));
    long parsed = strtol(number, NULL, 10);
    if (parsed <= 0 || parsed > UINT16_MAX) {
        return false;
    }
    *port = (uint16_t)parsed;
    return true;
}

static esp_err_t login(ftps_control_t *control,
                       const nh_ftps_upload_config_t *config)
{
    if (read_reply(control) != 220 ||
        command(control, "USER bblp\r\n", NULL) != 331) {
        return ESP_ERR_INVALID_RESPONSE;
    }
    char pass[NH_FTPS_LINE_MAX];
    int length =
        snprintf(pass, sizeof(pass), "PASS %s\r\n", config->access_code);
    if (length <= 0 || length >= (int)sizeof(pass) ||
        !tls_write_all(control->tls, pass, (size_t)length)) {
        nh_secure_zero(pass, sizeof(pass));
        return ESP_FAIL;
    }
    nh_secure_zero(pass, sizeof(pass));
    if (read_reply(control) != 230 ||
        command(control, "PBSZ 0\r\n", NULL) != 200 ||
        command(control, "PROT P\r\n", NULL) != 200 ||
        command(control, "TYPE I\r\n", NULL) != 200) {
        return ESP_ERR_INVALID_RESPONSE;
    }
    return ESP_OK;
}

static esp_err_t server_size(ftps_control_t *control,
                             const char *remote,
                             uint64_t *size)
{
    int code = command(control, "SIZE %s\r\n", remote);
    if (code == 550) {
        *size = 0;
        return ESP_OK;
    }
    if (code != 213) {
        return ESP_ERR_INVALID_RESPONSE;
    }
    const char *cursor = control->line + 3;
    while (*cursor == ' ') {
        cursor++;
    }
    char *end = NULL;
    unsigned long long parsed = strtoull(cursor, &end, 10);
    if (end == cursor || (*end && *end != ' ')) {
        return ESP_ERR_INVALID_RESPONSE;
    }
    *size = (uint64_t)parsed;
    return ESP_OK;
}

static esp_err_t upload_payload(ftps_control_t *control,
                                const nh_ftps_upload_config_t *config,
                                const char *temporary_name,
                                uint64_t local_size,
                                uint64_t offset,
                                uint64_t *uploaded)
{
    if (offset > 0) {
        char request[64];
        int length = snprintf(
            request, sizeof(request), "REST %" PRIu64 "\r\n", offset);
        if (length <= 0 || length >= (int)sizeof(request) ||
            !tls_write_all(control->tls, request, (size_t)length) ||
            read_reply(control) != 350) {
            return ESP_ERR_INVALID_RESPONSE;
        }
    }
    int epsv = command(control, "EPSV\r\n", NULL);
    uint16_t data_port = 0;
    if (epsv != 229 ||
        !parse_epsv_port(control->line, &data_port)) {
        return ESP_ERR_INVALID_RESPONSE;
    }
    esp_tls_t *data_tls = open_tls(config, data_port);
    if (!data_tls) {
        return ESP_ERR_TIMEOUT;
    }
    int stor = command(control, "STOR %s\r\n", temporary_name);
    if (!expected(stor, 125, 150)) {
        esp_tls_conn_destroy(data_tls);
        return ESP_ERR_INVALID_RESPONSE;
    }

    FILE *file = fopen(config->local_path, "rb");
    if (!file || offset > LONG_MAX ||
        fseek(file, (long)offset, SEEK_SET) != 0) {
        if (file) {
            fclose(file);
        }
        esp_tls_conn_destroy(data_tls);
        return ESP_ERR_NOT_FOUND;
    }
    uint8_t *buffer = malloc(NH_FTPS_IO_BUFFER);
    if (!buffer) {
        fclose(file);
        esp_tls_conn_destroy(data_tls);
        return ESP_ERR_NO_MEM;
    }
    uint64_t sent = offset;
    bool ok = true;
    while (sent < local_size) {
        size_t wanted =
            local_size - sent > NH_FTPS_IO_BUFFER
                ? NH_FTPS_IO_BUFFER
                : (size_t)(local_size - sent);
        size_t count = fread(buffer, 1, wanted, file);
        if (count != wanted ||
            !tls_write_all(data_tls, buffer, count)) {
            ok = false;
            break;
        }
        sent += count;
        *uploaded = sent;
        if (config->progress_cb) {
            config->progress_cb(
                sent, local_size, config->progress_ctx);
        }
    }
    nh_secure_zero(buffer, NH_FTPS_IO_BUFFER);
    free(buffer);
    ok = fclose(file) == 0 && ok;
    esp_tls_conn_destroy(data_tls);
    if (!ok || read_reply(control) != 226) {
        return ESP_FAIL;
    }
    return ESP_OK;
}

esp_err_t nh_ftps_upload(const nh_ftps_upload_config_t *config,
                         uint64_t *uploaded_bytes)
{
    if (!config || !uploaded_bytes ||
        !valid_text(config->ip_address, 16, 7) ||
        !valid_private_ipv4(config->ip_address) ||
        !valid_text(config->server_common_name, 32, 10) ||
        !valid_text(config->access_code, 17, 8) ||
        !valid_text(config->local_path, 192, 1) ||
        !valid_remote_name(config->remote_name) ||
        !config->expected_sha256) {
        return ESP_ERR_INVALID_ARG;
    }
    struct stat info;
    if (stat(config->local_path, &info) != 0 ||
        !S_ISREG(info.st_mode) || info.st_size <= 0) {
        return ESP_ERR_NOT_FOUND;
    }
    uint64_t local_size = (uint64_t)info.st_size;
    if (!hash_matches(config->local_path, config->expected_sha256)) {
        return ESP_ERR_INVALID_CRC;
    }
    char temporary[NH_FTPS_REMOTE_NAME_LENGTH + 8];
    if (snprintf(temporary, sizeof(temporary), "%s.part",
                 config->remote_name) >= (int)sizeof(temporary)) {
        return ESP_ERR_INVALID_SIZE;
    }

    ftps_control_t control = {
        .tls = open_tls(config, NH_FTPS_PORT),
    };
    if (!control.tls) {
        return ESP_ERR_TIMEOUT;
    }
    esp_err_t err = login(&control, config);
    uint64_t remote_size = 0;
    if (err == ESP_OK) {
        err = server_size(&control, temporary, &remote_size);
    }
    if (err == ESP_OK &&
        (remote_size > local_size ||
         config->resume_offset > local_size ||
         (config->resume_offset != 0 &&
          config->resume_offset != remote_size))) {
        err = ESP_ERR_INVALID_SIZE;
    }
    uint64_t offset =
        config->resume_offset ? config->resume_offset : remote_size;
    *uploaded_bytes = offset;
    if (err == ESP_OK && offset < local_size) {
        err = upload_payload(
            &control, config, temporary, local_size,
            offset, uploaded_bytes);
    }
    if (err == ESP_OK &&
        command(&control, "RNFR %s\r\n", temporary) != 350) {
        err = ESP_ERR_INVALID_RESPONSE;
    }
    if (err == ESP_OK &&
        command(&control, "RNTO %s\r\n", config->remote_name) != 250) {
        err = ESP_ERR_INVALID_RESPONSE;
    }
    (void)command(&control, "QUIT\r\n", NULL);
    esp_tls_conn_destroy(control.tls);
    return err;
}
