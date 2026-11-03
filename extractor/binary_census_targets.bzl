load("@rules_python//python:defs.bzl", "py_test")
load("@wruh_census_binaries//:metadata.bzl", "CENSUS_METADATA")


_CENSUS_REMOTE_TARGETS = [
    ("lua", "interpreter", "Lua"),
    ("quickjs", "interpreter", "QuickJS"),
    ("cpython", "interpreter", "CPython"),
    ("apache", "generic", None),
    ("node", "interpreter", "Node.js"),
    ("bun", "interpreter", "Bun"),
]


def _binary_census_remote_test(target_id, target_kind, implementation):
    metadata = CENSUS_METADATA[target_id]
    args = [
        "--binary",
        "$(rlocationpath @wruh_census_binaries//:{})".format(target_id),
        "--binary-identifier",
        metadata["binary_identifier"],
        "--target-id",
        target_id,
        "--target-kind",
        target_kind,
        "--target-version",
        metadata["target_version"],
        "--target-platform",
        "x86_64-linux",
        "--build-package",
        metadata["build_package"],
        "--build-configuration",
        metadata["build_configuration"],
        "--build-output",
        metadata["build_output"],
        "--nixpkgs-revision",
        metadata["nixpkgs_revision"],
        "--ayxg-revision",
        metadata["ayxg_revision"],
    ]
    if target_id == "bun":
        args.extend(["--inventory-mode", "cfgfast"])
    if implementation:
        args.extend(["--target-implementation", implementation])

    py_test(
        name = "binary_census_{}_remote_test".format(target_id),
        srcs = ["binary_census.py"],
        main = "binary_census.py",
        size = "enormous",
        timeout = "eternal",
        args = args,
        data = [
            "@nix_native_deps//:libstdcxx",
            "@wruh_census_binaries//:{}".format(target_id),
        ],
        env = {
            "GHOT_LIBSTDCXX_RLOCATION": "$(rlocationpath @nix_native_deps//:libstdcxx)",
            "PYTHONNOUSERSITE": "1",
            "PYTHONSAFEPATH": "1",
        },
        deps = [":binary_census_runtime"],
        target_compatible_with = ["@platforms//os:linux", "@platforms//cpu:x86_64"],
    )


def binary_census_remote_tests():
    for target_id, target_kind, implementation in _CENSUS_REMOTE_TARGETS:
        _binary_census_remote_test(target_id, target_kind, implementation)
