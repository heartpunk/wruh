import Lake
open Lake DSL

package wruh

-- Keep the Lake edge on the same immutable AYXG revision as flake.nix/flake.lock.
require ayxg from git
  "https://github.com/heartpunk/ayxg.git" @ "3fee3ef8d1e056be85d97756acf9aceb1a634c49"

lean_lib Wruh where
  globs := #[`Wruh.*]

lean_exe «wruh-fresh» where
  root := `Wruh.AngrMain
