"""Parse data from raw incoming bytes."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar, overload

from cable_club.constants import UTF8
from cable_club.exceptions import ExhaustedReaderError, ValidationError

if TYPE_CHECKING:
    from collections.abc import Container
    from typing import Literal

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

    def read(
        self,
        *,
        max_len: int | None = None,
    ) -> str:
        """Get a raw item from the reader."""
        try:
            value = self.fields.pop()
        except IndexError:  # pop from empty list
            raise ExhaustedReaderError from None

        length = len(value)
        if max_len is not None and length > max_len:
            msg = f"len(value) has to be <= {max_len} (was {length})."
            raise ValidationError(msg)

        return value

    def left(self) -> list[str]:
        """Return raw data."""
        return list(reversed(self.fields))

    @overload
    def boolean(
        self,
        *,
        allow_none: Literal[False] = ...,
    ) -> bool: ...

    @overload
    def boolean(
        self,
        *,
        allow_none: Literal[True] = ...,
    ) -> bool | None: ...

    def boolean(self, *, allow_none: bool = False) -> bool | None:
        """Get a bool from the reader."""
        raw = self.read()
        if not raw:
            if allow_none:
                return None

            msg = "value was required"
            raise ValidationError(msg)

        return {"true": True, "false": False}[raw]

    @overload
    def integer(
        self,
        *,
        min_val: int | None = ...,
        max_val: int | None = ...,
        allow_none: Literal[False] = ...,
    ) -> int: ...

    @overload
    def integer(
        self,
        *,
        min_val: int | None = ...,
        max_val: int | None = ...,
        allow_none: Literal[True] = ...,
    ) -> int | None: ...

    def integer(
        self,
        *,
        min_val: int | None = None,
        max_val: int | None = None,
        allow_none: bool = False,
    ) -> int | None:
        """Get an int from the reader."""
        raw = self.read()
        if not raw:
            if allow_none:
                return None

            msg = "value was required"
            raise ValidationError(msg)

        value = int(raw)

        if min_val is not None and not value >= min_val:
            msg = f"value as to be >= {min_val} (was {value})."
            raise ValidationError(msg)

        if max_val is not None and not value <= max_val:
            msg = f"value has to be <= {max_val} (was {value})."
            raise ValidationError(msg)

        return value

    def one_of(self, *, options: Container[str]) -> str:
        """Read a value within a set of options."""
        value = self.read()
        if value in options:
            return value

        options = repr(options)

        max_len = 50
        if len(options) >= max_len:
            options = options[:max_len] + " ..."

        msg = f"value has to be one of: {options} (was '{value}')."
        raise ValidationError(msg)
