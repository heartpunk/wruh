# Successor-based instruction extraction

Design discussion: https://chatgpt.com/c/6aba058c-fc3c-83e8-8332-4eab6af78c48

Title: Angr Branching Design Smell (September 27).

Canonical primitive: execute one instruction; consume angr all_successors;
use each successor's complete solver constraints as guard, its post-state as
updates, and history.jumpkind as transition metadata. Remove VEX exit
reconstruction. Use NO_IP_CONCRETIZATION. Consolidate stepping paths.

Baseline for this work: dc38d2d3a5e36e400af3974188dbb977ddd06965.
Division fault generation and terminal-error classification must be explicit.
