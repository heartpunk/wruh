#include <xed/xed-interface.h>
#include <stdio.h>
#include <string.h>

/* One hex instruction per line; one classification per line. */
int main(void) {
    char line[64];
    xed_tables_init();
    while (fgets(line, sizeof(line), stdin)) {
        size_t len = strcspn(line, "\r\n");
        unsigned char bytes[15];
        if (!len || len % 2 || len > 30) return 1;
        for (size_t i = 0; i < len; i += 2) {
            unsigned v;
            if (sscanf(line + i, "%2x", &v) != 1) return 1;
            bytes[i / 2] = (unsigned char)v;
        }
        xed_decoded_inst_t d;
        xed_decoded_inst_zero(&d);
        xed_decoded_inst_set_mode(&d, XED_MACHINE_MODE_LONG_64, XED_ADDRESS_WIDTH_64b);
        xed_error_enum_t error = xed_decode(&d, bytes, (unsigned)len / 2);
        if (error != XED_ERROR_NONE || xed_decoded_inst_get_length(&d) != len / 2) {
            fprintf(stderr, "XED cannot decode entire instruction: %.*s\n", (int)len, line);
            return 2;
        }
        printf("%s\t%u\n", xed_iform_enum_t2str(xed_decoded_inst_get_iform_enum(&d)),
               xed_decoded_inst_get_operand_width(&d));
    }
    return ferror(stdin) || ferror(stdout);
}
