.intel_syntax noprefix
.section .text.paddq-xmm,"ax"
paddq xmm0, xmm1
.section .text.vpxor-ymm,"ax"
vpxor ymm0, ymm1, ymm2
.section .text.vpaddq-zmm,"ax"
vpaddq zmm0, zmm1, zmm2
.section .text.vpaddq-merge-high,"ax"
vpaddq zmm16{k1}, zmm17, zmm18
.section .text.vpaddq-zero-high,"ax"
vpaddq zmm16{k1}{z}, zmm17, zmm18
.section .text.vmovdqu64-store,"ax"
vmovdqu64 [rdi], zmm31
.section .text.kxorq,"ax"
kxorq k3, k1, k2
