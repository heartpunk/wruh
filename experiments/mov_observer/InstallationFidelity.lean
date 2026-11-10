import SparseInstaller
import InstallationEncoding

namespace MovObserver.NativeObserver
open Ayxg.QfAbv

@[simp] theorem encodeGprs_size (gprs : Array UInt64) :
    (encodeGprs gprs).size = 128 := by
  simp [encodeGprs, ByteArray.size]

/-- Every byte of every requested word appears at its actual loader slot. -/
theorem encodeGprs_byte (gprs : Array UInt64) (register : Fin 16) (byte : Fin 8) :
    (encodeGprs gprs)[8 * register.val + byte.val]! =
      (gprs[register.val]! >>> UInt64.ofNat (8 * byte.val)).toUInt8 := by
  have bound : 8 * register.val + byte.val < 128 := by omega
  have div : (8 * register.val + byte.val) / 8 = register.val := by omega
  have mod : (8 * register.val + byte.val) % 8 = byte.val := by omega
  rw [getElem!_pos (encodeGprs gprs) _ (by simpa using bound)]
  simp [encodeGprs, ByteArray.getElem_eq_getElem_data, div, mod]


/-- This is the same little-endian convention as the extracted MOV model. -/
theorem nativeByteRoundtrip (value : UInt64) :
    pack64
      ((value >>> 0).toUInt8.toBitVec) ((value >>> 8).toUInt8.toBitVec)
      ((value >>> 16).toUInt8.toBitVec) ((value >>> 24).toUInt8.toBitVec)
      ((value >>> 32).toUInt8.toBitVec) ((value >>> 40).toUInt8.toBitVec)
      ((value >>> 48).toUInt8.toBitVec) ((value >>> 56).toUInt8.toBitVec) =
      value.toBitVec := by
  simp only [UInt64.toBitVec_toUInt8, UInt64.toBitVec_shiftRight]
  change pack64
    ((value.toBitVec >>> (0 : Nat)).setWidth 8)
    ((value.toBitVec >>> (8 : Nat)).setWidth 8)
    ((value.toBitVec >>> (16 : Nat)).setWidth 8)
    ((value.toBitVec >>> (24 : Nat)).setWidth 8)
    ((value.toBitVec >>> (32 : Nat)).setWidth 8)
    ((value.toBitVec >>> (40 : Nat)).setWidth 8)
    ((value.toBitVec >>> (48 : Nat)).setWidth 8)
    ((value.toBitVec >>> (56 : Nat)).setWidth 8) = value.toBitVec
  simp only [BitVec.setWidth_ushiftRight_eq_extractLsb]
  exact byte_roundtrip value.toBitVec

#print axioms byte_roundtrip
#print axioms nativeByteRoundtrip

/-- Concrete byte installation of the actual native encoder, with all other
memory retained. This is a pure state transformer, not a syscall assumption. -/
def encodedInputMemory (gprs : Array UInt64) (ambient : Mem 64 8) : Mem 64 8 :=
  fun a => if 6295872 ≤ a.toNat ∧ a.toNat < 6296000 then
    ((encodeGprs gprs)[a.toNat - 6295872]!).toBitVec else ambient a

theorem encodedInputMemory_byte (gprs : Array UInt64) (ambient : Mem 64 8)
    (register : Fin 16) (byte : Fin 8) :
    encodedInputMemory gprs ambient (BitVec.ofNat 64 (6295872 + 8*register.val + byte.val)) =
      (gprs[register.val]! >>> UInt64.ofNat (8*byte.val)).toUInt8.toBitVec := by
  have bounded : 6295872 + 8*register.val + byte.val < 2^64 := by omega
  have low : 6295872 ≤ 6295872 + 8*register.val + byte.val := by omega
  have high : 6295872 + 8*register.val + byte.val < 6296000 := by omega
  have offset : 6295872 + 8*register.val + byte.val - 6295872 = 8*register.val+byte.val := by omega
  simp only [encodedInputMemory, BitVec.toNat_ofNat, Nat.mod_eq_of_lt bounded,
    low, high, and_self, ↓reduceIte, offset]
  exact congrArg UInt8.toBitVec (encodeGprs_byte gprs register byte)

