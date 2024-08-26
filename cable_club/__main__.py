"""Server for v20/v21. Not compatible with earlier versions of the script.

Modified by @elpekenin, some incompatibilities (even with original v20/21)
are to be expected.
"""

from __future__ import annotations

import atexit
import logging
import signal
import sys
from typing import TYPE_CHECKING, NoReturn

# TODO(elpekenin): specify class somehow? eg an argument via CLI + getattr(config, name)
from . import constants
from .config import Config, PyFileConfig
from .network.server import Server

if TYPE_CHECKING:
    from types import FrameType


def setup_remote_debugger(config: Config) -> None:
    """Configure remote debugging."""
    if not config.debug:
        return

    # lazy imports to reduce overhead on server spawn when remote debug isn't enabled

    try:
        import debugpy  # noqa: T100
    except ImportError:
        msg = "you must install debugpy to use remote debugging"
        raise ImportError(msg) from None

    # debugpy expects a path to the **directory**
    debugpy.log_to(str(config.log_dir))

    debugpy.listen(  # noqa: T100
        (config.debug_host, config.debug_port),
    )

    import warnings

    msg = "Remote debugging is enabled. Attackers may execute arbitrary code."
    warnings.warn(msg, stacklevel=1)


@atexit.register
def cleanup() -> None:
    """Logic to be run before exiting in any way."""
    logging.shutdown()


def signal_handler(signum: int, frame: FrameType | None) -> None:  # noqa: ARG001
    """Receive signals and close the app."""
    logging.info("Closing, killed by signal %s (%d)", signal.strsignal(signum), signum)
    sys.exit(0)


# these (try) get shutdown logic to run when process is closed in any way
# signal.SIGKILL can't be used? or not in the same way at least...
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def main() -> NoReturn:
    """Entrypoint of the server."""
    exception = None
    try:
        config = PyFileConfig()
        logging.basicConfig(
            level=config.log_level,
            filename=config.log_dir / constants.LOG_FILE,
            format=constants.LOG_FORMAT,
        )
        setup_remote_debugger(config)
        Server(config).run()
    # any unhandled error within the logic must be catched here to correctly shutdown
    except Exception as e:  # noqa: BLE001
        exception = e

    logging.exception("Shouldn't have gotten here...", exc_info=exception)
    sys.exit(1)


if __name__ == "__main__":
    """Run the server."""
    main()
