"""One-output action rule suitable for local or REAPI execution."""

load("@nix_native_deps//:runtime.bzl", "REAPI_WORKER_RUNTIME_ROOT")

ReapiArtifactBundleInfo = provider(
    "A structurally grouped set of declared action inputs.",
    fields = {
        "environment": "Environment entries naming files in the bundle.",
        "files": "The complete input depset.",
    },
)

def _single_file(target, owner):
    files = [
        file
        for file in target[DefaultInfo].files.to_list()
        if not file.basename.endswith(".runtime-trace.json")
    ]
    if len(files) != 1:
        fail("%s must provide exactly one file, got %d" % (owner, len(files)))
    return files[0]

def _reapi_artifact_action_impl(ctx):
    if len(ctx.attr.dependencies) != len(ctx.attr.dependency_arguments):
        fail("dependencies and dependency_arguments must have equal lengths")

    output = ctx.outputs.output
    runtime_trace = ctx.actions.declare_file(
        output.basename + ".runtime-trace.json",
    )
    cpu_profile = None
    if ctx.attr.native_cpu_profile:
        cpu_profile = ctx.actions.declare_file(
            output.basename + ".native-cpu-profile.pprof",
        )
    dependency_files = []
    bundled_inputs = [
        bundle[ReapiArtifactBundleInfo].files
        for bundle in ctx.attr.input_bundles
    ]
    arguments = ctx.actions.args()
    arguments.add_all(ctx.attr.arguments)
    for index, dependency in enumerate(ctx.attr.dependencies):
        dependency_file = _single_file(
            dependency,
            "%s dependency %d" % (ctx.label, index),
        )
        dependency_files.append(dependency_file)
        arguments.add(
            ctx.attr.dependency_arguments[index].replace(
                "{path}",
                dependency_file.path,
            ),
        )
    arguments.add("--output=%s" % output.path)

    if not REAPI_WORKER_RUNTIME_ROOT:
        fail("the REAPI worker runtime is unavailable on this analysis host")
    environment = {}
    if RunEnvironmentInfo in ctx.attr.tool:
        run_environment = ctx.attr.tool[RunEnvironmentInfo]
        if run_environment.inherited_environment:
            fail("{} tool inherits an ambient run environment".format(ctx.label))
        environment.update(run_environment.environment)
    environment.update(ctx.attr.env)
    for bundle in ctx.attr.input_bundles:
        for name, value in bundle[ReapiArtifactBundleInfo].environment.items():
            if name in environment:
                fail("{} bundle repeats environment {}".format(ctx.label, name))
            environment[name] = value
    if "PATH" in environment:
        fail("{} must use the declared REAPI worker runtime PATH".format(ctx.label))
    environment["PATH"] = REAPI_WORKER_RUNTIME_ROOT + "/bin"
    environment["GHOT_RUNTIME_TRACE_OUTPUT"] = runtime_trace.path
    if cpu_profile:
        environment["CPUPROFILE_FREQUENCY"] = str(ctx.attr.native_cpu_profile_hz)
        environment["GHOT_NATIVE_CPU_PROFILE_OUTPUT"] = cpu_profile.path
        environment["LD_PRELOAD"] = REAPI_WORKER_RUNTIME_ROOT + "/lib/libprofiler.so"

    files_to_run = ctx.attr.tool[DefaultInfo].files_to_run
    ctx.actions.run(
        executable = files_to_run,
        tools = [files_to_run],
        inputs = depset(
            ctx.files.inputs + dependency_files,
            transitive = bundled_inputs,
        ),
        outputs = [output, runtime_trace] + ([cpu_profile] if cpu_profile else []),
        arguments = [arguments],
        env = environment,
        execution_requirements = {"no-cache": "1"} if cpu_profile else {},
        mnemonic = ctx.attr.mnemonic,
        progress_message = ctx.attr.progress_message,
        use_default_shell_env = False,
    )
    return [DefaultInfo(files = depset(
        [output, runtime_trace] + ([cpu_profile] if cpu_profile else []),
    ))]

reapi_artifact_action = rule(
    implementation = _reapi_artifact_action_impl,
    attrs = {
        "arguments": attr.string_list(),
        "dependencies": attr.label_list(allow_files = True),
        "dependency_arguments": attr.string_list(),
        "env": attr.string_dict(),
        "inputs": attr.label_list(allow_files = True),
        "input_bundles": attr.label_list(
            providers = [ReapiArtifactBundleInfo],
        ),
        "mnemonic": attr.string(default = "ReapiArtifact"),
        "native_cpu_profile": attr.bool(default = False),
        "native_cpu_profile_hz": attr.int(default = 100),
        "output": attr.output(mandatory = True),
        "progress_message": attr.string(default = "Producing %{label}"),
        "tool": attr.label(
            executable = True,
            cfg = "exec",
            mandatory = True,
        ),
    },
)