theorem encodedInputMemory_word (gprs : Array UInt64) (ambient : Mem 64 8)
    (register : Fin 16) :
    read64 (encodedInputMemory gprs ambient) (6295872+8*register.val) =
      gprs[register.val]!.toBitVec := by
  unfold read64
  rw [encodedInputMemory_byte gprs ambient register ⟨0, by decide⟩]
  rw [encodedInputMemory_byte gprs ambient register ⟨1, by decide⟩]
  rw [encodedInputMemory_byte gprs ambient register ⟨2, by decide⟩]
  rw [encodedInputMemory_byte gprs ambient register ⟨3, by decide⟩]
  rw [encodedInputMemory_byte gprs ambient register ⟨4, by decide⟩]
  rw [encodedInputMemory_byte gprs ambient register ⟨5, by decide⟩]
  rw [encodedInputMemory_byte gprs ambient register ⟨6, by decide⟩]
  rw [encodedInputMemory_byte gprs ambient register ⟨7, by decide⟩]
  exact nativeByteRoundtrip _

/-- All sixteen entries are required by the runtime's existing request check. -/
def requestedGprWords (gprs : Array UInt64) : List (BitVec 64) :=
  (List.range 16).map (fun i => gprs[i]!.toBitVec)

theorem encoded_input_decodes (gprs : Array UInt64) (ambient : Mem 64 8) :
    decodeInput (encodedInputMemory gprs ambient) = requestedGprWords gprs := by
  unfold decodeInput
  have h0 : read64 (encodedInputMemory gprs ambient) 6295872 = gprs[0]!.toBitVec :=
    encodedInputMemory_word gprs ambient ⟨0, by decide⟩
  have h1 : read64 (encodedInputMemory gprs ambient) 6295880 = gprs[1]!.toBitVec :=
    encodedInputMemory_word gprs ambient ⟨1, by decide⟩
  have h2 : read64 (encodedInputMemory gprs ambient) 6295888 = gprs[2]!.toBitVec :=
    encodedInputMemory_word gprs ambient ⟨2, by decide⟩
  have h3 : read64 (encodedInputMemory gprs ambient) 6295896 = gprs[3]!.toBitVec :=
    encodedInputMemory_word gprs ambient ⟨3, by decide⟩
  have h4 : read64 (encodedInputMemory gprs ambient) 6295904 = gprs[4]!.toBitVec :=
    encodedInputMemory_word gprs ambient ⟨4, by decide⟩
  have h5 : read64 (encodedInputMemory gprs ambient) 6295912 = gprs[5]!.toBitVec :=
    encodedInputMemory_word gprs ambient ⟨5, by decide⟩
  have h6 : read64 (encodedInputMemory gprs ambient) 6295920 = gprs[6]!.toBitVec :=
    encodedInputMemory_word gprs ambient ⟨6, by decide⟩
  have h7 : read64 (encodedInputMemory gprs ambient) 6295928 = gprs[7]!.toBitVec :=
    encodedInputMemory_word gprs ambient ⟨7, by decide⟩
  have h8 : read64 (encodedInputMemory gprs ambient) 6295936 = gprs[8]!.toBitVec :=
    encodedInputMemory_word gprs ambient ⟨8, by decide⟩
  have h9 : read64 (encodedInputMemory gprs ambient) 6295944 = gprs[9]!.toBitVec :=
    encodedInputMemory_word gprs ambient ⟨9, by decide⟩
  have h10 : read64 (encodedInputMemory gprs ambient) 6295952 = gprs[10]!.toBitVec :=
    encodedInputMemory_word gprs ambient ⟨10, by decide⟩
  have h11 : read64 (encodedInputMemory gprs ambient) 6295960 = gprs[11]!.toBitVec :=
    encodedInputMemory_word gprs ambient ⟨11, by decide⟩
  have h12 : read64 (encodedInputMemory gprs ambient) 6295968 = gprs[12]!.toBitVec :=
    encodedInputMemory_word gprs ambient ⟨12, by decide⟩
  have h13 : read64 (encodedInputMemory gprs ambient) 6295976 = gprs[13]!.toBitVec :=
    encodedInputMemory_word gprs ambient ⟨13, by decide⟩
  have h14 : read64 (encodedInputMemory gprs ambient) 6295984 = gprs[14]!.toBitVec :=
    encodedInputMemory_word gprs ambient ⟨14, by decide⟩
  have h15 : read64 (encodedInputMemory gprs ambient) 6295992 = gprs[15]!.toBitVec :=
    encodedInputMemory_word gprs ambient ⟨15, by decide⟩
  rw [h0, h1, h2, h3, h4, h5, h6, h7, h8, h9, h10, h11, h12, h13, h14, h15]
  rfl

