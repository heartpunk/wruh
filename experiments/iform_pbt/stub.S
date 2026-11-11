/* One exact catalogue instruction, rooted as an ELF function for Wruh. */
.section .text
.globl wruh_pbt_target
.type wruh_pbt_target, @function
wruh_pbt_target:
.globl wruh_pbt_instruction
wruh_pbt_instruction:
.include "instruction-bytes.inc"
.include "continuation-bytes.inc"
.size wruh_pbt_target, .-wruh_pbt_target
.section .note.GNU-stack,"",@progbits
