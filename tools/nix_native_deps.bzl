"""Ghot's declared libstdc++ and qualified REAPI worker runtime for Wruh."""

_RUNTIME_ENV = "GHOT_REAPI_WORKER_RUNTIME_ROOT"
_LIBSTDCXX_ENV = "GHOT_NIX_LIBSTDCXX_ROOT"


def _repository_impl(ctx):
    runtime = ctx.os.environ.get(_RUNTIME_ENV)
    library_root = ctx.os.environ.get(_LIBSTDCXX_ENV)
    for name, path in [(_RUNTIME_ENV, runtime), (_LIBSTDCXX_ENV, library_root)]:
        if not path or not path.startswith("/nix/store/"):
            fail("{} must name an immutable Nix store output".format(name))
    if not ctx.path(runtime + "/bin/python3").exists:
        fail("{} lacks bin/python3".format(_RUNTIME_ENV))
    library = ctx.path(library_root + "/lib/libstdc++.so.6")
    if not library.exists:
        fail("{} lacks lib/libstdc++.so.6".format(_LIBSTDCXX_ENV))
    ctx.file("runtime.bzl", 'REAPI_WORKER_RUNTIME_ROOT = "{}"\n'.format(runtime))
    ctx.file("lib/.keep", "")
    ctx.symlink(library, "lib/libstdc++.so.6")
    ctx.file("BUILD.bazel", """\
package(default_visibility = ["//visibility:public"])
exports_files(["runtime.bzl"])
filegroup(name = "libstdcxx", srcs = ["lib/libstdc++.so.6"])
""")


_repository = repository_rule(
    implementation = _repository_impl,
    configure = True,
    environ = [_RUNTIME_ENV, _LIBSTDCXX_ENV],
    local = True,
)


def _extension_impl(_module_ctx):
    _repository(name = "nix_native_deps")


nix_native_deps = module_extension(implementation = _extension_impl)
