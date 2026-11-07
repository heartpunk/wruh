import Proof
import InputModel
import ByteCodec
set_option maxRecDepth 16384
set_option maxHeartbeats 2000000
namespace MovObserver
open Ayxg.QfAbv
variable [FPInterpretation]
def inputWrites : List ByteWrite :=
  expectedWrites.map fun w => (w.1 + BitVec.ofNat 64 256, w.2)
theorem input_destinations_unique : (inputWrites.map Prod.fst).Nodup := by decide
def prepareInputMemory (wanted : Env Γ) (ambient : Mem 64 8) : Mem 64 8 :=
  applyWrites wanted inputWrites ambient
theorem decode_rax (s : Env Γ) :
    read64 (Env.lookup (captureUpdate.eval s) v_mem) 6295616 =
      Env.lookup s v_rax := by
  have h0 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 0) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295616) =
    BitVec.extractLsb 7 0 (Env.lookup s v_rax) at h0
  have h1 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 1) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295617) =
    BitVec.extractLsb 15 8 (Env.lookup s v_rax) at h1
  have h2 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 2) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295618) =
    BitVec.extractLsb 23 16 (Env.lookup s v_rax) at h2
  have h3 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 3) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295619) =
    BitVec.extractLsb 31 24 (Env.lookup s v_rax) at h3
  have h4 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 4) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295620) =
    BitVec.extractLsb 39 32 (Env.lookup s v_rax) at h4
  have h5 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 5) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295621) =
    BitVec.extractLsb 47 40 (Env.lookup s v_rax) at h5
  have h6 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 6) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295622) =
    BitVec.extractLsb 55 48 (Env.lookup s v_rax) at h6
  have h7 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 7) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295623) =
    BitVec.extractLsb 63 56 (Env.lookup s v_rax) at h7
  unfold read64
  rw [h0, h1, h2, h3, h4, h5, h6, h7]
  exact byte_roundtrip (Env.lookup s v_rax)
theorem load_reads_rax (s : Env Γ) :
    Env.lookup (loadUpdate.eval s) v_rax =
      read64 (Env.lookup s v_mem) 6295872 := rfl
theorem encoded_input_rax (wanted : Env Γ) (ambient : Mem 64 8) :
    read64 (prepareInputMemory wanted ambient) 6295872 =
      Env.lookup wanted v_rax := by
  have h0 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 0) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295872) =
    BitVec.extractLsb 7 0 (Env.lookup wanted v_rax) at h0
  have h1 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 1) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295873) =
    BitVec.extractLsb 15 8 (Env.lookup wanted v_rax) at h1
  have h2 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 2) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295874) =
    BitVec.extractLsb 23 16 (Env.lookup wanted v_rax) at h2
  have h3 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 3) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295875) =
    BitVec.extractLsb 31 24 (Env.lookup wanted v_rax) at h3
  have h4 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 4) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295876) =
    BitVec.extractLsb 39 32 (Env.lookup wanted v_rax) at h4
  have h5 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 5) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295877) =
    BitVec.extractLsb 47 40 (Env.lookup wanted v_rax) at h5
  have h6 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 6) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295878) =
    BitVec.extractLsb 55 48 (Env.lookup wanted v_rax) at h6
  have h7 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 7) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295879) =
    BitVec.extractLsb 63 56 (Env.lookup wanted v_rax) at h7
  unfold read64 prepareInputMemory
  rw [h0, h1, h2, h3, h4, h5, h6, h7]
  exact byte_roundtrip (Env.lookup wanted v_rax)
theorem decode_rcx (s : Env Γ) :
    read64 (Env.lookup (captureUpdate.eval s) v_mem) 6295624 =
      Env.lookup s v_rcx := by
  have h0 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 8) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295624) =
    BitVec.extractLsb 7 0 (Env.lookup s v_rcx) at h0
  have h1 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 9) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295625) =
    BitVec.extractLsb 15 8 (Env.lookup s v_rcx) at h1
  have h2 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 10) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295626) =
    BitVec.extractLsb 23 16 (Env.lookup s v_rcx) at h2
  have h3 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 11) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295627) =
    BitVec.extractLsb 31 24 (Env.lookup s v_rcx) at h3
  have h4 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 12) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295628) =
    BitVec.extractLsb 39 32 (Env.lookup s v_rcx) at h4
  have h5 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 13) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295629) =
    BitVec.extractLsb 47 40 (Env.lookup s v_rcx) at h5
  have h6 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 14) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295630) =
    BitVec.extractLsb 55 48 (Env.lookup s v_rcx) at h6
  have h7 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 15) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295631) =
    BitVec.extractLsb 63 56 (Env.lookup s v_rcx) at h7
  unfold read64
  rw [h0, h1, h2, h3, h4, h5, h6, h7]
  exact byte_roundtrip (Env.lookup s v_rcx)
theorem load_reads_rcx (s : Env Γ) :
    Env.lookup (loadUpdate.eval s) v_rcx =
      read64 (Env.lookup s v_mem) 6295880 := rfl
theorem encoded_input_rcx (wanted : Env Γ) (ambient : Mem 64 8) :
    read64 (prepareInputMemory wanted ambient) 6295880 =
      Env.lookup wanted v_rcx := by
  have h0 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 8) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295880) =
    BitVec.extractLsb 7 0 (Env.lookup wanted v_rcx) at h0
  have h1 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 9) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295881) =
    BitVec.extractLsb 15 8 (Env.lookup wanted v_rcx) at h1
  have h2 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 10) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295882) =
    BitVec.extractLsb 23 16 (Env.lookup wanted v_rcx) at h2
  have h3 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 11) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295883) =
    BitVec.extractLsb 31 24 (Env.lookup wanted v_rcx) at h3
  have h4 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 12) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295884) =
    BitVec.extractLsb 39 32 (Env.lookup wanted v_rcx) at h4
  have h5 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 13) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295885) =
    BitVec.extractLsb 47 40 (Env.lookup wanted v_rcx) at h5
  have h6 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 14) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295886) =
    BitVec.extractLsb 55 48 (Env.lookup wanted v_rcx) at h6
  have h7 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 15) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295887) =
    BitVec.extractLsb 63 56 (Env.lookup wanted v_rcx) at h7
  unfold read64 prepareInputMemory
  rw [h0, h1, h2, h3, h4, h5, h6, h7]
  exact byte_roundtrip (Env.lookup wanted v_rcx)
