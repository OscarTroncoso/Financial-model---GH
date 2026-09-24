"""Immutable bronze/silver/gold snapshots with a DuckDB query catalog."""
from dataclasses import asdict
from datetime import date, datetime
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re
from contextlib import contextmanager
import uuid

import duckdb

from . import SCHEMA_VERSION
from .config import DataConfig
from .contracts import Datum, DataQualityError, Instrument, iso, utc, validate_series
from .features import make_features
from .providers import Capture, normalize


@contextmanager
def staging_root(parent: Path):
    """Same-volume staging with inherited ACLs; failed stages remain unpublished.

    Python's secure TemporaryDirectory ACL can remain unreadable by a Windows
    sandbox after an elevated download renames it. A workspace child inherits
    the project's normal permissions instead. Never delete nonempty failures.
    """
    folder = parent/(".pending-"+uuid.uuid4().hex)
    folder.mkdir()
    try:
        yield folder
    finally:
        if folder.exists() and not any(folder.iterdir()):
            folder.rmdir()


def encode(value: object) -> bytes:
    def default(item):
        if isinstance(item,datetime): return iso(item)
        if isinstance(item,date): return item.isoformat()
        raise TypeError(type(item).__name__)
    return (json.dumps(value,sort_keys=True,indent=2,default=default,allow_nan=False)+"\n").encode()


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def pipeline_hash() -> str:
    paths = list(Path(__file__).parent.glob("*.py"))
    # Include the reused volatility implementation in feature provenance.
    from portfolio_lab import rules
    paths.append(Path(rules.__file__))
    return digest(encode({p.name:p.read_text(encoding="utf-8") for p in sorted(paths)}))


DATUM_COLUMNS = {
    "instrument_id":"VARCHAR","observation_time":"TIMESTAMPTZ","value":"DOUBLE",
    "currency":"VARCHAR","basis":"VARCHAR","unit":"VARCHAR","ingested_at":"TIMESTAMPTZ",
    "available_to_model_time":"TIMESTAMPTZ","published_at":"TIMESTAMPTZ","revision_at":"TIMESTAMPTZ",
    "availability_basis":"VARCHAR",
}
FEATURE_COLUMNS = {
    "instrument_id":"VARCHAR","observation_time":"TIMESTAMPTZ","available_to_model_time":"TIMESTAMPTZ",
    "currency":"VARCHAR","basis":"VARCHAR","unit":"VARCHAR","return_1d":"DOUBLE",
    "realized_volatility":"DOUBLE","window_observations":"INTEGER",
}


def write_parquet(path: Path, rows: list[dict], columns: dict[str,str]) -> None:
    """Typed Parquet via DuckDB; no inference of null-only timestamp columns."""
    if not rows: raise DataQualityError("Cannot publish empty dataset")
    with duckdb.connect() as connection:
        connection.execute("CREATE TABLE records ("+",".join(f'{k} {t}' for k,t in columns.items())+")")
        connection.executemany("INSERT INTO records VALUES ("+",".join("?" for _ in columns)+")",
                               [[r[k] for k in columns] for r in rows])
        connection.execute("COPY records TO ? (FORMAT PARQUET, COMPRESSION ZSTD)",[str(path)])


def parquet_rows(path: Path) -> list[dict]:
    with duckdb.connect() as connection:
        result = connection.execute("SELECT * FROM read_parquet(?) ORDER BY observation_time",[str(path)])
        names = [item[0] for item in result.description]
        return [dict(zip(names,row)) for row in result.fetchall()]


