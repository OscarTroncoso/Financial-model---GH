"""Run the synthetic insurance laboratory from the installed package."""

import argparse
from pathlib import Path

from .config import load_config
from .validation import write_validation_suite
from .report import verify_replay, write_comparison


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("config/lab.json"))
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--output", type=Path, help="New directory for the immutable run bundle")
    action.add_argument("--replay", type=Path, help="Verify one saved JSON bundle")
    action.add_argument("--suite", type=Path, help="New directory for sensitivity and replay validation")
    args = parser.parse_args()
    try:
        if args.replay:
            verify_replay(args.replay)
            print("Replay verified: " + str(args.replay.resolve()))
            return
        report = (write_validation_suite(load_config(args.config), args.suite) if args.suite
                  else write_comparison(load_config(args.config), args.output))
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(2, f"Lab failed: {error}\n")
    print(report.resolve())


if __name__ == "__main__":
    main()
