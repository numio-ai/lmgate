"""LMGate entry point: start aiohttp server."""

import logging
import sys

from lmgate.config import load_config
from lmgate.server import create_app


def main() -> None:
    from aiohttp import web

    config = load_config()

    logging.basicConfig(
        level=getattr(logging, config["logging"]["level"].upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )

    app = create_app(config)
    web.run_app(app, port=config["server"]["port"])


if __name__ == "__main__":
    main()
