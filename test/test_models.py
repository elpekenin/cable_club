"""Test data models."""

import unittest

from cable_club.data import Reader, models
from test import fixtures
from test import utils as test_utils


class ModelTest(unittest.TestCase):
    """Test case for models."""

    @classmethod
    def setUpClass(cls) -> None:
        """Configure application."""
        config = test_utils.TestConfig(
            ESSENTIALS_DELUXE_INSTALLED=True,
            ZUD_DYNAMAX_INSTALLED=True,
            TERA_INSTALLED=True,
        )

        models.configure(config)

        return super().setUpClass()

    @staticmethod
    def reader_factory() -> Reader:
        """Configure a new Reader.

        It will be on the same state that the server would have it before parsing it.
        """
        reader = Reader.new(fixtures.VALID)
        if reader is None:
            msg = "Invalid reader from fixture???"
            raise AssertionError(msg)

        # fields that server would consume before parsing the party
        for _ in (
            "find",
            "version",
            "peer",
            "name",
            "id",
            "trainertype",
            "win_text",
            "lose_text",
        ):
            reader.read()

        return reader

    def test_parsing(self) -> None:
        """Confirm that parsing correct values does work."""
        reader = self.reader_factory()
        party = models.Party.read_from(reader)
        self.assertEqual(6, len(party.pokemons))
