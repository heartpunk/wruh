import Pipeline

set_option maxRecDepth 16384
set_option maxHeartbeats 2000000

namespace MovObserver
open Ayxg.QfAbv
open Ayxg.LTS.QfAbv (SymbolicTransitionSystem Config)
variable [FPInterpretation]

/-- The actual three modeled stages, with intermediate states explicit.
The target may have any labeled outcome. The supervisor saves that outcome
and PC before redirecting the stopped state to the capture fragment.

This is the modeled protocol, not a theorem that Linux ptrace implements it.
In particular, `enterCapture` is the specified OS handoff operation. -/
structure ProtocolExecution {C E : Type}
    (target : SymbolicTransitionSystem C Γ E)
    (control : C) (wanted ambient : Env Γ) (edge : E) (post : Config C Γ) where
  loaded : Env Γ
  captured : Env Γ
  inputStep : loadStep.denotes (prepareInput wanted ambient) loaded
  targetStep : target.toLTS.Tr ⟨control, loaded⟩ edge post
  captureStep : MovObserver.captureStep.denotes (enterCapture post.env) captured

def ProtocolExecution.observation {C E : Type}
    {target : SymbolicTransitionSystem C Γ E}
    {control : C} {wanted ambient : Env Γ} {edge : E} {post : Config C Γ}
    (run : ProtocolExecution target control wanted ambient edge post) : Observation C E :=
  ⟨post.control, edge, Env.lookup post.env v_rip,
    decodeRecord (Env.lookup run.captured v_mem)⟩

/-- Preparing the private input slots and executing the extracted loader cannot
change any other modeled memory byte before the original target step. -/
theorem protocol_input_memory_frame {C E : Type}
    {target : SymbolicTransitionSystem C Γ E}
    {control : C} {wanted ambient : Env Γ} {edge : E} {post : Config C Γ}
    (run : ProtocolExecution target control wanted ambient edge post)
    (a : BitVec 64)
    (outside : ∀ w ∈ inputWrites, a ≠ w.1) :
    Env.lookup run.loaded v_mem a = Env.lookup ambient v_mem a := by
  have input := run.inputStep.2
  change loadUpdate.eval (prepareInput wanted ambient) = run.loaded at input
  rw [← input, loader_preserves_mem]
  cases ambient with
  | cons memory tail =>
    cases tail with
    | cons pc rest =>
      exact writes_frame wanted inputWrites memory a outside

/-- Input fidelity, the identical target transition, exact output decoding,
and both input/capture memory frames follow from the extracted stub semantics.
No hypothesis asserts the observer's desired result. -/
theorem protocol_sound {C E : Type}
    {target : SymbolicTransitionSystem C Γ E}
    {control : C} {wanted ambient : Env Γ} {edge : E} {post : Config C Γ}
    (run : ProtocolExecution target control wanted ambient edge post) :
    observeGprs run.loaded = observeGprs wanted ∧
    (∀ a, (∀ w ∈ inputWrites, a ≠ w.1) →
      Env.lookup run.loaded v_mem a = Env.lookup ambient v_mem a) ∧
    target.toLTS.Tr ⟨control, run.loaded⟩ edge post ∧
    run.observation = expectedObservation edge post ∧
    CaptureSpec (enterCapture post.env) run.captured := by
  have input := run.inputStep.2
  have output := run.captureStep.2
  refine ⟨?_, protocol_input_memory_frame run, run.targetStep, ?_,
    modeled_step_captures run.captureStep⟩
  · rw [← input]
    exact input_installed wanted ambient
  · unfold ProtocolExecution.observation
    rw [← output]
    exact capture_observation_exact edge post

/-- Every target outcome admitted by the current model can be observed by
this modeled protocol. It is not silently restricted to a normal-return edge.
Native faults during the observer itself are outside this total-memory model. -/
theorem protocol_complete {C E : Type}
    (target : SymbolicTransitionSystem C Γ E)
    {control : C} {wanted ambient : Env Γ} {edge : E} {post : Config C Γ}
    (step : target.toLTS.Tr
      ⟨control, loadUpdate.eval (prepareInput wanted ambient)⟩ edge post) :
    Nonempty (ProtocolExecution target control wanted ambient edge post) := by
  exact ⟨{
    loaded := loadUpdate.eval (prepareInput wanted ambient)
    captured := captureUpdate.eval (enterCapture post.env)
    inputStep := input_enables_loader wanted ambient
    targetStep := step
    captureStep := handoff_enables_capture post.env
  }⟩

#print axioms protocol_input_memory_frame
#print axioms protocol_sound
#print axioms protocol_complete
end MovObserver
