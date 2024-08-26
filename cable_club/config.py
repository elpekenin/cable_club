"""Implement several "backends" to configure the server execution.

All of them **must not** involve the user editing application's source.
"""

from __future__ import annotations

import logging
import os
import warnings
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Generic, TypeVar, cast, final, overload

from . import exceptions
from .version import Version

if TYPE_CHECKING:
    from collections.abc import Callable

    from typing_extensions import Self

T = TypeVar("T")


class Setting(Generic[T]):
    """Data descriptor for the settings.

    :meta private:
    """

    # TODO(elpekenin): change logic, similar to models, to store on instance
    # instead of self? could cause some weird behavior with current code if there are
    # 2 instances of Config at the same time (shouldnt happen, tho)

    _value: T | None
    _name: str

    @overload
    def __get__(self, instance: None, owner: type[Config]) -> Self: ...

    @overload
    def __get__(self, instance: Config, owner: type[Config]) -> T: ...

    def __get__(self, instance: Config | None, owner: type[Config]) -> T | Self:
        """Read the value wrapped on this class."""
        if instance is None:
            return self

        if self._value is None:
            raw = instance.get(self.key)
            if raw is not Config.Sentinel:
                # mypy doesnt understand that `is not` cancels out the possibility of
                # raw being type[Sentinel]
                value = self.do_convert(cast(str | T, raw))
            else:
                value = self.default
                repr_ = repr(self.default)
                msg = f"Could not read setting '{self.key}', using default ({repr_})."
                warnings.warn(msg, stacklevel=2)

            self._value = value

        return self._value

    def __init__(
        self,
        *,
        key: str,
        default: T,
        convert: Callable[[str], T],
    ) -> None:
        """Intialize a setting getter."""
        self.key = key
        self.default = default
        self.convert = convert

        self._value = None

    def do_convert(self, raw: str | T) -> T:
        """Convert a raw value into the expected type."""
        expected_type = type(self.default)

        # value came already converted
        if isinstance(raw, expected_type):
            return raw

        # mypy somehow infers str | T, instead of str
        # even though it does note that expected_type is type[T]
        # weird...
        raw = cast(str, raw)
        converted = self.convert(raw)
        if isinstance(converted, expected_type):
            return converted

        converted_type = type(converted)
        msg = f"Reading {self._name} gave a {converted_type} (expected {expected_type})"
        raise exceptions.BadConfigurationError(msg)

    def __set_name__(self, owner: Config, name: str) -> None:
        """Store this instance's field name on the class where this field lives."""
        # keep track of all fields in a class, for pretty printing
        owner._fields = getattr(owner, "_fields", [])
        owner._fields.append(name)
        self._name = name

    def __set__(self, instance: Config, value: T) -> None:
        """Prevent assigning values."""
        raise exceptions.ConfigLockedError


