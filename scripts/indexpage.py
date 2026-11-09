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
import services.services as services  # noqa: E402
import clinecfg.clinecfg as clinecfg  # noqa: E402

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


def manifest_mcp_server(slug):
    """读 manifest 的结构化 mcp_server 定义（无则 None）"""
    mpath = os.path.join(cm.ROOT, 'plugins', 'manifests', slug, 'ov-plugin.yaml')
    if not os.path.exists(mpath):
        return None
    return y.load(mpath).get('mcp_server')


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
    # 服务实例状态 + Cline MCP 配置状态（互联视图）
    for item in docker + native_plugins:
        item['service'] = services.status(item['slug'])
        item['cline_mcp'] = clinecfg.has_server(item['slug'])
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


# ---------- 配置文件读写（页面 ↔ 工程配置映射） ----------

import subprocess  # noqa: E402

CONFIG_FILES = {
    'models': os.path.join(cm.CONFIG, 'models.yaml'),
    'runtime': os.path.join(cm.CONFIG, 'runtime.yaml'),
    'policy': POLICY,
    'centers': os.path.join(cm.CONFIG, 'centers.yaml'),   # 只读（中心定义唯一注册处）
}


def load_config():
    """各配置页对应的配置文件快照（解析后 JSON 视图 + 文件路径）"""
    return {
        'models': y.load(CONFIG_FILES['models']),
        'runtime': y.load(CONFIG_FILES['runtime']),
        'policy': y.load(CONFIG_FILES['policy']),
        'centers': y.load(CONFIG_FILES['centers']),
        'paths': {k: os.path.relpath(v, cm.ROOT) for k, v in CONFIG_FILES.items()},
    }


def save_config(file, keys, value):
    """写回配置文件；models/runtime/一般 yaml 键走行级写回，policy.grants 走授权矩阵专用编辑。
    全部先备份 .auto-bak/<ts>-config/。返回 (ok, message, config)"""
    assert file in ('models', 'runtime', 'policy'), '非法配置文件: ' + str(file)
    p = CONFIG_FILES[file]
    bdir = os.path.join(cm.ROOT, '.auto-bak', cm.today_tag() + '-config')
    os.makedirs(bdir, exist_ok=True)
    dest = os.path.join(bdir, os.path.basename(p))
    if not os.path.exists(dest):
        import shutil
        shutil.copy2(p, dest)
    cm.append_jsonl(os.path.join(cm.DATA, 'assets', 'plugins', 'audit', cm.today_tag() + '.jsonl'),
                    {'ts': cm.now_iso(), 'action': 'config_set', 'file': file,
                     'keys': keys, 'value': str(value)[:120]})
    if file == 'policy' and len(keys) >= 2 and keys[0] == 'grants':
        ok, msg = policy_edit(keys[1], str(value), add=(str(value).lower() != 'false'))
        return ok, msg, load_config()
    changed, old, new = cm.yaml_set(p, keys, value)
    if not changed:
        return False, str(old), load_config()
    subprocess_regen_registry()
    return True, '%s → %s' % ('/'.join(keys), value), load_config()


# ---------- GitHub 拉取/编译/部署（开发中心页面化） ----------

def _repo_name(url):
    n = os.path.basename(str(url).rstrip('/'))
    return n[:-4] if n.endswith('.git') else n


def github_import(url):
    """pipeline.sh 拉取 + 简版解析（deploy_mode/端口/简介）→ data/assets/engineering/<repo>/"""
    url = str(url).strip()
    if not url.startswith(('http://', 'https://', 'git@')):
        return {'ok': False, 'error': '非法仓库地址'}
    r = rt_run(['zsh', '-c',
                os.path.join(cm.ROOT, 'scripts', 'pipeline.sh') + ' ' + url],
               timeout_s=600)
    repo = _repo_name(url)
    parse = github_analyze(repo)
    repo_exists = os.path.isdir(os.path.join(cm.ROOT, 'repos', repo, '.git'))
    return {'ok': bool(repo_exists), 'repo': repo,
            'pull_output': (r.get('stdout', '') + r.get('stderr', ''))[-800:],
            'pull_ok': r.get('ok', False),
            'parse': parse, 'parse_saved': parse.get('saved')}


