"""Models for data sent over the wire."""

# ruff: noqa: RUF023

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar, final

from cable_club import constants
from cable_club.constants import ABILITIES_FILE, ITEMS_FILE, MOVES_FILE, POKEMONS_FILE
from cable_club.data import configparser
from cable_club.exceptions import ValidationError

if TYPE_CHECKING:
    from typing_extensions import Self

    from cable_club.config import Config
    from cable_club.data import Reader


# TODO(elpekenin): some sentinel value on the not-yet-configured fields
# so that they error out if we try and assign to them, rather than not running
# checks (or run wrong ones) ??


class Model(ABC):
    """Base class for all data models.

    Provides some common logic for all data models.
    """

    config: Config
    """Not present until configure() gets called."""

    __slots__: tuple[str, ...]

    @final
    def __repr__(self) -> str:
        """Represent an instance as string."""
        classname = type(self).__name__

        reprs: list[str] = []
        for field in self.__slots__:
            raw = getattr(self, field, "NOT_SET")
            repr_ = repr(raw)
            reprs.append(f"{field}: {repr_}")

        body = ", ".join(reprs)
        return f"<{classname}: {body}>"

    @abstractmethod
    def do_read_from(self, reader: Reader) -> None:
        """Model-specific reading."""

    def validate(self) -> None:
        """Run checks that can not be done in the fields (eg: inter-field relations).

        Default to noop rather than being an abstractmethod because most models wont
        need to do anything here.
        """
        return

    @final
    @classmethod
    def read_from(cls, reader: Reader) -> Self:
        """Create an instance by reading values."""
        self = cls()
        self.do_read_from(reader)
        self.validate()
        return self


class Move(Model):
    """Represent a Pokemon's move."""

    __slots__ = ("name",)

    names: ClassVar[set[str]] = set()

    def do_read_from(self, reader: Reader) -> None:
        """Initialize an instance by reading input."""
        self.name = reader.one_of(options=self.names)


class SketchedMove(Model):
    """Represent a Pokemon's move obtained via sketch."""

    __slots__ = (
        "name",
        "ppup",
        "mastery",
    )

    names: ClassVar[set[str]] = set()

    def do_read_from(self, reader: Reader) -> None:
        """Initialize an instance by reading input."""
        self.name = reader.one_of(options=self.names)
        self.ppup = reader.integer(min_val=0, max_val=3)

        if self.config.pla_installed:
            self.mastery = reader.boolean(allow_none=True)


class Iv(Model):
    """Represent a Pokemon's IV."""

    __slots__ = (
        "val",
        "maxed",
    )

    max_val: ClassVar[int] = 0

    def do_read_from(self, reader: Reader) -> None:
        """Initialize an instance by reading input."""
        self.val = reader.integer(
            min_val=0,
            max_val=self.max_val,
        )
        self.maxed = reader.boolean(allow_none=True)


class Ev(Model):
    """Represent a Pokemon's EV."""

    __slots__ = ("val",)

    max_val: ClassVar[int] = 0

    def do_read_from(self, reader: Reader) -> None:
        """Initialize an instance by reading input."""
        self.val = reader.integer(
            min_val=0,
            max_val=self.max_val,
        )


class ObtainStats(Model):
    """Represent how a Pokémon was obtained."""

    __slots__ = (
        "mode",
        "map",
        "text",
        "level",
        "hatched_map",
    )

    def do_read_from(self, reader: Reader) -> None:
        """Initialize an instance by reading input."""
        self.mode = reader.integer(min_val=0)
        self.map = reader.integer(min_val=0)
        self.text = reader.read()
        self.level = reader.integer(min_val=0)
        self.hatched_map = reader.integer(min_val=0)


class ContestStats(Model):
    """Represent a Pokémon stats for contests."""

    __slots__ = (
        "cool",
        "beauty",
        "cute",
        "smart",
        "tough",
        "sheen",
    )

    def do_read_from(self, reader: Reader) -> None:
        """Initialize an instance by reading input."""
        self.cool = reader.integer(min_val=0)
        self.beauty = reader.integer(min_val=0)
        self.cute = reader.integer(min_val=0)
        self.smart = reader.integer(min_val=0)
        self.tough = reader.integer(min_val=0)
        self.sheen = reader.integer(min_val=0)


