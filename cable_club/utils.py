"""Tiny reusable logic."""

import contextlib
import warnings
from collections.abc import Generator


def noop(*_args: object, **_kwargs: object) -> None:
    """Do nothing."""


@contextlib.contextmanager
def disable_warnings() -> Generator[None, None, None]:
    """Disable warnings temporarily."""
    orig = warnings.showwarning
    try:
        warnings.showwarning = noop
        yield
    finally:
        warnings.showwarning = orig
