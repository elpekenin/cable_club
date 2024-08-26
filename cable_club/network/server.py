"""Handle clients' connections."""

from __future__ import annotations

import logging
import select
import socket as s
import time
from typing import TYPE_CHECKING

from cable_club import watcher
from cable_club.data import models
from cable_club.data.writer import Writer

from .client import Client
from .states import Connected, Finding

if TYPE_CHECKING:
    from cable_club.config import Config


_logger = logging.getLogger(__name__)


class Server:
    """Model the server's logic."""

    def __init__(self, config: Config) -> None:
        """Initialize an instance."""
        self.config = config
        models.configure(config)

        self.refresh_rules_at = time.monotonic()
        self.clients: dict[s.socket, Client] = {}

        _, self.rules_files = watcher.rules_changed(self.config.rules_dir, {})
        self.rules = watcher.load_rules(self.config.rules_dir, self.rules_files)

    def select(self) -> tuple[list[s.socket], list[s.socket], list[s.socket]]:
        """Thin wrapper on top of select.

        Collects all readers and writers and hands them off to select.select().
        """
        reads = list(self.clients)
        reads.append(self.socket)

        writes = [sock for sock, client in self.clients.items() if client.send_buffer]

        return select.select(reads, writes, reads, 1.0)

    def run(self) -> None:
        """Execute the server's logic (blocking busy loop)."""
        with s.socket(s.AF_INET, s.SOCK_STREAM) as self.socket:
            self.socket.setsockopt(s.SOL_SOCKET, s.SO_REUSEADDR, 1)
            self.socket.bind((self.config.host, self.config.port))
            _logger.info("Started Server on %s:%d", self.config.host, self.config.port)
            self.socket.listen()
            try:
                while True:
                    self.maybe_reload_rules()

                    read, write, errors = self.select()
                    self.handle_errors(errors)
                    self.write_to_all(write)
                    self.read_all(read)
            except KeyboardInterrupt:
                _logger.info("Stopping Server")

    def maybe_reload_rules(self) -> None:
        """Check the rules folder for updates.

        This happens every config.rules_refresh_rate seconds (approx).
        """
        if time.monotonic() < self.refresh_rules_at:
            return

        reload_rules, rules_files = watcher.rules_changed(
            self.config.rules_dir,
            self.rules_files,
        )

        if reload_rules:
            self.rules_files = rules_files
            self.rules = watcher.load_rules(self.config.rules_dir, self.rules_files)

        self.refresh_rules_at = time.monotonic() + self.config.rules_refresh_rate

    def handle_error(self, socket: s.socket) -> None:
        """Handle a single error socket."""
        if socket is self.socket:
            msg = "Error on listening socket."
            raise RuntimeError(msg)

        self.disconnect(socket)

    def handle_errors(self, sockets: list[s.socket]) -> None:
        """Handle all error sockets."""
        for socket in sockets:
            self.handle_error(socket)

    def write_to(self, socket: s.socket) -> None:
        """Write to a single socket."""
        client = self.clients[socket]
        try:
            buffer = client.send_buffer
            n = socket.send(buffer)
            _logger.debug("sent %s to %s", buffer, socket)
            client.send_buffer = client.send_buffer[n:]
        except s.error as e:  # noqa: UP024
            # ruff complains that socket.error is an alias to OSError and should use
            # it instead. however, keeping it like this in case this implementation
            # detail changes and `socket.error` becomes something else
            self.disconnect(socket, str(e))

    def write_to_all(self, sockets: list[s.socket]) -> None:
        """Write to all sockets."""
        for socket in sockets:
            self.write_to(socket)

    def read_from(self, socket: s.socket) -> None:
        """Read from a single socket."""
        if socket is self.socket:
            new_sock, address = self.socket.accept()
            # ruff doesnt like a boolean argument without any name
            # but that's the function signature, nothing we can do here
            new_sock.setblocking(False)  # noqa: FBT003
            # NOTE: address is `Any` based on official Python hinting...
            client = self.clients[new_sock] = Client(address)
            _logger.info("%s: connected", client)
            return

        client = self.clients[socket]
        try:
            recvd = socket.recv(4096)
        except ConnectionResetError:
            self.disconnect(socket)
            return

        if not recvd:
            # Zero-length read from a non-blocking socket is
            # a disconnect.
            self.disconnect(socket, "client disconnected")
            return

        recv_buffer = client.recv_buffer + recvd
        while True:
            message, sep, recv_buffer = recv_buffer.partition(b"\n")
            if not sep:
                # No newline, buffer the partial message.
                client.recv_buffer = message
                break

            _logger.debug("received: %s", message)
            try:
                old = client.state
                client.state, state_changed = old.handle(socket, self, message)

                if state_changed:
                    _logger.debug("transition: %s -> %s", old, client.state)
            except Exception as e:
                msg = "server error"
                _logger.exception(msg, exc_info=e)
                self.disconnect(socket, msg)

    def read_all(self, sockets: list[s.socket]) -> None:
        """Read from all sockets."""
        for socket in sockets:
            self.read_from(socket)

    def connect(self, s_connecting: s.socket, s_finding: s.socket) -> None:
        """Tell two clients about each other's existence."""
        c_connecting = self.clients[s_connecting]
        c_finding = self.clients[s_finding]

        if not (
            isinstance(c_connecting.state, Finding)
            and isinstance(c_finding.state, Finding)
        ):
            _logger.error(
                "Can only use Server.connect() on players in the Finding state",
            )
            return

        # let them know about each other
        writer = Writer()
        writer.add("found")
        writer.add(0)
        c_finding.state.write(writer)
        self.write_server_rules(writer)
        writer.send(c_connecting)

        writer = Writer()
        writer.add("found")
        writer.add(1)
        c_connecting.state.write(writer)
        self.write_server_rules(writer)
        writer.send(c_finding)

        # mark them as connected
        c_connecting.state = Connected(s_finding)
        c_finding.state = Connected(s_connecting)
        _logger.info("%s: connected to %s", c_connecting, c_finding)

    def disconnect(self, socket: s.socket, reason: str = "unknown error") -> None:
        """Close a client's connection."""
        _logger.debug("disconnecting %s. reason: %s", socket, reason)

        try:
            client = self.clients.pop(socket)
        # this happens, at least, when a bad message comes is (eg: bots looking for
        # vulnerabilities). socket wasn't setup as a client yet and thus .pop() fails...
        # instead of cluttering logs with it, lets just ignore the exception
        except KeyError:
            return

        try:
            writer = Writer()
            writer.add("disconnect")
            writer.add(reason)
            writer.send_now(socket)
            socket.close()
        except Exception as e:
            _logger.exception("Couldnt send reason to socket", exc_info=e)
            return

        # disconnect the other end
        if isinstance(client.state, Connected):
            self.disconnect(client.state.peer, "peer disconnected")

    def write_server_rules(self, writer: Writer) -> None:
        """Dump server's rules into a writer."""
        writer.add(len(self.rules))
        for r in self.rules:
            writer.add_raw(r)
