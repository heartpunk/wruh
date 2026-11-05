/* One-instruction AMD64 capture. Run only inside the bubblewrap launcher. */
#define _GNU_SOURCE
#include <errno.h>
#include <inttypes.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/ptrace.h>
#include <sys/types.h>
#include <sys/uio.h>
#include <sys/user.h>
#include <sys/wait.h>
#include <unistd.h>
#include <elf.h>
#include <cpuid.h>

#define CODE_ADDR ((void *)0x400000UL)
#define DATA_ADDR ((void *)0x100000UL)
#define STACK_ADDR ((void *)0x200000UL)
#define PAGE 4096
#define INPUT_LIMIT 32768
#define XSTATE_LIMIT 16384

static const char *field(const char *input, const char *name) {
    char key[80];
    if (snprintf(key, sizeof key, "\"%s\":", name) >= (int)sizeof key) return NULL;
    const char *p = strstr(input, key);
    if (!p || strstr(p + strlen(key), key)) return NULL;
    return p + strlen(key);
}

static int number(const char *input, const char *name, unsigned long long *value) {
    const char *p = field(input, name);
    char *end;
    if (!p || *p < '0' || *p > '9') return 0;
    errno = 0;
    *value = strtoull(p, &end, 10);
    return !errno && end != p && (*end == ',' || *end == '}');
}

static int nibble(char c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    return -1;
}

static int hexfield(const char *input, const char *name, unsigned char *out,
                    size_t max, size_t *length) {
    const char *p = field(input, name);
    if (!p || *p++ != '"') return 0;
    size_t n = 0;
    while (*p && *p != '"') {
        if (!p[1] || n == max) return 0;
        int a = nibble(p[0]), b = nibble(p[1]);
        if (a < 0 || b < 0) return 0;
        out[n++] = (unsigned char)((a << 4) | b);
        p += 2;
    }
    if (*p != '"' || (p[1] != ',' && p[1] != '}')) return 0;
    *length = n;
    return 1;
}

static void print_hex(const unsigned char *p, size_t n) {
    for (size_t i = 0; i < n; ++i) printf("%02x", p[i]);
}

static void print_regs(const struct user_regs_struct *r) {
#define OUTREG(name) printf("\"" #name "\":%llu,", (unsigned long long)r->name)
    OUTREG(rax); OUTREG(rbx); OUTREG(rcx); OUTREG(rdx); OUTREG(rsi); OUTREG(rdi);
    OUTREG(rbp); OUTREG(rsp); OUTREG(r8); OUTREG(r9); OUTREG(r10); OUTREG(r11);
    OUTREG(r12); OUTREG(r13); OUTREG(r14); OUTREG(r15); OUTREG(rip); OUTREG(eflags);
    OUTREG(cs); OUTREG(ss); OUTREG(ds); OUTREG(es); OUTREG(fs); OUTREG(gs);
    OUTREG(fs_base);
    printf("\"gs_base\":%llu", (unsigned long long)r->gs_base);
#undef OUTREG
}

static int capture_xstate(pid_t child, unsigned char *buffer, size_t *length, int *format) {
    struct iovec iov = {buffer, XSTATE_LIMIT};
    if (ptrace(PTRACE_GETREGSET, child, (void *)(uintptr_t)NT_X86_XSTATE, &iov) != -1) {
        *length = iov.iov_len;
        *format = 1; /* standard Linux NT_X86_XSTATE */
        return 1;
    }
    if (errno != ENODEV) return 0;
    unsigned int eax, ebx, ecx, edx;
    if (!__get_cpuid(1, &eax, &ebx, &ecx, &edx) || (ecx & bit_XSAVE)) {
        errno = ENOTSUP;
        return 0;
    }
    struct user_fpregs_struct fp = {0};
    if (ptrace(PTRACE_GETFPREGS, child, 0, &fp) == -1) return 0;
    memcpy(buffer, &fp, sizeof fp);
    *length = sizeof fp;
    *format = 2; /* legacy FXSAVE on a CPU without XSAVE */
    return 1;
}

