"""trace.py — 操作轨迹：data/trace/<center>/<run_id>.jsonl"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_CAP = os.path.dirname(_HERE)
if _CAP not in sys.path:
    sys.path.insert(0, _CAP)

import _common as cm  # noqa: E402


def _path(run_id, center):
    d = os.path.join(cm.DATA, 'trace', center)
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, run_id + '.jsonl')


def append(run_id, center, event, detail=None):
    cm.append_jsonl(_path(run_id, center),
                    {'ts': cm.now_iso(), 'run_id': run_id,
                     'center': center, 'event': event, 'detail': detail or {}})


def read(run_id, center):
    return cm.read_jsonl(_path(run_id, center))


def centers(run_id):
    """返回该 run_id 有轨迹的所有中心"""
    base = os.path.join(cm.DATA, 'trace')
    out = []
    if not os.path.isdir(base):
        return out
    for c in sorted(os.listdir(base)):
        if os.path.exists(os.path.join(base, c, run_id + '.jsonl')):
            out.append(c)
    return out
