/* Linux x86-64 / pinned Lean ABI. No authored C implementation.
 * rdi=pid, rsi=remote address, rdx=borrowed ByteArray.
 * No world argument or allocation: verified generated Lean 4.34 ABI.
 * Lean scalar-array layout: size at +8, data at +24.
 */
.text
.globl wruh_write_memory_once
.type wruh_write_memory_once,@function
wruh_write_memory_once:
    subq $32, %rsp
    movq %rsi, 16(%rsp)
    leaq 24(%rdx), %rax
    movq %rax, 0(%rsp)
    movq 8(%rdx), %rax
    movq %rax, 8(%rsp)
    movq %rax, 24(%rsp)
    movq %rsp, %rsi
    movl $1, %edx
    leaq 16(%rsp), %r10
    movl $1, %r8d
    xorl %r9d, %r9d
    movl $311, %eax
    syscall
    addq $32, %rsp
    ret
.size wruh_write_memory_once, .-wruh_write_memory_once
.section .note.GNU-stack,"",@progbits
