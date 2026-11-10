import Protocol
import Lean.Elab.Tactic.Omega

set_option maxHeartbeats 10000000
set_option maxRecDepth 16384

namespace MovObserver

private theorem decoded_valid (word : BitVec 64) :
    (flagsFromRflags word).Valid := by
  simp only [flagsFromRflags, ModeledFlags.Valid]
  split <;> split <;> split <;> simp_all

private theorem bit_cases (b : BitVec 1) : b = 0 ∨ b = 1 := by
  have := b.isLt
  have h : b.toNat = 0 ∨ b.toNat = 1 := by omega
  rcases h with h | h
  · left; apply BitVec.eq_of_toNat_eq; exact h
  · right; apply BitVec.eq_of_toNat_eq; exact h

private theorem patch_frame (original bits mask : BitVec 64)
    (h : bits &&& ~~~mask = 0) :
    ((original &&& ~~~mask) ||| bits) &&& ~~~mask = original &&& ~~~mask := by
  rw [BitVec.and_or_distrib_right, h]
  simp [BitVec.and_assoc]

private theorem encoded_valid (f : ModeledFlags) (original : BitVec 64)
    (valid : f.Valid) :
    ∃ encoded : BitVec 64,
      flagsToRflags f original = some encoded ∧
      flagsFromRflags encoded = f ∧
      (encoded &&& ~~~modeledRflagsMask) =
        (original &&& ~~~modeledRflagsMask) := by
  unfold flagsToRflags
  rw [ite_eq_left valid]
  refine ⟨_, rfl, ?_, ?_⟩
  · rcases f with ⟨cf, pf, af, zf, sf, of_, d, ac, id⟩
    rcases valid with ⟨hd, hac, hid⟩
    rcases hd with rfl | rfl <;> rcases hac with rfl | rfl <;>
      rcases hid with rfl | rfl <;>
      rcases bit_cases cf with rfl | rfl <;>
      rcases bit_cases pf with rfl | rfl <;>
      rcases bit_cases af with rfl | rfl <;>
      rcases bit_cases zf with rfl | rfl <;>
      rcases bit_cases sf with rfl | rfl <;>
      rcases bit_cases of_ with rfl | rfl <;>
      simp [flagsFromRflags, modeledRflagsMask]
  · apply patch_frame
    rcases f with ⟨cf, pf, af, zf, sf, of_, d, ac, id⟩
    rcases valid with ⟨hd, hac, hid⟩
    rcases hd with rfl | rfl <;> rcases hac with rfl | rfl <;>
      rcases hid with rfl | rfl <;>
      rcases bit_cases cf with rfl | rfl <;>
      rcases bit_cases pf with rfl | rfl <;>
      rcases bit_cases af with rfl | rfl <;>
      rcases bit_cases zf with rfl | rfl <;>
      rcases bit_cases sf with rfl | rfl <;>
      rcases bit_cases of_ with rfl | rfl <;>
      decide

private theorem decoded_injective (a b : BitVec 64)
    (decoded : flagsFromRflags a = flagsFromRflags b)
    (frame : a &&& ~~~modeledRflagsMask = b &&& ~~~modeledRflagsMask) : a = b := by
  have h0 : a.getLsbD 0 = b.getLsbD 0 := by
    have h := congrArg ModeledFlags.cf decoded
    simp only [flagsFromRflags] at h
    cases ha : a.getLsbD 0 <;> cases hb : b.getLsbD 0 <;> simp_all
  have h2 : a.getLsbD 2 = b.getLsbD 2 := by
    have h := congrArg ModeledFlags.pf decoded
    simp only [flagsFromRflags] at h
    cases ha : a.getLsbD 2 <;> cases hb : b.getLsbD 2 <;> simp_all
  have h4 : a.getLsbD 4 = b.getLsbD 4 := by
    have h := congrArg ModeledFlags.af decoded
    simp only [flagsFromRflags] at h
    cases ha : a.getLsbD 4 <;> cases hb : b.getLsbD 4 <;> simp_all
  have h6 : a.getLsbD 6 = b.getLsbD 6 := by
    have h := congrArg ModeledFlags.zf decoded
    simp only [flagsFromRflags] at h
    cases ha : a.getLsbD 6 <;> cases hb : b.getLsbD 6 <;> simp_all
  have h7 : a.getLsbD 7 = b.getLsbD 7 := by
    have h := congrArg ModeledFlags.sf decoded
    simp only [flagsFromRflags] at h
    cases ha : a.getLsbD 7 <;> cases hb : b.getLsbD 7 <;> simp_all
  have h11 : a.getLsbD 11 = b.getLsbD 11 := by
    have h := congrArg ModeledFlags.of_ decoded
    simp only [flagsFromRflags] at h
    cases ha : a.getLsbD 11 <;> cases hb : b.getLsbD 11 <;> simp_all
  have h10 : a.getLsbD 10 = b.getLsbD 10 := by
    have h := congrArg ModeledFlags.d decoded
    simp only [flagsFromRflags] at h
    cases ha : a.getLsbD 10 <;> cases hb : b.getLsbD 10 <;> simp_all
  have h18 : a.getLsbD 18 = b.getLsbD 18 := by
    have h := congrArg ModeledFlags.ac decoded
    simp only [flagsFromRflags] at h
    cases ha : a.getLsbD 18 <;> cases hb : b.getLsbD 18 <;> simp_all
  have h21 : a.getLsbD 21 = b.getLsbD 21 := by
    have h := congrArg ModeledFlags.id decoded
    simp only [flagsFromRflags] at h
    cases ha : a.getLsbD 21 <;> cases hb : b.getLsbD 21 <;> simp_all
  apply BitVec.eq_of_getLsbD_eq
  intro i hi
  have h := congrArg (fun word : BitVec 64 => word.getLsbD i) frame
  by_cases selected : i = 0 ∨ i = 2 ∨ i = 4 ∨ i = 6 ∨ i = 7 ∨
      i = 10 ∨ i = 11 ∨ i = 18 ∨ i = 21
  · rcases selected with rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl <;>
      assumption
  · have mask_bits : ∀ j : Fin 64, modeledRflagsMask.getLsbD j =
        decide (j.val = 0 ∨ j.val = 2 ∨ j.val = 4 ∨ j.val = 6 ∨ j.val = 7 ∨
          j.val = 10 ∨ j.val = 11 ∨ j.val = 18 ∨ j.val = 21) := by decide
    have cleared : modeledRflagsMask.getLsbD i = false := by
      simpa [selected] using mask_bits ⟨i, hi⟩
    simpa only [BitVec.getLsbD_and, BitVec.getLsbD_not, cleared,
      Bool.not_false, decide_eq_true hi, Bool.and_self, Bool.and_true] using h

/-- The existing codec obligation, without changing its modeled flags domain. -/
theorem flags_conversion_correct : FlagsConversionCorrect := by
  refine ⟨decoded_valid, encoded_valid, ?_, ?_⟩
  · intro word
    obtain ⟨encoded, encode, decode, frame⟩ :=
      encoded_valid (flagsFromRflags word) word (decoded_valid word)
    have same : encoded = word := decoded_injective encoded word decode frame
    simpa [same] using encode
  · intro f original
    simp only [flagsToRflags]
    split <;> simp_all

#print axioms flags_conversion_correct

end MovObserver