theorem decode_rdx (s : Env Γ) :
    read64 (Env.lookup (captureUpdate.eval s) v_mem) 6295632 =
      Env.lookup s v_rdx := by
  have h0 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 16) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295632) =
    BitVec.extractLsb 7 0 (Env.lookup s v_rdx) at h0
  have h1 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 17) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295633) =
    BitVec.extractLsb 15 8 (Env.lookup s v_rdx) at h1
  have h2 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 18) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295634) =
    BitVec.extractLsb 23 16 (Env.lookup s v_rdx) at h2
  have h3 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 19) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295635) =
    BitVec.extractLsb 31 24 (Env.lookup s v_rdx) at h3
  have h4 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 20) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295636) =
    BitVec.extractLsb 39 32 (Env.lookup s v_rdx) at h4
  have h5 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 21) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295637) =
    BitVec.extractLsb 47 40 (Env.lookup s v_rdx) at h5
  have h6 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 22) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295638) =
    BitVec.extractLsb 55 48 (Env.lookup s v_rdx) at h6
  have h7 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 23) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295639) =
    BitVec.extractLsb 63 56 (Env.lookup s v_rdx) at h7
  unfold read64
  rw [h0, h1, h2, h3, h4, h5, h6, h7]
  exact byte_roundtrip (Env.lookup s v_rdx)
theorem load_reads_rdx (s : Env Γ) :
    Env.lookup (loadUpdate.eval s) v_rdx =
      read64 (Env.lookup s v_mem) 6295888 := rfl
theorem encoded_input_rdx (wanted : Env Γ) (ambient : Mem 64 8) :
    read64 (prepareInputMemory wanted ambient) 6295888 =
      Env.lookup wanted v_rdx := by
  have h0 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 16) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295888) =
    BitVec.extractLsb 7 0 (Env.lookup wanted v_rdx) at h0
  have h1 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 17) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295889) =
    BitVec.extractLsb 15 8 (Env.lookup wanted v_rdx) at h1
  have h2 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 18) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295890) =
    BitVec.extractLsb 23 16 (Env.lookup wanted v_rdx) at h2
  have h3 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 19) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295891) =
    BitVec.extractLsb 31 24 (Env.lookup wanted v_rdx) at h3
  have h4 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 20) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295892) =
    BitVec.extractLsb 39 32 (Env.lookup wanted v_rdx) at h4
  have h5 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 21) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295893) =
    BitVec.extractLsb 47 40 (Env.lookup wanted v_rdx) at h5
  have h6 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 22) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295894) =
    BitVec.extractLsb 55 48 (Env.lookup wanted v_rdx) at h6
  have h7 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 23) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295895) =
    BitVec.extractLsb 63 56 (Env.lookup wanted v_rdx) at h7
  unfold read64 prepareInputMemory
  rw [h0, h1, h2, h3, h4, h5, h6, h7]
  exact byte_roundtrip (Env.lookup wanted v_rdx)
theorem decode_rbx (s : Env Γ) :
    read64 (Env.lookup (captureUpdate.eval s) v_mem) 6295640 =
      Env.lookup s v_rbx := by
  have h0 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 24) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295640) =
    BitVec.extractLsb 7 0 (Env.lookup s v_rbx) at h0
  have h1 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 25) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295641) =
    BitVec.extractLsb 15 8 (Env.lookup s v_rbx) at h1
  have h2 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 26) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295642) =
    BitVec.extractLsb 23 16 (Env.lookup s v_rbx) at h2
  have h3 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 27) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295643) =
    BitVec.extractLsb 31 24 (Env.lookup s v_rbx) at h3
  have h4 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 28) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295644) =
    BitVec.extractLsb 39 32 (Env.lookup s v_rbx) at h4
  have h5 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 29) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295645) =
    BitVec.extractLsb 47 40 (Env.lookup s v_rbx) at h5
  have h6 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 30) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295646) =
    BitVec.extractLsb 55 48 (Env.lookup s v_rbx) at h6
  have h7 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 31) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295647) =
    BitVec.extractLsb 63 56 (Env.lookup s v_rbx) at h7
  unfold read64
  rw [h0, h1, h2, h3, h4, h5, h6, h7]
  exact byte_roundtrip (Env.lookup s v_rbx)
theorem load_reads_rbx (s : Env Γ) :
    Env.lookup (loadUpdate.eval s) v_rbx =
      read64 (Env.lookup s v_mem) 6295896 := rfl
theorem encoded_input_rbx (wanted : Env Γ) (ambient : Mem 64 8) :
    read64 (prepareInputMemory wanted ambient) 6295896 =
      Env.lookup wanted v_rbx := by
  have h0 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 24) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295896) =
    BitVec.extractLsb 7 0 (Env.lookup wanted v_rbx) at h0
  have h1 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 25) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295897) =
    BitVec.extractLsb 15 8 (Env.lookup wanted v_rbx) at h1
  have h2 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 26) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295898) =
    BitVec.extractLsb 23 16 (Env.lookup wanted v_rbx) at h2
  have h3 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 27) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295899) =
    BitVec.extractLsb 31 24 (Env.lookup wanted v_rbx) at h3
  have h4 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 28) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295900) =
    BitVec.extractLsb 39 32 (Env.lookup wanted v_rbx) at h4
  have h5 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 29) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295901) =
    BitVec.extractLsb 47 40 (Env.lookup wanted v_rbx) at h5
  have h6 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 30) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295902) =
    BitVec.extractLsb 55 48 (Env.lookup wanted v_rbx) at h6
  have h7 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 31) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295903) =
    BitVec.extractLsb 63 56 (Env.lookup wanted v_rbx) at h7
  unfold read64 prepareInputMemory
  rw [h0, h1, h2, h3, h4, h5, h6, h7]
  exact byte_roundtrip (Env.lookup wanted v_rbx)
theorem decode_rsp (s : Env Γ) :
    read64 (Env.lookup (captureUpdate.eval s) v_mem) 6295648 =
      Env.lookup s v_rsp := by
  have h0 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 32) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295648) =
    BitVec.extractLsb 7 0 (Env.lookup s v_rsp) at h0
  have h1 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 33) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295649) =
    BitVec.extractLsb 15 8 (Env.lookup s v_rsp) at h1
  have h2 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 34) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295650) =
    BitVec.extractLsb 23 16 (Env.lookup s v_rsp) at h2
  have h3 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 35) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295651) =
    BitVec.extractLsb 31 24 (Env.lookup s v_rsp) at h3
  have h4 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 36) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295652) =
    BitVec.extractLsb 39 32 (Env.lookup s v_rsp) at h4
  have h5 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 37) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295653) =
    BitVec.extractLsb 47 40 (Env.lookup s v_rsp) at h5
  have h6 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 38) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295654) =
    BitVec.extractLsb 55 48 (Env.lookup s v_rsp) at h6
  have h7 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 39) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295655) =
    BitVec.extractLsb 63 56 (Env.lookup s v_rsp) at h7
  unfold read64
  rw [h0, h1, h2, h3, h4, h5, h6, h7]
  exact byte_roundtrip (Env.lookup s v_rsp)
theorem load_reads_rsp (s : Env Γ) :
    Env.lookup (loadUpdate.eval s) v_rsp =
      read64 (Env.lookup s v_mem) 6295904 := rfl
