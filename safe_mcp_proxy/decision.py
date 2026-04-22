from __future__ import annotations

from enum import Enum
from typing import Union


class Decision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    ABSENT = "ABSENT"
    SIMULATE = "SIMULATE"

    @classmethod
    def parse(cls, value: str) -> Union["Decision", str]:
        try:
            return cls(value)
        except ValueError:
            return value

    @classmethod
    def values(cls) -> tuple[str, ...]:
        return tuple(decision.value for decision in cls)
