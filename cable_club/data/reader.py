"""Parse data from raw incoming bytes."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

from cable_club import exceptions
from cable_club.constants import UTF8

if TYPE_CHECKING:
    from typing_extensions import Self

T = TypeVar("T")


class Reader:
    """Parse incoming data."""

    fields: list[str]

    @classmethod
    def new(cls, raw: bytes) -> Self | None:
        """Try an initialize a reader."""
        self = cls()

        try:
            line = raw.decode(UTF8)
        except UnicodeDecodeError:
            # unvalid UTF8 came in (automated HTTP request?)
            # prevent raising and cluttering logs
            return None

        self.fields = []
        field = ""
        escape = False
        for c in line:
            if c == "," and not escape:
                self.fields.append(field)
                field = ""
            elif c == "\\" and not escape:
                escape = True
            else:
                field += c
                escape = False
        self.fields.append(field)
        self.fields.reverse()

        return self

    def consume(self) -> str:
        """Get a raw item from the reader."""
        try:
            return self.fields.pop()
        except IndexError:  # pop from empty list
            raise exceptions.ExhaustedReaderError from None

    @staticmethod
    def _bool(raw: str) -> bool:
        """Convert to bool."""
        return {"true": True, "false": False}[raw]

    def consume_bool(self) -> bool:
        """Get a bool from the reader."""
        return self._bool(self.consume())

    def consume_bool_or_none(self) -> bool | None:
        """Get a bool or None from the reader."""
        raw = self.consume()
        if not raw:
            return None

        return self._bool(raw)

    @staticmethod
    def _int(raw: str) -> int:
        """Convert to int."""
        return int(raw)

    def consume_int(self) -> int:
        """Get an int from the reader."""
        return self._int(self.consume())

    def consume_int_or_none(self) -> int | None:
        """Get an int or None from the reader."""
        raw = self.consume()
        if not raw:
            return None

        return self._int(raw)

    def raw_all(self) -> list[str]:
        """Return raw data."""
        return list(reversed(self.fields))