theorem encoded_input_rsp (wanted : Env Γ) (ambient : Mem 64 8) :
    read64 (prepareInputMemory wanted ambient) 6295904 =
      Env.lookup wanted v_rsp := by
  have h0 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 32) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295904) =
    BitVec.extractLsb 7 0 (Env.lookup wanted v_rsp) at h0
  have h1 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 33) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295905) =
    BitVec.extractLsb 15 8 (Env.lookup wanted v_rsp) at h1
  have h2 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 34) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295906) =
    BitVec.extractLsb 23 16 (Env.lookup wanted v_rsp) at h2
  have h3 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 35) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295907) =
    BitVec.extractLsb 31 24 (Env.lookup wanted v_rsp) at h3
  have h4 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 36) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295908) =
    BitVec.extractLsb 39 32 (Env.lookup wanted v_rsp) at h4
  have h5 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 37) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295909) =
    BitVec.extractLsb 47 40 (Env.lookup wanted v_rsp) at h5
  have h6 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 38) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295910) =
    BitVec.extractLsb 55 48 (Env.lookup wanted v_rsp) at h6
  have h7 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 39) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295911) =
    BitVec.extractLsb 63 56 (Env.lookup wanted v_rsp) at h7
  unfold read64 prepareInputMemory
  rw [h0, h1, h2, h3, h4, h5, h6, h7]
  exact byte_roundtrip (Env.lookup wanted v_rsp)
theorem decode_rbp (s : Env Γ) :
    read64 (Env.lookup (captureUpdate.eval s) v_mem) 6295656 =
      Env.lookup s v_rbp := by
  have h0 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 40) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295656) =
    BitVec.extractLsb 7 0 (Env.lookup s v_rbp) at h0
  have h1 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 41) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295657) =
    BitVec.extractLsb 15 8 (Env.lookup s v_rbp) at h1
  have h2 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 42) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295658) =
    BitVec.extractLsb 23 16 (Env.lookup s v_rbp) at h2
  have h3 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 43) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295659) =
    BitVec.extractLsb 31 24 (Env.lookup s v_rbp) at h3
  have h4 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 44) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295660) =
    BitVec.extractLsb 39 32 (Env.lookup s v_rbp) at h4
  have h5 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 45) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295661) =
    BitVec.extractLsb 47 40 (Env.lookup s v_rbp) at h5
  have h6 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 46) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295662) =
    BitVec.extractLsb 55 48 (Env.lookup s v_rbp) at h6
  have h7 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 47) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295663) =
    BitVec.extractLsb 63 56 (Env.lookup s v_rbp) at h7
  unfold read64
  rw [h0, h1, h2, h3, h4, h5, h6, h7]
  exact byte_roundtrip (Env.lookup s v_rbp)
theorem load_reads_rbp (s : Env Γ) :
    Env.lookup (loadUpdate.eval s) v_rbp =
      read64 (Env.lookup s v_mem) 6295912 := rfl
theorem encoded_input_rbp (wanted : Env Γ) (ambient : Mem 64 8) :
    read64 (prepareInputMemory wanted ambient) 6295912 =
      Env.lookup wanted v_rbp := by
  have h0 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 40) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295912) =
    BitVec.extractLsb 7 0 (Env.lookup wanted v_rbp) at h0
  have h1 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 41) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295913) =
    BitVec.extractLsb 15 8 (Env.lookup wanted v_rbp) at h1
  have h2 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 42) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295914) =
    BitVec.extractLsb 23 16 (Env.lookup wanted v_rbp) at h2
  have h3 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 43) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295915) =
    BitVec.extractLsb 31 24 (Env.lookup wanted v_rbp) at h3
  have h4 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 44) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295916) =
    BitVec.extractLsb 39 32 (Env.lookup wanted v_rbp) at h4
  have h5 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 45) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295917) =
    BitVec.extractLsb 47 40 (Env.lookup wanted v_rbp) at h5
  have h6 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 46) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295918) =
    BitVec.extractLsb 55 48 (Env.lookup wanted v_rbp) at h6
  have h7 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 47) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295919) =
    BitVec.extractLsb 63 56 (Env.lookup wanted v_rbp) at h7
  unfold read64 prepareInputMemory
  rw [h0, h1, h2, h3, h4, h5, h6, h7]
  exact byte_roundtrip (Env.lookup wanted v_rbp)
theorem decode_rsi (s : Env Γ) :
    read64 (Env.lookup (captureUpdate.eval s) v_mem) 6295664 =
      Env.lookup s v_rsi := by
  have h0 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 48) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295664) =
    BitVec.extractLsb 7 0 (Env.lookup s v_rsi) at h0
  have h1 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 49) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295665) =
    BitVec.extractLsb 15 8 (Env.lookup s v_rsi) at h1
  have h2 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 50) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295666) =
    BitVec.extractLsb 23 16 (Env.lookup s v_rsi) at h2
  have h3 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 51) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295667) =
    BitVec.extractLsb 31 24 (Env.lookup s v_rsi) at h3
  have h4 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 52) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295668) =
    BitVec.extractLsb 39 32 (Env.lookup s v_rsi) at h4
  have h5 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 53) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295669) =
    BitVec.extractLsb 47 40 (Env.lookup s v_rsi) at h5
  have h6 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 54) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295670) =
    BitVec.extractLsb 55 48 (Env.lookup s v_rsi) at h6
  have h7 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 55) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295671) =
    BitVec.extractLsb 63 56 (Env.lookup s v_rsi) at h7
  unfold read64
  rw [h0, h1, h2, h3, h4, h5, h6, h7]
  exact byte_roundtrip (Env.lookup s v_rsi)
theorem load_reads_rsi (s : Env Γ) :
    Env.lookup (loadUpdate.eval s) v_rsi =
      read64 (Env.lookup s v_mem) 6295920 := rfl
theorem encoded_input_rsi (wanted : Env Γ) (ambient : Mem 64 8) :
    read64 (prepareInputMemory wanted ambient) 6295920 =
      Env.lookup wanted v_rsi := by
  have h0 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 48) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295920) =
    BitVec.extractLsb 7 0 (Env.lookup wanted v_rsi) at h0
  have h1 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 49) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295921) =
    BitVec.extractLsb 15 8 (Env.lookup wanted v_rsi) at h1
  have h2 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 50) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295922) =
    BitVec.extractLsb 23 16 (Env.lookup wanted v_rsi) at h2
  have h3 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 51) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295923) =
    BitVec.extractLsb 31 24 (Env.lookup wanted v_rsi) at h3
  have h4 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 52) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295924) =
    BitVec.extractLsb 39 32 (Env.lookup wanted v_rsi) at h4
  have h5 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 53) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295925) =
    BitVec.extractLsb 47 40 (Env.lookup wanted v_rsi) at h5
  have h6 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 54) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295926) =
    BitVec.extractLsb 55 48 (Env.lookup wanted v_rsi) at h6
  have h7 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 55) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295927) =
    BitVec.extractLsb 63 56 (Env.lookup wanted v_rsi) at h7
  unfold read64 prepareInputMemory
  rw [h0, h1, h2, h3, h4, h5, h6, h7]
  exact byte_roundtrip (Env.lookup wanted v_rsi)
