"""Analysis-time settings and local fresh-extraction actions."""

def _integer_setting_impl(ctx):
    if ctx.build_setting_value <= 0:
        fail("extraction settings must be positive")
    return [Setting(value = ctx.build_setting_value)]

Setting = provider(fields = ["value"])

integer_setting = rule(
    implementation = _integer_setting_impl,
    build_setting = config.int(flag = True),
)

def _settings_impl(ctx):
    ctx.actions.write(ctx.outputs.out, json.encode({
        "scope_bytes": ctx.attr.scope_bytes[Setting].value,
        "window_bytes": ctx.attr.window_bytes[Setting].value,
    }))

extraction_settings = rule(
    implementation = _settings_impl,
    attrs = {
        "out": attr.output(mandatory = True),
        "scope_bytes": attr.label(mandatory = True, providers = [Setting]),
        "window_bytes": attr.label(mandatory = True, providers = [Setting]),
    },
)

_PYTHON_TOOLCHAIN = "@rules_python//python:toolchain_type"

def _python_path(ctx):
    runtime = ctx.toolchains[_PYTHON_TOOLCHAIN].py3_runtime
    if not runtime.interpreter_path:
        fail("Lua extraction requires the registered Nix Python runtime")
    return runtime.interpreter_path.rsplit("/", 1)[0]

def _shard_impl(ctx):
    runtime = ctx.file._libstdcxx.short_path
    ctx.actions.run(
        executable = ctx.attr._extractor[DefaultInfo].files_to_run,
        inputs = [ctx.file.image, ctx.file.selector],
        outputs = [ctx.outputs.out],
        arguments = [
            "--artifact",
            ctx.file.image.path,
            "--selector",
            ctx.file.selector.path,
            "--output",
            ctx.outputs.out.path,
        ],
        env = {
            "GHOT_LIBSTDCXX_RLOCATION": runtime[3:],
            "PATH": _python_path(ctx),
        },
        mnemonic = "WruhExtractShard",
    )

extract_shard = rule(
    implementation = _shard_impl,
    toolchains = [_PYTHON_TOOLCHAIN],
    attrs = {
        "image": attr.label(allow_single_file = True, mandatory = True),
        "out": attr.output(mandatory = True),
        "selector": attr.label(allow_single_file = True, mandatory = True),
        "_extractor": attr.label(default = "//extractor:fresh_extract", executable = True, cfg = "exec"),
        "_libstdcxx": attr.label(default = "@nix_native_deps//:libstdcxx", allow_single_file = True, cfg = "exec"),
    },
)

def _merge_impl(ctx):
    if not ctx.files.shards:
        fail("No Lua extraction jobs. Run scripts/extract-lua to prepare the catalog.")
    args = ctx.actions.args()
    args.add(ctx.file.metadata)
    args.add(ctx.outputs.out)
    args.add_all(ctx.files.shards)
    ctx.actions.run(
        executable = ctx.attr._merge[DefaultInfo].files_to_run,
        inputs = [ctx.file.metadata] + ctx.files.shards,
        outputs = [ctx.outputs.out],
        arguments = [args],
        env = {"PATH": _python_path(ctx)},
        mnemonic = "WruhMergeShards",
    )

merge_shards = rule(
    implementation = _merge_impl,
    toolchains = [_PYTHON_TOOLCHAIN],
    attrs = {
        "metadata": attr.label(allow_single_file = True, mandatory = True),
        "out": attr.output(mandatory = True),
        "shards": attr.label_list(allow_files = True),
        "_merge": attr.label(default = "//extractor:merge_fresh", executable = True, cfg = "exec"),
    },
)

def _empty_catalog_impl(ctx):
    ctx.file("jobs.bzl", "SELECTORS = []\n")
    ctx.file("metadata.json", "{}\n")
    ctx.file("BUILD.bazel", 'exports_files(["jobs.bzl", "metadata.json"], visibility = ["//visibility:public"])\n')

catalog_repository = repository_rule(implementation = _empty_catalog_impl)

def lua_bundle(selectors):
    shards = []
    for selector in selectors:
        name = selector[:-5]
        extract_shard(
            name = name,
            selector = "@wruh_lua_catalog//:" + selector,
            image = "@wruh_lua_catalog//:lua.elf",
            out = name + ".ayxg",
        )
        shards.append(":" + name)
    merge_shards(
        name = "bundle",
        metadata = "@wruh_lua_catalog//:metadata.json",
        shards = shards,
        out = "lua.ayxg",
        tags = ["manual"],
    )
