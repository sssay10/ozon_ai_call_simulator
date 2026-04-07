"""ASGI entrypoint for uvicorn (`main:app`)."""

from __future__ import annotations

import logging
import os

# Configure before importing the app so lifespan and imports see the same handlers.
_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
_level = getattr(logging, _level_name, logging.INFO)
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=_level,
        format="%(asctime)s | %(levelname)-5s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
else:
    logging.getLogger().setLevel(_level)

from api.app import create_app

app = create_app()
