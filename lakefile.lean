import Lake
open Lake DSL

package wruh

-- The integration uses an explicit isolated AYXG checkout. Its qualified Nix
-- environment supplies the matching Lean toolchain and pinned FloatLib source.
require ayxg from git
  "https://github.com/heartpunk/ayxg.git" @ "ada7c821a3d7610d9d3cd2d17cd2f1ab48537579"

require hegel from git
  "https://github.com/heartpunk/hegel-lean.git" @ "e402742baedef2aa584d309760d56ec6f19d4f83"

lean_lib Wruh where
  globs := #[`Wruh.*]

lean_exe «wruh-fresh» where
  root := `Wruh.AngrMain
