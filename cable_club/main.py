"""Server for v20/v21. Not compatible with earlier versions of the script.

Modified by @elpekenin, some incompatibilities (even with original v20/21)
are to be expected.
"""

from __future__ import annotations

import argparse
import logging
import sys

# TODO(elpekenin): specify class somehow? eg an argument via CLI + getattr(config, name)
from cable_club import constants
from cable_club.config import PyFileConfig
from cable_club.network import Server

_logger = logging.getLogger(__name__)


def main() -> int:
    """Entrypoint of the server."""
    config = PyFileConfig()
    logging.basicConfig(
        level=config.log_level,
        format=constants.LOG_FORMAT,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(
                filename=config.log_dir / constants.LOG_FILE,
                mode="w",
            ),
        ],
    )

    parser = argparse.ArgumentParser()
    _ = parser.parse_args()

    try:
        Server(config).run()
    # any unhandled error within the logic must be catched here to correctly shutdown
    except Exception:
        _logger.exception("Unhandled exception")
    except KeyboardInterrupt:
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
