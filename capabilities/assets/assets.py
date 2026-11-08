"""assets.py — 契约 3 · 资产库与 URI 寻址（替代 OpenViking，文件实现）

URI: viking://<namespace>/<path>，namespace ∈ {engineering, datacenter, solution, plugins}
写入更新 manifest.json + index.jsonl；覆盖写保留 .versions/ 旧版本快照（版本号自增）。
分层读取：L0=标题+首段摘要 · L1=标题+全部小节标题+首段 · full=全文
"""
import json
import os
import re
import shutil
import sys
import uuid

_HERE = os.path.dirname(os.path.abspath(__file__))
_CAP = os.path.dirname(_HERE)
if _CAP not in sys.path:
    sys.path.insert(0, _CAP)

import _common as cm  # noqa: E402

NAMESPACES = ('engineering', 'datacenter', 'solution', 'plugins')


def _ns_dir(namespace):
    assert namespace in NAMESPACES, 'bad namespace: ' + str(namespace)
    d = os.path.join(cm.DATA, 'assets', namespace)
    os.makedirs(d, exist_ok=True)
    return d


def _to_path(uri):
    """viking://<ns>/<path> → (ns, relpath)"""
    assert uri.startswith('viking://'), 'bad uri: ' + uri
    rest = uri[len('viking://'):]
    ns, _, rel = rest.partition('/')
    return ns, rel


def _manifest_path(namespace):
    return os.path.join(_ns_dir(namespace), 'manifest.json')


def _load_manifest(namespace):
    p = _manifest_path(namespace)
    if not os.path.exists(p):
        return {}
    return json.load(open(p, encoding='utf-8'))


def _save_manifest(namespace, m):
    cm.atomic_write_json(_manifest_path(namespace), m)


def write(namespace, path, content, meta=None):
    """写资产；已存在 → 旧文件进 .versions/v<N>-，manifest version 自增"""
    meta = dict(meta or {})
    rel = path.lstrip('/')
    full = os.path.join(_ns_dir(namespace), rel)
    m = _load_manifest(namespace)
    uri = 'viking://%s/%s' % (namespace, rel)
    entry = m.get(uri, {'versions': 0})
    if os.path.exists(full):
        entry['versions'] += 1
        vdir = os.path.join(os.path.dirname(full), '.versions')
        os.makedirs(vdir, exist_ok=True)
        shutil.copy2(full, os.path.join(vdir, 'v%d-%s' % (entry['versions'], os.path.basename(full))))
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, 'w', encoding='utf-8') as f:
        f.write(content)
    entry.update({'uri': uri, 'type': 'file', 'size': len(content.encode('utf-8')),
                  'updated': cm.now_iso(), 'version': entry['versions'] + 1,
                  'meta': meta})
    m[uri] = entry
    _save_manifest(namespace, m)
    cm.append_jsonl(os.path.join(_ns_dir(namespace), 'index.jsonl'),
                    {'ts': cm.now_iso(), 'action': 'write', 'uri': uri,
                     'version': entry['version'], 'size': entry['size']})
    return uri


def _levels(content):
    lines = content.splitlines()
    title = ''
    headings = []
    for ln in lines:
        s = ln.strip()
        if not title and s.startswith('#'):
            title = s.lstrip('#').strip()
        elif s.startswith('#'):
            headings.append(s.lstrip('#').strip())
    body_first = ''
    for ln in lines:
        s = ln.strip()
        if s and not s.startswith('#') and not s.startswith('>'):
            body_first = s
            break
    return title, headings, body_first


def read(uri, level='L1'):
    ns, rel = _to_path(uri)
    full = os.path.join(_ns_dir(ns), rel)
    if not os.path.exists(full):
        raise FileNotFoundError(uri)
    with open(full, encoding='utf-8') as f:
        content = f.read()
    m = _load_manifest(ns)
    entry = m.get(uri, {})
    meta = dict(entry.get('meta', {}))
    meta['version'] = entry.get('version', 1)
    if level == 'full':
        return {'content': content, 'level': 'full', 'meta': meta}
    title, headings, body_first = _levels(content)
    if level == 'L0':
        return {'content': (title or rel) + (' | ' + body_first[:120] if body_first else ''),
                'level': 'L0', 'meta': meta}
    # L1
    l1 = [title or rel] + ['## ' + h for h in headings] + ([body_first] if body_first else [])
    return {'content': '\n'.join(l1), 'level': 'L1', 'meta': meta}


def list(namespace, prefix=''):
    m = _load_manifest(namespace)
    out = []
    for uri, e in sorted(m.items()):
        if uri[len('viking://%s/' % namespace):].startswith(prefix):
            out.append({'uri': uri, 'type': e.get('type', 'file'),
                        'size': e.get('size', 0), 'updated': e.get('updated')})
    return out


def stat(uri):
    ns, rel = _to_path(uri)
    m = _load_manifest(ns)
    entry = m.get(uri)
    if not entry:
        raise FileNotFoundError(uri)
    return {'uri': uri, 'meta': entry.get('meta', {}), 'versions': entry.get('versions', 0),
            'version': entry.get('version', 1), 'size': entry.get('size', 0),
            'updated': entry.get('updated')}


def delete(uri, reason=''):
    """删除 = 移入 .trash/（审计可回放），manifest 标记 deleted"""
    ns, rel = _to_path(uri)
    full = os.path.join(_ns_dir(ns), rel)
    if os.path.exists(full):
        tdir = os.path.join(_ns_dir(ns), '.trash')
        os.makedirs(tdir, exist_ok=True)
        shutil.move(full, os.path.join(tdir, uuid.uuid4().hex[:8] + '-' + os.path.basename(full)))
    m = _load_manifest(ns)
    if uri in m:
        m[uri]['deleted'] = True
        m[uri]['delete_reason'] = reason
        m[uri]['updated'] = cm.now_iso()
        _save_manifest(ns, m)
    return True
