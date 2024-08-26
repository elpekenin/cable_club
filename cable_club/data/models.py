"""Models for data sent over the wire."""

from __future__ import annotations

import warnings
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, final

from cable_club import constants, exceptions
from cable_club.constants import ABILITIES_FILE, ITEMS_FILE, MOVES_FILE, POKEMONS_FILE

from . import configparser, fields

if TYPE_CHECKING:
    from typing_extensions import Self

    from cable_club.config import Config

    from .reader import Reader


# TODO(elpekenin): some sentinel value on the not-yet-configured fields
# so that they error out if we try and assign to them, rather than not running
# checks (or run wrong ones) ??


class Model(ABC):
    """Base class for all data models.

    Provides some common logic for all data models.
    """

    config: Config
    """Not present until configure() gets called."""

    attributes: list[str]
    """Name of each field in this class.

    Auto-magically updated by classes on :py:mod:`cable_club.data.fields`.

    Note: Is a list, opposed to a set, to preserve the order of the fields, this is
    useful as it informs in which order we parse things from the reader.

    :meta private:
    """

    values: fields.ValueStorage
    """Actual storage of the fields."""

    @final
    def __repr__(self) -> str:
        """Represent an instance as string."""
        classname = self.__class__.__name__

        reprs: list[str] = []
        for field in self.attributes:
            raw = getattr(self, field, "NOTSET")
            repr_ = repr(raw)
            reprs.append(f"{field}: {repr_}")

        body = ", ".join(reprs)
        return f"<{classname}: {body}>"

    @final
    def __setattr__(self, name: str, value: object) -> None:
        """Avoid assigning unidentified fields."""
        if name == "values":
            msg = "Do not edit the 'values' attribute."
            warnings.warn(msg, stacklevel=2)

        elif name not in self.attributes:
            classname = self.__class__.__name__
            msg = f"{classname}.{name} is not a field defined on the model."
            raise exceptions.UnknownFieldError(msg)

        super().__setattr__(name, value)

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

    name: fields.OneOf[str] = fields.OneOf()

    def do_read_from(self, reader: Reader) -> None:
        """Initialize an instance by reading input."""
        self.name = reader.consume()


class SketchedMove(Model):
    """Represent a Pokemon's move obtained via sketch."""

    name: fields.OneOf[str] = fields.OneOf()

    ppup = fields.Int(
        min_val=0,
        max_val=3,
    )

    mastery = fields.OptionalBool()

    def do_read_from(self, reader: Reader) -> None:
        """Initialize an instance by reading input."""
        self.name = reader.consume()

        self.ppup = reader.consume_int()

        if self.config.pla_installed:
            self.mastery = reader.consume_bool_or_none()


class IV(Model):
    """Represent a Pokemon's IV."""

    val = fields.Int(min_val=0)

    maxed = fields.OptionalBool()

    def do_read_from(self, reader: Reader) -> None:
        """Initialize an instance by reading input."""
        self.val = reader.consume_int()
        self.maxed = reader.consume_bool_or_none()


class EV(Model):
    """Represent a Pokemon's EV."""

    val = fields.Int(min_val=0)

    def do_read_from(self, reader: Reader) -> None:
        """Initialize an instance by reading input."""
        self.val = reader.consume_int()


class ObtainStats(Model):
    """Represent how a Pokémon was obtained."""

    mode = fields.Int(min_val=0)
    map = fields.Int(min_val=0)
    text = fields.Str()
    level = fields.Int(min_val=0)
    hatched_map = fields.Int(min_val=0)

    def do_read_from(self, reader: Reader) -> None:
        """Initialize an instance by reading input."""
        self.mode = reader.consume_int()
        self.map = reader.consume_int()
        self.text = reader.consume()
        self.level = reader.consume_int()
        self.hatched_map = reader.consume_int()


class ContestStats(Model):
    """Represent a Pokémon stats for contests."""

    cool = fields.Int(min_val=0)
    beauty = fields.Int(min_val=0)
    cute = fields.Int(min_val=0)
    smart = fields.Int(min_val=0)
    tough = fields.Int(min_val=0)
    sheen = fields.Int(min_val=0)

    def do_read_from(self, reader: Reader) -> None:
        """Initialize an instance by reading input."""
        self.cool = reader.consume_int()
        self.beauty = reader.consume_int()
        self.cute = reader.consume_int()
        self.smart = reader.consume_int()
        self.tough = reader.consume_int()
        self.sheen = reader.consume_int()


