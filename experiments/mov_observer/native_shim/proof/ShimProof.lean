import ShimModel
import ByteCodec
set_option maxRecDepth 32768
set_option maxHeartbeats 8000000
namespace MovObserver.Shim
open Ayxg.QfAbv
variable [FPInterpretation]

/-- The six SysV callee-saved GPRs; RSP is specified separately across ret. -/
def calleeSaved (s : Env Γ) : List (BitVec 64) :=
  [s.lookup v_rbx, s.lookup v_rbp, s.lookup v_r12, s.lookup v_r13,
   s.lookup v_r14, s.lookup v_r15]

theorem prefix_callee (s : Env Γ) : calleeSaved (prefixUpdate.eval s) = calleeSaved s := rfl
theorem suffix_callee (s : Env Γ) : calleeSaved (suffixUpdate.eval s) = calleeSaved s := rfl

omit [FPInterpretation] in
private theorem minus32 (sp : BitVec 64) : 18446744073709551584#64 + sp = sp - 32 := by bv_decide
omit [FPInterpretation] in
private theorem minus16 (sp : BitVec 64) : 18446744073709551600#64 + sp = sp - 16 := by bv_decide

/-- Exact register setup before syscall. PID bits are retained, not assumed
zero-extended; the kernel pid interpretation uses their low 32 bits. -/
theorem syscall_arguments (s : Env Γ) :
    let k := prefixUpdate.eval s
    k.lookup v_rax = 311 ∧ k.lookup v_rdi = s.lookup v_rdi ∧
    k.lookup v_rsi = s.lookup v_rsp - 32 ∧ k.lookup v_rdx = 1 ∧
    k.lookup v_r10 = s.lookup v_rsp - 16 ∧ k.lookup v_r8 = 1 ∧
    k.lookup v_r9 = 0 ∧ k.lookup v_rsp = s.lookup v_rsp - 32 ∧
    k.lookup v_rip = 0x40003a := by
  change _ = _ ∧ _ = _ ∧ (18446744073709551584#64 + s.lookup v_rsp) = _ ∧
    _ = _ ∧ (18446744073709551600#64 + s.lookup v_rsp) = _ ∧ _ = _ ∧ _ = _ ∧
    (18446744073709551584#64 + s.lookup v_rsp) = _ ∧ _ = _
  exact ⟨rfl, rfl, minus32 _, rfl, minus16 _, rfl, rfl, minus32 _, rfl⟩

def applyDynamic (s : Env Γ) : List (Expr Γ (.bv 64) × Expr Γ (.bv 8)) → Mem 64 8 → Mem 64 8
  | [], m => m
  | w :: ws, m => applyDynamic s ws (Eval.memStore m (Eval.eval s w.1) (Eval.eval s w.2))

theorem dynamic_frame (s : Env Γ) (ws : List (Expr Γ (.bv 64) × Expr Γ (.bv 8)))
    (m : Mem 64 8) (a : BitVec 64)
    (outside : ∀ w ∈ ws, a ≠ Eval.eval s w.1) : applyDynamic s ws m a = m a := by
  induction ws generalizing m with
  | nil => rfl
  | cons w ws ih =>
    change applyDynamic s ws (Eval.memStore m (Eval.eval s w.1) (Eval.eval s w.2)) a = _
    rw [ih _ (fun b hb => outside b (List.mem_cons_of_mem _ hb))]
    exact if_neg (outside w (by simp))

theorem prefix_memory (s : Env Γ) :
    (prefixUpdate.eval s).lookup v_mem = applyDynamic s prefixWrites (s.lookup v_mem) := rfl

theorem prefix_frame (s : Env Γ) (a : BitVec 64)
    (outside : ∀ w ∈ prefixWrites, a ≠ Eval.eval s w.1) :
    (prefixUpdate.eval s).lookup v_mem a = s.lookup v_mem a := by
  rw [prefix_memory]; exact dynamic_frame s prefixWrites _ a outside

theorem suffix_memory (s : Env Γ) : (suffixUpdate.eval s).lookup v_mem = s.lookup v_mem := rfl
theorem suffix_result (s : Env Γ) : (suffixUpdate.eval s).lookup v_rax = s.lookup v_rax := rfl

theorem suffix_stack (s : Env Γ) :
    (suffixUpdate.eval s).lookup v_rsp = s.lookup v_rsp + 40 := by
  change 40#64 + s.lookup v_rsp = _
  exact BitVec.add_comm _ _



/-- Independent 32-byte stack footprint, with modular addresses. -/
def frameAddress (sp : BitVec 64) (i : Nat) : BitVec 64 :=
  BitVec.ofNat 64 (2^64 - 32 + i) + sp

theorem writes_in_frame (s : Env Γ) (w : Expr Γ (.bv 64) × Expr Γ (.bv 8))
    (hw : w ∈ prefixWrites) : ∃ i : Fin 32, Eval.eval s w.1 = frameAddress (s.lookup v_rsp) i.val := by
  simp only [prefixWrites, List.mem_cons, List.not_mem_nil, or_false] at hw
  rcases hw with rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl
  · exact ⟨⟨16, by decide⟩, rfl⟩
  · exact ⟨⟨17, by decide⟩, rfl⟩
  · exact ⟨⟨18, by decide⟩, rfl⟩
  · exact ⟨⟨19, by decide⟩, rfl⟩
  · exact ⟨⟨20, by decide⟩, rfl⟩
  · exact ⟨⟨21, by decide⟩, rfl⟩
  · exact ⟨⟨22, by decide⟩, rfl⟩
  · exact ⟨⟨23, by decide⟩, rfl⟩
  · exact ⟨⟨0, by decide⟩, rfl⟩
  · exact ⟨⟨1, by decide⟩, rfl⟩
  · exact ⟨⟨2, by decide⟩, rfl⟩
  · exact ⟨⟨3, by decide⟩, rfl⟩
  · exact ⟨⟨4, by decide⟩, rfl⟩
  · exact ⟨⟨5, by decide⟩, rfl⟩
  · exact ⟨⟨6, by decide⟩, rfl⟩
  · exact ⟨⟨7, by decide⟩, rfl⟩
  · exact ⟨⟨8, by decide⟩, rfl⟩
  · exact ⟨⟨9, by decide⟩, rfl⟩
  · exact ⟨⟨10, by decide⟩, rfl⟩
  · exact ⟨⟨11, by decide⟩, rfl⟩
  · exact ⟨⟨12, by decide⟩, rfl⟩
  · exact ⟨⟨13, by decide⟩, rfl⟩
  · exact ⟨⟨14, by decide⟩, rfl⟩
  · exact ⟨⟨15, by decide⟩, rfl⟩
  · exact ⟨⟨24, by decide⟩, rfl⟩
  · exact ⟨⟨25, by decide⟩, rfl⟩
  · exact ⟨⟨26, by decide⟩, rfl⟩
  · exact ⟨⟨27, by decide⟩, rfl⟩
  · exact ⟨⟨28, by decide⟩, rfl⟩
  · exact ⟨⟨29, by decide⟩, rfl⟩
  · exact ⟨⟨30, by decide⟩, rfl⟩
  · exact ⟨⟨31, by decide⟩, rfl⟩

theorem prefix_stack_frame (s : Env Γ) (a : BitVec 64)
    (outside : ∀ i : Fin 32, a ≠ frameAddress (s.lookup v_rsp) i.val) :
    (prefixUpdate.eval s).lookup v_mem a = s.lookup v_mem a := by
  apply prefix_frame s a
  intro w hw
  obtain ⟨i, eq⟩ := writes_in_frame s w hw
  rw [eq]; exact outside i

omit [FPInterpretation] in
private theorem add_cancel (a b c : BitVec 64) : a + c = b + c ↔ a = b := by bv_decide

theorem write_addresses_unique (s : Env Γ) :
    (prefixWrites.map (fun w => Eval.eval s w.1)).Nodup := by
  change [(18446744073709551600#64 + s.lookup v_rsp), (18446744073709551601#64 + s.lookup v_rsp), (18446744073709551602#64 + s.lookup v_rsp), (18446744073709551603#64 + s.lookup v_rsp), (18446744073709551604#64 + s.lookup v_rsp), (18446744073709551605#64 + s.lookup v_rsp), (18446744073709551606#64 + s.lookup v_rsp), (18446744073709551607#64 + s.lookup v_rsp), (18446744073709551584#64 + s.lookup v_rsp), (18446744073709551585#64 + s.lookup v_rsp), (18446744073709551586#64 + s.lookup v_rsp), (18446744073709551587#64 + s.lookup v_rsp), (18446744073709551588#64 + s.lookup v_rsp), (18446744073709551589#64 + s.lookup v_rsp), (18446744073709551590#64 + s.lookup v_rsp), (18446744073709551591#64 + s.lookup v_rsp), (18446744073709551592#64 + s.lookup v_rsp), (18446744073709551593#64 + s.lookup v_rsp), (18446744073709551594#64 + s.lookup v_rsp), (18446744073709551595#64 + s.lookup v_rsp), (18446744073709551596#64 + s.lookup v_rsp), (18446744073709551597#64 + s.lookup v_rsp), (18446744073709551598#64 + s.lookup v_rsp), (18446744073709551599#64 + s.lookup v_rsp), (18446744073709551608#64 + s.lookup v_rsp), (18446744073709551609#64 + s.lookup v_rsp), (18446744073709551610#64 + s.lookup v_rsp), (18446744073709551611#64 + s.lookup v_rsp), (18446744073709551612#64 + s.lookup v_rsp), (18446744073709551613#64 + s.lookup v_rsp), (18446744073709551614#64 + s.lookup v_rsp), (18446744073709551615#64 + s.lookup v_rsp)].Nodup
  simp only [List.nodup_cons, List.mem_cons, List.not_mem_nil, List.nodup_nil, add_cancel]
  simp

theorem dynamic_capture (s : Env Γ) (ws : List (Expr Γ (.bv 64) × Expr Γ (.bv 8)))
    (m : Mem 64 8) (w : Expr Γ (.bv 64) × Expr Γ (.bv 8))
    (distinct : (ws.map (fun w => Eval.eval s w.1)).Nodup) (member : w ∈ ws) :
    applyDynamic s ws m (Eval.eval s w.1) = Eval.eval s w.2 := by
  induction ws generalizing m with
  | nil => simp at member
  | cons head tail ih =>
    have parts := List.nodup_cons.mp distinct
    rcases List.mem_cons.mp member with same | later
    · subst w
      change applyDynamic s tail (Eval.memStore m (Eval.eval s head.1) (Eval.eval s head.2)) _ = _
      rw [dynamic_frame]
      · simp [Eval.memStore]
      · intro v hv eq
        exact parts.1 (List.mem_map.mpr ⟨v, hv, eq.symm⟩)
    · exact ih _ parts.2 later

/-- The actual model's memory at the size load, after the first 16 byte stores. -/
theorem memory_at_size_read (s : Env Γ) :
    Eval.eval s e77 = applyDynamic s (prefixWrites.take 16) (s.lookup v_mem) := rfl

/-- Only the length field must avoid the stack writes before its read.
Payload/whole-object preservation follows separately from the full frame. -/
def SizeFieldSeparate (s : Env Γ) : Prop :=
  ∀ i : Fin 8, ∀ j : Fin 32,
    (BitVec.ofNat 64 (8+i.val) + s.lookup v_rdx) ≠ frameAddress (s.lookup v_rsp) j.val

theorem size_read_original (s : Env Γ) (h : SizeFieldSeparate s) (i : Fin 8) :
    Eval.eval s e77 (BitVec.ofNat 64 (8+i.val) + s.lookup v_rdx) =
      s.lookup v_mem (BitVec.ofNat 64 (8+i.val) + s.lookup v_rdx) := by
  rw [memory_at_size_read]
  apply dynamic_frame
  intro w hw
  obtain ⟨j, eq⟩ := writes_in_frame s w (List.mem_of_mem_take hw)
  rw [eq]; exact h i j

theorem descriptor_byte_16 (s : Env Γ) (h : SizeFieldSeparate s) :
    (prefixUpdate.eval s).lookup v_mem (frameAddress (s.lookup v_rsp) 16) = BitVec.extractLsb 7 0 (s.lookup v_rsi) := by
  rw [prefix_memory]
  have cap := dynamic_capture s prefixWrites (s.lookup v_mem) (e7, e13)
    (write_addresses_unique s) (by simp [prefixWrites])
  change applyDynamic s prefixWrites (s.lookup v_mem) (Eval.eval s e7) = _
  rw [cap]
  rfl

theorem descriptor_byte_17 (s : Env Γ) (h : SizeFieldSeparate s) :
    (prefixUpdate.eval s).lookup v_mem (frameAddress (s.lookup v_rsp) 17) = BitVec.extractLsb 15 8 (s.lookup v_rsi) := by
  rw [prefix_memory]
  have cap := dynamic_capture s prefixWrites (s.lookup v_mem) (e16, e17)
    (write_addresses_unique s) (by simp [prefixWrites])
  change applyDynamic s prefixWrites (s.lookup v_mem) (Eval.eval s e16) = _
  rw [cap]
  rfl

theorem descriptor_byte_18 (s : Env Γ) (h : SizeFieldSeparate s) :
    (prefixUpdate.eval s).lookup v_mem (frameAddress (s.lookup v_rsp) 18) = BitVec.extractLsb 23 16 (s.lookup v_rsi) := by
  rw [prefix_memory]
  have cap := dynamic_capture s prefixWrites (s.lookup v_mem) (e20, e21)
    (write_addresses_unique s) (by simp [prefixWrites])
  change applyDynamic s prefixWrites (s.lookup v_mem) (Eval.eval s e20) = _
  rw [cap]
  rfl

theorem descriptor_byte_19 (s : Env Γ) (h : SizeFieldSeparate s) :
    (prefixUpdate.eval s).lookup v_mem (frameAddress (s.lookup v_rsp) 19) = BitVec.extractLsb 31 24 (s.lookup v_rsi) := by
  rw [prefix_memory]
  have cap := dynamic_capture s prefixWrites (s.lookup v_mem) (e24, e25)
    (write_addresses_unique s) (by simp [prefixWrites])
  change applyDynamic s prefixWrites (s.lookup v_mem) (Eval.eval s e24) = _
  rw [cap]
  rfl

theorem descriptor_byte_20 (s : Env Γ) (h : SizeFieldSeparate s) :
    (prefixUpdate.eval s).lookup v_mem (frameAddress (s.lookup v_rsp) 20) = BitVec.extractLsb 39 32 (s.lookup v_rsi) := by
  rw [prefix_memory]
  have cap := dynamic_capture s prefixWrites (s.lookup v_mem) (e28, e29)
    (write_addresses_unique s) (by simp [prefixWrites])
  change applyDynamic s prefixWrites (s.lookup v_mem) (Eval.eval s e28) = _
  rw [cap]
  rfl

theorem descriptor_byte_21 (s : Env Γ) (h : SizeFieldSeparate s) :
    (prefixUpdate.eval s).lookup v_mem (frameAddress (s.lookup v_rsp) 21) = BitVec.extractLsb 47 40 (s.lookup v_rsi) := by
  rw [prefix_memory]
  have cap := dynamic_capture s prefixWrites (s.lookup v_mem) (e32, e33)
    (write_addresses_unique s) (by simp [prefixWrites])
  change applyDynamic s prefixWrites (s.lookup v_mem) (Eval.eval s e32) = _
  rw [cap]
  rfl

theorem descriptor_byte_22 (s : Env Γ) (h : SizeFieldSeparate s) :
    (prefixUpdate.eval s).lookup v_mem (frameAddress (s.lookup v_rsp) 22) = BitVec.extractLsb 55 48 (s.lookup v_rsi) := by
  rw [prefix_memory]
  have cap := dynamic_capture s prefixWrites (s.lookup v_mem) (e36, e37)
    (write_addresses_unique s) (by simp [prefixWrites])
  change applyDynamic s prefixWrites (s.lookup v_mem) (Eval.eval s e36) = _
  rw [cap]
  rfl

theorem descriptor_byte_23 (s : Env Γ) (h : SizeFieldSeparate s) :
    (prefixUpdate.eval s).lookup v_mem (frameAddress (s.lookup v_rsp) 23) = BitVec.extractLsb 63 56 (s.lookup v_rsi) := by
  rw [prefix_memory]
  have cap := dynamic_capture s prefixWrites (s.lookup v_mem) (e40, e41)
    (write_addresses_unique s) (by simp [prefixWrites])
  change applyDynamic s prefixWrites (s.lookup v_mem) (Eval.eval s e40) = _
  rw [cap]
  rfl

theorem descriptor_byte_0 (s : Env Γ) (h : SizeFieldSeparate s) :
    (prefixUpdate.eval s).lookup v_mem (frameAddress (s.lookup v_rsp) 0) = BitVec.extractLsb 7 0 (24#64 + s.lookup v_rdx) := by
  rw [prefix_memory]
  have cap := dynamic_capture s prefixWrites (s.lookup v_mem) (e4, e46)
    (write_addresses_unique s) (by simp [prefixWrites])
  change applyDynamic s prefixWrites (s.lookup v_mem) (Eval.eval s e4) = _
  rw [cap]
  change (24#8 + BitVec.extractLsb 7 0 (s.lookup v_rdx)) = BitVec.extractLsb 7 0 (24#64 + s.lookup v_rdx)
  bv_decide

theorem descriptor_byte_1 (s : Env Γ) (h : SizeFieldSeparate s) :
    (prefixUpdate.eval s).lookup v_mem (frameAddress (s.lookup v_rsp) 1) = BitVec.extractLsb 15 8 (24#64 + s.lookup v_rdx) := by
  rw [prefix_memory]
  have cap := dynamic_capture s prefixWrites (s.lookup v_mem) (e49, e52)
    (write_addresses_unique s) (by simp [prefixWrites])
  change applyDynamic s prefixWrites (s.lookup v_mem) (Eval.eval s e49) = _
  rw [cap]
  change BitVec.extractLsb 15 8 (24#64 + s.lookup v_rdx) = BitVec.extractLsb 15 8 (24#64 + s.lookup v_rdx)
  rfl

theorem descriptor_byte_2 (s : Env Γ) (h : SizeFieldSeparate s) :
    (prefixUpdate.eval s).lookup v_mem (frameAddress (s.lookup v_rsp) 2) = BitVec.extractLsb 23 16 (24#64 + s.lookup v_rdx) := by
  rw [prefix_memory]
  have cap := dynamic_capture s prefixWrites (s.lookup v_mem) (e55, e56)
    (write_addresses_unique s) (by simp [prefixWrites])
  change applyDynamic s prefixWrites (s.lookup v_mem) (Eval.eval s e55) = _
  rw [cap]
  change BitVec.extractLsb 23 16 (24#64 + s.lookup v_rdx) = BitVec.extractLsb 23 16 (24#64 + s.lookup v_rdx)
  rfl

theorem descriptor_byte_3 (s : Env Γ) (h : SizeFieldSeparate s) :
    (prefixUpdate.eval s).lookup v_mem (frameAddress (s.lookup v_rsp) 3) = BitVec.extractLsb 31 24 (24#64 + s.lookup v_rdx) := by
  rw [prefix_memory]
  have cap := dynamic_capture s prefixWrites (s.lookup v_mem) (e59, e60)
    (write_addresses_unique s) (by simp [prefixWrites])
  change applyDynamic s prefixWrites (s.lookup v_mem) (Eval.eval s e59) = _
  rw [cap]
  change BitVec.extractLsb 31 24 (24#64 + s.lookup v_rdx) = BitVec.extractLsb 31 24 (24#64 + s.lookup v_rdx)
  rfl

theorem descriptor_byte_4 (s : Env Γ) (h : SizeFieldSeparate s) :
    (prefixUpdate.eval s).lookup v_mem (frameAddress (s.lookup v_rsp) 4) = BitVec.extractLsb 39 32 (24#64 + s.lookup v_rdx) := by
  rw [prefix_memory]
  have cap := dynamic_capture s prefixWrites (s.lookup v_mem) (e63, e64)
    (write_addresses_unique s) (by simp [prefixWrites])
  change applyDynamic s prefixWrites (s.lookup v_mem) (Eval.eval s e63) = _
  rw [cap]
  change BitVec.extractLsb 39 32 (24#64 + s.lookup v_rdx) = BitVec.extractLsb 39 32 (24#64 + s.lookup v_rdx)
  rfl

theorem descriptor_byte_5 (s : Env Γ) (h : SizeFieldSeparate s) :
    (prefixUpdate.eval s).lookup v_mem (frameAddress (s.lookup v_rsp) 5) = BitVec.extractLsb 47 40 (24#64 + s.lookup v_rdx) := by
  rw [prefix_memory]
  have cap := dynamic_capture s prefixWrites (s.lookup v_mem) (e67, e68)
    (write_addresses_unique s) (by simp [prefixWrites])
  change applyDynamic s prefixWrites (s.lookup v_mem) (Eval.eval s e67) = _
  rw [cap]
  change BitVec.extractLsb 47 40 (24#64 + s.lookup v_rdx) = BitVec.extractLsb 47 40 (24#64 + s.lookup v_rdx)
  rfl

theorem descriptor_byte_6 (s : Env Γ) (h : SizeFieldSeparate s) :
    (prefixUpdate.eval s).lookup v_mem (frameAddress (s.lookup v_rsp) 6) = BitVec.extractLsb 55 48 (24#64 + s.lookup v_rdx) := by
  rw [prefix_memory]
  have cap := dynamic_capture s prefixWrites (s.lookup v_mem) (e71, e72)
    (write_addresses_unique s) (by simp [prefixWrites])
  change applyDynamic s prefixWrites (s.lookup v_mem) (Eval.eval s e71) = _
  rw [cap]
  change BitVec.extractLsb 55 48 (24#64 + s.lookup v_rdx) = BitVec.extractLsb 55 48 (24#64 + s.lookup v_rdx)
  rfl

theorem descriptor_byte_7 (s : Env Γ) (h : SizeFieldSeparate s) :
    (prefixUpdate.eval s).lookup v_mem (frameAddress (s.lookup v_rsp) 7) = BitVec.extractLsb 63 56 (24#64 + s.lookup v_rdx) := by
  rw [prefix_memory]
  have cap := dynamic_capture s prefixWrites (s.lookup v_mem) (e75, e76)
    (write_addresses_unique s) (by simp [prefixWrites])
  change applyDynamic s prefixWrites (s.lookup v_mem) (Eval.eval s e75) = _
  rw [cap]
  change BitVec.extractLsb 63 56 (24#64 + s.lookup v_rdx) = BitVec.extractLsb 63 56 (24#64 + s.lookup v_rdx)
  rfl

theorem descriptor_byte_8 (s : Env Γ) (h : SizeFieldSeparate s) :
    (prefixUpdate.eval s).lookup v_mem (frameAddress (s.lookup v_rsp) 8) = s.lookup v_mem (8#64 + s.lookup v_rdx) := by
  rw [prefix_memory]
  have cap := dynamic_capture s prefixWrites (s.lookup v_mem) (e79, e82)
    (write_addresses_unique s) (by simp [prefixWrites])
  change applyDynamic s prefixWrites (s.lookup v_mem) (Eval.eval s e79) = _
  rw [cap]
  exact size_read_original s h ⟨0, by decide⟩

theorem descriptor_byte_9 (s : Env Γ) (h : SizeFieldSeparate s) :
    (prefixUpdate.eval s).lookup v_mem (frameAddress (s.lookup v_rsp) 9) = s.lookup v_mem (9#64 + s.lookup v_rdx) := by
  rw [prefix_memory]
  have cap := dynamic_capture s prefixWrites (s.lookup v_mem) (e85, e88)
    (write_addresses_unique s) (by simp [prefixWrites])
  change applyDynamic s prefixWrites (s.lookup v_mem) (Eval.eval s e85) = _
  rw [cap]
  exact size_read_original s h ⟨1, by decide⟩

theorem descriptor_byte_10 (s : Env Γ) (h : SizeFieldSeparate s) :
    (prefixUpdate.eval s).lookup v_mem (frameAddress (s.lookup v_rsp) 10) = s.lookup v_mem (10#64 + s.lookup v_rdx) := by
  rw [prefix_memory]
  have cap := dynamic_capture s prefixWrites (s.lookup v_mem) (e91, e94)
    (write_addresses_unique s) (by simp [prefixWrites])
  change applyDynamic s prefixWrites (s.lookup v_mem) (Eval.eval s e91) = _
  rw [cap]
  exact size_read_original s h ⟨2, by decide⟩

theorem descriptor_byte_11 (s : Env Γ) (h : SizeFieldSeparate s) :
    (prefixUpdate.eval s).lookup v_mem (frameAddress (s.lookup v_rsp) 11) = s.lookup v_mem (11#64 + s.lookup v_rdx) := by
  rw [prefix_memory]
  have cap := dynamic_capture s prefixWrites (s.lookup v_mem) (e97, e100)
    (write_addresses_unique s) (by simp [prefixWrites])
  change applyDynamic s prefixWrites (s.lookup v_mem) (Eval.eval s e97) = _
  rw [cap]
  exact size_read_original s h ⟨3, by decide⟩

theorem descriptor_byte_12 (s : Env Γ) (h : SizeFieldSeparate s) :
    (prefixUpdate.eval s).lookup v_mem (frameAddress (s.lookup v_rsp) 12) = s.lookup v_mem (12#64 + s.lookup v_rdx) := by
  rw [prefix_memory]
  have cap := dynamic_capture s prefixWrites (s.lookup v_mem) (e103, e106)
    (write_addresses_unique s) (by simp [prefixWrites])
  change applyDynamic s prefixWrites (s.lookup v_mem) (Eval.eval s e103) = _
  rw [cap]
  exact size_read_original s h ⟨4, by decide⟩

theorem descriptor_byte_13 (s : Env Γ) (h : SizeFieldSeparate s) :
    (prefixUpdate.eval s).lookup v_mem (frameAddress (s.lookup v_rsp) 13) = s.lookup v_mem (13#64 + s.lookup v_rdx) := by
  rw [prefix_memory]
  have cap := dynamic_capture s prefixWrites (s.lookup v_mem) (e109, e112)
    (write_addresses_unique s) (by simp [prefixWrites])
  change applyDynamic s prefixWrites (s.lookup v_mem) (Eval.eval s e109) = _
  rw [cap]
  exact size_read_original s h ⟨5, by decide⟩

theorem descriptor_byte_14 (s : Env Γ) (h : SizeFieldSeparate s) :
    (prefixUpdate.eval s).lookup v_mem (frameAddress (s.lookup v_rsp) 14) = s.lookup v_mem (14#64 + s.lookup v_rdx) := by
  rw [prefix_memory]
  have cap := dynamic_capture s prefixWrites (s.lookup v_mem) (e115, e118)
    (write_addresses_unique s) (by simp [prefixWrites])
  change applyDynamic s prefixWrites (s.lookup v_mem) (Eval.eval s e115) = _
  rw [cap]
  exact size_read_original s h ⟨6, by decide⟩

theorem descriptor_byte_15 (s : Env Γ) (h : SizeFieldSeparate s) :
    (prefixUpdate.eval s).lookup v_mem (frameAddress (s.lookup v_rsp) 15) = s.lookup v_mem (15#64 + s.lookup v_rdx) := by
  rw [prefix_memory]
  have cap := dynamic_capture s prefixWrites (s.lookup v_mem) (e121, e124)
    (write_addresses_unique s) (by simp [prefixWrites])
  change applyDynamic s prefixWrites (s.lookup v_mem) (Eval.eval s e121) = _
  rw [cap]
  exact size_read_original s h ⟨7, by decide⟩

theorem descriptor_byte_24 (s : Env Γ) (h : SizeFieldSeparate s) :
    (prefixUpdate.eval s).lookup v_mem (frameAddress (s.lookup v_rsp) 24) = s.lookup v_mem (8#64 + s.lookup v_rdx) := by
  rw [prefix_memory]
  have cap := dynamic_capture s prefixWrites (s.lookup v_mem) (e127, e82)
    (write_addresses_unique s) (by simp [prefixWrites])
  change applyDynamic s prefixWrites (s.lookup v_mem) (Eval.eval s e127) = _
  rw [cap]
  exact size_read_original s h ⟨0, by decide⟩

theorem descriptor_byte_25 (s : Env Γ) (h : SizeFieldSeparate s) :
    (prefixUpdate.eval s).lookup v_mem (frameAddress (s.lookup v_rsp) 25) = s.lookup v_mem (9#64 + s.lookup v_rdx) := by
  rw [prefix_memory]
  have cap := dynamic_capture s prefixWrites (s.lookup v_mem) (e130, e88)
    (write_addresses_unique s) (by simp [prefixWrites])
  change applyDynamic s prefixWrites (s.lookup v_mem) (Eval.eval s e130) = _
  rw [cap]
  exact size_read_original s h ⟨1, by decide⟩

theorem descriptor_byte_26 (s : Env Γ) (h : SizeFieldSeparate s) :
    (prefixUpdate.eval s).lookup v_mem (frameAddress (s.lookup v_rsp) 26) = s.lookup v_mem (10#64 + s.lookup v_rdx) := by
  rw [prefix_memory]
  have cap := dynamic_capture s prefixWrites (s.lookup v_mem) (e133, e94)
    (write_addresses_unique s) (by simp [prefixWrites])
  change applyDynamic s prefixWrites (s.lookup v_mem) (Eval.eval s e133) = _
  rw [cap]
  exact size_read_original s h ⟨2, by decide⟩

theorem descriptor_byte_27 (s : Env Γ) (h : SizeFieldSeparate s) :
    (prefixUpdate.eval s).lookup v_mem (frameAddress (s.lookup v_rsp) 27) = s.lookup v_mem (11#64 + s.lookup v_rdx) := by
  rw [prefix_memory]
  have cap := dynamic_capture s prefixWrites (s.lookup v_mem) (e136, e100)
    (write_addresses_unique s) (by simp [prefixWrites])
  change applyDynamic s prefixWrites (s.lookup v_mem) (Eval.eval s e136) = _
  rw [cap]
  exact size_read_original s h ⟨3, by decide⟩

theorem descriptor_byte_28 (s : Env Γ) (h : SizeFieldSeparate s) :
    (prefixUpdate.eval s).lookup v_mem (frameAddress (s.lookup v_rsp) 28) = s.lookup v_mem (12#64 + s.lookup v_rdx) := by
  rw [prefix_memory]
  have cap := dynamic_capture s prefixWrites (s.lookup v_mem) (e139, e106)
    (write_addresses_unique s) (by simp [prefixWrites])
  change applyDynamic s prefixWrites (s.lookup v_mem) (Eval.eval s e139) = _
  rw [cap]
  exact size_read_original s h ⟨4, by decide⟩

theorem descriptor_byte_29 (s : Env Γ) (h : SizeFieldSeparate s) :
    (prefixUpdate.eval s).lookup v_mem (frameAddress (s.lookup v_rsp) 29) = s.lookup v_mem (13#64 + s.lookup v_rdx) := by
  rw [prefix_memory]
  have cap := dynamic_capture s prefixWrites (s.lookup v_mem) (e142, e112)
    (write_addresses_unique s) (by simp [prefixWrites])
  change applyDynamic s prefixWrites (s.lookup v_mem) (Eval.eval s e142) = _
  rw [cap]
  exact size_read_original s h ⟨5, by decide⟩

theorem descriptor_byte_30 (s : Env Γ) (h : SizeFieldSeparate s) :
    (prefixUpdate.eval s).lookup v_mem (frameAddress (s.lookup v_rsp) 30) = s.lookup v_mem (14#64 + s.lookup v_rdx) := by
  rw [prefix_memory]
  have cap := dynamic_capture s prefixWrites (s.lookup v_mem) (e145, e118)
    (write_addresses_unique s) (by simp [prefixWrites])
  change applyDynamic s prefixWrites (s.lookup v_mem) (Eval.eval s e145) = _
  rw [cap]
  exact size_read_original s h ⟨6, by decide⟩

theorem descriptor_byte_31 (s : Env Γ) (h : SizeFieldSeparate s) :
    (prefixUpdate.eval s).lookup v_mem (frameAddress (s.lookup v_rsp) 31) = s.lookup v_mem (15#64 + s.lookup v_rdx) := by
  rw [prefix_memory]
  have cap := dynamic_capture s prefixWrites (s.lookup v_mem) (e148, e124)
    (write_addresses_unique s) (by simp [prefixWrites])
  change applyDynamic s prefixWrites (s.lookup v_mem) (Eval.eval s e148) = _
  rw [cap]
  exact size_read_original s h ⟨7, by decide⟩



/-- Little-endian word at base+offset; arithmetic remains bitvector/modular. -/
def readWordAt (memory : Mem 64 8) (base : BitVec 64) (offset : Nat) : BitVec 64 :=
  (((((((memory (BitVec.ofNat 64 (offset+7) + base) ++ memory (BitVec.ofNat 64 (offset+6) + base)) ++ memory (BitVec.ofNat 64 (offset+5) + base)) ++ memory (BitVec.ofNat 64 (offset+4) + base)) ++ memory (BitVec.ofNat 64 (offset+3) + base)) ++ memory (BitVec.ofNat 64 (offset+2) + base)) ++ memory (BitVec.ofNat 64 (offset+1) + base)) ++ memory (BitVec.ofNat 64 (offset+0) + base))

theorem suffix_return (s : Env Γ) :
    (suffixUpdate.eval s).lookup v_rip = readWordAt (s.lookup v_mem) (s.lookup v_rsp) 32 := rfl

/-- Only these modeled fields may change across the whole shim. This retains
all other model fields, including direction, FP control and vector state. -/
def clobbered : List (Σ t : TermSort, Var Γ t) :=
  [⟨_, v_mem⟩, ⟨_, v_rax⟩, ⟨_, v_rcx⟩, ⟨_, v_rdx⟩, ⟨_, v_rsp⟩, ⟨_, v_rsi⟩, ⟨_, v_rdi⟩, ⟨_, v_r8⟩, ⟨_, v_r9⟩, ⟨_, v_r10⟩, ⟨_, v_r11⟩, ⟨_, v_rip⟩, ⟨_, v_rflags_CF⟩, ⟨_, v_rflags_PF⟩, ⟨_, v_rflags_AF⟩, ⟨_, v_rflags_ZF⟩, ⟨_, v_rflags_SF⟩, ⟨_, v_rflags_OF⟩]

set_option maxHeartbeats 4000000 in
theorem prefix_other (s : Env Γ) (t : TermSort) (v : Var Γ t)
    (outside : (⟨t,v⟩ : Σ t, Var Γ t) ∉ clobbered) :
    (prefixUpdate.eval s).lookup v = s.lookup v := by
  repeat (first
    | rfl
    | (solve | apply False.elim; apply outside; simp [clobbered, v_mem, v_rax, v_rcx, v_rdx, v_rsp, v_rsi, v_rdi, v_r8, v_r9, v_r10, v_r11, v_rip, v_rflags_CF, v_rflags_PF, v_rflags_AF, v_rflags_ZF, v_rflags_SF, v_rflags_OF])
    | cases ‹Var _ _›)

set_option maxHeartbeats 4000000 in
theorem suffix_other (s : Env Γ) (t : TermSort) (v : Var Γ t)
    (outside : (⟨t,v⟩ : Σ t, Var Γ t) ∉ clobbered) :
    (suffixUpdate.eval s).lookup v = s.lookup v := by
  repeat (first
    | rfl
    | (solve | apply False.elim; apply outside; simp [clobbered, v_mem, v_rax, v_rcx, v_rdx, v_rsp, v_rsi, v_rdi, v_r8, v_r9, v_r10, v_r11, v_rip, v_rflags_CF, v_rflags_PF, v_rflags_AF, v_rflags_ZF, v_rflags_SF, v_rflags_OF])
    | cases ‹Var _ _›)

/-- The kernel boundary only: syscall is issued against a separate process,
without caller-memory interference. The OS return convention supplies raw RAX,
restores the user stack pointer, and resumes at the suffix. Kernel memory-transfer
semantics remain the separately specified process_vm_writev contract; this
record does not assume the shim's argument setup or final ABI conclusion. -/
structure SyscallABI (before after : Env Γ) (raw : BitVec 64) : Prop where
  result : after.lookup v_rax = raw
  resume : after.lookup v_rip = 0x40003c
  stack : after.lookup v_rsp = before.lookup v_rsp
  memory : after.lookup v_mem = before.lookup v_mem
  preserved : ∀ (t : TermSort) (v : Var Γ t),
    (⟨t,v⟩ : Σ t, Var Γ t) ∉ clobbered → after.lookup v = before.lookup v

omit [FPInterpretation] in
private theorem return_outside (sp : BitVec 64) (i : Fin 8) (j : Fin 32) :
    BitVec.ofNat 64 i.val + sp ≠ frameAddress sp j.val := by
  intro eq
  have h := (add_cancel _ _ sp).mp eq
  have hn := congrArg BitVec.toNat h
  change i.val % 2^64 = (2^64 - 32 + j.val) % 2^64 at hn
  rw [Nat.mod_eq_of_lt (by have := i.isLt; omega),
      Nat.mod_eq_of_lt (by have := j.isLt; omega)] at hn
  have := i.isLt; have := j.isLt
  omega

theorem prefix_saved_return (s : Env Γ) :
    readWordAt ((prefixUpdate.eval s).lookup v_mem) (s.lookup v_rsp) 0 =
      readWordAt (s.lookup v_mem) (s.lookup v_rsp) 0 := by
  have byte (i : Fin 8) := prefix_stack_frame s (BitVec.ofNat 64 i.val + s.lookup v_rsp)
    (return_outside (s.lookup v_rsp) i)
  unfold readWordAt
  rw [byte ⟨0, by decide⟩]
  rw [byte ⟨1, by decide⟩]
  rw [byte ⟨2, by decide⟩]
  rw [byte ⟨3, by decide⟩]
  rw [byte ⟨4, by decide⟩]
  rw [byte ⟨5, by decide⟩]
  rw [byte ⟨6, by decide⟩]
  rw [byte ⟨7, by decide⟩]

/-- A borrowed object occupies its 24-byte header plus its payload. Its
separation is geometric, not an assumption that the shim already preserved it. -/
def BufferSeparate (s : Env Γ) (length : Nat) : Prop :=
  ∀ i : Fin (24+length), ∀ j : Fin 32,
    BitVec.ofNat 64 i.val + s.lookup v_rdx ≠ frameAddress (s.lookup v_rsp) j.val

theorem buffer_implies_size (s : Env Γ) (length : Nat) (h : BufferSeparate s length) :
    SizeFieldSeparate s := by
  intro i j
  exact h ⟨8+i.val, by have := i.isLt; omega⟩ j

omit [FPInterpretation] in
private theorem stack_adjust (sp : BitVec 64) : sp - 32 + 40 = sp + 8 := by bv_decide

omit [FPInterpretation] in
private theorem address_adjust (sp i : BitVec 64) : (32 + i) + (sp - 32) = i + sp := by
  rw [BitVec.add_comm (32 : BitVec 64) i, BitVec.add_assoc,
    BitVec.add_comm (32 : BitVec 64) (sp - 32), BitVec.sub_add_cancel]

/-- ABI and frame conclusion for the concrete extracted prefix and suffix,
conditional only on their explicit kernel boundary contract. -/
theorem shim_abi (entry kernel : Env Γ) (raw : BitVec 64)
    (os : SyscallABI (prefixUpdate.eval entry) kernel raw) :
    let final := suffixUpdate.eval kernel
    final.lookup v_rax = raw ∧
    final.lookup v_rsp = entry.lookup v_rsp + 8 ∧
    final.lookup v_rip = readWordAt (entry.lookup v_mem) (entry.lookup v_rsp) 0 ∧
    (∀ (t : TermSort) (v : Var Γ t),
      (⟨t,v⟩ : Σ t, Var Γ t) ∉ clobbered → final.lookup v = entry.lookup v) ∧
    (∀ a, (∀ i : Fin 32, a ≠ frameAddress (entry.lookup v_rsp) i.val) →
      final.lookup v_mem a = entry.lookup v_mem a) := by
  dsimp only
  refine ⟨(suffix_result kernel).trans os.result, ?_, ?_, ?_, ?_⟩
  · rw [suffix_stack, os.stack, (syscall_arguments entry).2.2.2.2.2.2.2.1]
    exact stack_adjust (entry.lookup v_rsp)
  · rw [suffix_return, os.memory, os.stack]
    have sp : (prefixUpdate.eval entry).lookup v_rsp = entry.lookup v_rsp - 32 :=
      (syscall_arguments entry).2.2.2.2.2.2.2.1
    rw [sp]
    have adjust : readWordAt ((prefixUpdate.eval entry).lookup v_mem) (entry.lookup v_rsp - 32) 32 =
        readWordAt ((prefixUpdate.eval entry).lookup v_mem) (entry.lookup v_rsp) 0 := by
      unfold readWordAt
      have a0 : (32#64 + (entry.lookup v_rsp - 32)) = 0#64 + entry.lookup v_rsp := address_adjust (entry.lookup v_rsp) 0
      have a1 : (33#64 + (entry.lookup v_rsp - 32)) = 1#64 + entry.lookup v_rsp := address_adjust (entry.lookup v_rsp) 1
      have a2 : (34#64 + (entry.lookup v_rsp - 32)) = 2#64 + entry.lookup v_rsp := address_adjust (entry.lookup v_rsp) 2
      have a3 : (35#64 + (entry.lookup v_rsp - 32)) = 3#64 + entry.lookup v_rsp := address_adjust (entry.lookup v_rsp) 3
      have a4 : (36#64 + (entry.lookup v_rsp - 32)) = 4#64 + entry.lookup v_rsp := address_adjust (entry.lookup v_rsp) 4
      have a5 : (37#64 + (entry.lookup v_rsp - 32)) = 5#64 + entry.lookup v_rsp := address_adjust (entry.lookup v_rsp) 5
      have a6 : (38#64 + (entry.lookup v_rsp - 32)) = 6#64 + entry.lookup v_rsp := address_adjust (entry.lookup v_rsp) 6
      have a7 : (39#64 + (entry.lookup v_rsp - 32)) = 7#64 + entry.lookup v_rsp := address_adjust (entry.lookup v_rsp) 7
      simp only [a0, a1, a2, a3, a4, a5, a6, a7]
    exact adjust.trans (prefix_saved_return entry)
  · intro t v outside
    exact (suffix_other kernel t v outside).trans
      ((os.preserved t v outside).trans (prefix_other entry t v outside))
  · intro a outside
    rw [suffix_memory, os.memory]
    exact prefix_stack_frame entry a outside

theorem shim_borrowed_buffer (entry kernel : Env Γ) (raw : BitVec 64)
    (os : SyscallABI (prefixUpdate.eval entry) kernel raw)
    (length : Nat) (separate : BufferSeparate entry length) (i : Fin (24+length)) :
    (suffixUpdate.eval kernel).lookup v_mem (BitVec.ofNat 64 i.val + entry.lookup v_rdx) =
      entry.lookup v_mem (BitVec.ofNat 64 i.val + entry.lookup v_rdx) :=
  (shim_abi entry kernel raw os).2.2.2.2 _ (separate i)

/-- These are actual enabled AYXG steps, not just unguarded updates. -/
theorem prefix_available (entry : Env Γ) (pc : entry.lookup v_rip = 0x400000) :
    prefixStep.denotes entry (prefixUpdate.eval entry) := by
  constructor
  · change (entry.lookup v_rip == (0x400000 : BitVec 64)) = true
    simp [pc]
  · rfl

theorem suffix_available (entry kernel : Env Γ) (raw : BitVec 64)
    (os : SyscallABI (prefixUpdate.eval entry) kernel raw) :
    suffixStep.denotes kernel (suffixUpdate.eval kernel) := by
  constructor
  · change (kernel.lookup v_rip == (0x40003c : BitVec 64)) = true
    simp [os.resume]
  · rfl

#print axioms shim_abi
#print axioms shim_borrowed_buffer
end MovObserver.Shim