def rt_run(cmd, timeout_s=120):
    """subprocess 包装（indexpage 内部用）"""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s, cwd=cm.ROOT)
        return {'ok': r.returncode == 0, 'code': r.returncode,
                'stdout': r.stdout[-4000:], 'stderr': r.stderr[-2000:]}
    except subprocess.TimeoutExpired:
        return {'ok': False, 'stdout': '', 'stderr': 'timeout'}
    except FileNotFoundError as e:
        return {'ok': False, 'stdout': '', 'stderr': str(e)}


def github_analyze(repo):
    """简版 9 维度解析（deploy_mode / 端口 / 简介 / 启动方式线索）"""
    root = os.path.join(cm.ROOT, 'repos', repo)
    if not os.path.isdir(root):
        return {'ok': False, 'error': 'repos/%s 不存在' % repo}
    files = os.listdir(root)
    mode, hints = 'unknown', []
    if any(f.startswith('docker-compose') and ('.yml' in f or '.yaml' in f) for f in files):
        mode = 'docker'
    elif 'pom.xml' in files:
        mode = 'native-java'
    elif 'package.json' in files:
        mode = 'native-node'
    elif 'requirements.txt' in files or 'app.py' in files or 'main.py' in files:
        mode = 'native-python'
    ports = []
    import re
    for f in files:
        if f.startswith('docker-compose') and ('.yml' in f or '.yaml' in f):
            txt = cm.read_text(os.path.join(root, f))
            ports = re.findall(r'-\s*["\']?(\d{2,5})[:\s]', txt)[:8]
    readme = ''
    for cand in ('README.md', 'README_zh.md', 'README_CN.md', 'readme.md'):
        if cand in files:
            readme = cm.read_text(os.path.join(root, cand))[:400]
            break
    data = {'repo': repo, 'deploy_mode': mode, 'ports': ports,
            'intro': readme.splitlines()[0][:120] if readme else '',
            'parsed_by': 'indexpage-lite', 'parsed_at': cm.now_iso(),
            'files_sample': files[:25], 'hints': hints}
    cm.atomic_write_json(os.path.join(cm.DATA, 'assets', 'engineering', repo, 'readme-parse.json'), data)
    data['saved'] = 'data/assets/engineering/%s/readme-parse.json' % repo
    return data


def github_action(repo, action):
    """one-key.sh 页面化：start/stop/build/status（部署模式自动检测由 one-key 承担）"""
    assert action in ('start', 'stop', 'build', 'status'), '非法动作'
    r = rt_run([os.path.join(cm.ROOT, 'scripts', 'one-key.sh'), repo, action], timeout_s=900)
    tail = (r.get('stdout', '') + r.get('stderr', ''))[-1500:]
    return {**r, 'action': action, 'repo': repo, 'output': tail}


# ---------- 产品文档（方案中心页面化） ----------

def docs_list():
    import assets.assets as ast
    return {'ok': True, 'items': ast.list('solution', 'manuals/') + ast.list('solution', 'papers/')}


def docs_outline(topic, audience=''):
    import llm.llm as llm
    r = llm.complete('solution', 'docs-outline', [
        {'role': 'system', 'content': '你是方案中心智能体。先出大纲再细化，禁止编造数据。'},
        {'role': 'user', 'content': '为主题「%s」生成产品功能文档大纲（5 章内，每章一行）。读者：%s' % (topic, audience or '产品/业务')},
    ], {'max_tokens': 600})
    return r


def docs_full(topic, outline, audience=''):
    """按大纲成文（degraded 时返回降级标记，页面转人工编辑）"""
    import llm.llm as llm
    r = llm.complete('solution', 'docs-full', [
        {'role': 'system', 'content': '你是方案中心智能体。按给定大纲用 Markdown 成文；数据口径缺失处标「待补」，禁止编造。'},
        {'role': 'user', 'content': '主题「%s」（读者：%s）按以下大纲成文（全文 Markdown）：\n%s' % (topic, audience or '产品/业务', outline)},
    ], {'max_tokens': 4000})
    return r


def docs_write(topic, content, kind='manuals'):
    import assets.assets as ast
    safe = ''.join(c for c in topic if c not in '/\\:*?"<>| ')[:60] or 'untitled'
    uri = ast.write('solution', '%s/%s.md' % (kind, safe), content,
                    {'title': topic, 'via': 'IndexPage'})
    return {'ok': True, 'uri': uri}


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
    inv['config'] = load_config()
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
