"""Generate assembled Revizor cases from an ISA description and config."""
from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--isa", required=True, help="Revizor ISA description")
    parser.add_argument("--config", required=True, help="Revizor config, including exclusions")
    parser.add_argument("--output", required=True, help="directory for generated cases")
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--seed", type=int, default=1)
    args = parser.parse_args()
    if args.count < 1:
        parser.error("--count must be positive")

    from rvzr.config import CONF
    from rvzr.factory import get_program_generator
    from rvzr.isa_spec import InstructionSet

    CONF.load(args.config)
    isa = InstructionSet(args.isa, CONF.instruction_categories)
    generator = get_program_generator(args.seed, isa)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    for index in range(args.count):
        case = output / f"case-{index}"
        case.mkdir(exist_ok=False)
        generator.create_test_case(str(case / "program.asm"))


if __name__ == "__main__":
    main()
