"""CableClub server."""

from importlib import metadata

try:
    __version__ = metadata.version("cable_club")
except metadata.PackageNotFoundError:
    __version__ = "<unknown>"


del metadata
