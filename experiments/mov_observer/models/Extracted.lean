-- Generated from the exact observer.bin, not hand-written MOV semantics.
-- SHA256 b1f9eb3a26a7f70bd278fb11f1844c408e13150bf8433605d1d92522db10b339
import Ayxg.QfAbv.Step
import Ayxg.LTS.QfAbv.SymbolicTransitionSystem
set_option maxRecDepth 16384
namespace MovObserver
open Ayxg.QfAbv
def Γ : Ctx := [  { name := "mem", sort := (.array 64 8) },
  { name := "rip", sort := (.bv 64) },
  { name := "rax", sort := (.bv 64) },
  { name := "rcx", sort := (.bv 64) },
  { name := "rdx", sort := (.bv 64) },
  { name := "rbx", sort := (.bv 64) },
  { name := "rsp", sort := (.bv 64) },
  { name := "rbp", sort := (.bv 64) },
  { name := "rsi", sort := (.bv 64) },
  { name := "rdi", sort := (.bv 64) },
  { name := "r8", sort := (.bv 64) },
  { name := "r9", sort := (.bv 64) },
  { name := "r10", sort := (.bv 64) },
  { name := "r11", sort := (.bv 64) },
  { name := "r12", sort := (.bv 64) },
  { name := "r13", sort := (.bv 64) },
  { name := "r14", sort := (.bv 64) },
  { name := "r15", sort := (.bv 64) },
  { name := "d", sort := (.bv 64) },
  { name := "ac", sort := (.bv 64) },
  { name := "id", sort := (.bv 64) },
  { name := "fs", sort := (.bv 64) },
  { name := "sseround", sort := (.bv 64) },
  { name := "zmm0", sort := (.bv 512) },
  { name := "zmm1", sort := (.bv 512) },
  { name := "zmm2", sort := (.bv 512) },
  { name := "zmm3", sort := (.bv 512) },
  { name := "zmm4", sort := (.bv 512) },
  { name := "zmm5", sort := (.bv 512) },
  { name := "zmm6", sort := (.bv 512) },
  { name := "zmm7", sort := (.bv 512) },
  { name := "zmm8", sort := (.bv 512) },
  { name := "zmm9", sort := (.bv 512) },
  { name := "zmm10", sort := (.bv 512) },
  { name := "zmm11", sort := (.bv 512) },
  { name := "zmm12", sort := (.bv 512) },
  { name := "zmm13", sort := (.bv 512) },
  { name := "zmm14", sort := (.bv 512) },
  { name := "zmm15", sort := (.bv 512) },
  { name := "zmm16", sort := (.bv 512) },
  { name := "zmm17", sort := (.bv 512) },
  { name := "zmm18", sort := (.bv 512) },
  { name := "zmm19", sort := (.bv 512) },
  { name := "zmm20", sort := (.bv 512) },
  { name := "zmm21", sort := (.bv 512) },
  { name := "zmm22", sort := (.bv 512) },
  { name := "zmm23", sort := (.bv 512) },
  { name := "zmm24", sort := (.bv 512) },
  { name := "zmm25", sort := (.bv 512) },
  { name := "zmm26", sort := (.bv 512) },
  { name := "zmm27", sort := (.bv 512) },
  { name := "zmm28", sort := (.bv 512) },
  { name := "zmm29", sort := (.bv 512) },
  { name := "zmm30", sort := (.bv 512) },
  { name := "zmm31", sort := (.bv 512) },
  { name := "k0", sort := (.bv 64) },
  { name := "k1", sort := (.bv 64) },
  { name := "k2", sort := (.bv 64) },
  { name := "k3", sort := (.bv 64) },
  { name := "k4", sort := (.bv 64) },
  { name := "k5", sort := (.bv 64) },
  { name := "k6", sort := (.bv 64) },
  { name := "k7", sort := (.bv 64) },
  { name := "ftop", sort := (.bv 32) },
  { name := "fpreg", sort := (.bv 512) },
  { name := "fptag", sort := (.bv 64) },
  { name := "fpround", sort := (.bv 64) },
  { name := "fc3210", sort := (.bv 64) },
  { name := "emnote", sort := (.bv 32) },
  { name := "cmstart", sort := (.bv 64) },
  { name := "cmlen", sort := (.bv 64) },
  { name := "nraddr", sort := (.bv 64) },
  { name := "gs", sort := (.bv 64) },
  { name := "ip_at_syscall", sort := (.bv 64) },
  { name := "cs_seg", sort := (.bv 16) },
  { name := "ds_seg", sort := (.bv 16) },
  { name := "es_seg", sort := (.bv 16) },
  { name := "fs_seg", sort := (.bv 16) },
  { name := "gs_seg", sort := (.bv 16) },
  { name := "ss_seg", sort := (.bv 16) },
  { name := "cr0", sort := (.bv 64) },
  { name := "cr2", sort := (.bv 64) },
  { name := "cr3", sort := (.bv 64) },
  { name := "cr4", sort := (.bv 64) },
  { name := "cr8", sort := (.bv 64) },
  { name := "rflags_CF", sort := (.bv 1) },
  { name := "rflags_ZF", sort := (.bv 1) },
  { name := "rflags_SF", sort := (.bv 1) },
  { name := "rflags_OF", sort := (.bv 1) },
  { name := "rflags_PF", sort := (.bv 1) },
  { name := "rflags_AF", sort := (.bv 1) }]
