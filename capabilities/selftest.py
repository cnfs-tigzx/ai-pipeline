"""selftest.py — capabilities 全模块最小自测（零依赖）

用法：python3 capabilities/selftest.py [--skip-llm]
--skip-llm 跳过真实方舟调用（无密钥/离线环境用）
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import _yamlmini as y  # noqa: E402

ROOT = os.path.dirname(HERE)
PASS = []
FAIL = []


def check(name, fn):
    try:
        fn()
        PASS.append(name)
        print('PASS', name)
    except Exception as e:  # noqa: BLE001
        FAIL.append((name, str(e)))
        print('FAIL', name, '->', e)


# ---------- 1. yamlmini ----------
def t_yaml():
    m = y.load(os.path.join(ROOT, 'config/models.yaml'))
    assert m['routing']['eng']['primary'] == 'ep-20261105181307-4s825'
    assert m['provider']['base_url'] == 'https://ark.cn-beijing.volces.com/api/v3'
    assert m['provider']['timeout_s'] == 60 and m['offline_mode']['enabled'] is True
    c = y.load(os.path.join(ROOT, 'config/centers.yaml'))
    assert c['centers']['eng']['name'] == '开发中心'
    assert 'W6-plugin-release' in c['centers']['eng']['workflows']
    cfg = y.load(os.path.join(ROOT, 'config/runtime.yaml'))
    assert cfg['runner']['poll_interval_s'] == 5 and cfg['mailbox']['retention_days'] == 7
    p = y.load(os.path.join(ROOT, 'plugins/policy.yaml'))
    assert p['grants']['eng'] == ['tabclaw'] and p['grants']['solution'] == []
    sample = '''
# 注释行
nodes:
  - name: fetch
    retry: 2
    on_fail: gate
  - name: build
    active: true
plain_list:
  - a
  - b-2
nested:
  level1:
    level2: deep
empty_key:
quoted: 'has # hash'
url: https://example.com/a#frag
'''
    s = y.loads(sample)
    assert s['nodes'][0]['name'] == 'fetch' and s['nodes'][0]['retry'] == 2
    assert s['nodes'][0]['on_fail'] == 'gate' and s['nodes'][1]['active'] is True
    assert s['plain_list'] == ['a', 'b-2']
    assert s['nested']['level1']['level2'] == 'deep'
    assert s['empty_key'] is None
    assert s['quoted'] == 'has # hash'
    assert s['url'] == 'https://example.com/a#frag'


# ---------- 2. common ----------
def t_common():
    import _common as cm
    rid = cm.run_id()
    assert rid.startswith('run-') and len(rid) > 20
    p = os.path.join(cm.DATA, 'tmp', 'selftest-common.json')
    cm.atomic_write_json(p, {'a': 1})
    assert json.load(open(p))['a'] == 1
    cm.append_jsonl(p + '.jsonl', {'x': 1})
    cm.append_jsonl(p + '.jsonl', {'x': 2})
    assert len(cm.read_jsonl(p + '.jsonl')) == 2
    os.remove(p)
    os.remove(p + '.jsonl')


# ---------- 3. memory ----------
def t_memory():
    import memory.memory as mem
    import _common as cm
    mid = mem.add('eng', '自测记忆：docker compose 端口冲突需先查占用', ['安装测试'], {'src': 'selftest'})
    hits = mem.search('eng', '端口冲突', limit=3)
    assert hits and hits[0]['score'] > 0
    mem.update(mid, {'content': '自测记忆（已更新）：端口冲突先查 lsof'})
    mem.forget(mid, 'selftest cleanup')
    mem.search('data', '端口冲突', limit=1, cross_domain=True, requester='selftest')
    assert os.path.exists(os.path.join(cm.DATA, 'memory', 'eng', 'index.json'))


# ---------- 4. assets ----------
def t_assets():
    import assets.assets as ast
    uri = ast.write('solution', 'selftest/doc.md', '# 测试文档\n\n正文第一段。',
                    {'title': '自测文档', 'author': 'selftest'})
    r0 = ast.read(uri, 'L0')
    assert r0['level'] == 'L0'
    r1 = ast.read(uri, 'L1')
    assert '正文第一段' in r1['content']
    rf = ast.read(uri, 'full')
    assert '# 测试文档' in rf['content']
    ast.write('solution', 'selftest/doc.md', '# 测试文档 V2\n\n新内容。', {'title': '自测文档'})
    rf2 = ast.read(uri, 'full')
    assert 'V2' in rf2['content'] and rf2['meta'].get('version', 1) >= 2
    old = ast.stat(uri)
    assert old['versions'] >= 1
    lst = ast.list('solution', 'selftest/')
    assert any(i['uri'] == uri for i in lst)
    ast.delete(uri, reason='selftest cleanup')


# ---------- 5. trace ----------
def t_trace():
    import shutil
    import trace.trace as tr
    rid = 'run-selftest-trace'
    p = os.path.join(ROOT, 'data', 'trace', 'eng', rid + '.jsonl')
    if os.path.exists(p):
        os.remove(p)  # 幂等：先清理旧轨迹
    tr.append(rid, 'eng', 'node_start', {'node': 'n1'})
    tr.append(rid, 'eng', 'node_end', {'node': 'n1', 'ok': True})
    evs = tr.read(rid, 'eng')
    assert len(evs) == 2 and evs[0]['event'] == 'node_start'
    shutil.rmtree(os.path.join(ROOT, 'data', 'trace', 'eng'), ignore_errors=False)
    os.makedirs(os.path.join(ROOT, 'data', 'trace', 'eng'), exist_ok=True)


# ---------- 6. tools ----------
def t_tools():
    import tools.tools as tools
    reg = tools.list('eng')
    assert reg['version'] >= 0
    all_tools = tools.list('solution')
    assert all(t['name'] for t in all_tools['tools'])


# ---------- 7. scrape ----------
def t_scrape():
    import scrape.scrape as sc
    r = sc.fetch_local_html()  # 内置本地样例，不依赖外网
    assert r['ok'] is True and '<html' in r['text'].lower()


# ---------- 8. vcs ----------
def t_vcs():
    import vcs.vcs as vcs
    r = vcs.git(['status', '--porcelain'], cwd=ROOT)
    assert r['ok'] is True and r['code'] == 0


# ---------- 9. runtime ----------
def t_runtime():
    import runtime.runtime as rt
    r = rt.run([sys.executable, '-c', 'print(1+1)'], timeout_s=10)
    assert r['ok'] and r['stdout'].strip() == '2'
    caps = rt.detect()
    assert 'git' in caps


# ---------- 9b. db ----------
def t_db():
    import db.db as db
    r = db.table_from_rows('t_selftest_demo',
                           [['名称', '数量'], ['苹果', '3'], ['香蕉', '5']],
                           src_url='local://selftest', note='selftest')
    assert r['ok'] and r['rows'] == 2 and '_src_url' in r['columns']
    q = db.query('SELECT COUNT(*) AS n FROM t_selftest_demo WHERE _src_url=?', ['local://selftest'])
    assert q['ok'] and q['rows'][0]['n'] == 2
    db.query('DROP TABLE t_selftest_demo')


# ---------- 10. llm ----------
def t_llm():
    import llm.llm as llm
    mode = llm.mode()
    assert mode in ('normal', 'offline')
    # GLM-5.3-Flash 为推理模型：max_tokens 需覆盖推理消耗，太小会返回空正文
    r = llm.complete('eng', 'selftest', [{'role': 'user', 'content': '回复OK两个字母即可'}], {'max_tokens': 100})
    assert 'degraded' in r and 'model' in r
    if mode == 'normal':
        assert not r['degraded'], r.get('error', '')
        assert 'OK' in r['text'].upper(), 'text=%r' % r['text']
    else:
        assert r['degraded'] is True


# ---------- 11. mailbox ----------
def t_mailbox():
    if not os.path.exists(os.path.join(HERE, 'mailbox', 'mailbox.py')):
        return
    import glob
    import _common as cm
    import mailbox.mailbox as mb
    # 幂等：清理历史遗留（lock 与同名 req/res/err）
    for f in glob.glob(os.path.join(cm.DATA, 'mailbox', '*', 'run-selftest-mb*')):
        os.remove(f)
    rid = mb.send('solution', 'data', 'read_data', {'need': '自测数据'}, run_id='run-selftest-mb')
    env = mb.claim('data')
    assert env is not None and env['req_id'] == rid, 'claim mismatch: %s vs %s' % (env and env['req_id'], rid)
    mb.reply(rid, {'dataset_uri': 'viking://datacenter/datasets/selftest'})
    got = mb.poll_result(rid)
    assert got['ok'] and got['result']['dataset_uri'].endswith('selftest')


if __name__ == '__main__':
    skip_llm = '--skip-llm' in sys.argv
    check('yamlmini', t_yaml)
    check('common', t_common)
    check('memory', t_memory)
    check('assets', t_assets)
    check('trace', t_trace)
    check('tools', t_tools)
    check('scrape', t_scrape)
    check('vcs', t_vcs)
    check('runtime', t_runtime)
    check('db', t_db)
    if not skip_llm:
        check('llm', t_llm)
    check('mailbox', t_mailbox)
    print('---')
    print(f'PASS {len(PASS)} / FAIL {len(FAIL)}')
    if FAIL:
        sys.exit(1)