class DataLake:
    """Append-only data artifacts. Catalog registration happens only after checks."""
    def __init__(self, root: Path):
        self.root = root.resolve()
        for layer in ("raw","clean","features","cache"):
            (self.root/layer).mkdir(parents=True,exist_ok=True)
        self.catalog = self.root/"catalog.duckdb"
        with duckdb.connect(str(self.catalog)) as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS snapshots (
                snapshot_id VARCHAR PRIMARY KEY, instrument_id VARCHAR,
                provider VARCHAR, ingested_at TIMESTAMPTZ)""")

    def _folder(self, layer: str, snapshot_id: str) -> Path:
        if not re.fullmatch(r"[0-9a-f]{64}",snapshot_id):
            raise DataQualityError("Invalid snapshot ID")
        return self.root/layer/snapshot_id

    def ingest(self, capture: Capture, max_gap_days: int = 7) -> str:
        """Preserve original payload first; invalid data never becomes clean/cataloged.

        Failed normalization leaves bronze evidence only. Concurrent identical
        publication fails rather than overwriting. Retry is idempotent.
        """
        meta = {"schema_version":SCHEMA_VERSION,"instrument":asdict(capture.instrument),
                "start":capture.start.isoformat(),"end":capture.end.isoformat(),
                "ingested_at":iso(capture.ingested_at),"payload_sha256":digest(capture.payload),
                "media_type":capture.media_type,"source_url":capture.source_url,
                "adapter_version":capture.adapter_version,"pipeline_hash":pipeline_hash(),
                "max_gap_days":max_gap_days}
        snapshot_id = digest(encode(meta))
        raw = self._folder("raw",snapshot_id)
        if not raw.exists():
            with staging_root(self.root/"raw") as temp:
                stage = Path(temp)/snapshot_id
                stage.mkdir()
                (stage/"payload.dat").write_bytes(capture.payload)
                (stage/"metadata.json").write_bytes(encode(meta))
                stage.rename(raw)
        else:
            self.read_capture(snapshot_id)
        rows = validate_series(normalize(capture),max_gap_days)
        clean = self._folder("clean",snapshot_id)
        if not clean.exists():
            with staging_root(self.root/"clean") as temp:
                stage = Path(temp)/snapshot_id
                stage.mkdir()
                write_parquet(stage/"observations.parquet",[asdict(r) for r in rows],DATUM_COLUMNS)
                manifest = {"snapshot_id":snapshot_id,"schema_version":SCHEMA_VERSION,
                    "pipeline_hash":pipeline_hash(),"row_count":len(rows),
                    "logical_hash":digest(encode([r.to_dict() for r in rows])),
                    "parquet_sha256":digest((stage/"observations.parquet").read_bytes())}
                (stage/"manifest.json").write_bytes(encode(manifest))
                stage.rename(clean)
        self.read_rows(snapshot_id)
        with duckdb.connect(str(self.catalog)) as connection:
            connection.execute("INSERT OR IGNORE INTO snapshots VALUES (?,?,?,?)",
                [snapshot_id,capture.instrument.instrument_id,capture.instrument.provider,utc(capture.ingested_at)])
        return snapshot_id

    def read_capture(self, snapshot_id: str) -> Capture:
        raw = self._folder("raw",snapshot_id)
        meta = json.loads((raw/"metadata.json").read_bytes())
        payload = (raw/"payload.dat").read_bytes()
        if digest(encode(meta)) != snapshot_id or digest(payload) != meta["payload_sha256"]:
            raise DataQualityError("Raw snapshot integrity failure")
        if meta["schema_version"] != SCHEMA_VERSION:
            raise DataQualityError("Unsupported snapshot schema")
        return Capture(Instrument(**meta["instrument"]),date.fromisoformat(meta["start"]),
                       date.fromisoformat(meta["end"]),utc(meta["ingested_at"]),payload,
                       meta["media_type"],meta["source_url"],meta["adapter_version"])

    def read_rows(self, snapshot_id: str) -> list[Datum]:
        capture = self.read_capture(snapshot_id)
        folder = self._folder("clean",snapshot_id)
        manifest = json.loads((folder/"manifest.json").read_bytes())
        path = folder/"observations.parquet"
        if manifest["snapshot_id"] != snapshot_id or digest(path.read_bytes()) != manifest["parquet_sha256"]:
            raise DataQualityError("Clean snapshot integrity failure")
        rows = [Datum(**r) for r in parquet_rows(path)]
        if len(rows) != manifest["row_count"] or digest(encode([r.to_dict() for r in rows])) != manifest["logical_hash"]:
            raise DataQualityError("Clean logical hash failure")
        if any(r.instrument_id != capture.instrument.instrument_id for r in rows):
            raise DataQualityError("Instrument identity changed")
        return rows

    def as_of(self, snapshot_ids: list[str], decision_time: datetime) -> list[Datum]:
        """DuckDB availability filter BEFORE latest-vintage selection.

        Caller explicitly pins snapshot IDs; newer downloads never mutate old
        experiment inputs. Equal-time conflicting vintages fail, not arbitrary
        selection. Currency, unit, and basis may not change within an instrument.
        """
        if not snapshot_ids or len(set(snapshot_ids)) != len(snapshot_ids):
            raise DataQualityError("Unique nonempty snapshot list required")
        decision_time = utc(decision_time)
        paths = []
        for snapshot_id in sorted(snapshot_ids):
            self.read_rows(snapshot_id)
            paths.append(str(self._folder("clean",snapshot_id)/"observations.parquet"))
        with duckdb.connect() as connection:
            result = connection.execute("""SELECT DISTINCT * FROM read_parquet(?)
                WHERE available_to_model_time <= ? AND observation_time <= ?
                ORDER BY instrument_id, observation_time, available_to_model_time, ingested_at""",
                [paths,decision_time,decision_time])
            names = [d[0] for d in result.description]
            available = [Datum(**dict(zip(names,row))) for row in result.fetchall()]
        selected = {}
        identities = {}
        for row in available:
            identity = (row.currency,row.basis,row.unit)
            if row.instrument_id in identities and identities[row.instrument_id] != identity:
                raise DataQualityError("Incompatible series definitions")
            identities[row.instrument_id] = identity
            key = (row.instrument_id,row.observation_time)
            old = selected.get(key)
            if old and (old.available_to_model_time,old.ingested_at)==(row.available_to_model_time,row.ingested_at) and old != row:
                raise DataQualityError("Conflicting vintages at identical availability")
            selected[key] = row
        return list(selected.values())

    def build_features(self, snapshot_ids: list[str], decision_time: datetime, config: DataConfig) -> str:
        """Publish deterministic gold with complete config/input/code provenance."""
        decision_time = utc(decision_time)
        rows = self.as_of(snapshot_ids,decision_time)
        expected = {i.instrument_id:i for i in config.instruments}
        if {r.instrument_id for r in rows} != set(expected):
            raise DataQualityError("Missing or extra instruments at decision time")
        for snapshot_id in snapshot_ids:
            captured = self.read_capture(snapshot_id).instrument
            if captured.instrument_id not in expected or captured != expected[captured.instrument_id]:
                raise DataQualityError("Instrument metadata does not match feature configuration")
        features = []
        for name,instrument in sorted(expected.items()):
            series = [r for r in rows if r.instrument_id==name]
            if any((r.currency,r.basis,r.unit)!=(instrument.currency,instrument.basis,instrument.unit) for r in series):
                raise DataQualityError("Feature configuration conflicts with source units")
            features.extend(make_features(series,decision_time,config))
        meta = {"schema_version":SCHEMA_VERSION,"pipeline_hash":pipeline_hash(),
            "snapshots":sorted(snapshot_ids),"decision_time":iso(decision_time),
            "config":asdict(config),"duckdb_version":duckdb.__version__,
            "tzdata_version":importlib.metadata.version("tzdata")}
        feature_id = digest(encode(meta))
        folder = self._folder("features",feature_id)
        logical_hash = digest(encode([asdict(f) for f in features]))
        if folder.exists():
            self.verify_features(feature_id)
            manifest = json.loads((folder/"manifest.json").read_bytes())
            if manifest["logical_hash"] != logical_hash:
                raise DataQualityError("Same inputs produced different features")
            return feature_id
        with staging_root(self.root/"features") as temp:
            stage = Path(temp)/feature_id
            stage.mkdir()
            write_parquet(stage/"features.parquet",[asdict(f) for f in features],FEATURE_COLUMNS)
            manifest = {"metadata":meta,"feature_id":feature_id,"logical_hash":logical_hash,
                        "row_count":len(features),"parquet_sha256":digest((stage/"features.parquet").read_bytes())}
            (stage/"manifest.json").write_bytes(encode(manifest))
            stage.rename(folder)
        self.verify_features(feature_id)
        return feature_id

    def verify_features(self, feature_id: str) -> None:
        """Verify file integrity and input dependencies without running saved code."""
        folder = self._folder("features",feature_id)
        manifest = json.loads((folder/"manifest.json").read_bytes())
        if digest(encode(manifest["metadata"])) != feature_id:
            raise DataQualityError("Feature metadata integrity failure")
        path = folder/"features.parquet"
        if digest(path.read_bytes()) != manifest["parquet_sha256"]:
            raise DataQualityError("Feature Parquet integrity failure")
        for snapshot_id in manifest["metadata"]["snapshots"]:
            self.read_rows(snapshot_id)
        # Canonical order independent of file physical row order.
        records = sorted(parquet_rows(path),key=lambda r:(r["instrument_id"],r["observation_time"]))
        if len(records)!=manifest["row_count"] or digest(encode(records))!=manifest["logical_hash"]:
            raise DataQualityError("Feature logical integrity failure")