theorem decode_rdi (s : Env Γ) :
    read64 (Env.lookup (captureUpdate.eval s) v_mem) 6295672 =
      Env.lookup s v_rdi := by
  have h0 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 56) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295672) =
    BitVec.extractLsb 7 0 (Env.lookup s v_rdi) at h0
  have h1 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 57) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295673) =
    BitVec.extractLsb 15 8 (Env.lookup s v_rdi) at h1
  have h2 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 58) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295674) =
    BitVec.extractLsb 23 16 (Env.lookup s v_rdi) at h2
  have h3 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 59) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295675) =
    BitVec.extractLsb 31 24 (Env.lookup s v_rdi) at h3
  have h4 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 60) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295676) =
    BitVec.extractLsb 39 32 (Env.lookup s v_rdi) at h4
  have h5 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 61) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295677) =
    BitVec.extractLsb 47 40 (Env.lookup s v_rdi) at h5
  have h6 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 62) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295678) =
    BitVec.extractLsb 55 48 (Env.lookup s v_rdi) at h6
  have h7 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 63) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295679) =
    BitVec.extractLsb 63 56 (Env.lookup s v_rdi) at h7
  unfold read64
  rw [h0, h1, h2, h3, h4, h5, h6, h7]
  exact byte_roundtrip (Env.lookup s v_rdi)
theorem load_reads_rdi (s : Env Γ) :
    Env.lookup (loadUpdate.eval s) v_rdi =
      read64 (Env.lookup s v_mem) 6295928 := rfl
theorem encoded_input_rdi (wanted : Env Γ) (ambient : Mem 64 8) :
    read64 (prepareInputMemory wanted ambient) 6295928 =
      Env.lookup wanted v_rdi := by
  have h0 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 56) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295928) =
    BitVec.extractLsb 7 0 (Env.lookup wanted v_rdi) at h0
  have h1 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 57) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295929) =
    BitVec.extractLsb 15 8 (Env.lookup wanted v_rdi) at h1
  have h2 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 58) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295930) =
    BitVec.extractLsb 23 16 (Env.lookup wanted v_rdi) at h2
  have h3 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 59) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295931) =
    BitVec.extractLsb 31 24 (Env.lookup wanted v_rdi) at h3
  have h4 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 60) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295932) =
    BitVec.extractLsb 39 32 (Env.lookup wanted v_rdi) at h4
  have h5 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 61) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295933) =
    BitVec.extractLsb 47 40 (Env.lookup wanted v_rdi) at h5
  have h6 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 62) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295934) =
    BitVec.extractLsb 55 48 (Env.lookup wanted v_rdi) at h6
  have h7 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 63) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295935) =
    BitVec.extractLsb 63 56 (Env.lookup wanted v_rdi) at h7
  unfold read64 prepareInputMemory
  rw [h0, h1, h2, h3, h4, h5, h6, h7]
  exact byte_roundtrip (Env.lookup wanted v_rdi)
theorem decode_r8 (s : Env Γ) :
    read64 (Env.lookup (captureUpdate.eval s) v_mem) 6295680 =
      Env.lookup s v_r8 := by
  have h0 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 64) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295680) =
    BitVec.extractLsb 7 0 (Env.lookup s v_r8) at h0
  have h1 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 65) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295681) =
    BitVec.extractLsb 15 8 (Env.lookup s v_r8) at h1
  have h2 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 66) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295682) =
    BitVec.extractLsb 23 16 (Env.lookup s v_r8) at h2
  have h3 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 67) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295683) =
    BitVec.extractLsb 31 24 (Env.lookup s v_r8) at h3
  have h4 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 68) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295684) =
    BitVec.extractLsb 39 32 (Env.lookup s v_r8) at h4
  have h5 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 69) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295685) =
    BitVec.extractLsb 47 40 (Env.lookup s v_r8) at h5
  have h6 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 70) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295686) =
    BitVec.extractLsb 55 48 (Env.lookup s v_r8) at h6
  have h7 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 71) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295687) =
    BitVec.extractLsb 63 56 (Env.lookup s v_r8) at h7
  unfold read64
  rw [h0, h1, h2, h3, h4, h5, h6, h7]
  exact byte_roundtrip (Env.lookup s v_r8)
theorem load_reads_r8 (s : Env Γ) :
    Env.lookup (loadUpdate.eval s) v_r8 =
      read64 (Env.lookup s v_mem) 6295936 := rfl
theorem encoded_input_r8 (wanted : Env Γ) (ambient : Mem 64 8) :
    read64 (prepareInputMemory wanted ambient) 6295936 =
      Env.lookup wanted v_r8 := by
  have h0 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 64) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295936) =
    BitVec.extractLsb 7 0 (Env.lookup wanted v_r8) at h0
  have h1 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 65) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295937) =
    BitVec.extractLsb 15 8 (Env.lookup wanted v_r8) at h1
  have h2 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 66) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295938) =
    BitVec.extractLsb 23 16 (Env.lookup wanted v_r8) at h2
  have h3 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 67) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295939) =
    BitVec.extractLsb 31 24 (Env.lookup wanted v_r8) at h3
  have h4 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 68) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295940) =
    BitVec.extractLsb 39 32 (Env.lookup wanted v_r8) at h4
  have h5 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 69) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295941) =
    BitVec.extractLsb 47 40 (Env.lookup wanted v_r8) at h5
  have h6 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 70) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295942) =
    BitVec.extractLsb 55 48 (Env.lookup wanted v_r8) at h6
  have h7 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 71) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295943) =
    BitVec.extractLsb 63 56 (Env.lookup wanted v_r8) at h7
  unfold read64 prepareInputMemory
  rw [h0, h1, h2, h3, h4, h5, h6, h7]
  exact byte_roundtrip (Env.lookup wanted v_r8)
theorem decode_r9 (s : Env Γ) :
    read64 (Env.lookup (captureUpdate.eval s) v_mem) 6295688 =
      Env.lookup s v_r9 := by
  have h0 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 72) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295688) =
    BitVec.extractLsb 7 0 (Env.lookup s v_r9) at h0
  have h1 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 73) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295689) =
    BitVec.extractLsb 15 8 (Env.lookup s v_r9) at h1
  have h2 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 74) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295690) =
    BitVec.extractLsb 23 16 (Env.lookup s v_r9) at h2
  have h3 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 75) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295691) =
    BitVec.extractLsb 31 24 (Env.lookup s v_r9) at h3
  have h4 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 76) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295692) =
    BitVec.extractLsb 39 32 (Env.lookup s v_r9) at h4
  have h5 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 77) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295693) =
    BitVec.extractLsb 47 40 (Env.lookup s v_r9) at h5
  have h6 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 78) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295694) =
    BitVec.extractLsb 55 48 (Env.lookup s v_r9) at h6
  have h7 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 79) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295695) =
    BitVec.extractLsb 63 56 (Env.lookup s v_r9) at h7
  unfold read64
  rw [h0, h1, h2, h3, h4, h5, h6, h7]
  exact byte_roundtrip (Env.lookup s v_r9)
