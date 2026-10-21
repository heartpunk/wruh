import Lake
open Lake DSL

package wruh

-- The integration uses an explicit isolated AYXG checkout. Its qualified Nix
-- environment supplies the matching Lean toolchain and pinned FloatLib source.
require ayxg from git
  "https://github.com/heartpunk/ayxg.git" @ "f643678e5ac49d1268e4bc5480e26821164d7ffa"

lean_lib Wruh where
  globs := #[`Wruh.*]

lean_exe «wruh-fresh» where
  root := `Wruh.AngrMain