int main(void) {
    /* Refuse ordinary direct invocation. The launcher also requires the full
       bubblewrap namespace setup and bounded cgroup before starting us. */
    const char *sandbox = getenv("WRUH_NATIVE_SANDBOX");
    if (!sandbox || strcmp(sandbox, "1") || getpid() != 2) {
        fputs("runner requires the bubblewrap PID namespace\n", stderr);
        return 5;
    }
    char input[INPUT_LIMIT];
    unsigned char insn[15], memory[2 * PAGE], xmm[256], before_xstate[XSTATE_LIMIT], after_xstate[XSTATE_LIMIT];
    size_t insn_len, memory_len, xmm_len;
    if (!fgets(input, sizeof input, stdin) || !strchr(input, '\n') ||
        !hexfield(input, "bytes", insn, sizeof insn, &insn_len) || !insn_len ||
        !hexfield(input, "memory", memory, sizeof memory, &memory_len) || memory_len != sizeof memory ||
        !hexfield(input, "xmm", xmm, sizeof xmm, &xmm_len) || xmm_len != sizeof xmm) {
        fputs("invalid request\n", stderr); return 2;
    }
    unsigned long long extra1_base, extra2_base;
    if (!number(input, "extra1_base", &extra1_base) || !number(input, "extra2_base", &extra2_base)) {
        fputs("missing extra-page addresses\n", stderr); return 2;
    }
    unsigned long long extra_bases[2] = {extra1_base, extra2_base};
    for (int i = 0; i < 2; ++i) {
        unsigned long long base = extra_bases[i];
        if (base && (base < 0x10000 || base > 0x00007ffffffff000ULL || (base & (PAGE - 1)) ||
                     base == (unsigned long long)(uintptr_t)CODE_ADDR || base == (unsigned long long)(uintptr_t)DATA_ADDR ||
                     base == (unsigned long long)(uintptr_t)STACK_ADDR || (i && base == extra_bases[0]))) {
            fputs("invalid extra-page address\n", stderr); return 2;
        }
    }
    struct user_regs_struct desired = {0};
#define INREG(name) do { unsigned long long value; if (!number(input, #name, &value)) { fputs("missing " #name "\n", stderr); return 2; } desired.name = value; } while (0)
    INREG(rax); INREG(rbx); INREG(rcx); INREG(rdx); INREG(rsi); INREG(rdi);
    INREG(rbp); INREG(rsp); INREG(r8); INREG(r9); INREG(r10); INREG(r11);
    INREG(r12); INREG(r13); INREG(r14); INREG(r15); INREG(eflags); INREG(fs_base); INREG(gs_base);
#undef INREG
    /* Only arithmetic flags and direction are controllable by this runner. */
    if (desired.eflags & ~0xcd5ULL) { fputs("unsupported flags\n", stderr); return 2; }
    desired.eflags |= 0x202;
    void *code = mmap(CODE_ADDR, PAGE, PROT_READ | PROT_WRITE,
                      MAP_PRIVATE | MAP_ANONYMOUS | MAP_FIXED_NOREPLACE, -1, 0);
    void *data = mmap(DATA_ADDR, PAGE, PROT_READ | PROT_WRITE,
                      MAP_SHARED | MAP_ANONYMOUS | MAP_FIXED_NOREPLACE, -1, 0);
    void *stack = mmap(STACK_ADDR, PAGE, PROT_READ | PROT_WRITE,
                       MAP_SHARED | MAP_ANONYMOUS | MAP_FIXED_NOREPLACE, -1, 0);
    if (code != CODE_ADDR || data != DATA_ADDR || stack != STACK_ADDR) { perror("mmap"); return 3; }
    void *extra[2] = {NULL, NULL};
    for (int i = 0; i < 2; ++i) {
        if (!extra_bases[i]) continue;
        extra[i] = mmap((void *)(uintptr_t)extra_bases[i], PAGE, PROT_READ | PROT_WRITE,
                        MAP_SHARED | MAP_ANONYMOUS | MAP_FIXED_NOREPLACE, -1, 0);
        if (extra[i] != (void *)(uintptr_t)extra_bases[i]) { perror("extra mmap"); return 3; }
    }
    memcpy(code, insn, insn_len);
    memcpy(data, memory, PAGE);
    memcpy(stack, memory + PAGE, PAGE);
    if (mprotect(code, PAGE, PROT_READ | PROT_EXEC)) { perror("mprotect"); return 3; }
    pid_t child = fork();
    if (child < 0) { perror("fork"); return 3; }
    if (!child) {
        if (ptrace(PTRACE_TRACEME, 0, NULL, NULL) == -1) _exit(120);
        raise(SIGSTOP);
        _exit(121);
    }
    int status;
    if (waitpid(child, &status, 0) != child || !WIFSTOPPED(status) || WSTOPSIG(status) != SIGSTOP) {
        fputs("tracee did not stop\n", stderr); return 4;
    }
    struct user_regs_struct current;
    if (ptrace(PTRACE_GETREGS, child, 0, &current) == -1) { perror("GETREGS"); return 4; }
    /* Preserve segment selectors; FS/GS bases are explicit inputs. */
    desired.cs = current.cs; desired.ss = current.ss; desired.ds = current.ds; desired.es = current.es;
    desired.fs = current.fs; desired.gs = current.gs;
    desired.rip = (unsigned long)CODE_ADDR;
    desired.orig_rax = (unsigned long long)-1;
    if (ptrace(PTRACE_SETREGS, child, 0, &desired) == -1 ||
        ptrace(PTRACE_GETREGS, child, 0, &current) == -1) { perror("SETREGS"); return 4; }
    struct user_regs_struct before = current;
    struct user_fpregs_struct initial_fp = {0};
    if (ptrace(PTRACE_GETFPREGS, child, 0, &initial_fp) == -1) { perror("GETFPREGS"); return 4; }
    memcpy(initial_fp.xmm_space, xmm, sizeof xmm);
    if (ptrace(PTRACE_SETFPREGS, child, 0, &initial_fp) == -1) { perror("SETFPREGS"); return 4; }
    size_t pre_len, post_len;
    int pre_format, post_format;
    if (!capture_xstate(child, before_xstate, &pre_len, &pre_format)) { perror("xstate before"); return 4; }
    if (pre_len < 416 || memcmp(before_xstate + 160, xmm, sizeof xmm)) { fputs("XMM pre-state mismatch\n", stderr); return 4; }
    if (ptrace(PTRACE_SINGLESTEP, child, 0, 0) == -1 || waitpid(child, &status, 0) != child || !WIFSTOPPED(status)) {
        fputs("single-step failed or tracee exited\n", stderr); return 4;
    }
    int signal_number = WSTOPSIG(status);
    siginfo_t signal_info;
    if (ptrace(PTRACE_GETSIGINFO, child, 0, &signal_info) == -1) { perror("GETSIGINFO"); return 4; }
    if (ptrace(PTRACE_GETREGS, child, 0, &current) == -1) { perror("GETREGS after"); return 4; }
    if (!capture_xstate(child, after_xstate, &post_len, &post_format) || pre_format != post_format) { perror("xstate after"); return 4; }
    if (ptrace(PTRACE_KILL, child, 0, 0) == -1 || waitpid(child, &status, 0) != child) { perror("tracee cleanup"); return 4; }
    printf("{\"signal\":%d,\"signal_code\":%d,\"xstate_format\":%d,\"before\":{", signal_number, signal_info.si_code, pre_format); print_regs(&before);
    printf("},\"after\":{"); print_regs(&current);
    printf("},\"before_xstate\":\""); print_hex(before_xstate, pre_len);
    printf("\",\"after_xstate\":\""); print_hex(after_xstate, post_len);
    printf("\",\"data\":\""); print_hex(data, PAGE);
    printf("\",\"stack\":\""); print_hex(stack, PAGE);
    printf("\",\"code\":\""); print_hex(code, PAGE);
    printf("\",\"extra1_base\":%llu,\"extra1\":\"", extra1_base);
    if (extra[0]) print_hex(extra[0], PAGE);
    printf("\",\"extra2_base\":%llu,\"extra2\":\"", extra2_base);
    if (extra[1]) print_hex(extra[1], PAGE);
    puts("\"}");
    return 0;
}
