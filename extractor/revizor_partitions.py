"""Use composed WRUH paths and SMT to choose native differential inputs."""
from __future__ import annotations

import hashlib
import json
import time

import z3
from ayxg.z3 import declaration_variables, expr_to_z3

from extractor.corpus_runner import RETURN, STACK, STORAGE
from extractor.fresh import FreshFunction
from extractor.fresh_composition import ComposedPath, compose_fresh_paths


def solve_samples(model: dict, count: int, *, timeout_ms: int = 30000, seed: int = 1,
                  path_indices: set[int] | None = None, statistics: bool = False,
                  functions: tuple[FreshFunction, ...] | None = None,
                  paths: tuple[ComposedPath, ...] | None = None):
    """Solve path guards under exactly the concrete runner's entry state.

    UNSAT and UNKNOWN are recorded per path. The finite path/step bounds and
    solver timeouts make this an explicitly bounded exploration.
    """
    function = FreshFunction.from_data(model["fresh_model"])
    if paths is None:
        paths = compose_fresh_paths(model["cfg"], functions or (function,), function.function_id)
    ctx = z3.Context()
    variables = declaration_variables(function.declarations, ctx)
    x = z3.BitVec("wruh_input_x", 32, ctx=ctx)
    y = z3.BitVec("wruh_input_y", 32, ctx=ctx)
    memory = z3.K(z3.BitVecSort(64, ctx=ctx), z3.BitVecVal(0, 8, ctx=ctx))
    for i in range(8):
        word = y ^ z3.BitVecVal(i, 32, ctx=ctx)
        for j in range(4):
            memory = z3.Store(memory, z3.BitVecVal(STORAGE + 4*i+j, 64, ctx=ctx),
                              z3.Extract(8*j+7, 8*j, word))
    for j in range(8):
        memory = z3.Store(memory, z3.BitVecVal(STACK+j, 64, ctx=ctx),
                          z3.BitVecVal((RETURN >> (8*j)) & 255, 8, ctx=ctx))
    initial = {"rip": function.entry, "rsp": STACK, "rdx": STORAGE,
               "d": 1, "ftop": 0, "fpround": 0, "sseround": 0}
    for name, variable in tuple(variables.items()):
        if name == "mem":
            variables[name] = memory
        elif name == "rdi":
            variables[name] = z3.ZeroExt(32, x)
        elif name == "rsi":
            variables[name] = z3.ZeroExt(32, y)
        elif z3.is_bv(variable):
            variables[name] = z3.BitVecVal(initial.get(name, 0), variable.size(), ctx=ctx)
        elif z3.is_bool(variable):
            variables[name] = z3.BoolVal(False, ctx=ctx)
        else:
            raise ValueError(f"unsupported initial-state sort for {name}: {variable.sort()}")

    partitions = []
    for index, path in enumerate(paths):
        if path_indices is not None and index not in path_indices:
            continue
        solver = z3.Solver(ctx=ctx)
        solver.set(timeout=timeout_ms, random_seed=seed)
        solver.add(expr_to_z3(path.guard, variables, ctx))
        path_id = hashlib.sha256(json.dumps(path.edge_ids).encode()).hexdigest()
        partitions.append({"index": index, "path_id": path_id, "solver": solver,
                           "status": "UNASSESSED", "samples": 0})
    samples = []
    active = list(partitions)
    while active and len(samples) < count:
        for partition in active[:]:
            solver = partition["solver"]
            started = time.monotonic()
            status = solver.check()
            if statistics:
                z3_stats = solver.statistics()
                partition["last_check"] = {
                    "elapsed_seconds": time.monotonic() - started,
                    "result": str(status),
                    "statistics": {key: z3_stats.get_key_value(key) for key in z3_stats.keys()},
                }
            if status != z3.sat:
                partition["status"] = ("EXHAUSTED" if partition["samples"] else "UNSAT") if status == z3.unsat else "UNKNOWN"
                if status == z3.unknown:
                    partition["reason"] = solver.reason_unknown()
                active.remove(partition)
                continue
            values = solver.model()
            xv = values.eval(x, model_completion=True).as_long()
            yv = values.eval(y, model_completion=True).as_long()
            samples.append({"x": xv, "y": yv, "path_id": partition["path_id"]})
            partition["samples"] += 1
            partition["status"] = "SAT"
            different_input = z3.Or(x != z3.BitVecVal(xv, 32, ctx=ctx),
                                    y != z3.BitVecVal(yv, 32, ctx=ctx))
            for other in active:
                other["solver"].add(different_input)
            if len(samples) == count:
                break
    return samples, [{key: value for key, value in part.items() if key != "solver"}
                     for part in partitions]