def v_mem : Var Γ (.array 64 8) := (.here)
def v_rip : Var Γ (.bv 64) := (.there (.here))
def v_rax : Var Γ (.bv 64) := (.there (.there (.here)))
def v_rcx : Var Γ (.bv 64) := (.there (.there (.there (.here))))
def v_rdx : Var Γ (.bv 64) := (.there (.there (.there (.there (.here)))))
def v_rbx : Var Γ (.bv 64) := (.there (.there (.there (.there (.there (.here))))))
def v_rsp : Var Γ (.bv 64) := (.there (.there (.there (.there (.there (.there (.here)))))))
def v_rbp : Var Γ (.bv 64) := (.there (.there (.there (.there (.there (.there (.there (.here))))))))
def v_rsi : Var Γ (.bv 64) := (.there (.there (.there (.there (.there (.there (.there (.there (.here)))))))))
def v_rdi : Var Γ (.bv 64) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here))))))))))
def v_r8 : Var Γ (.bv 64) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here)))))))))))
def v_r9 : Var Γ (.bv 64) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here))))))))))))
def v_r10 : Var Γ (.bv 64) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here)))))))))))))
def v_r11 : Var Γ (.bv 64) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here))))))))))))))
def v_r12 : Var Γ (.bv 64) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here)))))))))))))))
def v_r13 : Var Γ (.bv 64) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here))))))))))))))))
def v_r14 : Var Γ (.bv 64) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here)))))))))))))))))
def v_r15 : Var Γ (.bv 64) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here))))))))))))))))))
def v_d : Var Γ (.bv 64) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here)))))))))))))))))))
def v_ac : Var Γ (.bv 64) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here))))))))))))))))))))
def v_id : Var Γ (.bv 64) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here)))))))))))))))))))))
def v_fs : Var Γ (.bv 64) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here))))))))))))))))))))))
def v_sseround : Var Γ (.bv 64) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here)))))))))))))))))))))))
def v_zmm0 : Var Γ (.bv 512) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here))))))))))))))))))))))))
def v_zmm1 : Var Γ (.bv 512) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here)))))))))))))))))))))))))
def v_zmm2 : Var Γ (.bv 512) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here))))))))))))))))))))))))))
def v_zmm3 : Var Γ (.bv 512) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here)))))))))))))))))))))))))))
def v_zmm4 : Var Γ (.bv 512) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here))))))))))))))))))))))))))))
def v_zmm5 : Var Γ (.bv 512) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here)))))))))))))))))))))))))))))
def v_zmm6 : Var Γ (.bv 512) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here))))))))))))))))))))))))))))))
def v_zmm7 : Var Γ (.bv 512) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here)))))))))))))))))))))))))))))))
def v_zmm8 : Var Γ (.bv 512) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here))))))))))))))))))))))))))))))))
def v_zmm9 : Var Γ (.bv 512) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here)))))))))))))))))))))))))))))))))
def v_zmm10 : Var Γ (.bv 512) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here))))))))))))))))))))))))))))))))))
def v_zmm11 : Var Γ (.bv 512) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here)))))))))))))))))))))))))))))))))))
def v_zmm12 : Var Γ (.bv 512) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here))))))))))))))))))))))))))))))))))))
def v_zmm13 : Var Γ (.bv 512) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here)))))))))))))))))))))))))))))))))))))
def v_zmm14 : Var Γ (.bv 512) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here))))))))))))))))))))))))))))))))))))))
def v_zmm15 : Var Γ (.bv 512) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here)))))))))))))))))))))))))))))))))))))))
def v_zmm16 : Var Γ (.bv 512) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here))))))))))))))))))))))))))))))))))))))))
def v_zmm17 : Var Γ (.bv 512) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here)))))))))))))))))))))))))))))))))))))))))
def v_zmm18 : Var Γ (.bv 512) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here))))))))))))))))))))))))))))))))))))))))))
def v_zmm19 : Var Γ (.bv 512) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here)))))))))))))))))))))))))))))))))))))))))))
def v_zmm20 : Var Γ (.bv 512) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here))))))))))))))))))))))))))))))))))))))))))))
def v_zmm21 : Var Γ (.bv 512) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here)))))))))))))))))))))))))))))))))))))))))))))
def v_zmm22 : Var Γ (.bv 512) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here))))))))))))))))))))))))))))))))))))))))))))))
def v_zmm23 : Var Γ (.bv 512) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here)))))))))))))))))))))))))))))))))))))))))))))))
def v_zmm24 : Var Γ (.bv 512) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here))))))))))))))))))))))))))))))))))))))))))))))))
def v_zmm25 : Var Γ (.bv 512) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here)))))))))))))))))))))))))))))))))))))))))))))))))
def v_zmm26 : Var Γ (.bv 512) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here))))))))))))))))))))))))))))))))))))))))))))))))))
def v_zmm27 : Var Γ (.bv 512) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here)))))))))))))))))))))))))))))))))))))))))))))))))))
def v_zmm28 : Var Γ (.bv 512) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here))))))))))))))))))))))))))))))))))))))))))))))))))))
def v_zmm29 : Var Γ (.bv 512) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here)))))))))))))))))))))))))))))))))))))))))))))))))))))
def v_zmm30 : Var Γ (.bv 512) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here))))))))))))))))))))))))))))))))))))))))))))))))))))))
def v_zmm31 : Var Γ (.bv 512) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here)))))))))))))))))))))))))))))))))))))))))))))))))))))))
def v_k0 : Var Γ (.bv 64) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here))))))))))))))))))))))))))))))))))))))))))))))))))))))))
def v_k1 : Var Γ (.bv 64) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here)))))))))))))))))))))))))))))))))))))))))))))))))))))))))
def v_k2 : Var Γ (.bv 64) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here))))))))))))))))))))))))))))))))))))))))))))))))))))))))))
def v_k3 : Var Γ (.bv 64) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here)))))))))))))))))))))))))))))))))))))))))))))))))))))))))))
def v_k4 : Var Γ (.bv 64) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))
def v_k5 : Var Γ (.bv 64) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here)))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))
def v_k6 : Var Γ (.bv 64) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))
def v_k7 : Var Γ (.bv 64) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here)))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))
def v_ftop : Var Γ (.bv 32) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))
def v_fpreg : Var Γ (.bv 512) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here)))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))
def v_fptag : Var Γ (.bv 64) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))
def v_fpround : Var Γ (.bv 64) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here)))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))
def v_fc3210 : Var Γ (.bv 64) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))
def v_emnote : Var Γ (.bv 32) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here)))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))
def v_cmstart : Var Γ (.bv 64) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))
def v_cmlen : Var Γ (.bv 64) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here)))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))
def v_nraddr : Var Γ (.bv 64) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))
def v_gs : Var Γ (.bv 64) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here)))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))
def v_ip_at_syscall : Var Γ (.bv 64) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))
def v_cs_seg : Var Γ (.bv 16) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here)))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))
def v_ds_seg : Var Γ (.bv 16) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))
def v_es_seg : Var Γ (.bv 16) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here)))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))
def v_fs_seg : Var Γ (.bv 16) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))
def v_gs_seg : Var Γ (.bv 16) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here)))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))
def v_ss_seg : Var Γ (.bv 16) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))
def v_cr0 : Var Γ (.bv 64) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here)))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))
def v_cr2 : Var Γ (.bv 64) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))
def v_cr3 : Var Γ (.bv 64) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here)))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))
def v_cr4 : Var Γ (.bv 64) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))
def v_cr8 : Var Γ (.bv 64) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here)))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))
def v_rflags_CF : Var Γ (.bv 1) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))
def v_rflags_ZF : Var Γ (.bv 1) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here)))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))
def v_rflags_SF : Var Γ (.bv 1) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))
def v_rflags_OF : Var Γ (.bv 1) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here)))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))
def v_rflags_PF : Var Γ (.bv 1) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))
def v_rflags_AF : Var Γ (.bv 1) := (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.there (.here)))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))
abbrev ByteWrite := BitVec 64 × Expr Γ (.bv 8)
def extractedWrites : List ByteWrite := [  (BitVec.ofNat 64 6295616, (.extract { hi := 7, lo := 0, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rax))),
  (BitVec.ofNat 64 6295617, (.extract { hi := 15, lo := 8, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rax))),
  (BitVec.ofNat 64 6295618, (.extract { hi := 23, lo := 16, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rax))),
  (BitVec.ofNat 64 6295619, (.extract { hi := 31, lo := 24, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rax))),
  (BitVec.ofNat 64 6295620, (.extract { hi := 39, lo := 32, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rax))),
  (BitVec.ofNat 64 6295621, (.extract { hi := 47, lo := 40, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rax))),
  (BitVec.ofNat 64 6295622, (.extract { hi := 55, lo := 48, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rax))),
  (BitVec.ofNat 64 6295623, (.extract { hi := 63, lo := 56, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rax))),
  (BitVec.ofNat 64 6295624, (.extract { hi := 7, lo := 0, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rcx))),
  (BitVec.ofNat 64 6295625, (.extract { hi := 15, lo := 8, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rcx))),
  (BitVec.ofNat 64 6295626, (.extract { hi := 23, lo := 16, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rcx))),
  (BitVec.ofNat 64 6295627, (.extract { hi := 31, lo := 24, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rcx))),
  (BitVec.ofNat 64 6295628, (.extract { hi := 39, lo := 32, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rcx))),
  (BitVec.ofNat 64 6295629, (.extract { hi := 47, lo := 40, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rcx))),
  (BitVec.ofNat 64 6295630, (.extract { hi := 55, lo := 48, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rcx))),
  (BitVec.ofNat 64 6295631, (.extract { hi := 63, lo := 56, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rcx))),
  (BitVec.ofNat 64 6295632, (.extract { hi := 7, lo := 0, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rdx))),
  (BitVec.ofNat 64 6295633, (.extract { hi := 15, lo := 8, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rdx))),
  (BitVec.ofNat 64 6295634, (.extract { hi := 23, lo := 16, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rdx))),
  (BitVec.ofNat 64 6295635, (.extract { hi := 31, lo := 24, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rdx))),
  (BitVec.ofNat 64 6295636, (.extract { hi := 39, lo := 32, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rdx))),
  (BitVec.ofNat 64 6295637, (.extract { hi := 47, lo := 40, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rdx))),
  (BitVec.ofNat 64 6295638, (.extract { hi := 55, lo := 48, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rdx))),
  (BitVec.ofNat 64 6295639, (.extract { hi := 63, lo := 56, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rdx))),
  (BitVec.ofNat 64 6295640, (.extract { hi := 7, lo := 0, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rbx))),
  (BitVec.ofNat 64 6295641, (.extract { hi := 15, lo := 8, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rbx))),
  (BitVec.ofNat 64 6295642, (.extract { hi := 23, lo := 16, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rbx))),
  (BitVec.ofNat 64 6295643, (.extract { hi := 31, lo := 24, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rbx))),
  (BitVec.ofNat 64 6295644, (.extract { hi := 39, lo := 32, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rbx))),
  (BitVec.ofNat 64 6295645, (.extract { hi := 47, lo := 40, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rbx))),
  (BitVec.ofNat 64 6295646, (.extract { hi := 55, lo := 48, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rbx))),
  (BitVec.ofNat 64 6295647, (.extract { hi := 63, lo := 56, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rbx))),
  (BitVec.ofNat 64 6295648, (.extract { hi := 7, lo := 0, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rsp))),
  (BitVec.ofNat 64 6295649, (.extract { hi := 15, lo := 8, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rsp))),
  (BitVec.ofNat 64 6295650, (.extract { hi := 23, lo := 16, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rsp))),
  (BitVec.ofNat 64 6295651, (.extract { hi := 31, lo := 24, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rsp))),
  (BitVec.ofNat 64 6295652, (.extract { hi := 39, lo := 32, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rsp))),
  (BitVec.ofNat 64 6295653, (.extract { hi := 47, lo := 40, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rsp))),
  (BitVec.ofNat 64 6295654, (.extract { hi := 55, lo := 48, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rsp))),
  (BitVec.ofNat 64 6295655, (.extract { hi := 63, lo := 56, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rsp))),
  (BitVec.ofNat 64 6295656, (.extract { hi := 7, lo := 0, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rbp))),
  (BitVec.ofNat 64 6295657, (.extract { hi := 15, lo := 8, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rbp))),
  (BitVec.ofNat 64 6295658, (.extract { hi := 23, lo := 16, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rbp))),
  (BitVec.ofNat 64 6295659, (.extract { hi := 31, lo := 24, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rbp))),
  (BitVec.ofNat 64 6295660, (.extract { hi := 39, lo := 32, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rbp))),
  (BitVec.ofNat 64 6295661, (.extract { hi := 47, lo := 40, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rbp))),
  (BitVec.ofNat 64 6295662, (.extract { hi := 55, lo := 48, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rbp))),
  (BitVec.ofNat 64 6295663, (.extract { hi := 63, lo := 56, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rbp))),
  (BitVec.ofNat 64 6295664, (.extract { hi := 7, lo := 0, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rsi))),
  (BitVec.ofNat 64 6295665, (.extract { hi := 15, lo := 8, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rsi))),
  (BitVec.ofNat 64 6295666, (.extract { hi := 23, lo := 16, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rsi))),
  (BitVec.ofNat 64 6295667, (.extract { hi := 31, lo := 24, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rsi))),
  (BitVec.ofNat 64 6295668, (.extract { hi := 39, lo := 32, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rsi))),
  (BitVec.ofNat 64 6295669, (.extract { hi := 47, lo := 40, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rsi))),
  (BitVec.ofNat 64 6295670, (.extract { hi := 55, lo := 48, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rsi))),
  (BitVec.ofNat 64 6295671, (.extract { hi := 63, lo := 56, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rsi))),
  (BitVec.ofNat 64 6295672, (.extract { hi := 7, lo := 0, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rdi))),
  (BitVec.ofNat 64 6295673, (.extract { hi := 15, lo := 8, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rdi))),
  (BitVec.ofNat 64 6295674, (.extract { hi := 23, lo := 16, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rdi))),
  (BitVec.ofNat 64 6295675, (.extract { hi := 31, lo := 24, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rdi))),
  (BitVec.ofNat 64 6295676, (.extract { hi := 39, lo := 32, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rdi))),
  (BitVec.ofNat 64 6295677, (.extract { hi := 47, lo := 40, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rdi))),
  (BitVec.ofNat 64 6295678, (.extract { hi := 55, lo := 48, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rdi))),
  (BitVec.ofNat 64 6295679, (.extract { hi := 63, lo := 56, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rdi))),
  (BitVec.ofNat 64 6295680, (.extract { hi := 7, lo := 0, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r8))),
  (BitVec.ofNat 64 6295681, (.extract { hi := 15, lo := 8, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r8))),
  (BitVec.ofNat 64 6295682, (.extract { hi := 23, lo := 16, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r8))),
  (BitVec.ofNat 64 6295683, (.extract { hi := 31, lo := 24, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r8))),
  (BitVec.ofNat 64 6295684, (.extract { hi := 39, lo := 32, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r8))),
  (BitVec.ofNat 64 6295685, (.extract { hi := 47, lo := 40, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r8))),
  (BitVec.ofNat 64 6295686, (.extract { hi := 55, lo := 48, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r8))),
  (BitVec.ofNat 64 6295687, (.extract { hi := 63, lo := 56, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r8))),
  (BitVec.ofNat 64 6295688, (.extract { hi := 7, lo := 0, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r9))),
  (BitVec.ofNat 64 6295689, (.extract { hi := 15, lo := 8, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r9))),
  (BitVec.ofNat 64 6295690, (.extract { hi := 23, lo := 16, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r9))),
  (BitVec.ofNat 64 6295691, (.extract { hi := 31, lo := 24, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r9))),
  (BitVec.ofNat 64 6295692, (.extract { hi := 39, lo := 32, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r9))),
  (BitVec.ofNat 64 6295693, (.extract { hi := 47, lo := 40, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r9))),
  (BitVec.ofNat 64 6295694, (.extract { hi := 55, lo := 48, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r9))),
  (BitVec.ofNat 64 6295695, (.extract { hi := 63, lo := 56, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r9))),
  (BitVec.ofNat 64 6295696, (.extract { hi := 7, lo := 0, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r10))),
  (BitVec.ofNat 64 6295697, (.extract { hi := 15, lo := 8, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r10))),
  (BitVec.ofNat 64 6295698, (.extract { hi := 23, lo := 16, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r10))),
  (BitVec.ofNat 64 6295699, (.extract { hi := 31, lo := 24, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r10))),
  (BitVec.ofNat 64 6295700, (.extract { hi := 39, lo := 32, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r10))),
  (BitVec.ofNat 64 6295701, (.extract { hi := 47, lo := 40, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r10))),
  (BitVec.ofNat 64 6295702, (.extract { hi := 55, lo := 48, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r10))),
  (BitVec.ofNat 64 6295703, (.extract { hi := 63, lo := 56, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r10))),
  (BitVec.ofNat 64 6295704, (.extract { hi := 7, lo := 0, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r11))),
  (BitVec.ofNat 64 6295705, (.extract { hi := 15, lo := 8, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r11))),
  (BitVec.ofNat 64 6295706, (.extract { hi := 23, lo := 16, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r11))),
  (BitVec.ofNat 64 6295707, (.extract { hi := 31, lo := 24, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r11))),
  (BitVec.ofNat 64 6295708, (.extract { hi := 39, lo := 32, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r11))),
  (BitVec.ofNat 64 6295709, (.extract { hi := 47, lo := 40, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r11))),
  (BitVec.ofNat 64 6295710, (.extract { hi := 55, lo := 48, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r11))),
  (BitVec.ofNat 64 6295711, (.extract { hi := 63, lo := 56, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r11))),
  (BitVec.ofNat 64 6295712, (.extract { hi := 7, lo := 0, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r12))),
  (BitVec.ofNat 64 6295713, (.extract { hi := 15, lo := 8, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r12))),
  (BitVec.ofNat 64 6295714, (.extract { hi := 23, lo := 16, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r12))),
  (BitVec.ofNat 64 6295715, (.extract { hi := 31, lo := 24, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r12))),
  (BitVec.ofNat 64 6295716, (.extract { hi := 39, lo := 32, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r12))),
  (BitVec.ofNat 64 6295717, (.extract { hi := 47, lo := 40, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r12))),
  (BitVec.ofNat 64 6295718, (.extract { hi := 55, lo := 48, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r12))),
  (BitVec.ofNat 64 6295719, (.extract { hi := 63, lo := 56, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r12))),
  (BitVec.ofNat 64 6295720, (.extract { hi := 7, lo := 0, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r13))),
  (BitVec.ofNat 64 6295721, (.extract { hi := 15, lo := 8, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r13))),
  (BitVec.ofNat 64 6295722, (.extract { hi := 23, lo := 16, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r13))),
  (BitVec.ofNat 64 6295723, (.extract { hi := 31, lo := 24, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r13))),
  (BitVec.ofNat 64 6295724, (.extract { hi := 39, lo := 32, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r13))),
  (BitVec.ofNat 64 6295725, (.extract { hi := 47, lo := 40, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r13))),
  (BitVec.ofNat 64 6295726, (.extract { hi := 55, lo := 48, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r13))),
  (BitVec.ofNat 64 6295727, (.extract { hi := 63, lo := 56, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r13))),
  (BitVec.ofNat 64 6295728, (.extract { hi := 7, lo := 0, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r14))),
  (BitVec.ofNat 64 6295729, (.extract { hi := 15, lo := 8, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r14))),
  (BitVec.ofNat 64 6295730, (.extract { hi := 23, lo := 16, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r14))),
  (BitVec.ofNat 64 6295731, (.extract { hi := 31, lo := 24, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r14))),
  (BitVec.ofNat 64 6295732, (.extract { hi := 39, lo := 32, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r14))),
  (BitVec.ofNat 64 6295733, (.extract { hi := 47, lo := 40, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r14))),
  (BitVec.ofNat 64 6295734, (.extract { hi := 55, lo := 48, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r14))),
  (BitVec.ofNat 64 6295735, (.extract { hi := 63, lo := 56, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r14))),
  (BitVec.ofNat 64 6295736, (.extract { hi := 7, lo := 0, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r15))),
  (BitVec.ofNat 64 6295737, (.extract { hi := 15, lo := 8, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r15))),
  (BitVec.ofNat 64 6295738, (.extract { hi := 23, lo := 16, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r15))),
  (BitVec.ofNat 64 6295739, (.extract { hi := 31, lo := 24, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r15))),
  (BitVec.ofNat 64 6295740, (.extract { hi := 39, lo := 32, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r15))),
  (BitVec.ofNat 64 6295741, (.extract { hi := 47, lo := 40, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r15))),
  (BitVec.ofNat 64 6295742, (.extract { hi := 55, lo := 48, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r15))),
  (BitVec.ofNat 64 6295743, (.extract { hi := 63, lo := 56, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r15)))]
