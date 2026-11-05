"""Feature-level change detection between compatible snapshots."""
from hashlib import sha256
from shapely import normalize, to_wkb


def compare(before, after):
    def index(rows):
        result={}
        for key,geometry in rows:
            digest=sha256(to_wkb(normalize(geometry))).hexdigest()
            if key in result and result[key]!=digest:
                raise ValueError('conflicting duplicate feature identifier')
            result[key]=digest
        return result
    old,new=index(before),index(after)
    return dict(added=sorted(new.keys()-old.keys()),removed=sorted(old.keys()-new.keys()),
                changed=sorted(k for k in old.keys() & new.keys() if old[k]!=new[k]))
