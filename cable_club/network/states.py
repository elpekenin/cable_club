"""Actual game server, accept user connections and interact with them."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from cable_club import exceptions
from cable_club.data import models
from cable_club.data.reader import Reader
from cable_club.version import Version

if TYPE_CHECKING:
    from socket import socket

    from cable_club.data.writer import Writer

    from .server import Server

_logger = logging.getLogger(__name__)


class State(ABC):
    """Current state of a client's connection."""

    @abstractmethod
    def handle(
        self,
        socket: socket,
        server: Server,
        message: bytes,
    ) -> tuple[State, bool]:
        """Handle a message and return the new state, usually the current one (self).

        Second return value represents whether we've changed state.
        """


class Connecting(State):
    """Establishing a connection to the server."""

    def handle(
        self,
        socket: socket,
        server: Server,
        message: bytes,
    ) -> tuple[State, bool]:
        """Validate the party, and connect to peer if possible."""
        reader = Reader.new(message)
        if reader is None:
            server.disconnect(socket, "invalid content")
            return self, False

        if reader.consume() != "find":
            server.disconnect(socket, "not a cable_club message")
            return self, False

        version = reader.consume()
        if not Version(version) >= server.config.game_version:
            server.disconnect(socket, "invalid version")
            return self, False

        peer_id = int(reader.consume())
        name = reader.consume()
        id_ = int(reader.consume())
        trainertype = reader.consume()
        win_text = reader.consume()
        lose_text = reader.consume()
        party_raw = reader.raw_all()

        try:
            party = models.Party.read_from(reader)
        except exceptions.ExhaustedReaderError:
            msg = "party's stream was incomplete."
            server.disconnect(socket, msg)
            return self, False
        except exceptions.ValidationError:
            msg = "invalid party"
            server.disconnect(socket, msg)
            return self, False

        state = Finding(
            peer_id=peer_id,
            name=name,
            id_=id_,
            trainertype=trainertype,
            win_text=win_text,
            lose_text=lose_text,
            party=party,
            party_raw=party_raw,
        )

        server.clients[socket].state = state

        _logger.debug(
            "Trainer %s, id %d (%s) -> Finding %d",
            state.name,
            public_id(state.id),
            hex(state.id),
            state.peer_id,
        )

        # Is the peer already waiting?
        for other_socket, other_client in server.clients.items():
            # dont try and connect a server to itself
            if other_socket is socket:
                continue

            other_state = other_client.state
            if (
                isinstance(other_state, Finding)
                and public_id(other_state.id) == state.peer_id
                and other_state.peer_id == public_id(state.id)
            ):
                server.connect(socket, other_socket)
                break

        # we have set the socket's state already, return it just in case
        # and False ("no change") to prevent duplicated work or even messing states up
        return server.clients[socket].state, False


class Finding(State):
    """Looking for a match."""

    def __init__(  # noqa: PLR0913
        self,
        *,
        peer_id: int,
        name: str,
        id_: int,
        trainertype: str,
        win_text: str,
        lose_text: str,
        party: models.Party,
        party_raw: list[str],
    ) -> None:
        """Initialize an instance."""
        self.peer_id = peer_id
        self.name = name
        self.id = id_
        self.trainertype = trainertype
        self.win_text = win_text
        self.lose_text = lose_text
        self.party = party
        self.party_raw = party_raw

    def handle(
        self,
        socket: socket,  # noqa: ARG002
        server: Server,  # noqa: ARG002
        message: bytes,  # noqa: ARG002
    ) -> tuple[State, bool]:
        """Ignore messages until connected."""
        return self, False

    def write(self, writer: Writer) -> None:
        """Dump this state into the received writer."""
        writer.add(self.name)
        writer.add(self.trainertype)
        writer.add(self.win_text)
        writer.add(self.lose_text)
        writer.add_raw(self.party_raw)


class Connected(State):
    """Connected to the server."""

    peer: socket

    def __init__(self, peer: socket) -> None:
        """Intialize an instance."""
        self.peer = peer

    def handle(
        self,
        socket: socket,  # noqa: ARG002
        server: Server,
        message: bytes,
    ) -> tuple[State, bool]:
        """Forward messages to the peer."""
        state = server.clients.get(self.peer)

        if state:
            state.send_buffer += message + b"\n"
        else:
            _logger.debug("%s: message dropped (no peer)", state)

        return self, False


def public_id(id_: int) -> int:
    """Trim an arbitrary int into the expected size."""
    return id_ & 0xFFFF
