final: prev: {
  pythonPackagesExtensions = prev.pythonPackagesExtensions ++ [
    (_pythonFinal: pythonPrev: {
      pyvex = pythonPrev.pyvex.overridePythonAttrs (old: {
        postPatch = (old.postPatch or "") + ''
          # Temporary backport of https://github.com/angr/vex/pull/107.
          # Accept the already-patched source, but fail on an unknown source
          # instead of silently building without the fix.
          if patch --dry-run --batch --forward -d vex -p1 < ${./patches/vex-cmpxchg-preserve-rax.patch}; then
            patch --batch --forward -d vex -p1 < ${./patches/vex-cmpxchg-preserve-rax.patch}
          elif patch --dry-run --batch --reverse -d vex -p1 < ${./patches/vex-cmpxchg-preserve-rax.patch}; then
            echo "VEX CMPXCHG patch already present"
          else
            echo "VEX CMPXCHG source differs from both patch states" >&2
            exit 1
          fi
        '';
      });
    })
  ];
}
