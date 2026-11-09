#!/usr/bin/env python3
"""control_selftest.py — 总控制台(:8765)全模块 API 测试套件

覆盖：服务状态 / 页面静态 / 五视图数据源 / 授权动作 / 配置写回 / GitHub 导入 / 文档 / 边界与防御。
结果落 output/ui-verify/control-api-test.md（测试 case + 结果表）。
用法：python3 scripts/control_selftest.py [--base http://127.0.0.1:8765]
"""
import json
import os
import sys
import urllib.request
import urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'capabilities'))

BASE = 'http://127.0.0.1:8765'
if '--base' in sys.argv:
    BASE = sys.argv[sys.argv.index('--base') + 1]

RESULTS = []


def call(method, path, body=None, timeout=30):
    data = json.dumps(body or {}).encode() if method == 'POST' else None
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={'Content-Type': 'application/json'} if data else {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode('utf-8'))
        except Exception:  # noqa: BLE001
            return e.code, {}
    except Exception as e:  # noqa: BLE001
        return 0, {'error': str(e)[:200]}


def case(name, group, fn):
    try:
        detail = fn()
        RESULTS.append((group, name, 'PASS', detail))
        print('PASS %-14s %s %s' % (group, name, detail or ''))
    except AssertionError as e:
        RESULTS.append((group, name, 'FAIL', str(e)))
        print('FAIL %-14s %s -> %s' % (group, name, e))
    except Exception as e:  # noqa: BLE001
        RESULTS.append((group, name, 'ERROR', '%s: %s' % (type(e).__name__, str(e)[:150])))
        print('ERROR %-13s %s -> %s' % (group, name, e))


def eq(a, b, msg=''):
    assert a == b, '%s 期望 %r 实得 %r' % (msg, b, a)


G1 = '基础可达'
G2 = '授权动作'
G3 = 'MCP toggle'
G4 = '服务生命周期'
G5 = '配置写回'
G6 = 'GitHub 导入'
G7 = '产品文档'
G8 = '边界与防御'


def t_ping():
    code, r = call('GET', '/api/ping')
    eq(code, 200); eq(r['ok'], True); eq(r['service'], 'ai-three-center-control')

def t_state():
    code, r = call('GET', '/api/state')
    eq(code, 200); eq(r['ok'], True)
    s = r['state']
    assert s['registry_version'] >= 1
    assert s['plugins'] and s['mcp']
    assert s['config'] and s['config']['models']['routing']['eng']['primary']

def t_state_services():
    _, r = call('GET', '/api/state')
    s = r['state']
    p = s['plugins'][0]
    assert 'service' in p and p['service']['status'] in ('running', 'stopped', 'failed')
    assert 'cline_mcp' in p

def t_page():
    req = urllib.request.Request(BASE + '/')
    with urllib.request.urlopen(req, timeout=10) as resp:
        body = resp.read().decode('utf-8')
    assert resp.status == 200 and '三中心门户' in body and 'INVENTORY' in body

def t_config_get():
    code, r = call('GET', '/api/config')
    eq(code, 200)
    c = r['config']
    assert set(c['paths']) == {'models', 'runtime', 'policy', 'centers'}
    assert c['models']['provider']['base_url'].startswith('https://ark.cn-beijing')


def t_grant_revoke_known():
    _, r1 = call('POST', '/api/action', {'action': 'revoke', 'slug': 'tabclaw', 'center': 'eng'})
    assert r1['ok'] and '移除' in r1['message'], r1['message']
    _, r2 = call('POST', '/api/action', {'action': 'grant', 'slug': 'tabclaw', 'center': 'eng'})
    assert r2['ok'] and '授权' in r2['message']
    grants = r2['state']['config']['policy']['grants']
    assert 'tabclaw' in grants['eng']

def t_grant_mcp_defense():
    # 图中 bug 回归：MCP 条目（mem0）走 grant 必须被拒绝且不污染 policy
    code, r = call('POST', '/api/action', {'action': 'grant', 'slug': 'mem0', 'center': 'eng'})
    assert r['ok'] is False and 'MCP 服务（非插件）' in r.get('error', ''), r
    pol = open(os.path.join(ROOT, 'plugins', 'policy.yaml'), encoding='utf-8').read()
    assert 'undefined' not in pol and '- mem0' not in pol, 'policy 被污染'

def t_grant_bad_center():
    code, r = call('POST', '/api/action', {'action': 'grant', 'slug': 'tabclaw', 'center': 'nope'})
    assert r['ok'] is False, r

def t_grant_unknown_slug():
    code, r = call('POST', '/api/action', {'action': 'grant', 'slug': 'no-such-plugin', 'center': 'eng'})
    assert r['ok'] is False, r


