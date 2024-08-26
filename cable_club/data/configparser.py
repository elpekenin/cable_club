"""Functions to interact with config files."""

from __future__ import annotations

import functools
from configparser import ConfigParser
from typing import TYPE_CHECKING, TypedDict

from cable_club.constants import GENDERS, UTF8_SIG

if TYPE_CHECKING:
    from pathlib import Path


class PokeInfo(TypedDict):
    """Information about a Pokemon found in config files."""

    abilities: set[str]
    forms: set[int]
    genders: set[int]
    moves: set[str]


PokeDex = dict[str, PokeInfo]
"""Maps Pokemon names to their information."""


# NOTE(elpekenin): mypy complains:
# >>> error: Missing type parameters for generic type "set"  [type-arg]
# which is plain wrong :)
class Universe(set):  # type: ignore[type-arg]
    """Custom "set" whose __contains__ always returns True."""

    def __contains__(self, item: object) -> bool:
        """Check if item is contained in this set."""
        return True


def sections(file_path: Path) -> set[str]:
    """Read a config file and return its sections."""
    parser = ConfigParser()
    with file_path.open("r", encoding=UTF8_SIG) as file:
        parser.read_file(file)
        return set(parser.sections())


@functools.lru_cache(maxsize=1)
def parse_pokemon_data(file_path: Path) -> PokeDex:
    """Read all Pokemon data from a config file."""
    data: PokeDex = {}

    parser = ConfigParser()
    with file_path.open("r", encoding=UTF8_SIG) as file:
        parser.read_file(file)

    for section_name in parser.sections():
        section = parser[section_name]

        abilities = {ability for ability in section["abilities"].split(",") if ability}

        if "forms" in section:
            forms = {int(f) for f in section["forms"].split(",") if f}
        else:
            forms = Universe()

        # default to {male, female} ~~~~~~~~~~~~~~~~~~~~v
        genders = GENDERS.get(section["gender_ratio"], {0, 1})

        moves = {move for move in section["moves"].split(",") if move}

        data[section_name] = {
            "abilities": abilities,
            "forms": forms,
            "genders": genders,
            "moves": moves,
        }

    return data
