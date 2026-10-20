import Lake
open Lake DSL

package wruh

-- The integration uses an explicit isolated AYXG checkout. Its qualified Nix
-- environment supplies the matching Lean toolchain and pinned FloatLib source.
require ayxg from git
  "https://github.com/heartpunk/ayxg.git" @ "ee82ce56fe2f5e6c337f671c74b1ad9098890e9e"

lean_lib Wruh where
  globs := #[`Wruh.*]

lean_exe «wruh-fresh» where
  root := `Wruh.AngrMain