def expectedWrites : List ByteWrite := [  (BitVec.ofNat 64 6295616, .extract { hi := 7, lo := 0, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rax)),
  (BitVec.ofNat 64 6295617, .extract { hi := 15, lo := 8, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rax)),
  (BitVec.ofNat 64 6295618, .extract { hi := 23, lo := 16, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rax)),
  (BitVec.ofNat 64 6295619, .extract { hi := 31, lo := 24, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rax)),
  (BitVec.ofNat 64 6295620, .extract { hi := 39, lo := 32, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rax)),
  (BitVec.ofNat 64 6295621, .extract { hi := 47, lo := 40, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rax)),
  (BitVec.ofNat 64 6295622, .extract { hi := 55, lo := 48, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rax)),
  (BitVec.ofNat 64 6295623, .extract { hi := 63, lo := 56, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rax)),
  (BitVec.ofNat 64 6295624, .extract { hi := 7, lo := 0, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rcx)),
  (BitVec.ofNat 64 6295625, .extract { hi := 15, lo := 8, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rcx)),
  (BitVec.ofNat 64 6295626, .extract { hi := 23, lo := 16, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rcx)),
  (BitVec.ofNat 64 6295627, .extract { hi := 31, lo := 24, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rcx)),
  (BitVec.ofNat 64 6295628, .extract { hi := 39, lo := 32, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rcx)),
  (BitVec.ofNat 64 6295629, .extract { hi := 47, lo := 40, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rcx)),
  (BitVec.ofNat 64 6295630, .extract { hi := 55, lo := 48, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rcx)),
  (BitVec.ofNat 64 6295631, .extract { hi := 63, lo := 56, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rcx)),
  (BitVec.ofNat 64 6295632, .extract { hi := 7, lo := 0, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rdx)),
  (BitVec.ofNat 64 6295633, .extract { hi := 15, lo := 8, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rdx)),
  (BitVec.ofNat 64 6295634, .extract { hi := 23, lo := 16, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rdx)),
  (BitVec.ofNat 64 6295635, .extract { hi := 31, lo := 24, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rdx)),
  (BitVec.ofNat 64 6295636, .extract { hi := 39, lo := 32, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rdx)),
  (BitVec.ofNat 64 6295637, .extract { hi := 47, lo := 40, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rdx)),
  (BitVec.ofNat 64 6295638, .extract { hi := 55, lo := 48, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rdx)),
  (BitVec.ofNat 64 6295639, .extract { hi := 63, lo := 56, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rdx)),
  (BitVec.ofNat 64 6295640, .extract { hi := 7, lo := 0, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rbx)),
  (BitVec.ofNat 64 6295641, .extract { hi := 15, lo := 8, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rbx)),
  (BitVec.ofNat 64 6295642, .extract { hi := 23, lo := 16, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rbx)),
  (BitVec.ofNat 64 6295643, .extract { hi := 31, lo := 24, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rbx)),
  (BitVec.ofNat 64 6295644, .extract { hi := 39, lo := 32, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rbx)),
  (BitVec.ofNat 64 6295645, .extract { hi := 47, lo := 40, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rbx)),
  (BitVec.ofNat 64 6295646, .extract { hi := 55, lo := 48, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rbx)),
  (BitVec.ofNat 64 6295647, .extract { hi := 63, lo := 56, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rbx)),
  (BitVec.ofNat 64 6295648, .extract { hi := 7, lo := 0, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rsp)),
  (BitVec.ofNat 64 6295649, .extract { hi := 15, lo := 8, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rsp)),
  (BitVec.ofNat 64 6295650, .extract { hi := 23, lo := 16, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rsp)),
  (BitVec.ofNat 64 6295651, .extract { hi := 31, lo := 24, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rsp)),
  (BitVec.ofNat 64 6295652, .extract { hi := 39, lo := 32, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rsp)),
  (BitVec.ofNat 64 6295653, .extract { hi := 47, lo := 40, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rsp)),
  (BitVec.ofNat 64 6295654, .extract { hi := 55, lo := 48, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rsp)),
  (BitVec.ofNat 64 6295655, .extract { hi := 63, lo := 56, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rsp)),
  (BitVec.ofNat 64 6295656, .extract { hi := 7, lo := 0, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rbp)),
  (BitVec.ofNat 64 6295657, .extract { hi := 15, lo := 8, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rbp)),
  (BitVec.ofNat 64 6295658, .extract { hi := 23, lo := 16, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rbp)),
  (BitVec.ofNat 64 6295659, .extract { hi := 31, lo := 24, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rbp)),
  (BitVec.ofNat 64 6295660, .extract { hi := 39, lo := 32, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rbp)),
  (BitVec.ofNat 64 6295661, .extract { hi := 47, lo := 40, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rbp)),
  (BitVec.ofNat 64 6295662, .extract { hi := 55, lo := 48, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rbp)),
  (BitVec.ofNat 64 6295663, .extract { hi := 63, lo := 56, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rbp)),
  (BitVec.ofNat 64 6295664, .extract { hi := 7, lo := 0, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rsi)),
  (BitVec.ofNat 64 6295665, .extract { hi := 15, lo := 8, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rsi)),
  (BitVec.ofNat 64 6295666, .extract { hi := 23, lo := 16, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rsi)),
  (BitVec.ofNat 64 6295667, .extract { hi := 31, lo := 24, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rsi)),
  (BitVec.ofNat 64 6295668, .extract { hi := 39, lo := 32, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rsi)),
  (BitVec.ofNat 64 6295669, .extract { hi := 47, lo := 40, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rsi)),
  (BitVec.ofNat 64 6295670, .extract { hi := 55, lo := 48, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rsi)),
  (BitVec.ofNat 64 6295671, .extract { hi := 63, lo := 56, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rsi)),
  (BitVec.ofNat 64 6295672, .extract { hi := 7, lo := 0, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rdi)),
  (BitVec.ofNat 64 6295673, .extract { hi := 15, lo := 8, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rdi)),
  (BitVec.ofNat 64 6295674, .extract { hi := 23, lo := 16, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rdi)),
  (BitVec.ofNat 64 6295675, .extract { hi := 31, lo := 24, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rdi)),
  (BitVec.ofNat 64 6295676, .extract { hi := 39, lo := 32, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rdi)),
  (BitVec.ofNat 64 6295677, .extract { hi := 47, lo := 40, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rdi)),
  (BitVec.ofNat 64 6295678, .extract { hi := 55, lo := 48, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rdi)),
  (BitVec.ofNat 64 6295679, .extract { hi := 63, lo := 56, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_rdi)),
  (BitVec.ofNat 64 6295680, .extract { hi := 7, lo := 0, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r8)),
  (BitVec.ofNat 64 6295681, .extract { hi := 15, lo := 8, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r8)),
  (BitVec.ofNat 64 6295682, .extract { hi := 23, lo := 16, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r8)),
  (BitVec.ofNat 64 6295683, .extract { hi := 31, lo := 24, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r8)),
  (BitVec.ofNat 64 6295684, .extract { hi := 39, lo := 32, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r8)),
  (BitVec.ofNat 64 6295685, .extract { hi := 47, lo := 40, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r8)),
  (BitVec.ofNat 64 6295686, .extract { hi := 55, lo := 48, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r8)),
  (BitVec.ofNat 64 6295687, .extract { hi := 63, lo := 56, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r8)),
  (BitVec.ofNat 64 6295688, .extract { hi := 7, lo := 0, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r9)),
  (BitVec.ofNat 64 6295689, .extract { hi := 15, lo := 8, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r9)),
  (BitVec.ofNat 64 6295690, .extract { hi := 23, lo := 16, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r9)),
  (BitVec.ofNat 64 6295691, .extract { hi := 31, lo := 24, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r9)),
  (BitVec.ofNat 64 6295692, .extract { hi := 39, lo := 32, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r9)),
  (BitVec.ofNat 64 6295693, .extract { hi := 47, lo := 40, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r9)),
  (BitVec.ofNat 64 6295694, .extract { hi := 55, lo := 48, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r9)),
  (BitVec.ofNat 64 6295695, .extract { hi := 63, lo := 56, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r9)),
  (BitVec.ofNat 64 6295696, .extract { hi := 7, lo := 0, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r10)),
  (BitVec.ofNat 64 6295697, .extract { hi := 15, lo := 8, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r10)),
  (BitVec.ofNat 64 6295698, .extract { hi := 23, lo := 16, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r10)),
  (BitVec.ofNat 64 6295699, .extract { hi := 31, lo := 24, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r10)),
  (BitVec.ofNat 64 6295700, .extract { hi := 39, lo := 32, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r10)),
  (BitVec.ofNat 64 6295701, .extract { hi := 47, lo := 40, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r10)),
  (BitVec.ofNat 64 6295702, .extract { hi := 55, lo := 48, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r10)),
  (BitVec.ofNat 64 6295703, .extract { hi := 63, lo := 56, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r10)),
  (BitVec.ofNat 64 6295704, .extract { hi := 7, lo := 0, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r11)),
  (BitVec.ofNat 64 6295705, .extract { hi := 15, lo := 8, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r11)),
  (BitVec.ofNat 64 6295706, .extract { hi := 23, lo := 16, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r11)),
  (BitVec.ofNat 64 6295707, .extract { hi := 31, lo := 24, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r11)),
  (BitVec.ofNat 64 6295708, .extract { hi := 39, lo := 32, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r11)),
  (BitVec.ofNat 64 6295709, .extract { hi := 47, lo := 40, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r11)),
  (BitVec.ofNat 64 6295710, .extract { hi := 55, lo := 48, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r11)),
  (BitVec.ofNat 64 6295711, .extract { hi := 63, lo := 56, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r11)),
  (BitVec.ofNat 64 6295712, .extract { hi := 7, lo := 0, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r12)),
  (BitVec.ofNat 64 6295713, .extract { hi := 15, lo := 8, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r12)),
  (BitVec.ofNat 64 6295714, .extract { hi := 23, lo := 16, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r12)),
  (BitVec.ofNat 64 6295715, .extract { hi := 31, lo := 24, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r12)),
  (BitVec.ofNat 64 6295716, .extract { hi := 39, lo := 32, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r12)),
  (BitVec.ofNat 64 6295717, .extract { hi := 47, lo := 40, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r12)),
  (BitVec.ofNat 64 6295718, .extract { hi := 55, lo := 48, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r12)),
  (BitVec.ofNat 64 6295719, .extract { hi := 63, lo := 56, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r12)),
  (BitVec.ofNat 64 6295720, .extract { hi := 7, lo := 0, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r13)),
  (BitVec.ofNat 64 6295721, .extract { hi := 15, lo := 8, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r13)),
  (BitVec.ofNat 64 6295722, .extract { hi := 23, lo := 16, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r13)),
  (BitVec.ofNat 64 6295723, .extract { hi := 31, lo := 24, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r13)),
  (BitVec.ofNat 64 6295724, .extract { hi := 39, lo := 32, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r13)),
  (BitVec.ofNat 64 6295725, .extract { hi := 47, lo := 40, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r13)),
  (BitVec.ofNat 64 6295726, .extract { hi := 55, lo := 48, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r13)),
  (BitVec.ofNat 64 6295727, .extract { hi := 63, lo := 56, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r13)),
  (BitVec.ofNat 64 6295728, .extract { hi := 7, lo := 0, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r14)),
  (BitVec.ofNat 64 6295729, .extract { hi := 15, lo := 8, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r14)),
  (BitVec.ofNat 64 6295730, .extract { hi := 23, lo := 16, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r14)),
  (BitVec.ofNat 64 6295731, .extract { hi := 31, lo := 24, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r14)),
  (BitVec.ofNat 64 6295732, .extract { hi := 39, lo := 32, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r14)),
  (BitVec.ofNat 64 6295733, .extract { hi := 47, lo := 40, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r14)),
  (BitVec.ofNat 64 6295734, .extract { hi := 55, lo := 48, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r14)),
  (BitVec.ofNat 64 6295735, .extract { hi := 63, lo := 56, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r14)),
  (BitVec.ofNat 64 6295736, .extract { hi := 7, lo := 0, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r15)),
  (BitVec.ofNat 64 6295737, .extract { hi := 15, lo := 8, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r15)),
  (BitVec.ofNat 64 6295738, .extract { hi := 23, lo := 16, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r15)),
  (BitVec.ofNat 64 6295739, .extract { hi := 31, lo := 24, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r15)),
  (BitVec.ofNat 64 6295740, .extract { hi := 39, lo := 32, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r15)),
  (BitVec.ofNat 64 6295741, .extract { hi := 47, lo := 40, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r15)),
  (BitVec.ofNat 64 6295742, .extract { hi := 55, lo := 48, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r15)),
  (BitVec.ofNat 64 6295743, .extract { hi := 63, lo := 56, hi_lt_width := by decide, lo_le_hi := by decide } (.var v_r15))]
