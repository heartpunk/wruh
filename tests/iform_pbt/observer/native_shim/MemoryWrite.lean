namespace MovObserver.NativeShim

/-- Linux x86-64 syscall return bits, including negative errno. The borrowed
ByteArray remains live and unchanged throughout the synchronous call. -/
@[extern "wruh_write_memory_once"]
opaque writeMemoryOnce (pid : UInt32) (address : UInt64)
    (bytes : @& ByteArray) : BaseIO UInt64

end MovObserver.NativeShim
