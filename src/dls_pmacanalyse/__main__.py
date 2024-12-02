"""Interface for ``python -m dls_pmacanalyse``."""

from argparse import ArgumentParser
from collections.abc import Sequence

from dls_pmacanalyse.dls_pmacanalyse import main as dls_pmacanalyse_main

from . import __version__

__all__ = ["main"]


def main(args: Sequence[str] | None = None) -> None:
    """Argument parser for the CLI."""
    parser = ArgumentParser()
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=__version__,
    )
    parser.parse_args(args)
    dls_pmacanalyse_main()


if __name__ == "__main__":
    main()