theorem load_reads_r9 (s : Env Γ) :
    Env.lookup (loadUpdate.eval s) v_r9 =
      read64 (Env.lookup s v_mem) 6295944 := rfl
theorem encoded_input_r9 (wanted : Env Γ) (ambient : Mem 64 8) :
    read64 (prepareInputMemory wanted ambient) 6295944 =
      Env.lookup wanted v_r9 := by
  have h0 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 72) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295944) =
    BitVec.extractLsb 7 0 (Env.lookup wanted v_r9) at h0
  have h1 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 73) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295945) =
    BitVec.extractLsb 15 8 (Env.lookup wanted v_r9) at h1
  have h2 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 74) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295946) =
    BitVec.extractLsb 23 16 (Env.lookup wanted v_r9) at h2
  have h3 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 75) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295947) =
    BitVec.extractLsb 31 24 (Env.lookup wanted v_r9) at h3
  have h4 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 76) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295948) =
    BitVec.extractLsb 39 32 (Env.lookup wanted v_r9) at h4
  have h5 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 77) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295949) =
    BitVec.extractLsb 47 40 (Env.lookup wanted v_r9) at h5
  have h6 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 78) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295950) =
    BitVec.extractLsb 55 48 (Env.lookup wanted v_r9) at h6
  have h7 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 79) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295951) =
    BitVec.extractLsb 63 56 (Env.lookup wanted v_r9) at h7
  unfold read64 prepareInputMemory
  rw [h0, h1, h2, h3, h4, h5, h6, h7]
  exact byte_roundtrip (Env.lookup wanted v_r9)
theorem decode_r10 (s : Env Γ) :
    read64 (Env.lookup (captureUpdate.eval s) v_mem) 6295696 =
      Env.lookup s v_r10 := by
  have h0 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 80) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295696) =
    BitVec.extractLsb 7 0 (Env.lookup s v_r10) at h0
  have h1 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 81) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295697) =
    BitVec.extractLsb 15 8 (Env.lookup s v_r10) at h1
  have h2 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 82) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295698) =
    BitVec.extractLsb 23 16 (Env.lookup s v_r10) at h2
  have h3 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 83) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295699) =
    BitVec.extractLsb 31 24 (Env.lookup s v_r10) at h3
  have h4 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 84) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295700) =
    BitVec.extractLsb 39 32 (Env.lookup s v_r10) at h4
  have h5 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 85) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295701) =
    BitVec.extractLsb 47 40 (Env.lookup s v_r10) at h5
  have h6 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 86) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295702) =
    BitVec.extractLsb 55 48 (Env.lookup s v_r10) at h6
  have h7 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 87) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295703) =
    BitVec.extractLsb 63 56 (Env.lookup s v_r10) at h7
  unfold read64
  rw [h0, h1, h2, h3, h4, h5, h6, h7]
  exact byte_roundtrip (Env.lookup s v_r10)
theorem load_reads_r10 (s : Env Γ) :
    Env.lookup (loadUpdate.eval s) v_r10 =
      read64 (Env.lookup s v_mem) 6295952 := rfl
theorem encoded_input_r10 (wanted : Env Γ) (ambient : Mem 64 8) :
    read64 (prepareInputMemory wanted ambient) 6295952 =
      Env.lookup wanted v_r10 := by
  have h0 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 80) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295952) =
    BitVec.extractLsb 7 0 (Env.lookup wanted v_r10) at h0
  have h1 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 81) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295953) =
    BitVec.extractLsb 15 8 (Env.lookup wanted v_r10) at h1
  have h2 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 82) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295954) =
    BitVec.extractLsb 23 16 (Env.lookup wanted v_r10) at h2
  have h3 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 83) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295955) =
    BitVec.extractLsb 31 24 (Env.lookup wanted v_r10) at h3
  have h4 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 84) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295956) =
    BitVec.extractLsb 39 32 (Env.lookup wanted v_r10) at h4
  have h5 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 85) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295957) =
    BitVec.extractLsb 47 40 (Env.lookup wanted v_r10) at h5
  have h6 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 86) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295958) =
    BitVec.extractLsb 55 48 (Env.lookup wanted v_r10) at h6
  have h7 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 87) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295959) =
    BitVec.extractLsb 63 56 (Env.lookup wanted v_r10) at h7
  unfold read64 prepareInputMemory
  rw [h0, h1, h2, h3, h4, h5, h6, h7]
  exact byte_roundtrip (Env.lookup wanted v_r10)
theorem decode_r11 (s : Env Γ) :
    read64 (Env.lookup (captureUpdate.eval s) v_mem) 6295704 =
      Env.lookup s v_r11 := by
  have h0 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 88) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295704) =
    BitVec.extractLsb 7 0 (Env.lookup s v_r11) at h0
  have h1 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 89) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295705) =
    BitVec.extractLsb 15 8 (Env.lookup s v_r11) at h1
  have h2 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 90) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295706) =
    BitVec.extractLsb 23 16 (Env.lookup s v_r11) at h2
  have h3 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 91) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295707) =
    BitVec.extractLsb 31 24 (Env.lookup s v_r11) at h3
  have h4 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 92) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295708) =
    BitVec.extractLsb 39 32 (Env.lookup s v_r11) at h4
  have h5 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 93) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295709) =
    BitVec.extractLsb 47 40 (Env.lookup s v_r11) at h5
  have h6 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 94) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295710) =
    BitVec.extractLsb 55 48 (Env.lookup s v_r11) at h6
  have h7 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 95) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295711) =
    BitVec.extractLsb 63 56 (Env.lookup s v_r11) at h7
  unfold read64
  rw [h0, h1, h2, h3, h4, h5, h6, h7]
  exact byte_roundtrip (Env.lookup s v_r11)
theorem load_reads_r11 (s : Env Γ) :
    Env.lookup (loadUpdate.eval s) v_r11 =
      read64 (Env.lookup s v_mem) 6295960 := rfl
