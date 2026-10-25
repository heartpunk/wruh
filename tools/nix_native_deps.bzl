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
    identity = json.decode(ctx.read(Label("//evidence/cpython:identity.json")))
    cpython_files = []
    for index, record in enumerate(identity["objects"]):
        source = ctx.path(record["resolved_path"])
        if not source.exists:
            fail("pinned CPython closure object missing: {}".format(source))
        destination = "cpython/object_{}/{}".format(index, source.basename)
        ctx.symlink(source, destination)
        cpython_files.append(destination)
    ctx.file("BUILD.bazel", """\
package(default_visibility = ["//visibility:public"])
exports_files(["runtime.bzl"])
filegroup(name = "libstdcxx", srcs = ["lib/libstdc++.so.6"])
filegroup(name = "cpython_closure", srcs = glob(["cpython/**/*"]))
exports_files(glob(["cpython/**/*"]))
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


_ANGR_ENV = "GHOT_NIX_ANGR_ROOT"


def _angr_repository_impl(ctx):
    root = ctx.os.environ.get(_ANGR_ENV)
    if not root or not root.startswith("/nix/store/"):
        fail("{} must name an immutable Nix store output".format(_ANGR_ENV))
    site = ctx.path(root + "/lib/python3.12/site-packages")
    if not site.get_child("angr/__init__.py").exists:
        fail("{} lacks the Python 3.12 angr package".format(_ANGR_ENV))
    ctx.symlink(site, "site-packages")
    ctx.file("BUILD.bazel", """\
load("@rules_python//python:defs.bzl", "py_library")
package(default_visibility = ["//visibility:public"])
py_library(
    name = "pkg",
    srcs = glob(["site-packages/angr/**/*.py"]),
    data = glob(["site-packages/angr/**/*", "site-packages/angr-*.dist-info/**/*"], exclude = ["**/*.py", "**/__pycache__/**"]),
    imports = ["site-packages"],
    deps = ["@wruh_pypi//{}:pkg".format(name) for name in [
        "angr_data", "archinfo", "cachetools", "capstone", "cffi", "cle",
        "cxxheaderparser", "gitpython", "lmdb", "msgspec", "mulpyplexer",
        "networkx", "platformdirs", "protobuf", "psutil", "pycparser",
        "pydemumble", "pypcode", "pyvex", "rich", "sortedcontainers", "sympy",
        "typing_extensions", "z3_solver",
    ]],
)
""")


_angr_repository = repository_rule(
    implementation = _angr_repository_impl,
    configure = True,
    environ = [_ANGR_ENV],
    local = True,
)


def _angr_extension_impl(_module_ctx):
    _angr_repository(name = "nix_angr")


nix_angr = module_extension(implementation = _angr_extension_impl)


_AYXG_SOURCE_ENV = "WRUH_AYXG_SOURCE"


def _ayxg_repository_impl(ctx):
    root = ctx.os.environ.get(_AYXG_SOURCE_ENV)
    if not root or not root.startswith("/nix/store/"):
        fail("{} must name an immutable Nix store source".format(_AYXG_SOURCE_ENV))
    package = ctx.path(root + "/python/ayxg")
    if not package.get_child("__init__.py").exists:
        fail("{} lacks python/ayxg/__init__.py".format(_AYXG_SOURCE_ENV))
    ctx.symlink(ctx.path(root + "/python"), "python")
    ctx.file("BUILD.bazel", """load("@rules_python//python:defs.bzl", "py_library")
package(default_visibility = ["//visibility:public"])
py_library(
    name = "ayxg",
    srcs = glob(["python/ayxg/*.py"], exclude = ["python/ayxg/z3.py", "python/ayxg/fp_z3.py"]),
    data = ["python/ayxg/py.typed"],
    imports = ["python"],
)
py_library(
    name = "z3",
    srcs = ["python/ayxg/z3.py", "python/ayxg/fp_z3.py"],
    imports = ["python"],
    deps = [":ayxg", "@shared_angr//:pkg"],
)
""")


ayxg_python_repository = repository_rule(
    implementation = _ayxg_repository_impl,
    configure = True,
    environ = [_AYXG_SOURCE_ENV],
    local = True,
)


_CENSUS_BINARY_ENV = "WRUH_CENSUS_BINARY"


def _census_binary_repository_impl(ctx):
    binary = ctx.os.environ.get(_CENSUS_BINARY_ENV)
    if binary:
        if not binary.startswith("/nix/store/"):
            fail("{} must name an immutable Nix store file".format(_CENSUS_BINARY_ENV))
        path = ctx.path(binary)
        if not path.exists:
            fail("{} does not exist: {}".format(_CENSUS_BINARY_ENV, binary))
        ctx.symlink(path, "binary")
        sources = '["binary"]'
    else:
        # Keep ordinary Bazel queries and unrelated targets usable when no
        # census binary has been selected by the GitHub Actions job.
        ctx.file("binary", "")
        sources = '["binary"]'

    ctx.file("BUILD.bazel", """\
package(default_visibility = ["//visibility:public"])
filegroup(name = "binary", srcs = {})
""".format(sources))


census_binary_repository = repository_rule(
    implementation = _census_binary_repository_impl,
    configure = True,
    environ = [_CENSUS_BINARY_ENV],
    local = True,
)
