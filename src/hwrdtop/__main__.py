"""Command-line entry point for ``python -m hwrdtop``."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from hwrdtop.app import HWRDTopApp


def main(argv: Sequence[str] | None = None) -> int:
    """Parse command-line options and start the monitor."""
    parser = argparse.ArgumentParser(description="Live Linux system monitor")
    parser.add_argument(
        "-r",
        "--refresh-rate",
        type=float,
        default=1.0,
        metavar="SECONDS",
        help="screen refresh interval in seconds (default: 1.0)",
    )
    args = parser.parse_args(argv)
    if args.refresh_rate <= 0:
        parser.error("--refresh-rate must be greater than zero")

    HWRDTopApp(refresh_rate=args.refresh_rate).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
