"""Validate values sent over the wire."""

from __future__ import annotations

from typing import TYPE_CHECKING, Generic, TypeVar, cast, final, overload

from cable_club import exceptions, utils

if TYPE_CHECKING:
    from collections.abc import Container

    from typing_extensions import Self

    from .models import Model
else:

    class Self:
        """Stub class.

        Prevent pulling typing_extensions at runtime while keeping Self available
        for the cast() call.

        :meta private:
        """


T = TypeVar("T")


class ValueStorage:
    """Dummy class to store values on each instance."""


class Base(Generic[T]):
    """Common logic."""

    name: str
    """Name of this field on the owner."""

    qualname: str
    """Pretty name to display on errors."""

    @overload
    def __get__(self, instance: None, owner: type[Model]) -> Self: ...

    @overload
    def __get__(self, instance: Model, owner: type[Model]) -> T: ...

    def __get__(
        self,
        instance: Model | None,
        # TODO(elpekenin): read Python docs, should we default it to None?
        owner: type[Model],
    ) -> T | Self:
        """Get the enhanced value."""
        if instance is None:
            return self

        try:
            return cast(T | Self, getattr(instance.values, self.name))
        # do not raise as 'ValueStorage' has no attribute ...
        except AttributeError as e:
            classname = instance.__class__.__name__
            msg = e.args[0].replace("ValueStorage", classname)
            raise AttributeError(msg) from None

    @final
    def __set__(self, instance: Model, value: T) -> None:
        """Validate and set the value wrapped by this class."""
        self.validate(value)  # raise if value is bad

        # make sure storage exists
        try:
            # ruff false positive about some pandas anti-pattern
            _ = instance.values  # noqa: PD011
        except AttributeError:
            # Model.__setattr__ will throw warning about assigning to "values"
            # but this place is intended to do so, thus silence it
            # the warning should be raised anywhere else, so that user notices
            # they might have fucked up
            with utils.disable_warnings():
                instance.values = ValueStorage()

        setattr(instance.values, self.name, value)

    def validate(self, value: T) -> None:  # noqa: ARG002
        """Validate the incoming value, raise if wrong."""
        return  # by default: no checks

    @final
    def __set_name__(self, owner: type[Model], name: str) -> None:
        """Store this instance's field name on the class where this field lives."""
        classname = owner.__name__
        self.qualname = f"{classname}.{name}"

        self.name = name

        try:
            _ = owner.attributes
        except AttributeError:
            owner.attributes = []
        owner.attributes.append(name)


class Int(Base[int]):
    """Represent an integer."""

    def __init__(
        self,
        *,
        min_val: int | None = None,
        max_val: int | None = None,
    ) -> None:
        """Represent an integer, constrained within the range (limits included)."""
        self.min_val = min_val
        self.max_val = max_val

    def validate(self, value: int) -> None:
        """Run checks against the incoming value."""
        if self.min_val is not None and not value >= self.min_val:
            msg = f"{self.qualname} as to be >= {self.min_val} (was {value})."
            raise exceptions.ValidationError(msg)

        if self.max_val is not None and not value <= self.max_val:
            msg = f"{self.qualname} has to be <= {self.max_val} (was {value})."
            raise exceptions.ValidationError(msg)


class OneOf(Base[T]):
    """Represent a value within a set of options."""

    _MAX_MSG_LEN = 50
    """Maximum length of the representation of self.options.

    We dont want to raise an exception with very long text.
    """

    def __init__(
        self,
        *,
        options: Container[T] | None = None,
    ) -> None:
        """Initialize an instance."""
        self.options = options if options is not None else set()

    def validate(self, value: T) -> None:
        """Run checks against the incoming value."""
        if value in self.options:
            return

        options = repr(self.options)
        if len(options) >= self._MAX_MSG_LEN:
            options = (
                options[: self._MAX_MSG_LEN // 2]
                + " ... "
                + options[-self._MAX_MSG_LEN // 2 :]
            )

        repr_ = repr(value)
        msg = f"{self.qualname} has to be one of: {options} (was {repr_})."
        raise exceptions.ValidationError(msg)


class Str(Base[str]):
    """Represent a string."""

    def __init__(self, *, max_len: int | None = None) -> None:
        """Initialize an instance."""
        self.max_len = max_len

    def validate(self, value: str) -> None:
        """Run checks against the incoming value."""
        length = len(value)
        if self.max_len is not None and length > self.max_len:
            msg = f"len({self.qualname}) has to be <= {self.max_len} (was {length})."
            raise exceptions.ValidationError(msg)


class Bool(Base[bool]):
    """Represent a boolean."""


class OptionalInt(Int, Base[int | None]):
    """Represent an optional integer."""

    def validate(self, value: int | None) -> None:
        """Run checks against the incoming value."""
        if value is None:
            return

        super().validate(value)


class OptionalBool(Base[bool | None]):
    """Represent an optional boolean."""
