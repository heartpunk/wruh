import Lake
open Lake DSL

package wruh

-- Keep the Lake edge on the same immutable AYXG revision as flake.nix/flake.lock.
require ayxg from git
  "https://github.com/heartpunk/ayxg.git" @ "4ca2cf940f9ecb3bcb5a021fe8dfb2d9b80c2ede"

lean_lib Wruh where
  globs := #[`Wruh.*]

lean_exe «wruh-fresh» where
  root := `Wruh.AngrMain
