"""memory.py — 契约 2 · 分区记忆（替代 Mem0，jsonl 分片 + 朴素检索）"""
import json
import os
import sys
import uuid

_HERE = os.path.dirname(os.path.abspath(__file__))
_CAP = os.path.dirname(_HERE)
if _CAP not in sys.path:
    sys.path.insert(0, _CAP)

import _common as cm  # noqa: E402

DUP_THRESHOLD = 0.9      # 同 tag 摘要重合度阈值：超过则合并而非新增
DIGEST_LEN = 50


def _dir(center):
    d = os.path.join(cm.DATA, 'memory', center)
    os.makedirs(os.path.join(d, 'shards'), exist_ok=True)
    return d


def _shard_path(center):
    return os.path.join(_dir(center), 'shards', cm.month_tag() + '.jsonl')


def _index_path(center):
    return os.path.join(_dir(center), 'index.json')


def _load_index(center):
    p = _index_path(center)
    if not os.path.exists(p):
        return []
    return json.load(open(p, encoding='utf-8'))


def _save_index(center, idx):
    cm.atomic_write_json(_index_path(center), idx)


def _find_shard(center, mid):
    """按 id 在各分片定位记录，返回 (path, record) 或 (None, None)"""
    shards_dir = os.path.join(_dir(center), 'shards')
    for fn in sorted(os.listdir(shards_dir)):
        p = os.path.join(shards_dir, fn)
        for rec in cm.read_jsonl(p):
            if rec['id'] == mid:
                return p, rec
    return None, None


def _similarity(a, b):
    a, b = a[:DIGEST_LEN], b[:DIGEST_LEN]
    if not a or not b:
        return 0.0
    hit = sum(1 for x, y in zip(a, b) if x == y)
    return hit / max(len(a), len(b))


def _audit(event, detail):
    cm.append_jsonl(os.path.join(cm.DATA, 'assets', 'plugins', 'audit', cm.today_tag() + '.jsonl'),
                    {'ts': cm.now_iso(), 'event': event, **detail})


def add(center, content, tags, meta=None):
    """写入记忆；同 tag 且摘要重合度超阈值 → 合并（更新计数与时间）"""
    assert center in ('eng', 'data', 'solution'), 'bad center'
    assert tags and isinstance(tags, list) and tags[0], 'tags 必填至少一个业务标签'
    meta = meta or {}
    idx = _load_index(center)
    # 去重合并
    for it in idx:
        if set(it['tags']) & set(tags) and _similarity(it.get('digest', ''), content) > DUP_THRESHOLD:
            p, rec = _find_shard(center, it['id'])
            if p and rec:
                rec['content'] = content
                rec['merge_count'] = rec.get('merge_count', 1) + 1
                rec['updated_at'] = cm.now_iso()
                _rewrite_shard(p, rec)
                it['digest'] = content[:DIGEST_LEN]
                _save_index(center, idx)
                return it['id']
    mid = 'mem-' + uuid.uuid4().hex[:12]
    rec = {'id': mid, 'content': content, 'tags': tags, 'meta': meta,
           'created_at': cm.now_iso(), 'merge_count': 1}
    cm.append_jsonl(_shard_path(center), rec)
    idx.append({'id': mid, 'tags': tags, 'digest': content[:DIGEST_LEN],
                'month': cm.month_tag()})
    _save_index(center, idx)
    return mid


def _rewrite_shard(path, new_rec):
    recs = [new_rec if r['id'] == new_rec['id'] else r for r in cm.read_jsonl(path)]
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    os.replace(tmp, path)


def search(center, query, tags=None, limit=5, cross_domain=False, requester=None):
    """tag 交集*2 + 摘要/正文关键词重合度评分；cross_domain 必须记审计"""
    if cross_domain:
        assert requester, 'cross_domain 必须带 requester（谁、为什么跨区读）'
        _audit('memory_cross_domain', {'requester': requester,
                                       'from': requester, 'partition': center,
                                       'query': query, 'reason': 'cross_center_request'})
    idx = _load_index(center)
    q_words = set(query)
    hits = []
    for it in idx:
        if tags and not (set(it['tags']) & set(tags)):
            continue
        p, rec = _find_shard(center, it['id'])
        if not rec:
            continue
        score = 2.0 * len(set(it['tags']) & set(tags or []))
        text = rec['content']
        hit = sum(1 for w in q_words if w and w in text)
        score += hit / max(len(q_words), 1)
        if score <= 0:
            continue
        hits.append({'id': rec['id'], 'content': rec['content'],
                     'score': round(score, 3), 'tags': rec['tags']})
    hits.sort(key=lambda x: -x['score'])
    return hits[:limit]


def update(mid, patch):
    """按 id 定位（跨分片查 eng+data+solution），patch 合并进记录"""
    for center in ('eng', 'data', 'solution'):
        p, rec = _find_shard(center, mid)
        if rec:
            rec.update(patch)
            _rewrite_shard(p, rec)
            idx = _load_index(center)
            for it in idx:
                if it['id'] == mid:
                    if 'content' in patch:
                        it['digest'] = patch['content'][:DIGEST_LEN]
                    if 'tags' in patch:
                        it['tags'] = patch['tags']
            _save_index(center, idx)
            return True
    return False


def forget(mid, reason):
    """软删除：标记 deleted，不物理抹除（审计需要）"""
    ok = update(mid, {'deleted': True, 'delete_reason': reason, 'deleted_at': cm.now_iso()})
    if ok:
        _audit('memory_forget', {'id': mid, 'reason': reason})
    return ok
