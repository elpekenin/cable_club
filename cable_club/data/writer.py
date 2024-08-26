"""Convert data into raw bytes."""

from __future__ import annotations

import typing

from cable_club.constants import UTF8

if typing.TYPE_CHECKING:
    from socket import socket

    from cable_club.network.client import Client


class Writer:
    """Format some data to be sent."""

    def __init__(self) -> None:
        """Initialize an instance."""
        self.fields: list[str] = []

    def send_now(self, socket: socket) -> int:
        """Send variable over the wire."""
        line = ",".join(Writer.escape(f) for f in self.fields)
        line += "\n"
        return socket.send(line.encode(UTF8))

    def send(self, client: Client) -> None:
        """Get data into buffer to be later sent."""
        line = ",".join(Writer.escape(f) for f in self.fields)
        line += "\n"
        client.send_buffer += line.encode(UTF8)

    @staticmethod
    def escape(raw: str) -> str:
        """Escape special symbols in a raw string."""
        return raw.replace("\\", "\\\\").replace(",", "\\,")

    def add(self, f: object) -> None:
        """Add a field to the writer."""
        self.fields.append(str(f))

    def add_raw(self, fs: list[str]) -> None:
        """Add raw fields to the writer."""
        self.fields.extend(fs)