theorem encoded_input_r11 (wanted : Env Γ) (ambient : Mem 64 8) :
    read64 (prepareInputMemory wanted ambient) 6295960 =
      Env.lookup wanted v_r11 := by
  have h0 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 88) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295960) =
    BitVec.extractLsb 7 0 (Env.lookup wanted v_r11) at h0
  have h1 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 89) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295961) =
    BitVec.extractLsb 15 8 (Env.lookup wanted v_r11) at h1
  have h2 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 90) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295962) =
    BitVec.extractLsb 23 16 (Env.lookup wanted v_r11) at h2
  have h3 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 91) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295963) =
    BitVec.extractLsb 31 24 (Env.lookup wanted v_r11) at h3
  have h4 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 92) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295964) =
    BitVec.extractLsb 39 32 (Env.lookup wanted v_r11) at h4
  have h5 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 93) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295965) =
    BitVec.extractLsb 47 40 (Env.lookup wanted v_r11) at h5
  have h6 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 94) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295966) =
    BitVec.extractLsb 55 48 (Env.lookup wanted v_r11) at h6
  have h7 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 95) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295967) =
    BitVec.extractLsb 63 56 (Env.lookup wanted v_r11) at h7
  unfold read64 prepareInputMemory
  rw [h0, h1, h2, h3, h4, h5, h6, h7]
  exact byte_roundtrip (Env.lookup wanted v_r11)
theorem decode_r12 (s : Env Γ) :
    read64 (Env.lookup (captureUpdate.eval s) v_mem) 6295712 =
      Env.lookup s v_r12 := by
  have h0 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 96) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295712) =
    BitVec.extractLsb 7 0 (Env.lookup s v_r12) at h0
  have h1 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 97) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295713) =
    BitVec.extractLsb 15 8 (Env.lookup s v_r12) at h1
  have h2 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 98) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295714) =
    BitVec.extractLsb 23 16 (Env.lookup s v_r12) at h2
  have h3 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 99) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295715) =
    BitVec.extractLsb 31 24 (Env.lookup s v_r12) at h3
  have h4 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 100) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295716) =
    BitVec.extractLsb 39 32 (Env.lookup s v_r12) at h4
  have h5 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 101) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295717) =
    BitVec.extractLsb 47 40 (Env.lookup s v_r12) at h5
  have h6 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 102) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295718) =
    BitVec.extractLsb 55 48 (Env.lookup s v_r12) at h6
  have h7 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 103) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295719) =
    BitVec.extractLsb 63 56 (Env.lookup s v_r12) at h7
  unfold read64
  rw [h0, h1, h2, h3, h4, h5, h6, h7]
  exact byte_roundtrip (Env.lookup s v_r12)
theorem load_reads_r12 (s : Env Γ) :
    Env.lookup (loadUpdate.eval s) v_r12 =
      read64 (Env.lookup s v_mem) 6295968 := rfl
theorem encoded_input_r12 (wanted : Env Γ) (ambient : Mem 64 8) :
    read64 (prepareInputMemory wanted ambient) 6295968 =
      Env.lookup wanted v_r12 := by
  have h0 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 96) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295968) =
    BitVec.extractLsb 7 0 (Env.lookup wanted v_r12) at h0
  have h1 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 97) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295969) =
    BitVec.extractLsb 15 8 (Env.lookup wanted v_r12) at h1
  have h2 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 98) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295970) =
    BitVec.extractLsb 23 16 (Env.lookup wanted v_r12) at h2
  have h3 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 99) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295971) =
    BitVec.extractLsb 31 24 (Env.lookup wanted v_r12) at h3
  have h4 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 100) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295972) =
    BitVec.extractLsb 39 32 (Env.lookup wanted v_r12) at h4
  have h5 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 101) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295973) =
    BitVec.extractLsb 47 40 (Env.lookup wanted v_r12) at h5
  have h6 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 102) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295974) =
    BitVec.extractLsb 55 48 (Env.lookup wanted v_r12) at h6
  have h7 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 103) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295975) =
    BitVec.extractLsb 63 56 (Env.lookup wanted v_r12) at h7
  unfold read64 prepareInputMemory
  rw [h0, h1, h2, h3, h4, h5, h6, h7]
  exact byte_roundtrip (Env.lookup wanted v_r12)
theorem decode_r13 (s : Env Γ) :
    read64 (Env.lookup (captureUpdate.eval s) v_mem) 6295720 =
      Env.lookup s v_r13 := by
  have h0 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 104) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295720) =
    BitVec.extractLsb 7 0 (Env.lookup s v_r13) at h0
  have h1 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 105) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295721) =
    BitVec.extractLsb 15 8 (Env.lookup s v_r13) at h1
  have h2 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 106) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295722) =
    BitVec.extractLsb 23 16 (Env.lookup s v_r13) at h2
  have h3 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 107) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295723) =
    BitVec.extractLsb 31 24 (Env.lookup s v_r13) at h3
  have h4 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 108) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295724) =
    BitVec.extractLsb 39 32 (Env.lookup s v_r13) at h4
  have h5 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 109) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295725) =
    BitVec.extractLsb 47 40 (Env.lookup s v_r13) at h5
  have h6 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 110) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295726) =
    BitVec.extractLsb 55 48 (Env.lookup s v_r13) at h6
  have h7 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 111) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295727) =
    BitVec.extractLsb 63 56 (Env.lookup s v_r13) at h7
  unfold read64
  rw [h0, h1, h2, h3, h4, h5, h6, h7]
  exact byte_roundtrip (Env.lookup s v_r13)
theorem load_reads_r13 (s : Env Γ) :
    Env.lookup (loadUpdate.eval s) v_r13 =
      read64 (Env.lookup s v_mem) 6295976 := rfl
theorem encoded_input_r13 (wanted : Env Γ) (ambient : Mem 64 8) :
    read64 (prepareInputMemory wanted ambient) 6295976 =
      Env.lookup wanted v_r13 := by
  have h0 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 104) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295976) =
    BitVec.extractLsb 7 0 (Env.lookup wanted v_r13) at h0
  have h1 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 105) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295977) =
    BitVec.extractLsb 15 8 (Env.lookup wanted v_r13) at h1
  have h2 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 106) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295978) =
    BitVec.extractLsb 23 16 (Env.lookup wanted v_r13) at h2
  have h3 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 107) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295979) =
    BitVec.extractLsb 31 24 (Env.lookup wanted v_r13) at h3
  have h4 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 108) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295980) =
    BitVec.extractLsb 39 32 (Env.lookup wanted v_r13) at h4
  have h5 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 109) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295981) =
    BitVec.extractLsb 47 40 (Env.lookup wanted v_r13) at h5
  have h6 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 110) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295982) =
    BitVec.extractLsb 55 48 (Env.lookup wanted v_r13) at h6
  have h7 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 111) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295983) =
    BitVec.extractLsb 63 56 (Env.lookup wanted v_r13) at h7
  unfold read64 prepareInputMemory
  rw [h0, h1, h2, h3, h4, h5, h6, h7]
  exact byte_roundtrip (Env.lookup wanted v_r13)
