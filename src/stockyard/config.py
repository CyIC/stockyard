# -*- coding: utf-8 -*-
"""Runtime settings resolved from the environment."""
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Settings shared by every front end.

    :param data_dir: writable directory for the cache and chart output (STOCKYARD_DATA_DIR)
    """

    data_dir: Path

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "Settings":
        """Build settings from environment variables (defaults to os.environ)."""
        env = os.environ if environ is None else environ
        return cls(data_dir=Path(env.get("STOCKYARD_DATA_DIR", ".")))
