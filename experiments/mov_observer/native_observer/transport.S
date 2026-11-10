/* Pinned Lean scalar ABI, Linux AMD64. Borrowed output buffers are fresh,
 * privately allocated by Lean for each synchronous syscall. No authored C. */
.text
.globl observer_ptrace
.type observer_ptrace,@function
observer_ptrace:
 mov %rcx,%r10
 mov $101,%eax
 syscall
 ret
.globl observer_ptrace_buffer
.type observer_ptrace_buffer,@function
observer_ptrace_buffer:
 lea 24(%rcx),%r10
 mov $101,%eax
 syscall
 ret
.globl observer_wait
.type observer_wait,@function
observer_wait:
 lea 24(%rsi),%rsi
 xor %edx,%edx
 xor %r10d,%r10d
 mov $61,%eax
 syscall
 ret
.globl observer_kill
.type observer_kill,@function
observer_kill:
 mov $62,%eax
 syscall
 ret
.globl observer_read_memory
.type observer_read_memory,@function
observer_read_memory:
 sub $32,%rsp
 mov %rsi,16(%rsp)
 lea 24(%rdx),%rax
 mov %rax,(%rsp)
 mov 8(%rdx),%rax
 mov %rax,8(%rsp)
 mov %rax,24(%rsp)
 mov %rsp,%rsi
 mov $1,%edx
 lea 16(%rsp),%r10
 mov $1,%r8d
 xor %r9d,%r9d
 mov $310,%eax
 syscall
 add $32,%rsp
 ret
.section .note.GNU-stack,"",@progbits
.text
/* Fresh, zeroed ByteArray for kernel outputs. Runtime owns allocation/free;
 * initialize only pinned header fields, preserving allocator m_cs_sz. */
.globl observer_fresh_buffer
.type observer_fresh_buffer,@function
observer_fresh_buffer:
 push %rbx
 mov %rdi,%rbx
 add $24,%rdi
 jc .Ltoo_large
 call lean_alloc_object@PLT
 movl $1,(%rax)
 movb $1,6(%rax)
 movb $248,7(%rax)
 mov %rbx,8(%rax)
 mov %rbx,16(%rax)
 mov %rax,%rdx
 lea 24(%rax),%rdi
 mov %rbx,%rcx
 xor %eax,%eax
 rep stosb
 mov %rdx,%rax
 pop %rbx
 ret
.Ltoo_large:
 ud2
