"""Immutable replay bundles and synthetic acceptance reports."""
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import platform
import numpy as np
import portfolio_lab

from .contracts import Bar, Settings
from .engine import Result, run
from .policies import AllocationPolicy
from portfolio_lab.rules import safe_period_return


def encoded(value) -> bytes:
    return json.dumps(value, sort_keys=True, indent=2, allow_nan=False,
                      default=lambda x: x.isoformat()).encode("utf-8")


def checksum(value) -> str:
    return hashlib.sha256(encoded(value)).hexdigest()


def source_hash() -> str:
    paths = list(Path(__file__).parent.glob("*.py")) + list(Path(portfolio_lab.__file__).parent.glob("*.py"))
    return checksum({p.parent.name + "/" + p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in sorted(paths)})


def summarize(result: Result, settings: Settings, policy: AllocationPolicy) -> dict:
    """Flow-neutral compounded return and drawdown; EUR costs and terminal NAV."""
    peak, maximum_dd, capital, breaches = 1.0, 0.0, settings.initial_cash, 0
    for event in result.events:
        peak = max(peak, event.wealth_index)
        maximum_dd = max(maximum_dd, 1 - event.wealth_index / peak)
        capital += event.contribution
        reference = capital if policy.model == "cppi" else event.high_water_mark
        if policy.model != "static" and event.portfolio_value < policy.protected_fraction * reference:
            breaches += 1
    return {"final_nav": result.events[-1].portfolio_value,
            "contributions": capital - settings.initial_cash,
            "time_weighted_return": result.events[-1].wealth_index - 1,
            "maximum_drawdown": maximum_dd,
            "costs": sum(t.cost for t in result.trades),
            "carry": sum(e.carry for e in result.events),
            "safe_income": sum(e.safe_income for e in result.events),
            "trades": len(result.trades), "floor_breach_closes": breaches,
            "pending_terminal_order": result.pending is not None}


def bundle(bars: tuple[Bar, ...], settings: Settings, policy: AllocationPolicy) -> dict:
    result = run(bars, policy, settings)
    payload = {"schema": 1, "source_hash": source_hash(),
               "runtime": {"python": platform.python_version(), "numpy": np.__version__},
               "settings": asdict(settings), "policy": asdict(policy),
               "bars": [asdict(b) for b in bars], "result": asdict(result),
               "summary": summarize(result, settings, policy)}
    # Normalize datetimes and tuples before hashing or comparing loaded JSON.
    payload = json.loads(encoded(payload))
    return {"checksum": checksum(payload), "payload": payload}


def replay(path: Path) -> dict:
    document = json.loads(path.read_text(encoding="utf-8"))
    payload = document["payload"]
    if checksum(payload) != document["checksum"]:
        raise ValueError("Bundle checksum mismatch")
    if payload["schema"] != 1 or payload["source_hash"] != source_hash():
        raise ValueError("Replay requires matching source version")
    bars = []
    for row in payload["bars"]:
        row = dict(row)
        for key in ("open_time", "close_time", "available_to_model_time"):
            row[key] = datetime.fromisoformat(row[key])
        bars.append(Bar(**row))
    reconstructed = bundle(tuple(bars), Settings(**payload["settings"]), AllocationPolicy(**payload["policy"]))
    if reconstructed != document:
        raise ValueError("Replay result or runtime mismatch")
    return reconstructed["payload"]["summary"]


def scenarios() -> dict[str, tuple[Bar, ...]]:
    """Explicit synthetic OHLC fixtures, never presented as market data."""
    result = {}
    for name in ("steady_growth", "bear", "overnight_gap", "volatile", "flat"):
        rows, price = [], 100.0
        day = datetime(2020, 1, 2, 9, tzinfo=timezone.utc)
        previous_close_time = day
        for i in range(70):
            while day.weekday() >= 5:
                day += timedelta(days=1)
            opening = price * (.5 if name == "overnight_gap" and i == 23 else 1)
            ret = {"steady_growth": .002, "bear": -.006, "overnight_gap": .001,
                   "volatile": .03 if i % 2 == 0 else -.03, "flat": 0}[name]
            price = opening * (1 + ret)
            close_time = day + timedelta(hours=7)
            elapsed = (day - previous_close_time).total_seconds() / 86400
            rows.append(Bar(day, close_time, close_time, opening,
                            max(opening, price) * 1.005, min(opening, price) * .995,
                            price, safe_period_return(.03, elapsed)))
            previous_close_time = close_time
            day += timedelta(days=1)
        result[name] = tuple(rows)
    return result


def acceptance_suite(output: Path, settings: Settings, policy: AllocationPolicy) -> dict:
    """Run 45 deterministic cases, verify every replay, then publish summary."""
    output.mkdir(parents=True, exist_ok=False)
    lines = ["# Phase 3 synthetic execution comparison", "",
             "Synthetic engineering evidence; not historical investment performance.", "",
             "| Profile | Scenario | Model | Final NAV | TWR | Max DD | Costs | Trades |",
             "|---|---|---|---:|---:|---:|---:|---:|"]
    count = 0
    for profile, cfg in (("baseline", settings),
                         ("high_cost", replace(settings, commission_bps=50, half_spread_bps=20, slippage_bps=20)),
                         ("exits", replace(settings, stop_fraction=.08, take_profit_fraction=.12, time_stop_bars=10))):
        for scenario, path in scenarios().items():
            for model in ("static", "cppi", "tipp"):
                selected = replace(policy, model=model)
                document = bundle(path, cfg, selected)
                file = output / f"{profile}--{scenario}--{model}.json"
                file.write_bytes(encoded(document))
                summary = replay(file)
                count += 1
                lines.append(f"| {profile} | {scenario} | {model} | {summary['final_nav']:.2f} | "
                             f"{summary['time_weighted_return']:.2%} | {summary['maximum_drawdown']:.2%} | "
                             f"{summary['costs']:.2f} | {summary['trades']} |")
    (output / "comparison.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    validation = {"cases": count, "replays": count, "source_hash": source_hash(),
                  "status": "passed", "evidence": "synthetic_only"}
    (output / "validation.json").write_bytes(encoded(validation))
    return validation
