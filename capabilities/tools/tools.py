"""tools.py — 契约 4 · 工具注册表与分发（替代 MCP Gateway）

- 工具名 {slug}__{tool}；未在 plugins/policy.yaml 授权的插件对中心不可见
- 分发：按 manifest entry（command + args 模板）子进程直调，不走 MCP 传输层
- 审计：data/assets/plugins/audit/YYYY-MM-DD.jsonl（参数只记哈希）
"""
import json
import os
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_CAP = os.path.dirname(_HERE)
if _CAP not in sys.path:
    sys.path.insert(0, _CAP)

import _common as cm  # noqa: E402
import _yamlmini as y  # noqa: E402

REGISTRY = os.path.join(cm.CONFIG, 'tools.registry.json')
POLICY = os.path.join(cm.ROOT, 'plugins', 'policy.yaml')
MANIFESTS = os.path.join(cm.ROOT, 'plugins', 'manifests')


def _load_registry():
    if not os.path.exists(REGISTRY):
        return {'version': 0, 'tools': []}
    return json.load(open(REGISTRY, encoding='utf-8'))


def _policy():
    return y.load(POLICY)


def _granted(center):
    return _policy().get('grants', {}).get(center, []) or []


def list(center):
    reg = _load_registry()
    grants = _granted(center)
    tools = [t for t in reg.get('tools', []) if t.get('slug') in grants]
    return {'version': reg.get('version', 0), 'tools': tools}


def invoke(center, name, args=None, run_id=None):
    """子进程直调插件入口；全量审计；policy 未授权 → 拒绝"""
    args = args or {}
    slug, _, tool = name.partition('__')
    grants = _granted(center)
    if slug not in grants:
        return {'ok': False, 'data': None, 'error': 'plugin not granted: %s for %s' % (slug, center),
                'audit_id': _audit(center, slug, tool, args, 0, 'denied')}
    mpath = os.path.join(MANIFESTS, slug, 'ov-plugin.yaml')
    if not os.path.exists(mpath):
        return {'ok': False, 'data': None, 'error': 'manifest missing: ' + slug,
                'audit_id': _audit(center, slug, tool, args, 0, 'no_manifest')}
    m = y.load(mpath)
    tools_map = m.get('tools', {}) or {}
    if tool not in tools_map:
        return {'ok': False, 'data': None, 'error': 'tool not declared: %s@%s' % (tool, slug),
                'audit_id': _audit(center, slug, tool, args, 0, 'no_tool')}
    spec = tools_map[tool]
    # 高风险 gate 裁决（policy.approval.high_risk_tools=gate）
    pol = _policy()
    risk = spec.get('risk', 'low')
    if risk in (pol.get('defaults', {}).get('high_risk_classes') or []) or \
       (spec.get('class') in (pol.get('defaults', {}).get('high_risk_classes') or [])):
        if pol.get('approval', {}).get('high_risk_tools') == 'gate':
            return {'ok': False, 'data': None, 'error': 'high-risk tool requires gate approval',
                    'audit_id': _audit(center, slug, tool, args, 0, 'gate_required')}
    # entry: {command, args} 其中 args 模板支持 {arg}/{run_id} 占位
    entry = spec.get('entry', {})
    cmd = [str(entry.get('command', ''))]
    for a in entry.get('args', []):
        s = str(a)
        for k, v in (args or {}).items():
            s = s.replace('{%s}' % k, str(v))
        s = s.replace('{run_id}', str(run_id or 'no-run'))
        if '{' in s and '}' in s and s not in (args or {}).values():
            pass  # 未提供占位变量时保留原样交由插件报错
        cmd.append(s)
    import time
    t0 = time.time()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=spec.get('timeout_s', 60))
        ok = r.returncode == 0
        out = r.stdout.strip()
        try:
            data = json.loads(out) if out else None
        except json.JSONDecodeError:
            data = out
        err = r.stderr.strip()[-500:] if not ok else ''
        status = 'ok' if ok else 'error'
    except subprocess.TimeoutExpired:
        ok, data, err, status = False, None, 'timeout', 'timeout'
    dur = round((time.time() - t0) * 1000)
    return {'ok': ok, 'data': data, 'error': err,
            'audit_id': _audit(center, slug, tool, args, dur, status)}


def _audit(center, slug, tool, args, dur_ms, status):
    aid = 'aud-' + cm.rand_id(8)
    cm.append_jsonl(os.path.join(cm.DATA, 'assets', 'plugins', 'audit', cm.today_tag() + '.jsonl'),
                    {'ts': cm.now_iso(), 'audit_id': aid, 'center': center, 'slug': slug,
                     'tool': tool, 'args_hash': cm.sha256_text(json.dumps(args, sort_keys=True, ensure_ascii=False)),
                     'run_id': (args or {}).get('run_id', ''), 'duration_ms': dur_ms,
                     'status': status})
    return aid


def bump_version():
    reg = _load_registry()
    reg['version'] = reg.get('version', 0) + 1
    reg['generated_at'] = cm.now_iso()
    cm.atomic_write_json(REGISTRY, reg)
    return reg['version']


def regen_registry():
    """重建 registry + 三中心门户页（flow 节点用）"""
    ok_all = True
    outs = []
    for script in ('gen-registry.py', 'indexpage.py'):
        args = [sys.executable, os.path.join(cm.ROOT, 'scripts', script)]
        if script == 'indexpage.py':
            args.append('build')
        r = subprocess.run(args, capture_output=True, text=True, timeout=60)
        ok_all = ok_all and r.returncode == 0
        outs.append(r.stdout.strip() or r.stderr.strip()[-300:])
    return {'ok': ok_all, 'stdout': '\n'.join(outs)}
