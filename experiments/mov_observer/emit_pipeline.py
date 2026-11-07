"""Generate concrete per-slot proof goals; no axioms or admitted proofs."""
from pathlib import Path
from stub import GPRS, INPUT, RECORD, LOAD_CODE, CODE


def main(output=Path("Pipeline.lean")):
    lines = ["import Proof", "import InputModel", "import ByteCodec",
             "set_option maxRecDepth 16384", "set_option maxHeartbeats 2000000",
             "namespace MovObserver", "open Ayxg.QfAbv", "variable [FPInterpretation]",
             "def inputWrites : List ByteWrite :=",
             "  expectedWrites.map fun w => (w.1 + BitVec.ofNat 64 256, w.2)",
             "theorem input_destinations_unique : (inputWrites.map Prod.fst).Nodup := by decide",
             "def prepareInputMemory (wanted : Env Γ) (ambient : Mem 64 8) : Mem 64 8 :=",
             "  applyWrites wanted inputWrites ambient"]
    for index, name in enumerate(GPRS):
        lines += [f"theorem decode_{name} (s : Env Γ) :",
                  f"    read64 (Env.lookup (captureUpdate.eval s) v_mem) {RECORD+8*index} =",
                  f"      Env.lookup s v_{name} := by"]
        for byte in range(8):
            position = 8*index+byte
            lines += [f"  have h{byte} := (capture_spec s).recorded _",
                      f"    (List.getElem_mem (l := expectedWrites) (n := {position}) (by decide))",
                      f"  change Env.lookup (captureUpdate.eval s) v_mem (BitVec.ofNat 64 {RECORD+position}) =",
                      f"    BitVec.extractLsb {8*byte+7} {8*byte} (Env.lookup s v_{name}) at h{byte}"]
        lines += ["  unfold read64", "  rw [" + ", ".join(f"h{b}" for b in range(8)) + "]",
                  f"  exact byte_roundtrip (Env.lookup s v_{name})"]
        lines += [f"theorem load_reads_{name} (s : Env Γ) :",
                  f"    Env.lookup (loadUpdate.eval s) v_{name} =",
                  f"      read64 (Env.lookup s v_mem) {INPUT+8*index} := rfl"]
        lines += [f"theorem encoded_input_{name} (wanted : Env Γ) (ambient : Mem 64 8) :",
                  f"    read64 (prepareInputMemory wanted ambient) {INPUT+8*index} =",
                  f"      Env.lookup wanted v_{name} := by"]
        for byte in range(8):
            position = 8*index+byte
            lines += [f"  have h{byte} := writes_capture wanted inputWrites ambient _",
                      "    input_destinations_unique",
                      f"    (List.getElem_mem (l := inputWrites) (n := {position}) (by decide))",
                      f"  change applyWrites wanted inputWrites ambient (BitVec.ofNat 64 {INPUT+position}) =",
                      f"    BitVec.extractLsb {8*byte+7} {8*byte} (Env.lookup wanted v_{name}) at h{byte}"]
        lines += ["  unfold read64 prepareInputMemory", "  rw [" +
                  ", ".join(f"h{b}" for b in range(8)) + "]",
                  f"  exact byte_roundtrip (Env.lookup wanted v_{name})"]
    lines += ["def observeGprs (s : Env Γ) : List (BitVec 64) := [" +
              ", ".join(f"Env.lookup s v_{name}" for name in GPRS) + "]",
              "def decodeRecord (m : Mem 64 8) : List (BitVec 64) := [" +
              ", ".join(f"read64 m {RECORD+8*i}" for i in range(16)) + "]",
              "def decodeInput (m : Mem 64 8) : List (BitVec 64) := [" +
              ", ".join(f"read64 m {INPUT+8*i}" for i in range(16)) + "]",
              "theorem decode_capture (s : Env Γ) :",
              "    decodeRecord (Env.lookup (captureUpdate.eval s) v_mem) = observeGprs s := by",
              "  simp only [decodeRecord, observeGprs, " +
              ", ".join(f"decode_{name}" for name in GPRS) + "]",
              "theorem load_input (s : Env Γ) :",
              "    observeGprs (loadUpdate.eval s) = decodeInput (Env.lookup s v_mem) := by",
              "  simp only [decodeInput, observeGprs, " +
              ", ".join(f"load_reads_{name}" for name in GPRS) + "]",
              "def prepareInput (wanted : Env Γ) : Env Γ → Env Γ",
              "  | .cons memory (.cons _ rest) =>",
              f"    .cons (prepareInputMemory wanted memory) (.cons (BitVec.ofNat 64 {LOAD_CODE}) rest)",
              "theorem input_installed (wanted ambient : Env Γ) :",
              "    observeGprs (loadUpdate.eval (prepareInput wanted ambient)) = observeGprs wanted := by",
              "  rw [load_input]",
              "  cases ambient with",
              "  | cons memory tail =>",
              "    cases tail with",
              "    | cons pc rest =>",
              "      change decodeInput (prepareInputMemory wanted memory) = observeGprs wanted",
              "      simp only [decodeInput, observeGprs, " +
              ", ".join(f"encoded_input_{name}" for name in GPRS) + "]",
              "theorem input_enables_loader (wanted ambient : Env Γ) :",
              "    loadStep.denotes (prepareInput wanted ambient)",
              "      (loadUpdate.eval (prepareInput wanted ambient)) := by",
              "  constructor",
              "  · cases ambient with | cons memory tail => cases tail <;> rfl",
              "  · rfl",
              "/-- The supervisor's modeled handoff changes only the PC. Its concrete",
              "FFI refinement is a separate obligation; no saved-PC correctness is assumed. -/",
              "def enterCapture : Env Γ → Env Γ",
              f"  | .cons memory (.cons _ rest) => .cons memory (.cons (BitVec.ofNat 64 {CODE}) rest)",
              "theorem handoff_preserves_gprs (s : Env Γ) :",
              "    observeGprs (enterCapture s) = observeGprs s := by",
              "  cases s with | cons memory tail => cases tail <;> rfl",
              "theorem handoff_preserves_memory (s : Env Γ) :",
              "    Env.lookup (enterCapture s) v_mem = Env.lookup s v_mem := by",
              "  cases s with | cons memory tail => cases tail <;> rfl",
              "theorem handoff_enables_capture (s : Env Γ) :",
              "    captureStep.denotes (enterCapture s) (captureUpdate.eval (enterCapture s)) := by",
              "  constructor",
              "  · cases s with | cons memory tail => cases tail <;> rfl",
              "  · rfl",
              "/-- A completed observation preserves the model's edge identity and control",
              "outcome. A fault edge is never recategorized as normal completion here.",
              "This record currently observes sixteen GPRs and the saved PC; it does not",
              "claim byte-record capture of flags, vector registers, or all memory. -/",
              "structure Observation (C E : Type) where",
              "  control : C", "  edge : E", "  savedPC : BitVec 64",
              "  gprs : List (BitVec 64)",
              "def expectedObservation {C E : Type}",
              "    (edge : E) (post : Ayxg.LTS.QfAbv.Config C Γ) : Observation C E :=",
              "  ⟨post.control, edge, Env.lookup post.env v_rip, observeGprs post.env⟩",
              "def captureObservation {C E : Type}",
              "    (edge : E) (post : Ayxg.LTS.QfAbv.Config C Γ) : Observation C E :=",
              "  let savedPC := Env.lookup post.env v_rip",
              "  let captured := captureUpdate.eval (enterCapture post.env)",
              "  ⟨post.control, edge, savedPC, decodeRecord (Env.lookup captured v_mem)⟩",
              "theorem capture_observation_exact {C E : Type}",
              "    (edge : E) (post : Ayxg.LTS.QfAbv.Config C Γ) :",
              "    captureObservation edge post = expectedObservation edge post := by",
              "  simp only [captureObservation, expectedObservation, decode_capture, handoff_preserves_gprs]",
              "/-- Full modeled protocol: concrete extracted input loader, one complete",
              "labeled target step, modeled stopped-state handoff, concrete extracted",
              "capture fragment, and concrete byte decoding. No assumption states that",
              "the capture or decoder is correct; those facts are proved above. -/",
              "def Runs {C E : Type}",
              "    (target : Ayxg.LTS.QfAbv.SymbolicTransitionSystem C Γ E)",
              "    (control : C) (wanted ambient : Env Γ) (edge : E)",
              "    (post : Ayxg.LTS.QfAbv.Config C Γ) (report : Observation C E) : Prop :=",
              "  target.toLTS.Tr ⟨control, loadUpdate.eval (prepareInput wanted ambient)⟩ edge post ∧",
              "  report = captureObservation edge post",
              "theorem end_to_end_observation {C E : Type}",
              "    (target : Ayxg.LTS.QfAbv.SymbolicTransitionSystem C Γ E)",
              "    {control : C} {wanted ambient : Env Γ} {edge : E}",
              "    {post : Ayxg.LTS.QfAbv.Config C Γ} {report : Observation C E}",
              "    (run : Runs target control wanted ambient edge post report) :",
              "    observeGprs (loadUpdate.eval (prepareInput wanted ambient)) = observeGprs wanted ∧",
              "    target.toLTS.Tr ⟨control, loadUpdate.eval (prepareInput wanted ambient)⟩ edge post ∧",
              "    report = expectedObservation edge post := by",
              "  refine ⟨input_installed wanted ambient, run.1, ?_⟩",
              "  exact run.2.trans (capture_observation_exact edge post)",
              "theorem every_modeled_outcome_has_observation {C E : Type}",
              "    (target : Ayxg.LTS.QfAbv.SymbolicTransitionSystem C Γ E)",
              "    {control : C} {wanted ambient : Env Γ} {edge : E}",
              "    {post : Ayxg.LTS.QfAbv.Config C Γ}",
              "    (step : target.toLTS.Tr ⟨control, loadUpdate.eval (prepareInput wanted ambient)⟩ edge post) :",
              "    ∃ report, Runs target control wanted ambient edge post report ∧",
              "      report = expectedObservation edge post := by",
              "  exact ⟨captureObservation edge post, ⟨step, rfl⟩,",
              "    capture_observation_exact edge post⟩",
              "#print axioms end_to_end_observation",
              "#print axioms every_modeled_outcome_has_observation",
              "end MovObserver"]
    output.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    import sys
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("Pipeline.lean"))
