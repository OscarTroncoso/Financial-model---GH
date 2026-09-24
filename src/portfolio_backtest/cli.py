"""CLI for phase-3 synthetic acceptance and exact local replay."""
import argparse
import json
from pathlib import Path
from .contracts import Settings
from .policies import AllocationPolicy
from .report import acceptance_suite, replay


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--output", type=Path)
    group.add_argument("--replay", type=Path)
    parser.add_argument("--config", type=Path, default=Path("config/backtest.json"))
    args = parser.parse_args()
    if args.replay:
        result = replay(args.replay)
    else:
        config = json.loads(args.config.read_text(encoding="utf-8"))
        if set(config) != {"execution", "policy"}:
            raise ValueError("Config requires exactly execution and policy")
        result = acceptance_suite(args.output, Settings(**config["execution"]), AllocationPolicy(**config["policy"]))
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
