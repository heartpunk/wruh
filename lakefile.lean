import Lake
open Lake DSL

package wruh

-- The integration uses an explicit isolated AYXG checkout. Its qualified Nix
-- environment supplies the matching Lean toolchain and pinned FloatLib source.
require ayxg from git
  "https://github.com/heartpunk/ayxg.git" @ "885e5d86ba5ef606aa65e81cbfaecaa98770f2df"

lean_lib Wruh where
  globs := #[`Wruh.*]

lean_exe «wruh-fresh» where
  root := `Wruh.AngrMain