theorem extracted_matches_snapshot_spec : extractedWrites = expectedWrites := rfl
def storeChain {Δ : Ctx} (initial : Expr Δ (.array 64 8))
    (writes : List (BitVec 64 × Expr Δ (.bv 8))) : Expr Δ (.array 64 8) :=
  writes.foldl (fun m w => .store 64 8 m (.bvLit 64 w.1.toNat) w.2) initial
def capturedMemory : Expr Γ (.array 64 8) := storeChain (.var v_mem) extractedWrites
def captureUpdate : StateUpdate Γ Γ := (.cons capturedMemory
  (.cons (.bvLit 64 4194416)
  (.cons (.var v_rax)
  (.cons (.var v_rcx)
  (.cons (.var v_rdx)
  (.cons (.var v_rbx)
  (.cons (.var v_rsp)
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
  (.cons (.var v_rflags_CF)
  (.cons (.var v_rflags_ZF)
  (.cons (.var v_rflags_SF)
  (.cons (.var v_rflags_OF)
  (.cons (.var v_rflags_PF)
  (.cons (.var v_rflags_AF)
  .nil)))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))
def captureGuard : Expr Γ .bool := .eqBv 64 (.var v_rip) (.bvLit 64 4194304)
def captureStep : QFAbvStep Γ Γ := ⟨captureGuard, captureUpdate⟩
def model : Ayxg.LTS.QfAbv.SymbolicTransitionSystem Unit Γ Unit where
  edgeSemantics := {
    source := fun _ => ()
    symbolicLabel := fun _ => ⟨captureGuard, captureUpdate⟩
    nextControl := fun _ _ => () }
  transAt := fun _ => [()]
variable [FPInterpretation]
theorem preserves_rax (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_rax = Env.lookup s v_rax := rfl
theorem preserves_rcx (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_rcx = Env.lookup s v_rcx := rfl
theorem preserves_rdx (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_rdx = Env.lookup s v_rdx := rfl
theorem preserves_rbx (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_rbx = Env.lookup s v_rbx := rfl
theorem preserves_rsp (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_rsp = Env.lookup s v_rsp := rfl
theorem preserves_rbp (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_rbp = Env.lookup s v_rbp := rfl
theorem preserves_rsi (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_rsi = Env.lookup s v_rsi := rfl
theorem preserves_rdi (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_rdi = Env.lookup s v_rdi := rfl
theorem preserves_r8 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_r8 = Env.lookup s v_r8 := rfl
theorem preserves_r9 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_r9 = Env.lookup s v_r9 := rfl
theorem preserves_r10 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_r10 = Env.lookup s v_r10 := rfl
theorem preserves_r11 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_r11 = Env.lookup s v_r11 := rfl
theorem preserves_r12 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_r12 = Env.lookup s v_r12 := rfl
theorem preserves_r13 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_r13 = Env.lookup s v_r13 := rfl
theorem preserves_r14 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_r14 = Env.lookup s v_r14 := rfl
theorem preserves_r15 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_r15 = Env.lookup s v_r15 := rfl
theorem preserves_d (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_d = Env.lookup s v_d := rfl
theorem preserves_ac (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_ac = Env.lookup s v_ac := rfl
theorem preserves_id (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_id = Env.lookup s v_id := rfl
theorem preserves_fs (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_fs = Env.lookup s v_fs := rfl
theorem preserves_sseround (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_sseround = Env.lookup s v_sseround := rfl
theorem preserves_zmm0 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_zmm0 = Env.lookup s v_zmm0 := rfl
theorem preserves_zmm1 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_zmm1 = Env.lookup s v_zmm1 := rfl
theorem preserves_zmm2 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_zmm2 = Env.lookup s v_zmm2 := rfl
theorem preserves_zmm3 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_zmm3 = Env.lookup s v_zmm3 := rfl
theorem preserves_zmm4 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_zmm4 = Env.lookup s v_zmm4 := rfl
theorem preserves_zmm5 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_zmm5 = Env.lookup s v_zmm5 := rfl
theorem preserves_zmm6 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_zmm6 = Env.lookup s v_zmm6 := rfl
theorem preserves_zmm7 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_zmm7 = Env.lookup s v_zmm7 := rfl
theorem preserves_zmm8 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_zmm8 = Env.lookup s v_zmm8 := rfl
theorem preserves_zmm9 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_zmm9 = Env.lookup s v_zmm9 := rfl
theorem preserves_zmm10 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_zmm10 = Env.lookup s v_zmm10 := rfl
theorem preserves_zmm11 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_zmm11 = Env.lookup s v_zmm11 := rfl
theorem preserves_zmm12 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_zmm12 = Env.lookup s v_zmm12 := rfl
theorem preserves_zmm13 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_zmm13 = Env.lookup s v_zmm13 := rfl
theorem preserves_zmm14 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_zmm14 = Env.lookup s v_zmm14 := rfl
theorem preserves_zmm15 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_zmm15 = Env.lookup s v_zmm15 := rfl
theorem preserves_zmm16 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_zmm16 = Env.lookup s v_zmm16 := rfl
theorem preserves_zmm17 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_zmm17 = Env.lookup s v_zmm17 := rfl
theorem preserves_zmm18 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_zmm18 = Env.lookup s v_zmm18 := rfl
theorem preserves_zmm19 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_zmm19 = Env.lookup s v_zmm19 := rfl
theorem preserves_zmm20 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_zmm20 = Env.lookup s v_zmm20 := rfl
theorem preserves_zmm21 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_zmm21 = Env.lookup s v_zmm21 := rfl
theorem preserves_zmm22 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_zmm22 = Env.lookup s v_zmm22 := rfl
theorem preserves_zmm23 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_zmm23 = Env.lookup s v_zmm23 := rfl
theorem preserves_zmm24 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_zmm24 = Env.lookup s v_zmm24 := rfl
theorem preserves_zmm25 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_zmm25 = Env.lookup s v_zmm25 := rfl
theorem preserves_zmm26 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_zmm26 = Env.lookup s v_zmm26 := rfl
theorem preserves_zmm27 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_zmm27 = Env.lookup s v_zmm27 := rfl
theorem preserves_zmm28 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_zmm28 = Env.lookup s v_zmm28 := rfl
theorem preserves_zmm29 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_zmm29 = Env.lookup s v_zmm29 := rfl
theorem preserves_zmm30 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_zmm30 = Env.lookup s v_zmm30 := rfl
theorem preserves_zmm31 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_zmm31 = Env.lookup s v_zmm31 := rfl
theorem preserves_k0 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_k0 = Env.lookup s v_k0 := rfl
theorem preserves_k1 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_k1 = Env.lookup s v_k1 := rfl
theorem preserves_k2 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_k2 = Env.lookup s v_k2 := rfl
theorem preserves_k3 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_k3 = Env.lookup s v_k3 := rfl
theorem preserves_k4 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_k4 = Env.lookup s v_k4 := rfl
theorem preserves_k5 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_k5 = Env.lookup s v_k5 := rfl
theorem preserves_k6 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_k6 = Env.lookup s v_k6 := rfl
theorem preserves_k7 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_k7 = Env.lookup s v_k7 := rfl
theorem preserves_ftop (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_ftop = Env.lookup s v_ftop := rfl
theorem preserves_fpreg (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_fpreg = Env.lookup s v_fpreg := rfl
theorem preserves_fptag (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_fptag = Env.lookup s v_fptag := rfl
theorem preserves_fpround (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_fpround = Env.lookup s v_fpround := rfl
theorem preserves_fc3210 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_fc3210 = Env.lookup s v_fc3210 := rfl
theorem preserves_emnote (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_emnote = Env.lookup s v_emnote := rfl
theorem preserves_cmstart (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_cmstart = Env.lookup s v_cmstart := rfl
theorem preserves_cmlen (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_cmlen = Env.lookup s v_cmlen := rfl
theorem preserves_nraddr (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_nraddr = Env.lookup s v_nraddr := rfl
theorem preserves_gs (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_gs = Env.lookup s v_gs := rfl
theorem preserves_ip_at_syscall (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_ip_at_syscall = Env.lookup s v_ip_at_syscall := rfl
theorem preserves_cs_seg (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_cs_seg = Env.lookup s v_cs_seg := rfl
theorem preserves_ds_seg (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_ds_seg = Env.lookup s v_ds_seg := rfl
theorem preserves_es_seg (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_es_seg = Env.lookup s v_es_seg := rfl
theorem preserves_fs_seg (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_fs_seg = Env.lookup s v_fs_seg := rfl
theorem preserves_gs_seg (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_gs_seg = Env.lookup s v_gs_seg := rfl
theorem preserves_ss_seg (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_ss_seg = Env.lookup s v_ss_seg := rfl
theorem preserves_cr0 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_cr0 = Env.lookup s v_cr0 := rfl
theorem preserves_cr2 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_cr2 = Env.lookup s v_cr2 := rfl
theorem preserves_cr3 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_cr3 = Env.lookup s v_cr3 := rfl
theorem preserves_cr4 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_cr4 = Env.lookup s v_cr4 := rfl
theorem preserves_cr8 (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_cr8 = Env.lookup s v_cr8 := rfl
theorem preserves_rflags_CF (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_rflags_CF = Env.lookup s v_rflags_CF := rfl
theorem preserves_rflags_ZF (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_rflags_ZF = Env.lookup s v_rflags_ZF := rfl
theorem preserves_rflags_SF (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_rflags_SF = Env.lookup s v_rflags_SF := rfl
theorem preserves_rflags_OF (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_rflags_OF = Env.lookup s v_rflags_OF := rfl
theorem preserves_rflags_PF (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_rflags_PF = Env.lookup s v_rflags_PF := rfl
theorem preserves_rflags_AF (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_rflags_AF = Env.lookup s v_rflags_AF := rfl
theorem final_pc (s : Env Γ) :
    Env.lookup (captureUpdate.eval s) v_rip = BitVec.ofNat 64 4194416 := rfl
end MovObserver
