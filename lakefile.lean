import Lake
open Lake DSL

package wruh

-- The integration uses an explicit isolated AYXG checkout. Its qualified Nix
-- environment supplies the matching Lean toolchain and pinned FloatLib source.
require ayxg from (run_io do
  let some source ← IO.getEnv "WRUH_AYXG_SOURCE"
    | throw <| IO.userError "Set WRUH_AYXG_SOURCE to the AYXG integration checkout"
  return System.FilePath.mk source)

lean_lib Wruh where
  globs := #[`Wruh.*]
