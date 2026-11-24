import Lake
open Lake DSL

package wruh

-- The integration uses an explicit isolated AYXG checkout. Its qualified Nix
-- environment supplies the matching Lean toolchain and pinned FloatLib source.
require ayxg from (run_io do
  let some source ← IO.getEnv "WRUH_AYXG_SOURCE"
    | throw <| IO.userError "Run Lake through nix develop: WRUH_AYXG_SOURCE missing"
  return source)

lean_lib Wruh where
  globs := #[`Wruh.*]

lean_exe «wruh-fresh» where
  root := `Wruh.AngrMain