class Config(ABC):
    """Base logic to load variables from some source, with fallback to defaults."""

    _fields: list[str]

    class Sentinel:
        """Used to mark that get() did not find a value and fall back to default.

        :meta private:
        """

    host = Setting(
        key="HOST",
        default="127.0.0.1",
        convert=str,
    )
    """The host IP Address to run this server on. Should be 0.0.0.0 for Google Cloud."""

    port = Setting(
        key="PORT",
        default=9999,
        convert=int,
    )
    """The port the server is listening on."""

    pbs_dir = Setting(
        key="PBS_DIR",
        default=Path("PBS"),
        convert=Path,
    )
    """The path, relative to the working directory, where the PBS files are located."""

    rules_dir = Setting(
        key="RULES_DIR",
        default=Path("OnlinePresets"),
        convert=Path,
    )
    """Path, relative to the working directory, where the rules files are located."""

    log_dir = Setting(
        key="LOG_DIR",
        default=Path(),
        convert=Path,
    )
    """Path, relative to the working directory, where the log file will be stored."""

    log_level = Setting(
        key="LOG_LEVEL",
        default="INFO",
        convert=logging.getLevelName,
    )
    """The log level of the server. Messages lower than the level are not written."""

    rules_refresh_rate = Setting(
        key="RULES_REFRESH_RATE",
        default=60,
        convert=int,
    )
    """Rate (approximate) at which rule files are checked for changes, in seconds."""

    game_version = Setting(
        key="GAME_VERSION",
        default=Version("1.0.0"),
        convert=Version,
    )
    """Version of the game."""

    pokemon_max_name_size = Setting(
        key="POKEMON_MAX_NAME_SIZE",
        default=10,
        convert=int,
    )
    """Maximum length for a Pokemon's name."""

    player_max_name_size = Setting(
        key="PLAYER_MAX_NAME_SIZE",
        default=10,
        convert=int,
    )
    """Maximum length for a trainer's name."""

    maximum_level = Setting(
        key="MAXIMUM_LEVEL",
        default=100,
        convert=int,
    )
    """Maximum level for Pokemons."""

    iv_stat_limit = Setting(
        key="IV_STAT_LIMIT",
        default=31,
        convert=int,
    )
    """Stat limit for IVs."""

    ev_limit = Setting(
        key="EV_LIMIT",
        default=510,
        convert=int,
    )
    """Limit for EVs."""

    ev_stat_limit = Setting(
        key="EV_STAT_LIMIT",
        default=252,
        convert=int,
    )
    """Stat limit for EVs."""

    sketch_move_ids = Setting(
        key="SKETCH_MOVE_IDS",
        default=["SKETCH"],
        convert=lambda raw: raw.split(","),
    )
    """Sketch(-like) moves."""

    essentials_deluxe_installed = Setting(
        key="ESSENTIALS_DELUXE_INSTALLED",
        default=False,
        convert=bool,
    )
    """Specifically Essentials Deluxe, not DBK."""

    mui_mementos_installed = Setting(
        key="MUI_MEMENTOS_INSTALLED",
        default=False,
        convert=bool,
    )

    zud_dynamax_installed = Setting(
        key="ZUD_DYNAMAX_INSTALLED",
        default=False,
        convert=bool,
    )
    """ZUD Mechanics / [DBK] Dynamax."""

    pla_installed = Setting(
        key="PLA_INSTALLED",
        default=False,
        convert=bool,
    )
    """PLA Battle Styles."""

    tera_installed = Setting(
        key="TERA_INSTALLED",
        default=False,
        convert=bool,
    )
    """Terastal Phenomenon / [DBK] Terastallization."""

    focus_installed = Setting(
        key="FOCUS_INSTALLED",
        default=False,
        convert=bool,
    )
    """Focus Meter System."""

    # security warning!! only enable if you know what you are doing
    debug = Setting(
        key="DEBUG",
        default=False,
        convert=bool,
    )
    """Whether or not remote debugger is enabled."""

    debug_host = Setting(
        key="DEBUG_HOST",
        default="",
        convert=str,
    )
    """Address to listen on."""

    debug_port = Setting(
        key="DEBUG_PORT",
        default=0,
        convert=int,
    )
    """Port on which debugpy (remote debugger) will be listening."""

    @abstractmethod
    def get(self, key: str) -> str | T | type[Config.Sentinel]:
        """Backend-specific way to grab a configuration or mark it was not found."""

    @final
    def __str__(self) -> str:
        """Show the config."""
        fields: list[str] = []

        for field in self._fields:
            repr_ = repr(getattr(self, field))
            fields.append(f"{field}={repr_}")

        return ", ".join(fields)

    @final
    def __repr__(self) -> str:
        """Represent the config."""
        classname = self.__class__.__name__
        return f"<{classname}: {self}>"


@final
class PyFileConfig(Config):
    """Read constants from a Python file."""

    def __init__(self, *, file_name: str = "server_config") -> None:
        """Initialize an instance."""
        try:
            file = __import__(file_name)
        except ImportError:
            file = None
            msg = (
                f"No configuration file (`{file_name}.py`) found."
                " Using default values."
            )
            warnings.warn(msg, stacklevel=2)

        self._file = file

    def get(self, key: str) -> str | T | type[Config.Sentinel]:
        """Grab a key from a Python file."""
        return getattr(self._file, key, self.Sentinel)


@final
class EnvironmentConfig(Config):
    """Read environment variables."""

    def get(self, key: str) -> str | T | type[Config.Sentinel]:
        """Grab a key from environment variables."""
        return os.getenv(key, self.Sentinel)