theorem decode_r14 (s : Env Γ) :
    read64 (Env.lookup (captureUpdate.eval s) v_mem) 6295728 =
      Env.lookup s v_r14 := by
  have h0 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 112) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295728) =
    BitVec.extractLsb 7 0 (Env.lookup s v_r14) at h0
  have h1 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 113) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295729) =
    BitVec.extractLsb 15 8 (Env.lookup s v_r14) at h1
  have h2 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 114) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295730) =
    BitVec.extractLsb 23 16 (Env.lookup s v_r14) at h2
  have h3 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 115) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295731) =
    BitVec.extractLsb 31 24 (Env.lookup s v_r14) at h3
  have h4 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 116) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295732) =
    BitVec.extractLsb 39 32 (Env.lookup s v_r14) at h4
  have h5 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 117) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295733) =
    BitVec.extractLsb 47 40 (Env.lookup s v_r14) at h5
  have h6 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 118) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295734) =
    BitVec.extractLsb 55 48 (Env.lookup s v_r14) at h6
  have h7 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 119) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295735) =
    BitVec.extractLsb 63 56 (Env.lookup s v_r14) at h7
  unfold read64
  rw [h0, h1, h2, h3, h4, h5, h6, h7]
  exact byte_roundtrip (Env.lookup s v_r14)
theorem load_reads_r14 (s : Env Γ) :
    Env.lookup (loadUpdate.eval s) v_r14 =
      read64 (Env.lookup s v_mem) 6295984 := rfl
theorem encoded_input_r14 (wanted : Env Γ) (ambient : Mem 64 8) :
    read64 (prepareInputMemory wanted ambient) 6295984 =
      Env.lookup wanted v_r14 := by
  have h0 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 112) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295984) =
    BitVec.extractLsb 7 0 (Env.lookup wanted v_r14) at h0
  have h1 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 113) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295985) =
    BitVec.extractLsb 15 8 (Env.lookup wanted v_r14) at h1
  have h2 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 114) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295986) =
    BitVec.extractLsb 23 16 (Env.lookup wanted v_r14) at h2
  have h3 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 115) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295987) =
    BitVec.extractLsb 31 24 (Env.lookup wanted v_r14) at h3
  have h4 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 116) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295988) =
    BitVec.extractLsb 39 32 (Env.lookup wanted v_r14) at h4
  have h5 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 117) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295989) =
    BitVec.extractLsb 47 40 (Env.lookup wanted v_r14) at h5
  have h6 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 118) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295990) =
    BitVec.extractLsb 55 48 (Env.lookup wanted v_r14) at h6
  have h7 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 119) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295991) =
    BitVec.extractLsb 63 56 (Env.lookup wanted v_r14) at h7
  unfold read64 prepareInputMemory
  rw [h0, h1, h2, h3, h4, h5, h6, h7]
  exact byte_roundtrip (Env.lookup wanted v_r14)
theorem decode_r15 (s : Env Γ) :
    read64 (Env.lookup (captureUpdate.eval s) v_mem) 6295736 =
      Env.lookup s v_r15 := by
  have h0 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 120) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295736) =
    BitVec.extractLsb 7 0 (Env.lookup s v_r15) at h0
  have h1 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 121) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295737) =
    BitVec.extractLsb 15 8 (Env.lookup s v_r15) at h1
  have h2 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 122) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295738) =
    BitVec.extractLsb 23 16 (Env.lookup s v_r15) at h2
  have h3 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 123) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295739) =
    BitVec.extractLsb 31 24 (Env.lookup s v_r15) at h3
  have h4 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 124) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295740) =
    BitVec.extractLsb 39 32 (Env.lookup s v_r15) at h4
  have h5 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 125) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295741) =
    BitVec.extractLsb 47 40 (Env.lookup s v_r15) at h5
  have h6 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 126) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295742) =
    BitVec.extractLsb 55 48 (Env.lookup s v_r15) at h6
  have h7 := (capture_spec s).recorded _
    (List.getElem_mem (l := expectedWrites) (n := 127) (by decide))
  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 6295743) =
    BitVec.extractLsb 63 56 (Env.lookup s v_r15) at h7
  unfold read64
  rw [h0, h1, h2, h3, h4, h5, h6, h7]
  exact byte_roundtrip (Env.lookup s v_r15)
theorem load_reads_r15 (s : Env Γ) :
    Env.lookup (loadUpdate.eval s) v_r15 =
      read64 (Env.lookup s v_mem) 6295992 := rfl
theorem encoded_input_r15 (wanted : Env Γ) (ambient : Mem 64 8) :
    read64 (prepareInputMemory wanted ambient) 6295992 =
      Env.lookup wanted v_r15 := by
  have h0 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 120) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295992) =
    BitVec.extractLsb 7 0 (Env.lookup wanted v_r15) at h0
  have h1 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 121) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295993) =
    BitVec.extractLsb 15 8 (Env.lookup wanted v_r15) at h1
  have h2 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 122) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295994) =
    BitVec.extractLsb 23 16 (Env.lookup wanted v_r15) at h2
  have h3 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 123) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295995) =
    BitVec.extractLsb 31 24 (Env.lookup wanted v_r15) at h3
  have h4 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 124) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295996) =
    BitVec.extractLsb 39 32 (Env.lookup wanted v_r15) at h4
  have h5 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 125) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295997) =
    BitVec.extractLsb 47 40 (Env.lookup wanted v_r15) at h5
  have h6 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 126) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295998) =
    BitVec.extractLsb 55 48 (Env.lookup wanted v_r15) at h6
  have h7 := writes_capture wanted inputWrites ambient _
    input_destinations_unique
    (List.getElem_mem (l := inputWrites) (n := 127) (by decide))
  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 6295999) =
    BitVec.extractLsb 63 56 (Env.lookup wanted v_r15) at h7
  unfold read64 prepareInputMemory
  rw [h0, h1, h2, h3, h4, h5, h6, h7]
  exact byte_roundtrip (Env.lookup wanted v_r15)
def observeGprs (s : Env Γ) : List (BitVec 64) := [Env.lookup s v_rax, Env.lookup s v_rcx, Env.lookup s v_rdx, Env.lookup s v_rbx, Env.lookup s v_rsp, Env.lookup s v_rbp, Env.lookup s v_rsi, Env.lookup s v_rdi, Env.lookup s v_r8, Env.lookup s v_r9, Env.lookup s v_r10, Env.lookup s v_r11, Env.lookup s v_r12, Env.lookup s v_r13, Env.lookup s v_r14, Env.lookup s v_r15]
def decodeRecord (m : Mem 64 8) : List (BitVec 64) := [read64 m 6295616, read64 m 6295624, read64 m 6295632, read64 m 6295640, read64 m 6295648, read64 m 6295656, read64 m 6295664, read64 m 6295672, read64 m 6295680, read64 m 6295688, read64 m 6295696, read64 m 6295704, read64 m 6295712, read64 m 6295720, read64 m 6295728, read64 m 6295736]
def decodeInput (m : Mem 64 8) : List (BitVec 64) := [read64 m 6295872, read64 m 6295880, read64 m 6295888, read64 m 6295896, read64 m 6295904, read64 m 6295912, read64 m 6295920, read64 m 6295928, read64 m 6295936, read64 m 6295944, read64 m 6295952, read64 m 6295960, read64 m 6295968, read64 m 6295976, read64 m 6295984, read64 m 6295992]
theorem decode_capture (s : Env Γ) :
    decodeRecord (Env.lookup (captureUpdate.eval s) v_mem) = observeGprs s := by
  simp only [decodeRecord, observeGprs, decode_rax, decode_rcx, decode_rdx, decode_rbx, decode_rsp, decode_rbp, decode_rsi, decode_rdi, decode_r8, decode_r9, decode_r10, decode_r11, decode_r12, decode_r13, decode_r14, decode_r15]
