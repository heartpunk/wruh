import Wruh.AngrDriver

namespace Wruh.AngrDriverExamples

open Wruh.AngrDriver

example :
    parseFaultKind "Ijk_SigTRAP" (some "general_protection") =
      .ok (some .generalProtection) := by
  decide

example :
    parseFaultKind "Ijk_SigTRAP" (some "signal_trap") =
      .ok (some .signalTrap) := by
  decide

example : faultKindName .generalProtection = "general_protection" := by
  rfl

example : faultKindName .signalTrap = "signal_trap" := by
  rfl

example :
    parseFaultKind "Ijk_SigTRAP" none =
      .error "missing fault_kind for Ijk_SigTRAP" := by
  decide

end Wruh.AngrDriverExamples
