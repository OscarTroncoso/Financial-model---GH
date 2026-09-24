"""Reproducible phase-1 sensitivity suite, with no parameter selection."""

from dataclasses import replace
import json
from pathlib import Path

from .config import LabConfig
from .report import encode, verify_replay, write_comparison


def sensitivity_configs(config: LabConfig) -> dict[str, LabConfig]:
    """Fixed one-at-a-time probes; illustrative values, never optimized winners."""
    return {
        "baseline": config,
        "zero_cost": replace(config, commission_bps=0, half_spread_bps=0, slippage_bps=0),
        "high_cost": replace(config, commission_bps=5, half_spread_bps=5, slippage_bps=10),
        "floor_90": replace(config, protected_fraction=.9, max_drawdown=.1),
        "multiplier_2": replace(config, base_multiplier=2, min_multiplier=min(config.min_multiplier,2),
                                max_multiplier=max(config.max_multiplier,2)),
        "volatility_target_10": replace(config, volatility_target=.1),
        "eppi_exponent_3": replace(config, eppi_exponent=3),
        "monthly_ratchet": replace(config, floor_ratchet="monthly"),
        "no_optional_emergency": replace(config, emergency_enabled=False),
    }


def write_validation_suite(config: LabConfig, directory: Path) -> Path:
    """Save nine full comparisons, replay every bundle, write completion last.

    An interrupted/failed suite has no validation.json success artifact. Source
    and every input/event remain in each profile. No OOS or profitability claim.
    """
    if directory.exists():
        raise FileExistsError(f"Choose a new validation directory: {directory}")
    directory.mkdir(parents=True)
    rows = []
    count = 0
    hashes = {}
    for profile, settings in sensitivity_configs(config).items():
        output = directory / profile
        write_comparison(settings, output)
        manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
        hashes[profile] = manifest["code_hash"]
        model_metrics: dict[str, list[dict]] = {}
        for filename in manifest["files"]:
            path = output / filename
            verify_replay(path)
            payload = json.loads(path.read_text(encoding="utf-8"))
            model_metrics.setdefault(payload["model"], []).append(payload["metrics"])
            count += 1
        for model, metrics in model_metrics.items():
            rows.append((profile, model, min(m["time_weighted_return"] for m in metrics),
                         max(m["time_weighted_return"] for m in metrics),
                         max(m["maximum_drawdown"] for m in metrics),
                         sum(m["floor_breach_observations"] for m in metrics),
                         sum(m["costs_eur"] for m in metrics)))
        print(f"{profile}: {len(manifest['files'])} runs saved and replayed", flush=True)
    lines = ["# Phase 1 synthetic sensitivity suite", "",
             "Nine predefined profiles; ten synthetic paths and eight models per profile.",
             "Ranges are across heterogeneous stresses, not statistical confidence intervals.",
             "Costs and breach counts are summed across paths only as diagnostics.",
             "No optimization, historical data, OOS evidence, or strategy promotion.", "",
             "| Profile | Model | Min TWR | Max TWR | Worst drawdown | Breach observations | Costs EUR |",
             "|---|---|---:|---:|---:|---:|---:|"]
    for profile, model, low, high, dd, breaches, costs in rows:
        lines.append(f"| {profile} | {model} | {low:.2%} | {high:.2%} | {dd:.2%} | {breaches} | {costs:.2f} |")
    report = directory / "sensitivity.md"
    report.write_text("\n".join(lines)+"\n", encoding="utf-8")
    (directory / "validation.json").write_text(encode({
        "status": "PASS: all saved runs replayed", "replayed_runs": count,
        "profiles": list(sensitivity_configs(config)), "code_hashes": hashes,
        "scope": "Synthetic phase-1 mechanics; no empirical investment validation",
    }), encoding="utf-8")
    return report
