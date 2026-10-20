import Lake
open Lake DSL

package wruh

-- The integration uses an explicit isolated AYXG checkout. Its qualified Nix
-- environment supplies the matching Lean toolchain and pinned FloatLib source.
require ayxg from git
  "https://github.com/heartpunk/ayxg.git" @ "fe01a093ea197b84e92f11f18804814d8f9a9448"

lean_lib Wruh where
  globs := #[`Wruh.*]

lean_exe «wruh-fresh» where
  root := `Wruh.AngrMain
