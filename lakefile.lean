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

lean_lib ObserverShim where
  srcDir := "experiments/mov_observer/native_shim"
  globs := #[`MemoryWrite]

lean_lib ObserverNative where
  srcDir := "experiments/mov_observer/native_observer"
  globs := #[`InstallationEncoding, `FlagsBuffer, `Observer]

lean_lib IFormPbt where
  srcDir := "experiments/iform_pbt"
  globs := #[`GeneratedCase, `ExtractCase, `ModelFootprint, `ConcreteModel, `CompareCase]

lean_exe «wruh-iform-pbt» where
  root := `Campaign
  srcDir := "experiments/iform_pbt"

extern_lib observer_native pkg := do
  let transport ← inputTextFile <| pkg.dir / "experiments" / "mov_observer" / "native_observer" / "transport.S"
  let memory ← inputTextFile <| pkg.dir / "experiments" / "mov_observer" / "native_shim" / "write_memory.S"
  let transportObject ← buildO (pkg.buildDir / "ir" / "observer_transport.o") transport
  let memoryObject ← buildO (pkg.buildDir / "ir" / "observer_memory.o") memory
  buildStaticLib (pkg.staticLibDir / nameToStaticLib "observer_native") #[transportObject, memoryObject]
