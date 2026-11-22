"""Forward Bazel output while retaining complete streamed census failures."""

import json
import sys
from pathlib import Path

PREFIX = "CENSUS_FAILURE "


def capture(source, destination, output):
    for line in source:
        output.write(line)
        output.flush()
        if line.startswith(PREFIX) and line.endswith("\n"):
            record = line[len(PREFIX):]
            try:
                json.loads(record)
            except ValueError:
                continue
            destination.write(record)
            destination.flush()


if __name__ == "__main__":
    with Path(sys.argv[1]).open("w", encoding="utf-8") as output_file:
        capture(sys.stdin, output_file, sys.stdout)
