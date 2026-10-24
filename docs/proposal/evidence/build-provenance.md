# Bazel and Nix provenance anchors

This evidence note records repository structures that support extending the extraction ontology’s PROV-O provenance chain through build activities. It is not evidence that every historical extraction target was built by this exact workflow.

- [`MODULE.bazel`](../../../MODULE.bazel) declares the `wruh` Bazel module, dependencies, and an `ifrl` source override at a fixed commit. [`MODULE.bazel.lock`](../../../MODULE.bazel.lock) records resolved Bazel module metadata and lock information.
- [`flake.nix`](../../../flake.nix) declares the `ifrl`, `ayxg`, and `nixpkgs` flake inputs, supplies the angr environment, and selects `bazel_9` on Linux or Bazelisk on macOS. [`flake.lock`](../../../flake.lock) records locked flake inputs.
- [`tools/nix_native_deps.bzl`](../../../tools/nix_native_deps.bzl) has Bazel repository rules that consume immutable `/nix/store` paths, including the Nix-provided angr environment and native runtime dependencies.
- [`scripts/stage-angr-nix`](../../../scripts/stage-angr-nix) pins the `angr-nix` source commit used for its staging procedure.

The ontology should record each actual build or realization as a PROV-O `Activity`, associate the exact Bazel/Nix release entities used with that activity, record build inputs where available, and relate the activity to the binary objects, analyzed image, or tool-release entities it generated. The repository anchors establish that these concepts fit the project; the run record must still state which versions were actually used. A lockfile or source revision is provenance evidence, not a source-to-function mapping.