variable [FPInterpretation]

/-- Install the actual encoder's bytes and the loader entry PC. The existing
native supervisor performs these two preparation operations before continuation. -/
def prepareEncodedInput (gprs : Array UInt64) : Env Γ → Env Γ
  | .cons memory (.cons _ rest) =>
    .cons (encodedInputMemory gprs memory) (.cons (BitVec.ofNat 64 0x400100) rest)

/-- Evaluate the already-extracted sixteen-MOV loader after concrete byte/PC
preparation. No requested register is assumed installed beforehand. -/
def encodedLoader (gprs : Array UInt64) (ambient : Env Γ) : Env Γ :=
  loadUpdate.eval (prepareEncodedInput gprs ambient)

theorem encoded_input_enables_loader (gprs : Array UInt64) (ambient : Env Γ) :
    loadStep.denotes (prepareEncodedInput gprs ambient) (encodedLoader gprs ambient) := by
  constructor
  · cases ambient with | cons memory tail => cases tail <;> rfl
  · rfl

theorem encoded_loader_gprs (gprs : Array UInt64) (ambient : Env Γ) :
    observeGprs (encodedLoader gprs ambient) = requestedGprWords gprs := by
  unfold encodedLoader
  rw [load_input]
  have memory : Env.lookup (prepareEncodedInput gprs ambient) v_mem =
      encodedInputMemory gprs (Env.lookup ambient v_mem) := by
    cases ambient with | cons memory tail => cases tail <;> rfl
  rw [memory]
  exact encoded_input_decodes _ _

/-- With the already-enforced size, the result contains every caller entry,
not merely a proper prefix or a caller-selected admitted subset. -/
theorem requestedGprWords_all (gprs : Array UInt64) (size : gprs.size = 16) :
    requestedGprWords gprs = gprs.toList.map UInt64.toBitVec := by
  apply List.ext_getElem
  · simp [requestedGprWords, size]
  · intro i h₁ h₂
    simp only [requestedGprWords, List.getElem_map, List.getElem_range]
    have hi : i < gprs.size := by simpa using h₂
    simp [getElem!_pos gprs i hi]

/-- Concrete installation component certificate: the actual loader relation
runs after encoded-byte/entry-PC preparation and installs ALL sixteen caller
GPR values. The fixed size is exactly the existing native request validation. -/
theorem encoded_loader_fidelity (gprs : Array UInt64) (size : gprs.size = 16)
    (ambient : Env Γ) :
    loadStep.denotes (prepareEncodedInput gprs ambient) (encodedLoader gprs ambient) ∧
    observeGprs (encodedLoader gprs ambient) = gprs.toList.map UInt64.toBitVec := by
  exact ⟨encoded_input_enables_loader gprs ambient,
    (encoded_loader_gprs gprs ambient).trans (requestedGprWords_all gprs size)⟩

#print axioms encodeGprs_byte
#print axioms encoded_input_decodes
#print axioms encoded_input_enables_loader
#print axioms encoded_loader_gprs
#print axioms encoded_loader_fidelity
end MovObserver.NativeObserver