class EssentialDeluxeProperties(Model):
    """Represent optional fields based on game/server configuration."""

    __slots__ = (
        "scale",
        "memento",
        "dmax_level",
        "gmax_factor",
        "dmax_able",
        "tera_type",
        "focus_type",
    )

    def do_read_from(self, reader: Reader) -> None:
        """Initialize an instance by reading input."""
        if (
            self.config.essentials_deluxe_installed
            or self.config.mui_mementos_installed
        ):
            self.scale = reader.integer(min_val=0)

        if self.config.mui_mementos_installed:
            self.memento = reader.read()

        if self.config.zud_dynamax_installed:
            self.dmax_level = reader.integer(min_val=0)
            self.gmax_factor = reader.boolean()
            self.dmax_able = reader.boolean()

        if self.config.tera_installed:
            self.tera_type = reader.read()

        if self.config.focus_installed:
            self.focus_type = reader.read()


class _MailSpecies(Model):
    """Pokemon data on a mail."""

    __slots__ = (
        "gender",
        "shiny",
        "form",
        "shadow",
        "egg",
    )

    def do_read_from(self, reader: Reader) -> None:
        """Initialize an instance by reading input."""
        self.gender = reader.integer(min_val=0)
        self.shiny = reader.boolean()
        self.form = reader.integer(min_val=0)
        self.shadow = reader.boolean()
        self.egg = reader.boolean()


class Mail(Model):
    """Data on a mail."""

    __slots__ = (
        "item",
        "msg",
        "sender",
        "species",
    )

    def do_read_from(self, reader: Reader) -> None:
        """Initialize an instance by reading input."""
        self.item = reader.read()
        self.msg = reader.read()
        self.sender = reader.read()

        self.species: list[_MailSpecies] = []
        for _ in range(3):
            has_species = reader.integer(allow_none=True)
            if has_species:
                self.species.append(_MailSpecies.read_from(reader))


