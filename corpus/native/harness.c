/* Prepared only: no native execution authorized by this goal. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
extern uint32_t alias(uint32_t *, uint32_t *, uint32_t);
extern uint32_t overlap(unsigned char *, uint32_t);
extern unsigned long division(unsigned long, unsigned long);
int main(int argc, char **argv) {
    if (argc != 6) return 64;
    /* Domain: unsigned decimal numbers <= UINT32_MAX; case 0..2,
       offsets 0..7. Fixed aligned storage, no user pointers. */
    uint32_t v[5];
    for (int i = 0; i < 5; ++i) {
        for (const char *p = argv[i + 1]; *p; ++p) if (*p < '0' || *p > '9') return 65;
        char *end; unsigned long n = strtoul(argv[i + 1], &end, 10);
        if (!*argv[i + 1] || *end || argv[i + 1][0] == '-' || n > UINT32_MAX) return 65;
        v[i] = (uint32_t)n;
    }
    if (v[0] > 2 || v[1] > 7 || v[2] > 7) return 65;
    uint32_t storage[8];
    for (unsigned i = 0; i < 8; ++i) storage[i] = v[4] ^ i;
    unsigned long result;
    if (v[0] == 0) result = alias(&storage[v[1]], &storage[v[2]], v[3]);
    else if (v[0] == 1) result = overlap((unsigned char *)storage + v[1], v[3]);
    else result = division(v[3], v[4]);
    printf("%lu", result);
    for (unsigned i = 0; i < sizeof storage; ++i) printf(" %02x", ((unsigned char *)storage)[i]);
    puts("");
    return 0;
}
