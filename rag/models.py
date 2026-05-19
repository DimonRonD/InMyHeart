# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TextChunk:
    """Фрагмент базы знаний с полной трассировкой источника."""

    content: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def chunk_id(self) -> str:
        return str(self.metadata.get("chunk_id", ""))

    def chroma_metadata(self) -> dict[str, str | int | float | bool]:
        """Chroma принимает только скалярные типы в metadata."""
        out: dict[str, str | int | float | bool] = {}
        for key, value in self.metadata.items():
            if value is None or value == "":
                continue
            if isinstance(value, (str, int, float, bool)):
                out[key] = value
            else:
                out[key] = str(value)
        return out
