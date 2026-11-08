#!/usr/bin/env python3
"""indexpage.py — 三中心插件/服务门户页（plugins/IndexPage）

子命令：
  build   盘点三类资源（docker 产物登记 / MCP 服务 / 插件）→ 生成 inventory.json + index.html
  apply   应用 plugins/IndexPage/decisions.json：plugin/docker 类写回 policy.yaml grants，
          mcp 类输出人工操作清单 → 自动重新 build

决策闭环（零端口：页面与工程之间也走文件信封）：
  页面切换三中心开关 → 导出 decisions.json → 放置 plugins/IndexPage/decisions.json
  → python3 scripts/indexpage.py apply → policy.yaml 更新（registry 版本+1）→ 页面刷新即生效
"""
import json
import os
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'capabilities'))

import _common as cm  # noqa: E402
import _yamlmini as y  # noqa: E402

PAGE_DIR = os.path.join(ROOT, 'plugins', 'IndexPage')
REGISTRY = os.path.join(cm.CONFIG, 'tools.registry.json')
POLICY = os.path.join(cm.ROOT, 'plugins', 'policy.yaml')
PACKAGES = os.path.join(cm.ROOT, 'plugins', 'packages')
DECISIONS = os.path.join(PAGE_DIR, 'decisions.json')
MCP_SETTINGS_CANDIDATES = [
    os.path.expanduser('~/Library/Application Support/Code/User/globalStorage/'
                       'saoudrizwan.claude-dev/settings/cline_mcp_settings.json'),
    os.path.expanduser('~/.cline/cline_mcp_settings.json'),
]
# 联邦遗产（第一阶段已停用的第三方 MCP 服务，docs/01）
LEGACY_MCP = {'mem0': '联邦遗产（Mem0）— 第一阶段停用，恢复见 docs/01',
              'openviking': '联邦遗产（OpenViking）— 第一阶段停用，恢复见 docs/01',
              'weknora': '联邦遗产（WeKnora）— 第一阶段停用，恢复见 docs/01'}
CENTERS = ('eng', 'data', 'solution')


def _registry():
    if not os.path.exists(REGISTRY):
        return {'version': 0, 'plugins': [], 'tools': []}
    return json.load(open(REGISTRY, encoding='utf-8'))


def _policy_grants():
    p = y.load(POLICY)
    return {c: list(p.get('grants', {}).get(c, []) or []) for c in CENTERS}


def _mcp_inventory():
    """读 Cline 全局 MCP 配置（凭据脱敏），标注联邦遗产。"""
    out = []
    src = None
    for p in MCP_SETTINGS_CANDIDATES:
        if os.path.exists(p):
            src = p
            break
    if src is None:
        return out, '（未找到 Cline MCP 配置文件）'
    try:
        d = json.load(open(src, encoding='utf-8'))
    except Exception as e:  # noqa: BLE001
        return out, '（MCP 配置解析失败: %s）' % e
    for name, spec in (d.get('mcpServers', {}) or {}).items():
        kind = 'streamableHttp' if str(spec.get('type', '')).startswith('streamable') else 'stdio'
        legacy = name in LEGACY_MCP
        item = {'name': name, 'kind': kind,
                'endpoint': spec.get('url', '') or ' '.join([str(spec.get('command', ''))] +
                                                            [str(a) for a in spec.get('args', [])]),
                'legacy': legacy,
                'note': LEGACY_MCP.get(name, ''),
                'status': 'legacy-disabled' if legacy else 'active',
                'config_path': os.path.relpath(src, os.path.expanduser('~'))}
        out.append(item)
    return out, os.path.relpath(src, os.path.expanduser('~'))


