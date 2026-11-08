#!/usr/bin/env python3
"""runner.py — 单宿主进程编排器（契约 5 · Orchestrator）

- 启动三检查：目录可写 / config 可解析 / 模型密钥（缺失 → 离线模式标注）
- 节点类型：script（capabilities 模块函数）/ llm / gate / envelope
- 断点：data/runs/<run_id>/state.json（节点状态 + context 快照），resume 从未完成节点继续
- 卡点：gate 节点写 gate.json 等人工 decision（--auto-approve 供自测）
- 用法：
    python3 orchestration/runner.py run  <flow.yaml> [--inputs '{}' ] [--auto-approve]
    python3 orchestration/runner.py resume <run_id> [--auto-approve]
    python3 orchestration/runner.py status <run_id>
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'capabilities'))

import _common as cm  # noqa: E402
import _yamlmini as y  # noqa: E402
import llm.llm as llm  # noqa: E402
import trace.trace as trace  # noqa: E402

def _resolve(val, context):
    """整值引用 {node} → 原对象（list/dict 不转字符串）；其余走模板替换"""
    import re
    m = re.fullmatch(r'\{([A-Za-z_]\w*)\}', str(val))
    if m and m.group(1) in context:
        return context[m.group(1)]
    return _render(val, context)


def exec_node(node, run_id, state, auto_approve):
    ntype = node['type']
    name = node['name']
    context = state['context']
    if ntype == 'script':
        call = node['call']
        mod_name, _, func_name = call.rpartition('.')
        import importlib
        mod = importlib.import_module(mod_name)
        func = getattr(mod, func_name)
        args = {k: _resolve(v, context) for k, v in node.get('args', {}).items()}
        out = func(**args)
        ok = bool(out.get('ok', True)) if isinstance(out, dict) else True
        return ok, out
    if ntype == 'llm':
        center = node.get('center', state.get('center', 'eng'))
        messages = _render(node.get('messages', []), context)
        opt = node.get('options', {})
        out = llm.complete(center, name, messages, opt)
        return not out.get('degraded'), out
    if ntype == 'gate':
        return _gate(node, run_id, state, auto_approve)
    if ntype == 'envelope':
        import mailbox.mailbox as mb
        action = node.get('action', 'send')
        if action == 'send':
            req_id = mb.send(node['from'], node['to'], node.get('type', 'read_data'),
                             _render(node.get('payload', {}), context),
                             run_id=run_id, trace=node.get('trace', []))
            return True, {'req_id': req_id}
        if action == 'poll':
            out = mb.poll_result(_tpl(node['req_id'], context), wait_s=node.get('wait_s', 0))
            return out.get('ok') is True, out
        if action == 'claim_and_reply':
            env = mb.claim(node['center'])
            if env is None:
                return True, {'claimed': False}
            result = _render(node.get('result', {}), context)
            mb.reply(env['req_id'], result)
            return True, {'claimed': True, 'req_id': env['req_id'], 'payload': env.get('payload')}
    raise ValueError('unknown node type: ' + str(ntype))


def _gate(node, run_id, state, auto_approve):
    name = node['name']
    gpath = os.path.join(run_dir(run_id), 'gate.json')
    g = json.load(open(gpath, encoding='utf-8')) if os.path.exists(gpath) else {}
    if g.get('node') != name:
        cm.atomic_write_json(gpath, {'run_id': run_id, 'node': name,
                                     'note': _render(node.get('note', ''), state['context']),
                                     'decision': 'pending', 'updated_at': cm.now_iso()})
    g = json.load(open(gpath, encoding='utf-8'))
    if auto_approve:
        g['decision'] = 'approved'
        g['note'] = ((g.get('note') or '') + ' [auto-approve]')[:200]
        cm.atomic_write_json(gpath, g)
    import time
    while True:
        g = json.load(open(gpath, encoding='utf-8'))
        if g.get('decision') == 'approved':
            return True, {'decision': 'approved', 'note': g.get('note', '')}
        if g.get('decision') == 'rejected':
            return False, {'decision': 'rejected', 'note': g.get('note', '')}
        print('[gate] %s 等待人工 decision（编辑 data/runs/%s/gate.json）' % (name, run_id))
        time.sleep(5)


def execute(run_id, flow, auto_approve):
    """统一执行：从未完成节点继续（断点续跑）。"""
    state = load_state(run_id)
    state['status'] = 'running'
    save_state(run_id, state)
    for node in flow.get('nodes', []):
        name = node['name']
        st = state['nodes'][name]
        if st['status'] in ('done', 'skipped'):
            print('[node] %-16s skip(已 %s)' % (name, st['status']))
            continue
        trace.append(run_id, state['center'], 'node_start', {'node': name})
        st['status'] = 'running'
        save_state(run_id, state)
        attempt = 0
        while True:
            try:
                ok, out = exec_node(node, run_id, state, auto_approve)
            except Exception as e:  # noqa: BLE001
                ok, out = False, {'error': str(e)}
            if ok:
                st['status'] = 'done'
                state['context'][name] = out
                cm.write_text(os.path.join(run_dir(run_id), 'artifacts', name + '.json'),
                              json.dumps(out, ensure_ascii=False, indent=2, default=str))
                print('[node] %-16s done' % name)
                break
            attempt += 1
            if attempt <= node.get('retry', 0):
                st['retries'] = attempt
                save_state(run_id, state)
                print('[node] %-16s retry %d' % (name, attempt))
                continue
            on_fail = node.get('on_fail', 'abort')
            st['status'] = {'skip': 'skipped', 'gate': 'gate'}.get(on_fail, 'failed')
            state['context'][name] = out
            print('[node] %-16s %s err=%s' % (name, st['status'], str(out)[:140]))
            break
        save_state(run_id, state)
        trace.append(run_id, state['center'], 'node_end', {'node': name, 'status': st['status']})
        if st['status'] in ('failed', 'gate'):
            state['status'] = st['status']
            break
    if state['status'] == 'running':
        state['status'] = 'done'
    save_state(run_id, state)
    print('[run] %s => %s' % (run_id, state['status']))
    return state


def run_flow(flow_path, inputs=None, auto_approve=False):
    check_startup()
    run_id, flow = new_run(flow_path, inputs or {})
    print('[run] %s · flow=%s · center=%s' % (run_id, flow.get('name'), flow.get('center')))
    execute(run_id, flow, auto_approve)
    return run_id


def resume_run(run_id, auto_approve=False):
    state = load_state(run_id)
    flow_path = os.path.join(ROOT, state['flow'])
    flow = y.load(flow_path)
    print('[resume] %s' % run_id)
    execute(run_id, flow, auto_approve)
    return run_id


def check_startup():
    print('[check 1/3] 目录可写     :', end=' ')
    for d in (cm.DATA, os.path.join(cm.ROOT, 'db'), os.path.join(cm.ROOT, 'config')):
        assert os.access(d, os.W_OK), 'not writable: ' + d
    print('OK')
    print('[check 2/3] config 可解析:', end=' ')
    models = y.load(os.path.join(cm.CONFIG, 'models.yaml'))
    y.load(os.path.join(cm.CONFIG, 'centers.yaml'))
    y.load(os.path.join(cm.CONFIG, 'runtime.yaml'))
    json.load(open(os.path.join(cm.CONFIG, 'tools.registry.json'), encoding='utf-8'))
    print('OK')
    print('[check 3/3] 模型密钥     :', end=' ')
    mode = llm.mode()
    print('mode=%s' % mode)
    return mode


def runs_dir():
    return os.path.join(cm.DATA, 'runs')


def run_dir(run_id):
    d = os.path.join(runs_dir(), run_id)
    os.makedirs(os.path.join(d, 'artifacts'), exist_ok=True)
    return d


def _state_path(run_id):
    return os.path.join(run_dir(run_id), 'state.json')


def load_state(run_id):
    return json.load(open(_state_path(run_id), encoding='utf-8'))


def save_state(run_id, state):
    state['lock'] = {'holder': os.getpid(), 'heartbeat_ts': cm.now_iso()}
    cm.atomic_write_json(_state_path(run_id), state)


def new_run(flow_path, inputs):
    run_id = cm.run_id()
    flow = y.load(flow_path)
    state = {'run_id': run_id, 'flow': os.path.relpath(flow_path, ROOT),
             'flow_name': flow.get('name', ''), 'center': flow.get('center', ''),
             'status': 'running', 'inputs': inputs, 'context': dict(inputs),
             'nodes': {n['name']: {'status': 'pending', 'retries': 0}
                       for n in flow.get('nodes', [])},
             'created_at': cm.now_iso()}
    save_state(run_id, state)
    return run_id, flow


def _tpl(s, context):
    s = str(s)
    for k, v in context.items():
        s = s.replace('{%s}' % k, str(v))
    # 二级引用：{node.field}
    import re

    def _sub(m):
        node, field = m.group(1).split('.', 1)
        if node in context and isinstance(context[node], dict):
            val = context[node].get(field, m.group(0))
            return str(val)
        return m.group(0)

    return re.sub(r'\{([A-Za-z_]\w*\.\w+)\}', _sub, s)


def _render(obj, context):
    if isinstance(obj, str):
        return _tpl(obj, context)
    if isinstance(obj, dict):
        return {k: _render(v, context) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_render(v, context) for v in obj]
    return obj


def status_run(run_id):
    state = load_state(run_id)
    print('run_id :', state['run_id'])
    print('flow   :', state['flow_name'], '| center:', state['center'], '| status:', state['status'])
    for n, st in state['nodes'].items():
        print('  node %-18s %s' % (n, st['status']))
    return state


if __name__ == '__main__':
    args = sys.argv[1:]
    auto = '--auto-approve' in args
    args = [a for a in args if a != '--auto-approve']
    cmd = args[0] if args else 'help'
    if cmd == 'run' and len(args) >= 2:
        flow_path = args[1] if os.path.isabs(args[1]) else os.path.join(ROOT, args[1])
        inputs = {}
        if '--inputs' in args:
            inputs = json.loads(args[args.index('--inputs') + 1])
        run_flow(flow_path, inputs, auto)
    elif cmd == 'resume' and len(args) >= 2:
        resume_run(args[1], auto)
    elif cmd == 'status' and len(args) >= 2:
        status_run(args[1])
    else:
        print(__doc__)
