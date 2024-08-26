"""Utilities to use on tests."""

from typing import TypeVar, cast

from cable_club import config

T = TypeVar("T")


class TestConfig(config.Config):
    """Config class for testing, configured via **kwargs on __init__."""

    def __init__(self, **kwargs: object) -> None:
        """Initialize an instance."""
        self.kwargs = kwargs

    def get(
        self,
        key: str,
    ) -> T | type[config.Config.Sentinel]:
        """Get an configuration key."""
        return cast(
            T | type[config.Config.Sentinel],
            self.kwargs.get(key, self.Sentinel),
        )