def inventory():
    reg = _registry()
    grants = _policy_grants()
    mcp, mcp_src = _mcp_inventory()
    docker, native_plugins = [], []
    pkg_dirs = sorted(os.listdir(PACKAGES)) if os.path.isdir(PACKAGES) else []
    for slug in pkg_dirs:
        pj = os.path.join(PACKAGES, slug, 'package.json')
        if not os.path.exists(pj):
            continue
        pkg = json.load(open(pj, encoding='utf-8'))
        manifest = None
        mpath = os.path.join(cm.ROOT, 'plugins', 'manifests', slug, 'ov-plugin.yaml')
        if os.path.exists(mpath):
            manifest = y.load(mpath)
        item = {
            'slug': slug,
            'name': pkg.get('name') or (manifest or {}).get('name', slug),
            'description': (manifest or {}).get('description', ''),
            'version': (manifest or {}).get('version', pkg.get('version', '')),
            'runtime': pkg.get('runtime', 'native'),
            'artifact_path': pkg.get('artifact_path', ''),
            'entry': pkg.get('entry', (manifest or {}).get('env', {}).get('start', '')),
            'health': pkg.get('health', (manifest or {}).get('env', {}).get('health', '')),
            'image_digest': pkg.get('image_digest'),
            'grants': [c for c in CENTERS if slug in grants[c]],
        }
        (docker if item['runtime'] == 'docker' else native_plugins).append(item)
    return {
        'generated_at': cm.now_iso(),
        'registry_version': reg.get('version', 0),
        'centers': [
            {'id': c, 'name': n, 'core': k} for c, n, k in
            (('eng', '开发中心', 'Cline act + GLM'), ('data', '数策中心', 'Cline + deepseek'),
             ('solution', '方案中心', 'Cline plan + doubao'))],
        'docker': docker,
        'mcp': mcp,
        'mcp_config_src': mcp_src,
        'plugins': native_plugins,
        'note_docker': 'docker 产物由开发中心 W6-B 登记（plugins/packages/<slug>/package.json 的 image_digest）后自动出现在此处。',
    }


# ---------- policy.yaml 行级编辑（保留注释，_yamlmini 只读） ----------

def _line_has_slug(ln, slug):
    """列表项行是否为 '- slug'（兼容行尾注释）"""
    s = ln.strip()
    if not s.startswith('- '):
        return False
    return s[2:].split('#')[0].strip() == slug


def policy_edit(center, slug, add=True):
    """在 grants.<center> 块内增删 '- slug' 行；返回 (changed, message)"""
    lines = cm.read_text(POLICY).splitlines()
    start = None
    for i, ln in enumerate(lines):
        if ln.rstrip() == '  %s:' % center and start is None:
            start = i
    if start is None:
        return False, 'policy.yaml 未找到 grants.%s 块' % center
    end = len(lines)
    for i in range(start + 1, len(lines)):
        s = lines[i].strip()
        if s and not lines[i].startswith('    '):
            end = i
            break
    block = lines[start + 1:end]
    target = '    - %s' % slug
    has = any(_line_has_slug(ln, slug) for ln in block)
    if add and has:
        return False, '%s 已授权 %s（无变更）' % (center, slug)
    if not add and not has:
        return False, '%s 未授权 %s（无变更）' % (center, slug)
    if add:
        # [] 空流式集合行（可能带行内注释）→ 整行替换；否则插入到块尾
        for j in range(len(block)):
            if block[j].strip().startswith('[]'):
                block[j] = target
                break
        else:
            j = len(block)
            while j > 0 and not block[j - 1].strip():
                j -= 1
            block.insert(j, target)
    else:
        block = [ln for ln in block if not _line_has_slug(ln, slug)]
        if not any(ln.strip().startswith('- ') for ln in block):
            # 删空 → 恢复 [] 占位（保持块非空语义）
            block = ['    []']
    new_lines = lines[:start + 1] + block + lines[end:]
    cm.write_text(POLICY, '\n'.join(new_lines) + '\n')
    return True, '%s %s %s' % (center, '授权' if add else '移除', slug)


# ---------- apply ----------