class EssentialDeluxeProperties(Model):
    """Represent optional fields based on game/server configuration."""

    scale = fields.Int(min_val=0)
    memento = fields.Str()
    dmax_level = fields.Int(min_val=0)
    gmax_factor = fields.Bool()
    dmax_able = fields.Bool()
    tera_type = fields.Str()
    focus_type = fields.Str()

    def do_read_from(self, reader: Reader) -> None:
        """Initialize an instance by reading input."""
        if (
            self.config.essentials_deluxe_installed
            or self.config.mui_mementos_installed
        ):
            self.scale = reader.consume_int()
        if self.config.mui_mementos_installed:
            self.memento = reader.consume()
        if self.config.zud_dynamax_installed:
            self.dmax_level = reader.consume_int()
            self.gmax_factor = reader.consume_bool()
            self.dmax_able = reader.consume_bool()
        if self.config.tera_installed:
            self.tera_type = reader.consume()
        if self.config.focus_installed:
            self.focus_type = reader.consume()


class _MailSpecies(Model):
    """Pokemon data on a mail."""

    gender = fields.Int(min_val=0)
    shiny = fields.Bool()
    form = fields.Int(min_val=0)
    shadow = fields.Bool()
    egg = fields.Bool()

    def do_read_from(self, reader: Reader) -> None:
        """Initialize an instance by reading input."""
        self.gender = reader.consume_int()
        self.shiny = reader.consume_bool()
        self.form = reader.consume_int()
        self.shadow = reader.consume_bool()
        self.egg = reader.consume_bool()


class Mail(Model):
    """Data on a mail."""

    item = fields.Str()
    msg = fields.Str()
    sender = fields.Str()
    species: fields.Base[list[_MailSpecies]] = fields.Base()

    def do_read_from(self, reader: Reader) -> None:
        """Initialize an instance by reading input."""
        self.item = reader.consume()
        self.msg = reader.consume()
        self.sender = reader.consume()

        self.species = []
        for _ in range(3):
            has_species = reader.consume_int_or_none()
            if has_species:
                self.species.append(_MailSpecies.read_from(reader))


