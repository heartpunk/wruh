import Lake
open Lake DSL

package wruh

-- Keep the Lake edge on the same immutable AYXG revision as flake.nix/flake.lock.
require ayxg from git
  "https://github.com/heartpunk/ayxg.git" @ "43a701de2dcd7515faa1f0180c1d59ae3420a2b5"

lean_lib Wruh where
  globs := #[`Wruh.*]

lean_exe «wruh-fresh» where
  root := `Wruh.AngrMain
