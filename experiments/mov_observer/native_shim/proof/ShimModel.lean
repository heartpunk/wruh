-- Exact shim SHA256 318c587381ddd44658b17e8c40b4b80a857989da16581ec7aa546a4e157f982a
import Extracted
set_option maxRecDepth 32768
set_option maxHeartbeats 4000000
namespace MovObserver.Shim
open Ayxg.QfAbv
def e0 : Expr Γ (.bv 64) := .bvLit 64 311
def e1 : Expr Γ (.bv 64) := .bvLit 64 1
def e2 : Expr Γ (.bv 64) := .bvLit 64 18446744073709551584
def e3 : Expr Γ (.bv 64) := .var v_rsp
def e4 : Expr Γ (.bv 64) := (.bvBin .add 64 e2 e3)
def e5 : Expr Γ (.bv 64) := .bvLit 64 0
def e6 : Expr Γ (.bv 64) := .bvLit 64 18446744073709551600
def e7 : Expr Γ (.bv 64) := (.bvBin .add 64 e6 e3)
def e8 : Expr Γ (.bv 1) := .bvLit 1 0
def e9 : Expr Γ (.bv 1) := .bvLit 1 1
def e10 : Expr Γ (.bv 64) := .bvLit 64 4194362
def e11 : Expr Γ (.array 64 8) := .var v_mem
def e12 : Expr Γ (.bv 64) := .var v_rsi
def e13 : Expr Γ (.bv 8) := .extract {hi := 7, lo := 0, hi_lt_width := by decide, lo_le_hi := by decide} e12
def e14 : Expr Γ (.array 64 8) := .store 64 8 e11 e7 e13
def e15 : Expr Γ (.bv 64) := .bvLit 64 18446744073709551601
def e16 : Expr Γ (.bv 64) := (.bvBin .add 64 e15 e3)
def e17 : Expr Γ (.bv 8) := .extract {hi := 15, lo := 8, hi_lt_width := by decide, lo_le_hi := by decide} e12
def e18 : Expr Γ (.array 64 8) := .store 64 8 e14 e16 e17
def e19 : Expr Γ (.bv 64) := .bvLit 64 18446744073709551602
def e20 : Expr Γ (.bv 64) := (.bvBin .add 64 e19 e3)
def e21 : Expr Γ (.bv 8) := .extract {hi := 23, lo := 16, hi_lt_width := by decide, lo_le_hi := by decide} e12
def e22 : Expr Γ (.array 64 8) := .store 64 8 e18 e20 e21
def e23 : Expr Γ (.bv 64) := .bvLit 64 18446744073709551603
def e24 : Expr Γ (.bv 64) := (.bvBin .add 64 e23 e3)
def e25 : Expr Γ (.bv 8) := .extract {hi := 31, lo := 24, hi_lt_width := by decide, lo_le_hi := by decide} e12
def e26 : Expr Γ (.array 64 8) := .store 64 8 e22 e24 e25
def e27 : Expr Γ (.bv 64) := .bvLit 64 18446744073709551604
def e28 : Expr Γ (.bv 64) := (.bvBin .add 64 e27 e3)
def e29 : Expr Γ (.bv 8) := .extract {hi := 39, lo := 32, hi_lt_width := by decide, lo_le_hi := by decide} e12
def e30 : Expr Γ (.array 64 8) := .store 64 8 e26 e28 e29
def e31 : Expr Γ (.bv 64) := .bvLit 64 18446744073709551605
def e32 : Expr Γ (.bv 64) := (.bvBin .add 64 e31 e3)
def e33 : Expr Γ (.bv 8) := .extract {hi := 47, lo := 40, hi_lt_width := by decide, lo_le_hi := by decide} e12
def e34 : Expr Γ (.array 64 8) := .store 64 8 e30 e32 e33
def e35 : Expr Γ (.bv 64) := .bvLit 64 18446744073709551606
def e36 : Expr Γ (.bv 64) := (.bvBin .add 64 e35 e3)
def e37 : Expr Γ (.bv 8) := .extract {hi := 55, lo := 48, hi_lt_width := by decide, lo_le_hi := by decide} e12
def e38 : Expr Γ (.array 64 8) := .store 64 8 e34 e36 e37
def e39 : Expr Γ (.bv 64) := .bvLit 64 18446744073709551607
def e40 : Expr Γ (.bv 64) := (.bvBin .add 64 e39 e3)
def e41 : Expr Γ (.bv 8) := .extract {hi := 63, lo := 56, hi_lt_width := by decide, lo_le_hi := by decide} e12
def e42 : Expr Γ (.array 64 8) := .store 64 8 e38 e40 e41
def e43 : Expr Γ (.bv 8) := .bvLit 8 24
def e44 : Expr Γ (.bv 64) := .var v_rdx
def e45 : Expr Γ (.bv 8) := .extract {hi := 7, lo := 0, hi_lt_width := by decide, lo_le_hi := by decide} e44
def e46 : Expr Γ (.bv 8) := (.bvBin .add 8 e43 e45)
def e47 : Expr Γ (.array 64 8) := .store 64 8 e42 e4 e46
def e48 : Expr Γ (.bv 64) := .bvLit 64 18446744073709551585
def e49 : Expr Γ (.bv 64) := (.bvBin .add 64 e48 e3)
def e50 : Expr Γ (.bv 64) := .bvLit 64 24
def e51 : Expr Γ (.bv 64) := (.bvBin .add 64 e50 e44)
def e52 : Expr Γ (.bv 8) := .extract {hi := 15, lo := 8, hi_lt_width := by decide, lo_le_hi := by decide} e51
def e53 : Expr Γ (.array 64 8) := .store 64 8 e47 e49 e52
def e54 : Expr Γ (.bv 64) := .bvLit 64 18446744073709551586
def e55 : Expr Γ (.bv 64) := (.bvBin .add 64 e54 e3)
def e56 : Expr Γ (.bv 8) := .extract {hi := 23, lo := 16, hi_lt_width := by decide, lo_le_hi := by decide} e51
def e57 : Expr Γ (.array 64 8) := .store 64 8 e53 e55 e56
def e58 : Expr Γ (.bv 64) := .bvLit 64 18446744073709551587
def e59 : Expr Γ (.bv 64) := (.bvBin .add 64 e58 e3)
def e60 : Expr Γ (.bv 8) := .extract {hi := 31, lo := 24, hi_lt_width := by decide, lo_le_hi := by decide} e51
def e61 : Expr Γ (.array 64 8) := .store 64 8 e57 e59 e60
def e62 : Expr Γ (.bv 64) := .bvLit 64 18446744073709551588
def e63 : Expr Γ (.bv 64) := (.bvBin .add 64 e62 e3)
def e64 : Expr Γ (.bv 8) := .extract {hi := 39, lo := 32, hi_lt_width := by decide, lo_le_hi := by decide} e51
def e65 : Expr Γ (.array 64 8) := .store 64 8 e61 e63 e64
def e66 : Expr Γ (.bv 64) := .bvLit 64 18446744073709551589
def e67 : Expr Γ (.bv 64) := (.bvBin .add 64 e66 e3)
def e68 : Expr Γ (.bv 8) := .extract {hi := 47, lo := 40, hi_lt_width := by decide, lo_le_hi := by decide} e51
def e69 : Expr Γ (.array 64 8) := .store 64 8 e65 e67 e68
def e70 : Expr Γ (.bv 64) := .bvLit 64 18446744073709551590
def e71 : Expr Γ (.bv 64) := (.bvBin .add 64 e70 e3)
def e72 : Expr Γ (.bv 8) := .extract {hi := 55, lo := 48, hi_lt_width := by decide, lo_le_hi := by decide} e51
def e73 : Expr Γ (.array 64 8) := .store 64 8 e69 e71 e72
def e74 : Expr Γ (.bv 64) := .bvLit 64 18446744073709551591
def e75 : Expr Γ (.bv 64) := (.bvBin .add 64 e74 e3)
def e76 : Expr Γ (.bv 8) := .extract {hi := 63, lo := 56, hi_lt_width := by decide, lo_le_hi := by decide} e51
def e77 : Expr Γ (.array 64 8) := .store 64 8 e73 e75 e76
def e78 : Expr Γ (.bv 64) := .bvLit 64 18446744073709551592
def e79 : Expr Γ (.bv 64) := (.bvBin .add 64 e78 e3)
def e80 : Expr Γ (.bv 64) := .bvLit 64 8
def e81 : Expr Γ (.bv 64) := (.bvBin .add 64 e80 e44)
def e82 : Expr Γ (.bv 8) := .select 64 8 e77 e81
def e83 : Expr Γ (.array 64 8) := .store 64 8 e77 e79 e82
def e84 : Expr Γ (.bv 64) := .bvLit 64 18446744073709551593
def e85 : Expr Γ (.bv 64) := (.bvBin .add 64 e84 e3)
def e86 : Expr Γ (.bv 64) := .bvLit 64 9
def e87 : Expr Γ (.bv 64) := (.bvBin .add 64 e86 e44)
def e88 : Expr Γ (.bv 8) := .select 64 8 e77 e87
def e89 : Expr Γ (.array 64 8) := .store 64 8 e83 e85 e88
def e90 : Expr Γ (.bv 64) := .bvLit 64 18446744073709551594
def e91 : Expr Γ (.bv 64) := (.bvBin .add 64 e90 e3)
def e92 : Expr Γ (.bv 64) := .bvLit 64 10
def e93 : Expr Γ (.bv 64) := (.bvBin .add 64 e92 e44)
def e94 : Expr Γ (.bv 8) := .select 64 8 e77 e93
def e95 : Expr Γ (.array 64 8) := .store 64 8 e89 e91 e94
def e96 : Expr Γ (.bv 64) := .bvLit 64 18446744073709551595
def e97 : Expr Γ (.bv 64) := (.bvBin .add 64 e96 e3)
def e98 : Expr Γ (.bv 64) := .bvLit 64 11
def e99 : Expr Γ (.bv 64) := (.bvBin .add 64 e98 e44)
def e100 : Expr Γ (.bv 8) := .select 64 8 e77 e99
def e101 : Expr Γ (.array 64 8) := .store 64 8 e95 e97 e100
def e102 : Expr Γ (.bv 64) := .bvLit 64 18446744073709551596
def e103 : Expr Γ (.bv 64) := (.bvBin .add 64 e102 e3)
def e104 : Expr Γ (.bv 64) := .bvLit 64 12
def e105 : Expr Γ (.bv 64) := (.bvBin .add 64 e104 e44)
def e106 : Expr Γ (.bv 8) := .select 64 8 e77 e105
def e107 : Expr Γ (.array 64 8) := .store 64 8 e101 e103 e106
def e108 : Expr Γ (.bv 64) := .bvLit 64 18446744073709551597
def e109 : Expr Γ (.bv 64) := (.bvBin .add 64 e108 e3)
def e110 : Expr Γ (.bv 64) := .bvLit 64 13
def e111 : Expr Γ (.bv 64) := (.bvBin .add 64 e110 e44)
def e112 : Expr Γ (.bv 8) := .select 64 8 e77 e111
def e113 : Expr Γ (.array 64 8) := .store 64 8 e107 e109 e112
def e114 : Expr Γ (.bv 64) := .bvLit 64 18446744073709551598
def e115 : Expr Γ (.bv 64) := (.bvBin .add 64 e114 e3)
def e116 : Expr Γ (.bv 64) := .bvLit 64 14
def e117 : Expr Γ (.bv 64) := (.bvBin .add 64 e116 e44)
def e118 : Expr Γ (.bv 8) := .select 64 8 e77 e117
def e119 : Expr Γ (.array 64 8) := .store 64 8 e113 e115 e118
def e120 : Expr Γ (.bv 64) := .bvLit 64 18446744073709551599
def e121 : Expr Γ (.bv 64) := (.bvBin .add 64 e120 e3)
def e122 : Expr Γ (.bv 64) := .bvLit 64 15
def e123 : Expr Γ (.bv 64) := (.bvBin .add 64 e122 e44)
def e124 : Expr Γ (.bv 8) := .select 64 8 e77 e123
def e125 : Expr Γ (.array 64 8) := .store 64 8 e119 e121 e124
def e126 : Expr Γ (.bv 64) := .bvLit 64 18446744073709551608
def e127 : Expr Γ (.bv 64) := (.bvBin .add 64 e126 e3)
def e128 : Expr Γ (.array 64 8) := .store 64 8 e125 e127 e82
def e129 : Expr Γ (.bv 64) := .bvLit 64 18446744073709551609
def e130 : Expr Γ (.bv 64) := (.bvBin .add 64 e129 e3)
def e131 : Expr Γ (.array 64 8) := .store 64 8 e128 e130 e88
def e132 : Expr Γ (.bv 64) := .bvLit 64 18446744073709551610
def e133 : Expr Γ (.bv 64) := (.bvBin .add 64 e132 e3)
def e134 : Expr Γ (.array 64 8) := .store 64 8 e131 e133 e94
def e135 : Expr Γ (.bv 64) := .bvLit 64 18446744073709551611
def e136 : Expr Γ (.bv 64) := (.bvBin .add 64 e135 e3)
def e137 : Expr Γ (.array 64 8) := .store 64 8 e134 e136 e100
def e138 : Expr Γ (.bv 64) := .bvLit 64 18446744073709551612
def e139 : Expr Γ (.bv 64) := (.bvBin .add 64 e138 e3)
def e140 : Expr Γ (.array 64 8) := .store 64 8 e137 e139 e106
def e141 : Expr Γ (.bv 64) := .bvLit 64 18446744073709551613
def e142 : Expr Γ (.bv 64) := (.bvBin .add 64 e141 e3)
def e143 : Expr Γ (.array 64 8) := .store 64 8 e140 e142 e112
def e144 : Expr Γ (.bv 64) := .bvLit 64 18446744073709551614
def e145 : Expr Γ (.bv 64) := (.bvBin .add 64 e144 e3)
def e146 : Expr Γ (.array 64 8) := .store 64 8 e143 e145 e118
def e147 : Expr Γ (.bv 64) := .bvLit 64 18446744073709551615
def e148 : Expr Γ (.bv 64) := (.bvBin .add 64 e147 e3)
def e149 : Expr Γ (.array 64 8) := .store 64 8 e146 e148 e124
def prefixUpdate : StateUpdate Γ Γ := (.cons e149
 (.cons e10
 (.cons e0
 (.cons (.var v_rcx)
 (.cons e1
 (.cons (.var v_rbx)
 (.cons e4
 (.cons (.var v_rbp)
 (.cons e4
 (.cons (.var v_rdi)
 (.cons e1
 (.cons e5
 (.cons e7
 (.cons (.var v_r11)
 (.cons (.var v_r12)
 (.cons (.var v_r13)
 (.cons (.var v_r14)
 (.cons (.var v_r15)
 (.cons (.var v_d)
 (.cons (.var v_ac)
 (.cons (.var v_id)
 (.cons (.var v_fs)
 (.cons (.var v_sseround)
 (.cons (.var v_zmm0)
 (.cons (.var v_zmm1)
 (.cons (.var v_zmm2)
 (.cons (.var v_zmm3)
 (.cons (.var v_zmm4)
 (.cons (.var v_zmm5)
 (.cons (.var v_zmm6)
 (.cons (.var v_zmm7)
 (.cons (.var v_zmm8)
 (.cons (.var v_zmm9)
 (.cons (.var v_zmm10)
 (.cons (.var v_zmm11)
 (.cons (.var v_zmm12)
 (.cons (.var v_zmm13)
 (.cons (.var v_zmm14)
 (.cons (.var v_zmm15)
 (.cons (.var v_zmm16)
 (.cons (.var v_zmm17)
 (.cons (.var v_zmm18)
 (.cons (.var v_zmm19)
 (.cons (.var v_zmm20)
 (.cons (.var v_zmm21)
 (.cons (.var v_zmm22)
 (.cons (.var v_zmm23)
 (.cons (.var v_zmm24)
 (.cons (.var v_zmm25)
 (.cons (.var v_zmm26)
 (.cons (.var v_zmm27)
 (.cons (.var v_zmm28)
 (.cons (.var v_zmm29)
 (.cons (.var v_zmm30)
 (.cons (.var v_zmm31)
 (.cons (.var v_k0)
 (.cons (.var v_k1)
 (.cons (.var v_k2)
 (.cons (.var v_k3)
 (.cons (.var v_k4)
 (.cons (.var v_k5)
 (.cons (.var v_k6)
 (.cons (.var v_k7)
 (.cons (.var v_ftop)
 (.cons (.var v_fpreg)
 (.cons (.var v_fptag)
 (.cons (.var v_fpround)
 (.cons (.var v_fc3210)
 (.cons (.var v_emnote)
 (.cons (.var v_cmstart)
 (.cons (.var v_cmlen)
 (.cons (.var v_nraddr)
 (.cons (.var v_gs)
 (.cons (.var v_ip_at_syscall)
 (.cons (.var v_cs_seg)
 (.cons (.var v_ds_seg)
 (.cons (.var v_es_seg)
 (.cons (.var v_fs_seg)
 (.cons (.var v_gs_seg)
 (.cons (.var v_ss_seg)
 (.cons (.var v_cr0)
 (.cons (.var v_cr2)
 (.cons (.var v_cr3)
 (.cons (.var v_cr4)
 (.cons (.var v_cr8)
 (.cons e8
 (.cons e9
 (.cons e8
 (.cons e8
 (.cons e9
 (.cons e8
 .nil)))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))
def prefixStep : QFAbvStep Γ Γ := ⟨.eqBv 64 (.var v_rip) (.bvLit 64 4194304), prefixUpdate⟩
variable [FPInterpretation]
theorem prefix_mem (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_mem = Eval.eval s e149 := rfl
theorem prefix_rip (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_rip = Eval.eval s e10 := rfl
theorem prefix_rax (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_rax = Eval.eval s e0 := rfl
theorem prefix_rcx (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_rcx = Eval.eval s (.var v_rcx) := rfl
theorem prefix_rdx (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_rdx = Eval.eval s e1 := rfl
theorem prefix_rbx (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_rbx = Eval.eval s (.var v_rbx) := rfl
theorem prefix_rsp (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_rsp = Eval.eval s e4 := rfl
theorem prefix_rbp (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_rbp = Eval.eval s (.var v_rbp) := rfl
theorem prefix_rsi (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_rsi = Eval.eval s e4 := rfl
theorem prefix_rdi (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_rdi = Eval.eval s (.var v_rdi) := rfl
theorem prefix_r8 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_r8 = Eval.eval s e1 := rfl
theorem prefix_r9 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_r9 = Eval.eval s e5 := rfl
theorem prefix_r10 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_r10 = Eval.eval s e7 := rfl
theorem prefix_r11 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_r11 = Eval.eval s (.var v_r11) := rfl
theorem prefix_r12 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_r12 = Eval.eval s (.var v_r12) := rfl
theorem prefix_r13 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_r13 = Eval.eval s (.var v_r13) := rfl
theorem prefix_r14 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_r14 = Eval.eval s (.var v_r14) := rfl
theorem prefix_r15 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_r15 = Eval.eval s (.var v_r15) := rfl
theorem prefix_d (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_d = Eval.eval s (.var v_d) := rfl
theorem prefix_ac (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_ac = Eval.eval s (.var v_ac) := rfl
theorem prefix_id (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_id = Eval.eval s (.var v_id) := rfl
theorem prefix_fs (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_fs = Eval.eval s (.var v_fs) := rfl
theorem prefix_sseround (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_sseround = Eval.eval s (.var v_sseround) := rfl
theorem prefix_zmm0 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_zmm0 = Eval.eval s (.var v_zmm0) := rfl
theorem prefix_zmm1 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_zmm1 = Eval.eval s (.var v_zmm1) := rfl
theorem prefix_zmm2 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_zmm2 = Eval.eval s (.var v_zmm2) := rfl
theorem prefix_zmm3 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_zmm3 = Eval.eval s (.var v_zmm3) := rfl
theorem prefix_zmm4 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_zmm4 = Eval.eval s (.var v_zmm4) := rfl
theorem prefix_zmm5 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_zmm5 = Eval.eval s (.var v_zmm5) := rfl
theorem prefix_zmm6 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_zmm6 = Eval.eval s (.var v_zmm6) := rfl
theorem prefix_zmm7 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_zmm7 = Eval.eval s (.var v_zmm7) := rfl
theorem prefix_zmm8 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_zmm8 = Eval.eval s (.var v_zmm8) := rfl
theorem prefix_zmm9 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_zmm9 = Eval.eval s (.var v_zmm9) := rfl
theorem prefix_zmm10 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_zmm10 = Eval.eval s (.var v_zmm10) := rfl
theorem prefix_zmm11 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_zmm11 = Eval.eval s (.var v_zmm11) := rfl
theorem prefix_zmm12 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_zmm12 = Eval.eval s (.var v_zmm12) := rfl
theorem prefix_zmm13 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_zmm13 = Eval.eval s (.var v_zmm13) := rfl
theorem prefix_zmm14 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_zmm14 = Eval.eval s (.var v_zmm14) := rfl
theorem prefix_zmm15 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_zmm15 = Eval.eval s (.var v_zmm15) := rfl
theorem prefix_zmm16 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_zmm16 = Eval.eval s (.var v_zmm16) := rfl
theorem prefix_zmm17 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_zmm17 = Eval.eval s (.var v_zmm17) := rfl
theorem prefix_zmm18 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_zmm18 = Eval.eval s (.var v_zmm18) := rfl
theorem prefix_zmm19 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_zmm19 = Eval.eval s (.var v_zmm19) := rfl
theorem prefix_zmm20 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_zmm20 = Eval.eval s (.var v_zmm20) := rfl
theorem prefix_zmm21 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_zmm21 = Eval.eval s (.var v_zmm21) := rfl
theorem prefix_zmm22 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_zmm22 = Eval.eval s (.var v_zmm22) := rfl
theorem prefix_zmm23 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_zmm23 = Eval.eval s (.var v_zmm23) := rfl
theorem prefix_zmm24 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_zmm24 = Eval.eval s (.var v_zmm24) := rfl
theorem prefix_zmm25 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_zmm25 = Eval.eval s (.var v_zmm25) := rfl
theorem prefix_zmm26 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_zmm26 = Eval.eval s (.var v_zmm26) := rfl
theorem prefix_zmm27 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_zmm27 = Eval.eval s (.var v_zmm27) := rfl
theorem prefix_zmm28 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_zmm28 = Eval.eval s (.var v_zmm28) := rfl
theorem prefix_zmm29 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_zmm29 = Eval.eval s (.var v_zmm29) := rfl
theorem prefix_zmm30 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_zmm30 = Eval.eval s (.var v_zmm30) := rfl
theorem prefix_zmm31 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_zmm31 = Eval.eval s (.var v_zmm31) := rfl
theorem prefix_k0 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_k0 = Eval.eval s (.var v_k0) := rfl
theorem prefix_k1 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_k1 = Eval.eval s (.var v_k1) := rfl
theorem prefix_k2 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_k2 = Eval.eval s (.var v_k2) := rfl
theorem prefix_k3 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_k3 = Eval.eval s (.var v_k3) := rfl
theorem prefix_k4 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_k4 = Eval.eval s (.var v_k4) := rfl
theorem prefix_k5 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_k5 = Eval.eval s (.var v_k5) := rfl
theorem prefix_k6 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_k6 = Eval.eval s (.var v_k6) := rfl
theorem prefix_k7 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_k7 = Eval.eval s (.var v_k7) := rfl
theorem prefix_ftop (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_ftop = Eval.eval s (.var v_ftop) := rfl
theorem prefix_fpreg (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_fpreg = Eval.eval s (.var v_fpreg) := rfl
theorem prefix_fptag (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_fptag = Eval.eval s (.var v_fptag) := rfl
theorem prefix_fpround (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_fpround = Eval.eval s (.var v_fpround) := rfl
theorem prefix_fc3210 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_fc3210 = Eval.eval s (.var v_fc3210) := rfl
theorem prefix_emnote (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_emnote = Eval.eval s (.var v_emnote) := rfl
theorem prefix_cmstart (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_cmstart = Eval.eval s (.var v_cmstart) := rfl
theorem prefix_cmlen (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_cmlen = Eval.eval s (.var v_cmlen) := rfl
theorem prefix_nraddr (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_nraddr = Eval.eval s (.var v_nraddr) := rfl
theorem prefix_gs (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_gs = Eval.eval s (.var v_gs) := rfl
theorem prefix_ip_at_syscall (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_ip_at_syscall = Eval.eval s (.var v_ip_at_syscall) := rfl
theorem prefix_cs_seg (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_cs_seg = Eval.eval s (.var v_cs_seg) := rfl
theorem prefix_ds_seg (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_ds_seg = Eval.eval s (.var v_ds_seg) := rfl
theorem prefix_es_seg (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_es_seg = Eval.eval s (.var v_es_seg) := rfl
theorem prefix_fs_seg (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_fs_seg = Eval.eval s (.var v_fs_seg) := rfl
theorem prefix_gs_seg (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_gs_seg = Eval.eval s (.var v_gs_seg) := rfl
theorem prefix_ss_seg (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_ss_seg = Eval.eval s (.var v_ss_seg) := rfl
theorem prefix_cr0 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_cr0 = Eval.eval s (.var v_cr0) := rfl
theorem prefix_cr2 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_cr2 = Eval.eval s (.var v_cr2) := rfl
theorem prefix_cr3 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_cr3 = Eval.eval s (.var v_cr3) := rfl
theorem prefix_cr4 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_cr4 = Eval.eval s (.var v_cr4) := rfl
theorem prefix_cr8 (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_cr8 = Eval.eval s (.var v_cr8) := rfl
theorem prefix_rflags_CF (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_rflags_CF = Eval.eval s e8 := rfl
theorem prefix_rflags_ZF (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_rflags_ZF = Eval.eval s e9 := rfl
theorem prefix_rflags_SF (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_rflags_SF = Eval.eval s e8 := rfl
theorem prefix_rflags_OF (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_rflags_OF = Eval.eval s e8 := rfl
theorem prefix_rflags_PF (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_rflags_PF = Eval.eval s e9 := rfl
theorem prefix_rflags_AF (s : Env Γ) : Env.lookup (prefixUpdate.eval s) v_rflags_AF = Eval.eval s e8 := rfl
def prefixWrites : List (Expr Γ (.bv 64) × Expr Γ (.bv 8)) := [(e7,e13),
(e16,e17),
(e20,e21),
(e24,e25),
(e28,e29),
(e32,e33),
(e36,e37),
(e40,e41),
(e4,e46),
(e49,e52),
(e55,e56),
(e59,e60),
(e63,e64),
(e67,e68),
(e71,e72),
(e75,e76),
(e79,e82),
(e85,e88),
(e91,e94),
(e97,e100),
(e103,e106),
(e109,e112),
(e115,e118),
(e121,e124),
(e127,e82),
(e130,e88),
(e133,e94),
(e136,e100),
(e139,e106),
(e142,e112),
(e145,e118),
(e148,e124)]
def e150 : Expr Γ (.bv 64) := .bvLit 64 40
def e151 : Expr Γ (.bv 64) := (.bvBin .add 64 e150 e3)
def e152 : Expr Γ (.bv 64) := .bvLit 64 32
def e153 : Expr Γ (.bv 64) := (.bvBin .add 64 e152 e3)
def e154 : Expr Γ .bool := .bvUle 64 e3 e153
def e155 : Expr Γ (.bv 1) := .ite e154 e8 e9
def e156 : Expr Γ .bool := .eqBv 64 e3 e2
def e157 : Expr Γ (.bv 1) := .ite e156 e9 e8
def e158 : Expr Γ (.bv 1) := .extract {hi := 63, lo := 63, hi_lt_width := by decide, lo_le_hi := by decide} e153
def e159 : Expr Γ (.bv 1) := .extract {hi := 63, lo := 63, hi_lt_width := by decide, lo_le_hi := by decide} e3
def e160 : Expr Γ (.bv 1) := (.bvBin .xor 1 e159 e158)
def e161 : Expr Γ (.bv 1) := .bvNot 1 e160
def e162 : Expr Γ (.bv 1) := (.bvBin .or 1 e159 e161)
def e163 : Expr Γ (.bv 1) := .bvNot 1 e162
def e164 : Expr Γ (.bv 1) := .extract {hi := 0, lo := 0, hi_lt_width := by decide, lo_le_hi := by decide} e3
def e165 : Expr Γ (.bv 8) := .bvLit 8 32
def e166 : Expr Γ (.bv 8) := .extract {hi := 7, lo := 0, hi_lt_width := by decide, lo_le_hi := by decide} e3
def e167 : Expr Γ (.bv 8) := (.bvBin .add 8 e165 e166)
def e168 : Expr Γ (.bv 1) := .extract {hi := 1, lo := 1, hi_lt_width := by decide, lo_le_hi := by decide} e167
def e169 : Expr Γ (.bv 1) := .extract {hi := 2, lo := 2, hi_lt_width := by decide, lo_le_hi := by decide} e167
def e170 : Expr Γ (.bv 1) := .extract {hi := 3, lo := 3, hi_lt_width := by decide, lo_le_hi := by decide} e167
def e171 : Expr Γ (.bv 1) := .extract {hi := 4, lo := 4, hi_lt_width := by decide, lo_le_hi := by decide} e167
def e172 : Expr Γ (.bv 1) := .extract {hi := 5, lo := 5, hi_lt_width := by decide, lo_le_hi := by decide} e167
def e173 : Expr Γ (.bv 1) := .extract {hi := 6, lo := 6, hi_lt_width := by decide, lo_le_hi := by decide} e167
def e174 : Expr Γ (.bv 1) := .extract {hi := 7, lo := 7, hi_lt_width := by decide, lo_le_hi := by decide} e167
def e175 : Expr Γ (.bv 1) := (.bvBin .xor 1 (.bvBin .xor 1 (.bvBin .xor 1 (.bvBin .xor 1 (.bvBin .xor 1 (.bvBin .xor 1 (.bvBin .xor 1 (.bvBin .xor 1 e9 e164) e168) e169) e170) e171) e172) e173) e174)
def e176 : Expr Γ (.bv 1) := .extract {hi := 4, lo := 4, hi_lt_width := by decide, lo_le_hi := by decide} e3
def e177 : Expr Γ (.bv 1) := .extract {hi := 4, lo := 4, hi_lt_width := by decide, lo_le_hi := by decide} e153
def e178 : Expr Γ (.bv 1) := (.bvBin .xor 1 e176 e177)
def e179 : Expr Γ (.bv 64) := .bvLit 64 39
def e180 : Expr Γ (.bv 64) := (.bvBin .add 64 e179 e3)
def e181 : Expr Γ (.bv 8) := .select 64 8 e11 e180
def e182 : Expr Γ (.bv 64) := .bvLit 64 38
def e183 : Expr Γ (.bv 64) := (.bvBin .add 64 e182 e3)
def e184 : Expr Γ (.bv 8) := .select 64 8 e11 e183
def e185 : Expr Γ (.bv 64) := .bvLit 64 37
def e186 : Expr Γ (.bv 64) := (.bvBin .add 64 e185 e3)
def e187 : Expr Γ (.bv 8) := .select 64 8 e11 e186
def e188 : Expr Γ (.bv 64) := .bvLit 64 36
def e189 : Expr Γ (.bv 64) := (.bvBin .add 64 e188 e3)
def e190 : Expr Γ (.bv 8) := .select 64 8 e11 e189
def e191 : Expr Γ (.bv 64) := .bvLit 64 35
def e192 : Expr Γ (.bv 64) := (.bvBin .add 64 e191 e3)
def e193 : Expr Γ (.bv 8) := .select 64 8 e11 e192
def e194 : Expr Γ (.bv 64) := .bvLit 64 34
def e195 : Expr Γ (.bv 64) := (.bvBin .add 64 e194 e3)
def e196 : Expr Γ (.bv 8) := .select 64 8 e11 e195
def e197 : Expr Γ (.bv 64) := .bvLit 64 33
def e198 : Expr Γ (.bv 64) := (.bvBin .add 64 e197 e3)
def e199 : Expr Γ (.bv 8) := .select 64 8 e11 e198
def e200 : Expr Γ (.bv 8) := .select 64 8 e11 e153
def e201 : Expr Γ (.bv 64) := (.concat 56 8 (.concat 48 8 (.concat 40 8 (.concat 32 8 (.concat 24 8 (.concat 16 8 (.concat 8 8 e181 e184) e187) e190) e193) e196) e199) e200)
def suffixUpdate : StateUpdate Γ Γ := (.cons e11
 (.cons e201
 (.cons (.var v_rax)
 (.cons (.var v_rcx)
 (.cons (.var v_rdx)
 (.cons (.var v_rbx)
 (.cons e151
 (.cons (.var v_rbp)
 (.cons (.var v_rsi)
 (.cons (.var v_rdi)
 (.cons (.var v_r8)
 (.cons (.var v_r9)
 (.cons (.var v_r10)
 (.cons (.var v_r11)
 (.cons (.var v_r12)
 (.cons (.var v_r13)
 (.cons (.var v_r14)
 (.cons (.var v_r15)
 (.cons (.var v_d)
 (.cons (.var v_ac)
 (.cons (.var v_id)
 (.cons (.var v_fs)
 (.cons (.var v_sseround)
 (.cons (.var v_zmm0)
 (.cons (.var v_zmm1)
 (.cons (.var v_zmm2)
 (.cons (.var v_zmm3)
 (.cons (.var v_zmm4)
 (.cons (.var v_zmm5)
 (.cons (.var v_zmm6)
 (.cons (.var v_zmm7)
 (.cons (.var v_zmm8)
 (.cons (.var v_zmm9)
 (.cons (.var v_zmm10)
 (.cons (.var v_zmm11)
 (.cons (.var v_zmm12)
 (.cons (.var v_zmm13)
 (.cons (.var v_zmm14)
 (.cons (.var v_zmm15)
 (.cons (.var v_zmm16)
 (.cons (.var v_zmm17)
 (.cons (.var v_zmm18)
 (.cons (.var v_zmm19)
 (.cons (.var v_zmm20)
 (.cons (.var v_zmm21)
 (.cons (.var v_zmm22)
 (.cons (.var v_zmm23)
 (.cons (.var v_zmm24)
 (.cons (.var v_zmm25)
 (.cons (.var v_zmm26)
 (.cons (.var v_zmm27)
 (.cons (.var v_zmm28)
 (.cons (.var v_zmm29)
 (.cons (.var v_zmm30)
 (.cons (.var v_zmm31)
 (.cons (.var v_k0)
 (.cons (.var v_k1)
 (.cons (.var v_k2)
 (.cons (.var v_k3)
 (.cons (.var v_k4)
 (.cons (.var v_k5)
 (.cons (.var v_k6)
 (.cons (.var v_k7)
 (.cons (.var v_ftop)
 (.cons (.var v_fpreg)
 (.cons (.var v_fptag)
 (.cons (.var v_fpround)
 (.cons (.var v_fc3210)
 (.cons (.var v_emnote)
 (.cons (.var v_cmstart)
 (.cons (.var v_cmlen)
 (.cons (.var v_nraddr)
 (.cons (.var v_gs)
 (.cons (.var v_ip_at_syscall)
 (.cons (.var v_cs_seg)
 (.cons (.var v_ds_seg)
 (.cons (.var v_es_seg)
 (.cons (.var v_fs_seg)
 (.cons (.var v_gs_seg)
 (.cons (.var v_ss_seg)
 (.cons (.var v_cr0)
 (.cons (.var v_cr2)
 (.cons (.var v_cr3)
 (.cons (.var v_cr4)
 (.cons (.var v_cr8)
 (.cons e155
 (.cons e157
 (.cons e158
 (.cons e163
 (.cons e175
 (.cons e178
 .nil)))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))
def suffixStep : QFAbvStep Γ Γ := ⟨.eqBv 64 (.var v_rip) (.bvLit 64 4194364), suffixUpdate⟩
theorem suffix_mem (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_mem = Eval.eval s e11 := rfl
theorem suffix_rip (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_rip = Eval.eval s e201 := rfl
theorem suffix_rax (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_rax = Eval.eval s (.var v_rax) := rfl
theorem suffix_rcx (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_rcx = Eval.eval s (.var v_rcx) := rfl
theorem suffix_rdx (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_rdx = Eval.eval s (.var v_rdx) := rfl
theorem suffix_rbx (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_rbx = Eval.eval s (.var v_rbx) := rfl
theorem suffix_rsp (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_rsp = Eval.eval s e151 := rfl
theorem suffix_rbp (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_rbp = Eval.eval s (.var v_rbp) := rfl
theorem suffix_rsi (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_rsi = Eval.eval s (.var v_rsi) := rfl
theorem suffix_rdi (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_rdi = Eval.eval s (.var v_rdi) := rfl
theorem suffix_r8 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_r8 = Eval.eval s (.var v_r8) := rfl
theorem suffix_r9 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_r9 = Eval.eval s (.var v_r9) := rfl
theorem suffix_r10 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_r10 = Eval.eval s (.var v_r10) := rfl
theorem suffix_r11 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_r11 = Eval.eval s (.var v_r11) := rfl
theorem suffix_r12 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_r12 = Eval.eval s (.var v_r12) := rfl
theorem suffix_r13 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_r13 = Eval.eval s (.var v_r13) := rfl
theorem suffix_r14 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_r14 = Eval.eval s (.var v_r14) := rfl
theorem suffix_r15 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_r15 = Eval.eval s (.var v_r15) := rfl
theorem suffix_d (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_d = Eval.eval s (.var v_d) := rfl
theorem suffix_ac (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_ac = Eval.eval s (.var v_ac) := rfl
theorem suffix_id (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_id = Eval.eval s (.var v_id) := rfl
theorem suffix_fs (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_fs = Eval.eval s (.var v_fs) := rfl
theorem suffix_sseround (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_sseround = Eval.eval s (.var v_sseround) := rfl
theorem suffix_zmm0 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_zmm0 = Eval.eval s (.var v_zmm0) := rfl
theorem suffix_zmm1 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_zmm1 = Eval.eval s (.var v_zmm1) := rfl
theorem suffix_zmm2 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_zmm2 = Eval.eval s (.var v_zmm2) := rfl
theorem suffix_zmm3 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_zmm3 = Eval.eval s (.var v_zmm3) := rfl
theorem suffix_zmm4 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_zmm4 = Eval.eval s (.var v_zmm4) := rfl
theorem suffix_zmm5 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_zmm5 = Eval.eval s (.var v_zmm5) := rfl
theorem suffix_zmm6 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_zmm6 = Eval.eval s (.var v_zmm6) := rfl
theorem suffix_zmm7 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_zmm7 = Eval.eval s (.var v_zmm7) := rfl
theorem suffix_zmm8 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_zmm8 = Eval.eval s (.var v_zmm8) := rfl
theorem suffix_zmm9 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_zmm9 = Eval.eval s (.var v_zmm9) := rfl
theorem suffix_zmm10 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_zmm10 = Eval.eval s (.var v_zmm10) := rfl
theorem suffix_zmm11 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_zmm11 = Eval.eval s (.var v_zmm11) := rfl
theorem suffix_zmm12 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_zmm12 = Eval.eval s (.var v_zmm12) := rfl
theorem suffix_zmm13 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_zmm13 = Eval.eval s (.var v_zmm13) := rfl
theorem suffix_zmm14 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_zmm14 = Eval.eval s (.var v_zmm14) := rfl
theorem suffix_zmm15 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_zmm15 = Eval.eval s (.var v_zmm15) := rfl
theorem suffix_zmm16 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_zmm16 = Eval.eval s (.var v_zmm16) := rfl
theorem suffix_zmm17 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_zmm17 = Eval.eval s (.var v_zmm17) := rfl
theorem suffix_zmm18 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_zmm18 = Eval.eval s (.var v_zmm18) := rfl
theorem suffix_zmm19 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_zmm19 = Eval.eval s (.var v_zmm19) := rfl
theorem suffix_zmm20 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_zmm20 = Eval.eval s (.var v_zmm20) := rfl
theorem suffix_zmm21 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_zmm21 = Eval.eval s (.var v_zmm21) := rfl
theorem suffix_zmm22 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_zmm22 = Eval.eval s (.var v_zmm22) := rfl
theorem suffix_zmm23 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_zmm23 = Eval.eval s (.var v_zmm23) := rfl
theorem suffix_zmm24 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_zmm24 = Eval.eval s (.var v_zmm24) := rfl
theorem suffix_zmm25 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_zmm25 = Eval.eval s (.var v_zmm25) := rfl
theorem suffix_zmm26 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_zmm26 = Eval.eval s (.var v_zmm26) := rfl
theorem suffix_zmm27 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_zmm27 = Eval.eval s (.var v_zmm27) := rfl
theorem suffix_zmm28 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_zmm28 = Eval.eval s (.var v_zmm28) := rfl
theorem suffix_zmm29 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_zmm29 = Eval.eval s (.var v_zmm29) := rfl
theorem suffix_zmm30 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_zmm30 = Eval.eval s (.var v_zmm30) := rfl
theorem suffix_zmm31 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_zmm31 = Eval.eval s (.var v_zmm31) := rfl
theorem suffix_k0 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_k0 = Eval.eval s (.var v_k0) := rfl
theorem suffix_k1 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_k1 = Eval.eval s (.var v_k1) := rfl
theorem suffix_k2 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_k2 = Eval.eval s (.var v_k2) := rfl
theorem suffix_k3 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_k3 = Eval.eval s (.var v_k3) := rfl
theorem suffix_k4 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_k4 = Eval.eval s (.var v_k4) := rfl
theorem suffix_k5 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_k5 = Eval.eval s (.var v_k5) := rfl
theorem suffix_k6 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_k6 = Eval.eval s (.var v_k6) := rfl
theorem suffix_k7 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_k7 = Eval.eval s (.var v_k7) := rfl
theorem suffix_ftop (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_ftop = Eval.eval s (.var v_ftop) := rfl
theorem suffix_fpreg (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_fpreg = Eval.eval s (.var v_fpreg) := rfl
theorem suffix_fptag (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_fptag = Eval.eval s (.var v_fptag) := rfl
theorem suffix_fpround (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_fpround = Eval.eval s (.var v_fpround) := rfl
theorem suffix_fc3210 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_fc3210 = Eval.eval s (.var v_fc3210) := rfl
theorem suffix_emnote (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_emnote = Eval.eval s (.var v_emnote) := rfl
theorem suffix_cmstart (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_cmstart = Eval.eval s (.var v_cmstart) := rfl
theorem suffix_cmlen (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_cmlen = Eval.eval s (.var v_cmlen) := rfl
theorem suffix_nraddr (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_nraddr = Eval.eval s (.var v_nraddr) := rfl
theorem suffix_gs (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_gs = Eval.eval s (.var v_gs) := rfl
theorem suffix_ip_at_syscall (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_ip_at_syscall = Eval.eval s (.var v_ip_at_syscall) := rfl
theorem suffix_cs_seg (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_cs_seg = Eval.eval s (.var v_cs_seg) := rfl
theorem suffix_ds_seg (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_ds_seg = Eval.eval s (.var v_ds_seg) := rfl
theorem suffix_es_seg (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_es_seg = Eval.eval s (.var v_es_seg) := rfl
theorem suffix_fs_seg (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_fs_seg = Eval.eval s (.var v_fs_seg) := rfl
theorem suffix_gs_seg (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_gs_seg = Eval.eval s (.var v_gs_seg) := rfl
theorem suffix_ss_seg (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_ss_seg = Eval.eval s (.var v_ss_seg) := rfl
theorem suffix_cr0 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_cr0 = Eval.eval s (.var v_cr0) := rfl
theorem suffix_cr2 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_cr2 = Eval.eval s (.var v_cr2) := rfl
theorem suffix_cr3 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_cr3 = Eval.eval s (.var v_cr3) := rfl
theorem suffix_cr4 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_cr4 = Eval.eval s (.var v_cr4) := rfl
theorem suffix_cr8 (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_cr8 = Eval.eval s (.var v_cr8) := rfl
theorem suffix_rflags_CF (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_rflags_CF = Eval.eval s e155 := rfl
theorem suffix_rflags_ZF (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_rflags_ZF = Eval.eval s e157 := rfl
theorem suffix_rflags_SF (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_rflags_SF = Eval.eval s e158 := rfl
theorem suffix_rflags_OF (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_rflags_OF = Eval.eval s e163 := rfl
theorem suffix_rflags_PF (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_rflags_PF = Eval.eval s e175 := rfl
theorem suffix_rflags_AF (s : Env Γ) : Env.lookup (suffixUpdate.eval s) v_rflags_AF = Eval.eval s e178 := rfl
end MovObserver.Shim
