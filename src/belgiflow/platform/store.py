"""Atomic partition artifacts with explicit provenance and reproducible checksums."""
from datetime import date, datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import uuid
import pyarrow as pa
import pyarrow.parquet as pq


def day(value):
    return date.fromisoformat(value).isoformat()


class Store:
    def __init__(self, root, partition):
        self.root = Path(root)
        self.partition = day(partition)
        self.directory = self.root / 'partitions' / self.partition
        self.directory.mkdir(parents=True, exist_ok=True)

    def path(self, name, suffix='parquet'):
        if not name.replace('_', '').isalnum():
            raise ValueError('invalid dataset name')
        return self.directory / f'{name}.{suffix}'

    def write(self, name, rows, provenance=None):
        if not rows:
            raise ValueError(f'{name}: empty dataset requires an explicit schema')
        table = pa.Table.from_pylist(rows)
        target = self.path(name)
        temporary = target.with_suffix(f'.{uuid.uuid4().hex}.tmp')
        pq.write_table(table, temporary, compression='zstd')
        os.replace(temporary, target)
        digest = sha256(target.read_bytes()).hexdigest()
        manifest = dict(dataset=name, partition=self.partition, rows=len(rows), sha256=digest,
                        schema_sha256=sha256(str(table.schema).encode()).hexdigest(),
                        observed_at=datetime.now(timezone.utc).isoformat(), provenance=provenance or {})
        self.json(name + '_manifest', manifest)
        return manifest

    def read(self, name):
        target = self.path(name)
        manifest = self.read_json(name + '_manifest')
        if sha256(target.read_bytes()).hexdigest() != manifest['sha256']:
            raise ValueError(f'{name}: artifact checksum mismatch')
        return pq.ParquetFile(target).read().to_pylist()

    def json(self, name, value):
        target = self.path(name, 'json')
        temporary = target.with_suffix(f'.{uuid.uuid4().hex}.tmp')
        temporary.write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False), encoding='utf-8')
        os.replace(temporary, target)
        return value

    def read_json(self, name):
        return json.loads(self.path(name, 'json').read_text(encoding='utf-8'))
