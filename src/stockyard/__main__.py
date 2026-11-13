"""``python -m stockyard`` runs the CLI; Warren the bot is ``python -m stockyard.bot``."""

import sys

from stockyard.cli import main

sys.exit(main())
