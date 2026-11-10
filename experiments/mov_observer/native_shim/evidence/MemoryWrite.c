// Lean compiler output
// Module: MemoryWrite
// Imports: public import Init public meta import Init
#include <lean/lean.h>
#if defined(__clang__)
#pragma clang diagnostic ignored "-Wunused-parameter"
#pragma clang diagnostic ignored "-Wunused-label"
#elif defined(__GNUC__) && !defined(__CLANG__)
#pragma GCC diagnostic ignored "-Wunused-parameter"
#pragma GCC diagnostic ignored "-Wunused-label"
#pragma GCC diagnostic ignored "-Wunused-but-set-variable"
#endif
#ifdef __cplusplus
extern "C" {
#endif
uint64_t wruh_write_memory_once(uint32_t, uint64_t, lean_object*);
LEAN_EXPORT lean_object* l_MovObserver_NativeShim_writeMemoryOnce___boxed(lean_object*, lean_object*, lean_object*, lean_object*);
LEAN_EXPORT lean_object* l_MovObserver_NativeShim_writeMemoryOnce___boxed(lean_object* v_pid_5_, lean_object* v_address_6_, lean_object* v_bytes_7_, lean_object* v_a_00___x40___internal___hyg_8_){
_start:
{
uint32_t v_pid_boxed_9_; uint64_t v_address_boxed_10_; uint64_t v_res_11_; lean_object* v_r_12_; 
v_pid_boxed_9_ = lean_unbox_uint32(v_pid_5_);
lean_dec(v_pid_5_);
v_address_boxed_10_ = lean_unbox_uint64(v_address_6_);
lean_dec_ref(v_address_6_);
v_res_11_ = wruh_write_memory_once(v_pid_boxed_9_, v_address_boxed_10_, v_bytes_7_);
lean_dec_ref(v_bytes_7_);
v_r_12_ = lean_box_uint64(v_res_11_);
return v_r_12_;
}
}
lean_object* initialize_Init(uint8_t builtin);
lean_object* initialize_Init(uint8_t builtin);
void lean_initialize_runtime_module();
static bool _G_initialized = false;
LEAN_EXPORT lean_object* initialize_MemoryWrite(uint8_t builtin) {
lean_object * res;
if (_G_initialized) return lean_io_result_mk_ok(lean_box(0));
_G_initialized = true;
lean_initialize_runtime_module();
res = initialize_Init(builtin);
if (lean_io_result_is_error(res)) return res;
lean_dec_ref(res);
res = initialize_Init(builtin);
if (lean_io_result_is_error(res)) return res;
lean_dec_ref(res);
return lean_io_result_mk_ok(lean_box(0));
}
#ifdef __cplusplus
}
#endif
