"""Convenience aliases."""

ABILITIES_FILE = "abilities.txt"
ITEMS_FILE = "items.txt"
MOVES_FILE = "moves.txt"
POKEMONS_FILE = "server_pokemon.txt"

GENDERS = {
    "AlwaysMale": {0},
    "AlwaysFemale": {1},
    "Genderless": {2},
}

UTF8 = "utf8"
UTF8_SIG = "utf-8-sig"

LOG_FILE = "server.log"
LOG_FORMAT = (
    "[%(asctime)s] %(levelname)s - %(name)s (%(pathname)s:%(lineno)d) %(message)s"
)
