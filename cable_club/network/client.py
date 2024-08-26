"""Handle a client's state."""

from __future__ import annotations

from .states import Connecting, State


class Client:
    """Represent a client."""

    def __init__(self, address: tuple[int, int]) -> None:
        """Initialize an instance."""
        self.address = address
        self.state: State = Connecting()
        self.send_buffer = b""
        self.recv_buffer = b""

    def __str__(self) -> str:
        """Represent the state as a string."""
        return (
            f"{self.address[0]}:{self.address[1]}/{type(self.state).__name__.lower()}"
        )