def t_mcp_toggle_on_off():
    _, r1 = call('POST', '/api/action', {'action': 'mcp_toggle', 'slug': 'mem0', 'disabled': False})
    assert r1['ok'] and r1['disabled'] is False
    _, r2 = call('POST', '/api/action', {'action': 'mcp_toggle', 'slug': 'mem0', 'disabled': True})
    assert r2['ok'] and r2['disabled'] is True
    copy = json.load(open(os.path.join(ROOT, 'agents/init/cline_mcp_settings.json'), encoding='utf-8'))
    assert copy['mcpServers']['mem0']['disabled'] is True

def t_mcp_toggle_unknown():
    code, r = call('POST', '/api/action', {'action': 'mcp_toggle', 'slug': 'nope', 'disabled': True})
    assert r['ok'] is False and 'Cline 配置中无' in r.get('error', ''), r


def t_service_status():
    code, r = call('POST', '/api/action', {'action': 'status', 'slug': 'tabclaw'})
    eq(code, 200)
    assert r['status'] in ('running', 'stopped', 'failed') and 'health' in r

def t_service_start_stop():
    _, r1 = call('POST', '/api/action', {'action': 'stop', 'slug': 'tabclaw'})
    assert r1['ok'] and r1['status'] == 'stopped', r1
    _, r2 = call('POST', '/api/action', {'action': 'start', 'slug': 'tabclaw'})
    assert r2['ok'] and r2['status'] == 'running', r2
    assert r2['health'] and r2['health'].get('ok') is True

def t_service_unknown():
    code, r = call('POST', '/api/action', {'action': 'start', 'slug': 'no-such'})
    assert r['ok'] is False, r


def t_config_models():
    _, r1 = call('POST', '/api/config', {'file': 'models', 'keys': ['routing', 'data', 'primary'], 'value': 'ep-PAGE-TEST-1'})
    assert r1['ok'], r1
    assert r1['config']['models']['routing']['data']['primary'] == 'ep-PAGE-TEST-1'
    _, r2 = call('POST', '/api/config', {'file': 'models', 'keys': ['routing', 'data', 'primary'], 'value': 'sentinel-as-deepseek-01'})
    assert r2['ok'] and r2['config']['models']['routing']['data']['primary'] == 'sentinel-as-deepseek-01'

def t_config_runtime():
    _, r1 = call('POST', '/api/config', {'file': 'runtime', 'keys': ['node', 'max_retries'], 'value': 3})
    assert r1['ok'] and r1['config']['runtime']['node']['max_retries'] == 3
    _, r2 = call('POST', '/api/config', {'file': 'runtime', 'keys': ['node', 'max_retries'], 'value': 2})
    assert r2['ok'] and r2['config']['runtime']['node']['max_retries'] == 2

def t_config_policy_approval():
    _, r1 = call('POST', '/api/config', {'file': 'policy', 'keys': ['approval', 'plugin_enable'], 'value': 'auto'})
    assert r1['ok'] and r1['config']['policy']['approval']['plugin_enable'] == 'auto'
    _, r2 = call('POST', '/api/config', {'file': 'policy', 'keys': ['approval', 'plugin_enable'], 'value': 'manual'})
    assert r2['ok'] and r2['config']['policy']['approval']['plugin_enable'] == 'manual'

def t_config_bad_file():
    code, r = call('POST', '/api/config', {'file': 'nope', 'keys': ['a'], 'value': 1})
    assert r['ok'] is False, r


def t_github_import_existing():
    _, r = call('POST', '/api/github', {'action': 'import', 'url': 'https://github.com/fishsure/TabClaw'}, timeout=180)
    assert r['ok'] is True and r['repo'] == 'TabClaw', r.get('error', '')
    assert r['parse']['deploy_mode'] == 'native-python'
    assert r['parse']['saved'].startswith('data/assets/engineering/')

def t_github_bad_url():
    code, r = call('POST', '/api/github', {'action': 'import', 'url': 'ftp://x'})
    assert r['ok'] is False and '非法' in r.get('error', ''), r

def t_github_status():
    _, r = call('POST', '/api/github', {'repo': 'TabClaw', 'op': 'status'})
    assert 'output' in r or r.get('ok') is False


def t_docs_list():
    code, r = call('GET', '/api/docs')
    eq(code, 200); assert r['ok'] and isinstance(r['items'], list)

def t_docs_write_roundtrip():
    _, r1 = call('POST', '/api/docs', {'action': 'write', 'topic': '自测文档（API 测试）',
                                       'content': '# 自测\n\nAPI 测试内容。', 'kind': 'manuals'})
    assert r1['ok'] and 'manuals' in r1['uri'], r1
    _, r2 = call('GET', '/api/docs')
    norm = lambda s: str(s).replace(' ', '')   # docs_write 归一化去空格，断言同规则比较
    assert any(norm('自测文档（API 测试）') in norm(i['uri']) for i in r2['items']), r2['items']

