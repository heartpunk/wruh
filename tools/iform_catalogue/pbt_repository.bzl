"""Expose the pinned Nix Python packages as declared Bazel runfiles."""

def _impl(ctx):
    root = ctx.os.environ.get("WRUH_PBT_PYTHON")
    if not root or not root.startswith("/nix/store/"):
        fail("WRUH_PBT_PYTHON must name the pinned Nix Python environment")
    site = ctx.path(root + "/lib/python3.12/site-packages")
    if not site.get_child("iced_x86/__init__.py").exists or not site.get_child("hypothesis/__init__.py").exists:
        fail("WRUH_PBT_PYTHON must contain iced_x86 and hypothesis")
    ctx.symlink(site, "site-packages")
    ctx.file("BUILD.bazel", """load("@rules_python//python:defs.bzl", "py_library")
package(default_visibility = ["//visibility:public"])
py_library(
    name = "pkg",
    srcs = glob(["site-packages/**/*.py"]),
    data = glob(["site-packages/**/*"], exclude = ["**/*.py", "**/__pycache__/**"]),
    imports = ["site-packages"],
)
""")

pbt_python_repository = repository_rule(
    implementation = _impl,
    environ = ["WRUH_PBT_PYTHON"],
    local = True,
    configure = True,
)