class Pokemon(Model):
    """Represent a Pokemon's data."""

    # TODO(elpekenin): move related fields into classes

    species: fields.OneOf[str] = fields.OneOf()

    level = fields.Int(min_val=1)

    personal_id = fields.Int(min_val=0)

    owner_id = fields.Int(
        # NOTE(elpekenin): original code used if owner_id & ~0xFFFFFFFF
        # which i believe is equivalent max_val = flag+1
        max_val=0xFFFFFFFF + 1,
    )
    owner_name = fields.Str()
    owner_gender = fields.OneOf(options={0, 1})

    exp = fields.Int(min_val=0)  # TODO(original author): validate exp

    form = fields.Int(min_val=0)

    item: fields.OneOf[str] = fields.OneOf()

    sketched_moves: fields.Base[list[SketchedMove]] = fields.Base()
    regular_moves: fields.Base[list[Move]] = fields.Base()
    mastered_moves: fields.Base[list[Move]] = fields.Base()

    gender = fields.OneOf(options={0, 1, 2})

    shiny = fields.OptionalBool()

    ability: fields.OneOf[str] = fields.OneOf()
    ability_index = fields.OptionalInt(min_val=0)

    nature_id = fields.Str()
    nature_stats_id = fields.Str()

    ivs: fields.Base[list[IV]] = fields.Base()

    evs: fields.Base[list[EV]] = fields.Base()
    ev_sum = fields.Int(min_val=0)

    happiness = fields.Int(
        min_val=0,
        max_val=255,
    )

    name = fields.Str()

    pokeball: fields.OneOf[str] = fields.OneOf()

    steps_to_hatch = fields.Int(min_val=0)

    pokerus = fields.Int(min_val=0)

    obtain_stats: fields.Base[ObtainStats] = fields.Base()

    contest_stats: fields.Base[ContestStats] = fields.Base()

    ribbons: fields.Base[list[str]] = fields.Base()

    essential_deluxe_properties: fields.Base[EssentialDeluxeProperties] = fields.Base()

    mail: fields.Base[Mail] = fields.Base()

    fusion: fields.Base[Pokemon] = fields.Base()

    # ruff doesnt like the code being this long, but we dont care :)
    def do_read_from(self, reader: Reader) -> None:
        """Initialize an instance by reading input."""
        self.species = reader.consume()

        self.level = reader.consume_int()

        self.personal_id = reader.consume_int()

        self.owner_id = reader.consume_int()
        self.owner_name = reader.consume()
        self.owner_gender = reader.consume_int()

        self.exp = reader.consume_int()

        self.form = reader.consume_int()

        self.item = reader.consume()

        self.sketched_moves = []
        n_sketched_moves = reader.consume_int()
        for _ in range(n_sketched_moves):
            self.sketched_moves.append(SketchedMove.read_from(reader))

        self.regular_moves = []
        n_regular_moves = reader.consume_int()
        for _ in range(n_regular_moves):
            self.regular_moves.append(Move.read_from(reader))

        if self.config.pla_installed:
            self.mastered_moves = []
            n_mastered_moves = reader.consume_int()
            for _ in range(n_mastered_moves):
                self.mastered_moves.append(Move.read_from(reader))

        self.gender = reader.consume_int()

        self.shiny = reader.consume_bool()

        self.ability = reader.consume()
        self.ability_index = reader.consume_int()

        self.nature_id = reader.consume()
        self.nature_stats_id = reader.consume()

        self.ivs = []
        self.evs = []
        for _ in range(6):
            self.ivs.append(IV.read_from(reader))
            self.evs.append(EV.read_from(reader))

        ev_sum = 0
        for ev in self.evs:
            ev_sum += ev.val
        self.ev_sum = ev_sum

        self.happiness = reader.consume_int()

        self.name = reader.consume()

        self.pokeball = reader.consume()

        self.steps_to_hatch = reader.consume_int()

        self.pokerus = reader.consume_int()

        self.obtain_stats = ObtainStats.read_from(reader)

        self.contest_stats = ContestStats.read_from(reader)

        self.ribbons = []
        n_ribbons = reader.consume_int()
        for _ in range(n_ribbons):
            self.ribbons.append(reader.consume())

        self.essential_deluxe_properties = EssentialDeluxeProperties.read_from(reader)

        # mail
        has_mail = reader.consume_bool()
        if has_mail:
            self.mail = Mail.read_from(reader)

        fused = reader.consume_bool()
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
                raise exceptions.ValidationError(msg)

            for move in (
                *self.regular_moves,
                *self.mastered_moves,
            ):
                if move.name not in moves:
                    msg = f"{self.species} can not learn {move}."
                    raise exceptions.ValidationError(msg)

        genders = pokemon["genders"]
        if self.gender not in genders:
            msg = f"{self.species} can not have gender={self.gender}"
            raise exceptions.ValidationError(msg)

        forms = pokemon["forms"]
        if self.form not in forms:
            msg = f"{self.species} can not have form={self.form}"
            raise exceptions.ValidationError(msg)

        # TODO(elpekenin): check if any validation is missing


class Party(Model):
    """A team of Pokemon."""

    n_pokemon = fields.Int(min_val=0)
    pokemons: fields.Base[list[Pokemon]] = fields.Base()

    def do_read_from(self, reader: Reader) -> None:
        """Initialize an instance by reading input."""
        self.pokemons = []
        self.n_pokemon = reader.consume_int()
        for _ in range(self.n_pokemon):
            self.pokemons.append(Pokemon.read_from(reader))

        leftovers = reader.raw_all()
        if leftovers:
            rest = ", ".join(leftovers)
            msg = f"Data left in reader: {rest}"
            raise exceptions.ValidationError(msg)


def configure(config: Config) -> None:
    """Apply configuration on fields that depend on it."""
    Model.config = config

    # max int values
    IV.val.max_val = config.iv_stat_limit
    EV.val.max_val = config.ev_stat_limit
    Pokemon.ev_sum.max_val = config.ev_limit
    Pokemon.level.max_val = config.maximum_level

    # max text len
    Pokemon.owner_name.max_len = config.player_max_name_size
    Pokemon.name.max_len = config.pokemon_max_name_size

    # set of posible values
    Move.name.options = SketchedMove.name.options = configparser.sections(
        config.pbs_dir / MOVES_FILE,
    )
    Pokemon.species.options = configparser.sections(config.pbs_dir / POKEMONS_FILE)
    Pokemon.ability.options = configparser.sections(config.pbs_dir / ABILITIES_FILE)
    Pokemon.item.options = Pokemon.pokeball.options = configparser.sections(
        config.pbs_dir / ITEMS_FILE,
    )