def t_docs_outline_degraded_ok():
    _, r = call('POST', '/api/docs', {'action': 'outline', 'topic': '自测'}, timeout=90)
    assert 'degraded' in r and 'text' in r


def t_unknown_path():
    code, r = call('GET', '/api/no-such')
    eq(code, 404)

def t_dir_traversal():
    code, _ = call('GET', '/api/static/../config/models.yaml')
    assert code in (404, 500), '目录穿越被放行: %s' % code

def t_state_no_secret_leak():
    _, r = call('GET', '/api/state')
    raw = json.dumps(r, ensure_ascii=False)
    assert 'ark-' not in raw and 'Tab!Cl' not in raw and 'm0sk_' not in raw, '响应含明文凭据'


if __name__ == '__main__':
    case('ping 健康检查', G1, t_ping)
    case('/api/state 全量状态', G1, t_state)
    case('state 含服务/配置视图', G1, t_state_services)
    case('页面静态托管', G1, t_page)
    case('/api/config 读取', G1, t_config_get)
    case('revoke→grant 还原（tabclaw@eng）', G2, t_grant_revoke_known)
    case('MCP 类 grant 防御（图中bug回归）', G2, t_grant_mcp_defense)
    case('非法 center 拒绝', G2, t_grant_bad_center)
    case('未知 slug 拒绝', G2, t_grant_unknown_slug)
    case('mem0 disabled 开/关', G3, t_mcp_toggle_on_off)
    case('未知 MCP 拒绝', G3, t_mcp_toggle_unknown)
    case('status 查询', G4, t_service_status)
    case('stop→start（健康探测）', G4, t_service_start_stop)
    case('未知插件启动拒绝', G4, t_service_unknown)
    case('models.yaml routing 写回+还原', G5, t_config_models)
    case('runtime.yaml 写回+还原', G5, t_config_runtime)
    case('policy.yaml approval 写回+还原', G5, t_config_policy_approval)
    case('非法配置文件拒绝', G5, t_config_bad_file)
    case('已有仓库 import+解析', G6, t_github_import_existing)
    case('非法 URL 拒绝', G6, t_github_bad_url)
    case('one-key status 通道', G6, t_github_status)
    case('文档列表', G7, t_docs_list)
    case('write 归档+列表可见', G7, t_docs_write_roundtrip)
    case('outline 生成（降级可接受）', G7, t_docs_outline_degraded_ok)
    case('未知路径 404', G8, t_unknown_path)
    case('目录穿越拦截', G8, t_dir_traversal)
    case('响应无明文凭据', G8, t_state_no_secret_leak)

    total = len(RESULTS)
    passed = sum(1 for x in RESULTS if x[2] == 'PASS')
    print('---')
    print('总计 %d · PASS %d · FAIL %d' % (total, passed, total - passed))
    import _common as cm
    lines = ['# 控制台 API 测试报告（%s）' % cm.now_iso(), '',
             '- 目标：%s（三中心门户控制台，launchd 常驻）' % BASE,
             '- 套件：scripts/control_selftest.py（case 表驱动，可重复执行）', '',
             '| 组 | 测试 case | 结果 | 说明 |', '|---|---|---|---|']
    for g, n, s, d in RESULTS:
        lines.append('| %s | %s | %s | %s |' % (g, n, s, str(d or '')[:80].replace('|', '\\|')))
    lines += ['', '**结果：总计 %d · PASS %d · FAIL %d**' % (total, passed, total - passed), '',
              '## 本轮发现并修复的 bug', '',
              '| # | bug | 修复 |', '|---|---|---|',
              '| 1 | MCP 卡开关把 undefined 写入 policy.yaml（图中「已授权 undefined」错误） | MCP 条目补 slug；控制台 grant/revoke 拒绝 MCP 类；清理 policy 垃圾行 |',
              '| 2 | MCP 类条目无真实启停动作 | 新增 mcp_toggle（写 disabled，备份+审计+init 双写）；MCP 卡改「Cline 启用/停用」单开关 |',
              '| 3 | 联邦遗产三件套在 Cline 配置仍 enabled（与页面徽章不一致） | 落实 disabled=true，消除 Cline 重启连接报错噪音 |', '']
    cm.write_text(os.path.join(cm.ROOT, 'output', 'ui-verify', 'control-api-test.md'), '\n'.join(lines))
    print('报告 → output/ui-verify/control-api-test.md')
    sys.exit(0 if passed == total else 1)
