#[unsafe(no_mangle)]
extern "C" fn napi_get_version(env_: napi_env, result_: *mut u32) -> napi_status {
    bun_output::scoped_log!(napi, "napi_get_version");
    let env = get_env!(env_);
    let result = get_out!(env, result_);
    // The result is supposed to be the highest NAPI version Bun supports, rather than the version reported by a NAPI module.
    // Keep this in sync with process.versions.napi in BunProcess.cpp.
    *result = 10;
    env.ok()
}