theorem load_input (s : Env Γ) :
    observeGprs (loadUpdate.eval s) = decodeInput (Env.lookup s v_mem) := by
  simp only [decodeInput, observeGprs, load_reads_rax, load_reads_rcx, load_reads_rdx, load_reads_rbx, load_reads_rsp, load_reads_rbp, load_reads_rsi, load_reads_rdi, load_reads_r8, load_reads_r9, load_reads_r10, load_reads_r11, load_reads_r12, load_reads_r13, load_reads_r14, load_reads_r15]
def prepareInput (wanted : Env Γ) : Env Γ → Env Γ
  | .cons memory (.cons _ rest) =>
    .cons (prepareInputMemory wanted memory) (.cons (BitVec.ofNat 64 4194560) rest)
theorem input_installed (wanted ambient : Env Γ) :
    observeGprs (loadUpdate.eval (prepareInput wanted ambient)) = observeGprs wanted := by
  rw [load_input]
  cases ambient with
  | cons memory tail =>
    cases tail with
    | cons pc rest =>
      change decodeInput (prepareInputMemory wanted memory) = observeGprs wanted
      simp only [decodeInput, observeGprs, encoded_input_rax, encoded_input_rcx, encoded_input_rdx, encoded_input_rbx, encoded_input_rsp, encoded_input_rbp, encoded_input_rsi, encoded_input_rdi, encoded_input_r8, encoded_input_r9, encoded_input_r10, encoded_input_r11, encoded_input_r12, encoded_input_r13, encoded_input_r14, encoded_input_r15]
theorem input_enables_loader (wanted ambient : Env Γ) :
    loadStep.denotes (prepareInput wanted ambient)
      (loadUpdate.eval (prepareInput wanted ambient)) := by
  constructor
  · cases ambient with | cons memory tail => cases tail <;> rfl
  · rfl
/-- The supervisor's modeled handoff changes only the PC. Its concrete
FFI refinement is a separate obligation; no saved-PC correctness is assumed. -/
def enterCapture : Env Γ → Env Γ
  | .cons memory (.cons _ rest) => .cons memory (.cons (BitVec.ofNat 64 4194304) rest)
theorem handoff_preserves_gprs (s : Env Γ) :
    observeGprs (enterCapture s) = observeGprs s := by
  cases s with | cons memory tail => cases tail <;> rfl
theorem handoff_preserves_memory (s : Env Γ) :
    Env.lookup (enterCapture s) v_mem = Env.lookup s v_mem := by
  cases s with | cons memory tail => cases tail <;> rfl
theorem handoff_enables_capture (s : Env Γ) :
    captureStep.denotes (enterCapture s) (captureUpdate.eval (enterCapture s)) := by
  constructor
  · cases s with | cons memory tail => cases tail <;> rfl
  · rfl
/-- A completed observation preserves the model's edge identity and control
outcome. A fault edge is never recategorized as normal completion here.
This record currently observes sixteen GPRs and the saved PC; it does not
claim byte-record capture of flags, vector registers, or all memory. -/
structure Observation (C E : Type) where
  control : C
  edge : E
  savedPC : BitVec 64
  gprs : List (BitVec 64)
def expectedObservation {C E : Type}
    (edge : E) (post : Ayxg.LTS.QfAbv.Config C Γ) : Observation C E :=
  ⟨post.control, edge, Env.lookup post.env v_rip, observeGprs post.env⟩
def captureObservation {C E : Type}
    (edge : E) (post : Ayxg.LTS.QfAbv.Config C Γ) : Observation C E :=
  let savedPC := Env.lookup post.env v_rip
  let captured := captureUpdate.eval (enterCapture post.env)
  ⟨post.control, edge, savedPC, decodeRecord (Env.lookup captured v_mem)⟩
theorem capture_observation_exact {C E : Type}
    (edge : E) (post : Ayxg.LTS.QfAbv.Config C Γ) :
    captureObservation edge post = expectedObservation edge post := by
  simp only [captureObservation, expectedObservation, decode_capture, handoff_preserves_gprs]
/-- Full modeled protocol: concrete extracted input loader, one complete
labeled target step, modeled stopped-state handoff, concrete extracted
capture fragment, and concrete byte decoding. No assumption states that
the capture or decoder is correct; those facts are proved above. -/
def Runs {C E : Type}
    (target : Ayxg.LTS.QfAbv.SymbolicTransitionSystem C Γ E)
    (control : C) (wanted ambient : Env Γ) (edge : E)
    (post : Ayxg.LTS.QfAbv.Config C Γ) (report : Observation C E) : Prop :=
  target.toLTS.Tr ⟨control, loadUpdate.eval (prepareInput wanted ambient)⟩ edge post ∧
  report = captureObservation edge post
theorem end_to_end_observation {C E : Type}
    (target : Ayxg.LTS.QfAbv.SymbolicTransitionSystem C Γ E)
    {control : C} {wanted ambient : Env Γ} {edge : E}
    {post : Ayxg.LTS.QfAbv.Config C Γ} {report : Observation C E}
    (run : Runs target control wanted ambient edge post report) :
    observeGprs (loadUpdate.eval (prepareInput wanted ambient)) = observeGprs wanted ∧
    target.toLTS.Tr ⟨control, loadUpdate.eval (prepareInput wanted ambient)⟩ edge post ∧
    report = expectedObservation edge post := by
  refine ⟨input_installed wanted ambient, run.1, ?_⟩
  exact run.2.trans (capture_observation_exact edge post)
theorem every_modeled_outcome_has_observation {C E : Type}
    (target : Ayxg.LTS.QfAbv.SymbolicTransitionSystem C Γ E)
    {control : C} {wanted ambient : Env Γ} {edge : E}
    {post : Ayxg.LTS.QfAbv.Config C Γ}
    (step : target.toLTS.Tr ⟨control, loadUpdate.eval (prepareInput wanted ambient)⟩ edge post) :
    ∃ report, Runs target control wanted ambient edge post report ∧
      report = expectedObservation edge post := by
  exact ⟨captureObservation edge post, ⟨step, rfl⟩,
    capture_observation_exact edge post⟩
#print axioms end_to_end_observation
#print axioms every_modeled_outcome_has_observation
end MovObserver
