"""mailbox.py — 中心间文件信封（唯一跨中心通道）

data/mailbox/<from>_<to>/<req_id>.req.json  请求
data/mailbox/<from>_<to>/<req_id>.res.json  结果
data/mailbox/<from>_<to>/<req_id>.err.json  错误
消费方按 req_id 原子改名占用（.req.json → .req.lock）；信封保留 7 天。
"""
import json
import os
import sys
from datetime import datetime, timedelta

_HERE = os.path.dirname(os.path.abspath(__file__))
_CAP = os.path.dirname(_HERE)
if _CAP not in sys.path:
    sys.path.insert(0, _CAP)

import _common as cm  # noqa: E402

CENTERS = ('eng', 'data', 'solution')


def _box(frm, to):
    assert frm in CENTERS and to in CENTERS, 'bad center: %s->%s' % (frm, to)
    d = os.path.join(cm.DATA, 'mailbox', '%s_%s' % (frm, to))
    os.makedirs(d, exist_ok=True)
    return d


def send(frm, to, type_, payload, run_id=None, deadline_s=3600, return_as=None, trace=None):
    """投递请求信封，返回 req_id"""
    rid = (run_id or cm.run_id()) + '-or' + cm.rand_id()
    deadline = (datetime.now().astimezone() + timedelta(seconds=deadline_s)).isoformat(timespec='seconds')
    env = {'req_id': rid, 'run_id': run_id or '', 'from': frm, 'to': to,
           'type': type_, 'payload': payload, 'return_as': return_as or '',
           'deadline': deadline, 'trace': trace or [], 'created_at': cm.now_iso()}
    cm.atomic_write_json(os.path.join(_box(frm, to), rid + '.req.json'), env)
    return rid


def claim(center):
    """原子占用本中心收件箱中最早的一封请求（.req.json → .req.lock）"""
    base = os.path.join(cm.DATA, 'mailbox')
    if not os.path.isdir(base):
        return None
    candidates = []
    for d in os.listdir(base):
        if not d.endswith('_' + center):
            continue
        for fn in os.listdir(os.path.join(base, d)):
            if fn.endswith('.req.json'):
                candidates.append(os.path.join(base, d, fn))
    candidates.sort()
    lock = None
    for p in candidates:
        lock = p[:-len('.req.json')] + '.req.lock'
        try:
            os.replace(p, lock)   # 原子改名占用；失败说明被其他消费者抢先
        except FileNotFoundError:
            continue
        env = json.load(open(lock, encoding='utf-8'))
        if env.get('deadline') and env['deadline'] < datetime.now().astimezone().isoformat(timespec='seconds'):
            _write_err(env, 'timeout')
            os.remove(lock)
            continue
        return env
    return None


def _write_err(env, error):
    p = os.path.join(_box(env['from'], env['to']), env['req_id'] + '.err.json')
    cm.atomic_write_json(p, {'req_id': env['req_id'], 'ok': False,
                             'error': error, 'ts': cm.now_iso()})


def reply(req_id, result):
    """消费方产出 .res.json 并删除 lock"""
    env, lock = _find_lock(req_id)
    if env is None:
        raise FileNotFoundError('lock not found for ' + req_id)
    res = {'req_id': req_id, 'ok': True, 'result': result, 'ts': cm.now_iso()}
    cm.atomic_write_json(os.path.join(_box(env['from'], env['to']), req_id + '.res.json'), res)
    os.remove(lock)
    return True


def fail(req_id, error):
    env, lock = _find_lock(req_id)
    if env is None:
        raise FileNotFoundError('lock not found for ' + req_id)
    _write_err(env, error)
    os.remove(lock)
    return True


def _find_lock(req_id):
    base = os.path.join(cm.DATA, 'mailbox')
    for d in os.listdir(base):
        lock = os.path.join(base, d, req_id + '.req.lock')
        if os.path.exists(lock):
            return json.load(open(lock, encoding='utf-8')), lock
    return None, None


def poll_result(req_id, wait_s=0, poll_interval_s=2):
    """投递方轮询结果；wait_s>0 时阻塞等待"""
    base = os.path.join(cm.DATA, 'mailbox')
    waited = 0.0
    while True:
        for d in os.listdir(base) if os.path.isdir(base) else []:
            res = os.path.join(base, d, req_id + '.res.json')
            err = os.path.join(base, d, req_id + '.err.json')
            if os.path.exists(res):
                return {'ok': True, **json.load(open(res, encoding='utf-8'))}
            if os.path.exists(err):
                return {'ok': False, **json.load(open(err, encoding='utf-8'))}
        if waited >= wait_s:
            return {'ok': None, 'req_id': req_id, 'state': 'pending'}
        import time
        time.sleep(poll_interval_s)
        waited += poll_interval_s
