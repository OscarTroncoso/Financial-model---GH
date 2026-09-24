"""Download free daily data, publish immutable snapshots, query and replay features."""
import argparse
from dataclasses import asdict
from datetime import date, datetime, timezone
import json
from pathlib import Path
import sys
import duckdb

from .config import DataConfig, load_data_config
from .contracts import DataQualityError, Instrument, utc
from .providers import fetch
from .storage import DataLake, encode, pipeline_hash


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",type=Path,default=Path("data"))
    parser.add_argument("--config",type=Path,default=Path("config/data.json"))
    commands = parser.add_subparsers(dest="command",required=True)
    download = commands.add_parser("download")
    download.add_argument("--start",type=date.fromisoformat,required=True)
    download.add_argument("--end",type=date.fromisoformat,required=True,help="Exclusive local session date")
    download.add_argument("--instrument",action="append",help="Configured ID; repeat to select a subset")
    features = commands.add_parser("features")
    features.add_argument("--snapshots",nargs="+",required=True)
    features.add_argument("--as-of",type=utc,required=True)
    replay = commands.add_parser("replay")
    replay.add_argument("feature_id")
    commands.add_parser("list")
    args = parser.parse_args()
    try:
        lake = DataLake(args.root)
        if args.command == "list":
            with duckdb.connect(str(lake.catalog),read_only=True) as connection:
                rows = connection.execute("SELECT * FROM snapshots ORDER BY ingested_at,instrument_id").fetchall()
            print(encode(rows).decode())
        elif args.command == "download":
            config = load_data_config(args.config)
            selected = set(args.instrument or [i.instrument_id for i in config.instruments])
            if selected - {i.instrument_id for i in config.instruments}:
                raise DataQualityError("Unknown requested instrument")
            result, failures = {}, {}
            for instrument in config.instruments:
                if instrument.instrument_id not in selected: continue
                try:
                    capture = fetch(instrument,args.start,args.end,lake.root/"cache")
                    result[instrument.instrument_id] = lake.ingest(capture,config.max_gap_days)
                except Exception as error:
                    # Each failed provider is explicit; preserve other successful
                    # snapshots, but exit nonzero. Never declare batch success.
                    failures[instrument.instrument_id] = f"{type(error).__name__}: {error}"
            print(encode({"snapshots":result,"failures":failures}).decode())
            if failures: parser.exit(2,"Download incomplete; failed instruments cannot enter features.\n")
        elif args.command == "features":
            print(lake.build_features(args.snapshots,args.as_of,load_data_config(args.config)))
        else:
            manifest = json.loads((lake._folder("features",args.feature_id)/"manifest.json").read_bytes())
            meta = manifest["metadata"]
            if meta["pipeline_hash"] != pipeline_hash():
                raise DataQualityError("Replay requires the original pipeline source")
            cfg = dict(meta["config"])
            cfg["instruments"] = tuple(Instrument(**row) for row in cfg["instruments"])
            rebuilt = lake.build_features(meta["snapshots"],utc(meta["decision_time"]),DataConfig(**cfg))
            if rebuilt != args.feature_id:
                raise DataQualityError("Feature version does not reproduce")
            print("Replay verified: "+rebuilt)
    except (ValueError,KeyError,TypeError,OSError,duckdb.Error) as error:
        parser.exit(2,f"Data pipeline failed: {error}\n")


if __name__ == "__main__":
    main()
