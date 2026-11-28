"""WRUH's loaded Equanimity session and representation of its executable bytes."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import archinfo
from equanimity import Equanimity, Image, LoadRequest, StepResult

from extractor.instruction_inventory import Interval, Inventory, Span, inventory


@dataclass(frozen=True)
class Session:
    engine: Equanimity
    image: Image

    @classmethod
    def load(cls, artifact: Path, objects: Path | None = None, digest: str | None = None) -> Session:
        engine = Equanimity()
        return cls(engine, engine.load(LoadRequest(artifact, objects, digest)))

    def step(self, address: int) -> StepResult:
        return self.engine.step(self.image, address)

    def inventory(self, exclusions: list[Interval]) -> Inventory:
        spans = [
            Span(segment["address"], bytes.fromhex(segment["bytes"]),
                 obj["sha256"], obj["mapped_base"])
            for obj in self.image.loaded_image["objects"]
            for segment in obj["segments"]
            if segment["executable"] and segment["size"]
        ]
        if not spans:
            raise ValueError("no executable segments in the loaded object set")
        return inventory(spans, exclusions, archinfo.ArchAMD64().capstone)
