"""Portable reproducible run bundles: source, inputs, config, events and metrics."""

from dataclasses import asdict
from datetime import datetime
import hashlib
import json
from pathlib import Path
import platform

from . import __version__
from .config import LabConfig
from .data import Observation
from .engine import run
from .metrics import summarize
from .rules import BLOCKED_MODELS, ENABLED_MODELS
from .scenarios import stress_scenarios


def encode(value: object) -> str:
    """Canonical JSON, exact decimal float serialization, no NaN/Infinity."""
    def default(item: object) -> str:
        if isinstance(item, datetime):
            return item.isoformat()
        raise TypeError(f"Cannot serialize {type(item)}")
    return json.dumps(value, sort_keys=True, indent=2, default=default, allow_nan=False) + "\n"


def fingerprint(value: object) -> str:
    return hashlib.sha256(encode(value).encode()).hexdigest()


def write_comparison(config: LabConfig, directory: Path) -> Path:
    """Create a fresh audit bundle; refuse to overwrite any prior experiment."""
    if directory.exists():
        raise FileExistsError(f"Choose a new run directory: {directory}")
    sources = {path.name: path.read_text(encoding="utf-8") for path in sorted(Path(__file__).parent.glob("*.py"))}
    code_hash = fingerprint(sources)
    rows = []
    bundles = {}
    for scenario in stress_scenarios(config):
        for model in ENABLED_MODELS:
            result = run(scenario.observations, scenario.config, model)
            metrics = summarize(result)
            inputs = {"config": scenario.config.to_dict(), "observations": [asdict(x) for x in scenario.observations]}
            bundles[f"{scenario.name}--{model}.json"] = {
                "version": __version__, "code_hash": code_hash, "input_hash": fingerprint(inputs),
                "model": model, "scenario": scenario.name, "inputs": inputs,
                "events": [asdict(x) for x in result.events], "metrics": metrics,
            }
            rows.append((scenario.name, model, metrics))
    # All simulations and serializations complete before producing a usable bundle.
    serialized = {name: encode(bundle) for name, bundle in bundles.items()}
    directory.mkdir(parents=True)
    source_dir = directory / "source"
    source_dir.mkdir()
    for name, source in sources.items():
        (source_dir / name).write_text(source, encoding="utf-8")
    for name, payload in serialized.items():
        (directory / name).write_text(payload, encoding="utf-8")
    manifest = {
        "version": __version__, "python": platform.python_version(), "code_hash": code_hash,
        "enabled_models": ENABLED_MODELS, "blocked_models": BLOCKED_MODELS,
        "phase_1_gate": "Report generated; acceptance evidence is assessed in docs/PHASE1_ACCEPTANCE.md",
        "files": {name: hashlib.sha256(payload.encode()).hexdigest() for name, payload in serialized.items()},
    }
    (directory / "manifest.json").write_text(encode(manifest), encoding="utf-8")
    lines = ["# Synthetic portfolio insurance comparison", "",
             "Mechanical tests only: no historical/OOS evidence and no guaranteed floor.",
             "All mandatory variants are included; see docs/DYNAMIC_MODELS.md for exact identities.",
             "Static = monthly constant-mix aggregate risky proxy, without emergency overlay.",
             "All other models use configured emergency policy. Pure strategy tests can disable it.",
             "conditional_cppi uses a published quantile bound plus a rolling Gaussian baseline; not a probability guarantee.",
             "It holds safe during warm-up and waits for the next monthly decision before entering.",
             "TIPP and drawdown coincide when alpha = 1 - maximum_drawdown.", "",
             "| Synthetic path | Model | Net TWR | Max drawdown | Breach observations | Costs EUR |",
             "|---|---|---:|---:|---:|---:|"]
    for scenario, model, m in rows:
        lines.append(f"| {scenario} | {model} | {m['time_weighted_return']:.2%} | {m['maximum_drawdown']:.2%} | {m['floor_breach_observations']} | {m['costs_eur']:.2f} |")
    lines += ["", "Full metric definitions: source/metrics.py. Each JSON preserves inputs and every decision.",
              f"Code SHA256: `{code_hash}`."]
    report = directory / "comparison.md"
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def verify_replay(path: Path) -> None:
    """Recompute a saved run only with matching code and inputs; never run saved code."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    sources = {p.name: p.read_text(encoding="utf-8") for p in sorted(Path(__file__).parent.glob("*.py"))}
    if payload["code_hash"] != fingerprint(sources):
        raise ValueError("Code differs from saved run; use the matching package version")
    inputs = payload["inputs"]
    if payload["input_hash"] != fingerprint(inputs):
        raise ValueError("Saved input hash mismatch")
    observations = tuple(Observation(
        datetime.fromisoformat(row["timestamp"]),
        datetime.fromisoformat(row["available_to_model_time"]),
        row["risky_return"], row["safe_return"],
    ) for row in inputs["observations"])
    result = run(observations, LabConfig(**inputs["config"]), payload["model"])
    if encode([asdict(e) for e in result.events]) != encode(payload["events"]):
        raise ValueError("Saved events do not reproduce")
    if encode(summarize(result)) != encode(payload["metrics"]):
        raise ValueError("Saved metrics do not reproduce")
