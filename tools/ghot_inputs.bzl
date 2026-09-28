"""Declare Ghot-owned TinyMemory inputs without copying them into Wruh."""

_GHOT_ROOT_ENV = "WRUH_GHOT_ROOT"
_INPUTS = {
    "tinymemory_wruh_provider.py": "extractor/tinymemory_wruh_provider.py",
    "handler_authority.json": "extractor/handler_authority.json",
    "external_effects.py": "extractor/external_effects.py",
    "primitive.py": "extractor/primitive.py",
    "tinymemory_linux_x86_64_cfg.json": "bazel-bin/extractor/tinymemory_linux_x86_64_cfg.json",
    "tinymemory_linux_x86_64_manifest.json": "bazel-bin/extractor/tinymemory_linux_x86_64_manifest.json",
    "extractor_artifact": "bazel-bin/rust/tinymemory/extractor_artifact",
}


def _repository_impl(ctx):
    root = ctx.os.environ.get(_GHOT_ROOT_ENV)
    if not root or not root.startswith("/"):
        fail("{} must name an absolute Ghot checkout with a built ELF".format(_GHOT_ROOT_ENV))
    for name, relative in _INPUTS.items():
        source = ctx.path(root + "/" + relative)
        if not source.exists:
            fail("missing Ghot input {} at {}".format(name, source))
        ctx.symlink(source, name)
    ctx.file("BUILD.bazel", """\
package(default_visibility = ["//visibility:public"])
exports_files([
    "tinymemory_wruh_provider.py",
    "handler_authority.json",
    "external_effects.py",
    "primitive.py",
    "tinymemory_linux_x86_64_cfg.json",
    "tinymemory_linux_x86_64_manifest.json",
    "extractor_artifact",
])
filegroup(
    name = "provider_bundle",
    srcs = [
        "handler_authority.json",
        "external_effects.py",
        "primitive.py",
    ],
)
""")


ghot_inputs_repository = repository_rule(
    implementation = _repository_impl,
    configure = True,
    environ = [_GHOT_ROOT_ENV],
    local = True,
)