def apply():
    if not os.path.exists(DECISIONS):
        print('未找到 decisions.json：', os.path.relpath(DECISIONS, ROOT))
        return 1
    d = json.load(open(DECISIONS, encoding='utf-8'))
    decisions = d.get('decisions', [])
    if not decisions:
        print('decisions.json 无决策内容')
        return 1
    print('=== 应用 %d 条决策 ===' % len(decisions))
    changed = 0
    manual = []
    for dec in decisions:
        slug, center = dec.get('slug', ''), dec.get('center', '')
        action = dec.get('action', 'grant')
        if center not in CENTERS:
            print('[skip] 非法 center: %s' % center)
            continue
        # plugin/docker 类：写 policy.yaml
        if any(item['slug'] == slug for item in inventory()['plugins']) or \
           any(item['slug'] == slug for item in inventory()['docker']):
            ok, msg = policy_edit(center, slug, add=(action == 'grant'))
            print('[policy] %s' % msg)
            changed += int(ok)
        else:
            manual.append(dec)
    # mcp 类：人工清单
    if manual:
        print('\n=== MCP 类决策（需人工在 Cline 设置操作）===')
        for dec in manual:
            print('  - %s @ %s: %s' % (dec['slug'], dec['center'], dec['action']))
        cm.atomic_write_json(os.path.join(PAGE_DIR, 'mcp-pending-manual.json'),
                             {'applied_at': cm.now_iso(), 'pending': manual})
    if changed:
        subprocess_regen_registry()
    # 归档已应用的决策文件
    os.replace(DECISIONS, os.path.join(PAGE_DIR, 'decisions-applied-%s.json' %
                                       datetime.now().strftime('%Y%m%dT%H%M%S')))
    build()
    print('\n=== 完成：IndexPage 已重新生成（registry 版本随 policy 变更 +1）===')
    return 0


def subprocess_regen_registry():
    import subprocess
    r = subprocess.run([sys.executable, os.path.join(ROOT, 'scripts', 'gen-registry.py')],
                       capture_output=True, text=True, timeout=60)
    print(r.stdout.strip())
    if r.returncode != 0:
        print('registry 重建告警:', r.stderr[-300:])


# ---------- build ----------

TEMPLATE = os.path.join(ROOT, 'scripts', 'indexpage_template.html')


def _env_plain(manifest_env):
    """manifest env 压平为可读 dict（模板 only 显示键值）"""
    if not manifest_env:
        return {}
    return {k: v for k, v in manifest_env.items() if not isinstance(v, (dict, list))}


def build():
    inv = inventory()
    # tools_view：给插件卡的清单视图（registry.tools）
    reg = _registry()
    inv['tools_view'] = [{'name': t.get('name'), 'slug': t.get('slug'),
                          'description': t.get('description'),
                          'class': t.get('class'), 'risk': t.get('risk')}
                         for t in reg.get('tools', [])]
    # 插件卡带 env_plain
    for p in inv['plugins']:
        mpath = os.path.join(cm.ROOT, 'plugins', 'manifests', p['slug'], 'ov-plugin.yaml')
        p['env_plain'] = _env_plain(y.load(mpath).get('env', {})) if os.path.exists(mpath) else {}
    os.makedirs(PAGE_DIR, exist_ok=True)
    cm.atomic_write_json(os.path.join(PAGE_DIR, 'inventory.json'), inv)
    tpl = cm.read_text(TEMPLATE)
    inv_js = json.dumps(inv, ensure_ascii=False, indent=2, default=str)
    html = tpl.replace('__INVENTORY_JSON__', inv_js)
    out = os.path.join(PAGE_DIR, 'index.html')
    cm.write_text(out, html)
    print('IndexPage 已生成：')
    print('  页面     :', os.path.relpath(out, ROOT))
    print('  盘点快照 :', os.path.relpath(os.path.join(PAGE_DIR, 'inventory.json'), ROOT))
    print('  docker=%d mcp=%d 插件=%d（registry v%d）' % (
        len(inv['docker']), len(inv['mcp']), len(inv['plugins']), inv['registry_version']))
    return inv


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'build'
    if cmd == 'build':
        build()
    elif cmd == 'apply':
        sys.exit(apply())
    else:
        print(__doc__)