class Pokemon(Model):
    """Represent a Pokemon's data."""

    # TODO(elpekenin): move related fields into classes

    __slots__ = (
        "species",
        "level",
        "personal_id",
        "owner_id",
        "owner_name",
        "owner_gender",
        "exp",
        "form",
        "item",
        "sketched_moves",
        "regular_moves",
        "mastered_moves",
        "gender",
        "shiny",
        "ability",
        "ability_index",
        "nature_id",
        "nature_stats_id",
        "ivs",
        "evs",
        "happiness",
        "name",
        "pokeball",
        "steps_to_hatch",
        "pokerus",
        "obtain_stats",
        "contest_stats",
        "ribbons",
        "essential_deluxe_properties",
        "mail",
        "fusion",
    )

    species_names: ClassVar[set[str]] = set()
    max_level: ClassVar[int] = 0
    max_owner_name_len: ClassVar[int] = 0
    item_names: ClassVar[set[str]] = set()
    ability_names: ClassVar[set[str]] = set()
    max_ev_sum: ClassVar[int] = 0
    pokeball_names: ClassVar[set[str]] = set()
    max_name_len: ClassVar[int] = 0

    # ruff doesnt like the code being this long, but we dont care :)
    def do_read_from(self, reader: Reader) -> None:
        """Initialize an instance by reading input."""
        self.species = reader.one_of(options=self.species_names)
        self.level = reader.integer(min_val=1)
        self.personal_id = reader.integer(min_val=0)
        self.owner_id = reader.integer(
            # NOTE(elpekenin): original code used if owner_id & ~0xFFFFFFFF
            # which i believe is equivalent max_val = flag+1
            max_val=0xFFFFFFFF + 1,
        )
        self.owner_name = reader.read(max_len=self.max_owner_name_len)
        self.owner_gender = reader.integer(min_val=0, max_val=1)
        self.exp = reader.integer(min_val=0)
        self.form = reader.integer(min_val=0)
        self.item = reader.one_of(options=self.item_names)

        self.sketched_moves: list[SketchedMove] = []
        n_sketched_moves = reader.integer(min_val=0)
        for _ in range(n_sketched_moves):
            self.sketched_moves.append(SketchedMove.read_from(reader))

        self.regular_moves: list[Move] = []
        n_regular_moves = reader.integer(min_val=0)
        for _ in range(n_regular_moves):
            self.regular_moves.append(Move.read_from(reader))

        if self.config.pla_installed:
            self.mastered_moves: list[Move] = []
            n_mastered_moves = reader.integer(min_val=0)
            for _ in range(n_mastered_moves):
                self.mastered_moves.append(Move.read_from(reader))

        self.gender = reader.integer(min_val=0, max_val=2)
        self.shiny = reader.boolean()
        self.ability = reader.one_of(options=self.ability_names)
        self.ability_index = reader.integer(min_val=0, allow_none=True)
        self.nature_id = reader.read()
        self.nature_stats_id = reader.read()

        self.ivs: list[Iv] = []
        self.evs: list[Ev] = []
        for _ in range(6):
            self.ivs.append(Iv.read_from(reader))
            self.evs.append(Ev.read_from(reader))

        self.happiness = reader.integer(
            min_val=0,
            max_val=255,
        )
        self.name = reader.read(max_len=self.max_name_len)
        self.pokeball = reader.one_of(options=self.pokeball_names)
        self.steps_to_hatch = reader.integer(min_val=0)
        self.pokerus = reader.integer(min_val=0)
        self.obtain_stats = ObtainStats.read_from(reader)
        self.contest_stats = ContestStats.read_from(reader)

        self.ribbons: list[str] = []
        n_ribbons = reader.integer(min_val=0)
        for _ in range(n_ribbons):
            self.ribbons.append(reader.read())

        self.essential_deluxe_properties = EssentialDeluxeProperties.read_from(reader)

        # mail
        has_mail = reader.boolean()
        if has_mail:
            self.mail = Mail.read_from(reader)

        fused = reader.boolean()
        if fused:
            self.fusion = Pokemon.read_from(reader)

    def validate(self) -> None:
        """Run some checks between parsed attributes."""
        pokedex = configparser.parse_pokemon_data(
            self.config.pbs_dir / constants.POKEMONS_FILE,
        )
        pokemon = pokedex[self.species]

        # FIXME(elpekenin): this doesnt seem to be what i first thought
        if False:
            moves = pokemon["moves"]
            copy_moves = moves.intersection(self.config.sketch_move_ids)
            if not copy_moves and self.sketched_moves:
                msg = (
                    f"{self.species} can not learn any move to copy moves (eg: sketch)."
                    " Thus, it can not specify any moves as learnt this way."
                )
                raise ValidationError(msg)

            for move in (
                *self.regular_moves,
                *self.mastered_moves,
            ):
                if move.name not in moves:
                    msg = f"{self.species} can not learn {move}."
                    raise ValidationError(msg)

        genders = pokemon["genders"]
        if self.gender not in genders:
            msg = f"{self.species} can not have gender={self.gender}"
            raise ValidationError(msg)

        forms = pokemon["forms"]
        if self.form not in forms:
            msg = f"{self.species} can not have form={self.form}"
            raise ValidationError(msg)

        ev_sum = 0
        for ev in self.evs:
            ev_sum += ev.val
        if ev_sum > self.max_ev_sum:
            msg = "ev sum exceeds maximum configured value"
            raise ValidationError(msg)

        # TODO(elpekenin): check if any validation is missing


class Party(Model):
    """A team of Pokemon."""

    __slots__ = ("pokemons",)

    def do_read_from(self, reader: Reader) -> None:
        """Initialize an instance by reading input."""
        self.pokemons: list[Pokemon] = []
        n_pokemon = reader.integer(min_val=0)
        for _ in range(n_pokemon):
            self.pokemons.append(Pokemon.read_from(reader))

        leftovers = reader.left()
        if leftovers:
            rest = ", ".join(leftovers)
            msg = f"Data left in reader: {rest}"
            raise ValidationError(msg)


def configure(config: Config) -> None:
    """Apply configuration on fields that depend on it."""
    items = configparser.sections(config.pbs_dir / ITEMS_FILE)

    Model.config = config

    # max int values
    Iv.max_val = config.iv_stat_limit
    Ev.max_val = config.ev_stat_limit

    # set of posible values
    Move.names = SketchedMove.names = configparser.sections(
        config.pbs_dir / MOVES_FILE,
    )
    Pokemon.species_names = configparser.sections(config.pbs_dir / POKEMONS_FILE)
    Pokemon.max_level = config.maximum_level
    Pokemon.max_owner_name_len = config.player_max_name_size
    Pokemon.item_names = items | {""}  # allow no item
    Pokemon.ability_names = configparser.sections(config.pbs_dir / ABILITIES_FILE)
    Pokemon.max_ev_sum = config.ev_limit
    Pokemon.pokeball_names = items
    Pokemon.max_name_len = config.pokemon_max_name_size
