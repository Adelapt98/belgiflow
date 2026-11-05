"""Immutable generation publication with an atomic reader pointer."""
import hashlib
import json
import os
from pathlib import Path


def publish(root, payload):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    content = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()
    digest = hashlib.sha256(content).hexdigest()
    target = root / f'{digest}.json'
    if not target.exists():
        temporary = root / f'{digest}.{os.getpid()}.tmp'
        with temporary.open('wb') as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    pointer = root / f'CURRENT.{os.getpid()}.tmp'
    pointer.write_text(digest, encoding='utf-8')
    os.replace(pointer, root / 'CURRENT')
    return digest


def read_current(root):
    root = Path(root)
    digest = (root / 'CURRENT').read_text(encoding='utf-8')
    if len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
        raise ValueError('invalid publication pointer')
    content = (root / f'{digest}.json').read_bytes()
    if hashlib.sha256(content).hexdigest() != digest:
        raise ValueError('publication checksum mismatch')
    return json.loads(content)
