"""clinecfg.py — Cline MCP 配置管理（把插件以 MCP 方式配置到智能体）

- 目标文件：cline_mcp_settings.json（自动探测 VSCode globalStorage 路径）
- 写前强制备份：.auto-bak/<ts>-cline-mcp/cline_mcp_settings.json（docs/05 备份回滚）
- **双写工程副本**：agents/init/cline_mcp_settings.json（凭据 $KEEP 脱敏，agent_init_rules 纪律）
- **mcp_docs 自动生成**：agents/init/mcp_docs.md 的 AUTOGEN 区（人工踩坑区在标记外，不覆盖）
- env 值支持引用（manifest 中不落明文凭据，manifest 入 git）：
    $ENV{NAME}        → os.environ
    $FILE{relpath}    → 工程根相对文件首行（如密钥文件）
    $KEEP             → 保留 Cline 配置中的旧值（不改凭据）
  无法解析时写入占位 "<slug>-<KEY>-TODO"，并在返回体 missing_env 中列出提示人工补配。
- 凡读取/写回该文件，日志与返回体一律脱敏（值只显示前 6 位 + ***）
"""
import json
import os
import shutil
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_CAP = os.path.dirname(_HERE)
if _CAP not in sys.path:
    sys.path.insert(0, _CAP)

import _common as cm  # noqa: E402
import _yamlmini as y  # noqa: E402

CANDIDATES = [
    os.path.expanduser('~/Library/Application Support/Code/User/globalStorage/'
                       'saoudrizwan.claude-dev/settings/cline_mcp_settings.json'),
    os.path.expanduser('~/.cline/cline_mcp_settings.json'),
]
# 工程内初始化资产区（agent_init_rules.md 纪律的落位）
PROJECT_COPY = os.path.join(cm.ROOT, 'agents', 'init', 'cline_mcp_settings.json')
MCP_DOCS = os.path.join(cm.ROOT, 'agents', 'init', 'mcp_docs.md')
AUTOGEN_BEGIN = '<!-- AUTOGEN:BEGIN（此区由 clinecfg 自动生成，勿手改）-->'
AUTOGEN_END = '<!-- AUTOGEN:END -->'


def settings_path():
    for p in CANDIDATES:
        if os.path.exists(p):
            return p
    return CANDIDATES[0]


def _mask(v):
    v = str(v)
    return v[:6] + '***' if len(v) > 10 else '***'


def _read():
    p = settings_path()
    if not os.path.exists(p):
        return {'mcpServers': {}}, p
    return json.load(open(p, encoding='utf-8')), p


def _backup(p):
    bdir = os.path.join(cm.ROOT, '.auto-bak', cm.today_tag() + '-cline-mcp')
    os.makedirs(bdir, exist_ok=True)
    dest = os.path.join(bdir, 'cline_mcp_settings.json')
    if not os.path.exists(dest):
        shutil.copy2(p, dest)
    return dest


def _resolve_env(slug, env_spec, existing_env):
    """解析 manifest mcp_server.env 的引用；$KEEP 取旧值；返回 (env, missing)"""
    out, missing = {}, []
    for k, spec in (env_spec or {}).items():
        s = str(spec)
        if s == '$KEEP':
            if k in existing_env:
                out[k] = existing_env[k]
            else:
                missing.append(k)
        elif s.startswith('$ENV{') and s.endswith('}'):
            name = s[5:-1]
            if name in os.environ:
                out[k] = os.environ[name]
            else:
                missing.append(k)
        elif s.startswith('$FILE{') and s.endswith('}'):
            rel = s[6:-1]
            fp = os.path.join(cm.ROOT, rel)
            if os.path.exists(fp):
                with open(fp, encoding='utf-8') as f:
                    out[k] = f.readline().strip()
            else:
                missing.append(k)
        else:
            out[k] = s   # 非敏感字面量（URL/用户名等）
    return out, missing


def upsert_server(slug, spec):
    """把 manifest 的 mcp_server 写入 Cline 配置。返回 {ok, action, path, missing_env, servers}"""
    cfg, p = _read()
    servers = cfg.setdefault('mcpServers', {})
    existing = servers.get(slug, {})
    existing_env = existing.get('env', {}) or {}
    env, missing = ({}, [])
    if spec.get('type', 'stdio') == 'stdio':
        entry = {'type': 'stdio', 'command': spec['command'],
                 'args': [str(a) for a in spec.get('args', [])], 'disabled': False}
        if spec.get('env'):
            env, missing = _resolve_env(slug, spec['env'], existing_env)
            if env:
                entry['env'] = env
    else:
        entry = {'type': spec.get('type', 'streamableHttp'), 'url': spec['url'], 'disabled': False}
    servers[slug] = entry
    action = 'updated' if existing else 'created'
    bak = _backup(p) if os.path.exists(p) else None
    tmp = p + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    os.replace(tmp, p)
    _audit = os.path.join(cm.DATA, 'assets', 'plugins', 'audit', cm.today_tag() + '.jsonl')
    cm.append_jsonl(_audit, {'ts': cm.now_iso(), 'slug': slug, 'action': 'cline_mcp_' + action,
                             'path': os.path.relpath(p, os.path.expanduser('~')),
                             'missing_env': missing})
    env_view = {k: _mask(v) for k, v in (entry.get('env') or {}).items()}
    sync_project_copy()
    regen_mcp_docs()
    return {'ok': True, 'action': action, 'path': os.path.relpath(p, os.path.expanduser('~')),
            'backup': os.path.relpath(bak, cm.ROOT) if bak else None,
            'missing_env': missing, 'env_masked': env_view,
            'project_copy': 'agents/init/cline_mcp_settings.json',
            'note': '重启 Cline（reload MCP）后生效'}


def remove_server(slug):
    cfg, p = _read()
    servers = cfg.get('mcpServers', {})
    if slug not in servers:
        return {'ok': False, 'error': 'Cline 配置中无 ' + slug}
    del servers[slug]
    bak = _backup(p)
    tmp = p + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    os.replace(tmp, p)
    cm.append_jsonl(os.path.join(cm.DATA, 'assets', 'plugins', 'audit', cm.today_tag() + '.jsonl'),
                    {'ts': cm.now_iso(), 'slug': slug, 'action': 'cline_mcp_removed'})
    sync_project_copy()
    regen_mcp_docs()
    return {'ok': True, 'action': 'removed', 'backup': os.path.relpath(bak, cm.ROOT),
            'note': '重启 Cline（reload MCP）后生效'}


def has_server(slug):
    cfg, _ = _read()
    return slug in cfg.get('mcpServers', {})


def server_env_masked(slug):
    cfg, _ = _read()
    env = (cfg.get('mcpServers', {}).get(slug, {}) or {}).get('env', {})
    return {k: _mask(v) for k, v in env.items()}


# ---------- 双写工程副本（agents/init/ · agent_init_rules 纪律） ----------

def _sanitized_copy(cfg):
    """工程副本：凭据值替换为 $KEEP 占位（真实凭据只在全局配置/密钥文件）"""
    out = {'mcpServers': {}, '_note': '工程内 Cline 配置副本（凭据脱敏为 $KEEP 占位）。'
           '真实凭据位置见 .clinerules/agent_init_rules.md；恢复时 clinecfg 以 $KEEP 回填现值或引用密钥文件。',
           'skills': []}
    for name, spec in (cfg.get('mcpServers', {}) or {}).items():
        e = dict(spec)
        if e.get('env'):
            e['env'] = {k: '$KEEP' for k in e['env']}
        out['mcpServers'][name] = e
    return out


def sync_project_copy():
    """全局配置 → agents/init/cline_mcp_settings.json（脱敏副本）"""
    cfg, _ = _read()
    os.makedirs(os.path.dirname(PROJECT_COPY), exist_ok=True)
    cm.atomic_write_json(PROJECT_COPY, _sanitized_copy(cfg))
    return {'ok': True, 'path': os.path.relpath(PROJECT_COPY, cm.ROOT),
            'servers': sorted((cfg.get('mcpServers', {}) or {}).keys())}


def _manifest_info(slug):
    mpath = os.path.join(cm.ROOT, 'plugins', 'manifests', slug, 'ov-plugin.yaml')
    if not os.path.exists(mpath):
        return {}
    m = y.load(mpath)
    return {'description': m.get('description', ''), 'name': m.get('name', slug),
            'version': m.get('version', '')}


def regen_mcp_docs():
    """重新生成 mcp_docs.md 的 AUTOGEN 区；标记外的人工内容原样保留"""
    cfg, _ = _read()
    servers = cfg.get('mcpServers', {}) or {}
    legacy = {'mem0': '联邦遗产（Mem0）· 第一阶段停用 · 恢复见 docs/01',
              'openviking': '联邦遗产（OpenViking）· 第一阶段停用 · 恢复见 docs/01',
              'weknora': '联邦遗产（WeKnora）· 第一阶段停用 · 恢复见 docs/01'}
    lines = [AUTOGEN_BEGIN, '',
             '# Cline MCP 插件清单（自动生成 · ' + cm.now_iso() + '）', '',
             '| 名称 | 类型 | 安装/启动方式 | 功能 | 状态 | 中心授权 |', '|---|---|---|---|---|---|']
    policy_grants = {}
    try:
        policy_grants = y.load(os.path.join(cm.ROOT, 'plugins', 'policy.yaml')).get('grants', {})
    except Exception:  # noqa: BLE001
        pass
    for name, spec in sorted(servers.items()):
        kind = str(spec.get('type', 'stdio'))
        if kind.startswith('streamable'):
            install = 'HTTP 端点直连：' + str(spec.get('url', ''))
        else:
            install = '`' + str(spec.get('command', '')) + ' ' + ' '.join(
                str(a) for a in spec.get('args', [])) + '`'
        info = _manifest_info(name)
        desc = info.get('description') or legacy.get(name, '（见 mcp_docs 人工区）')
        grants = [c for c, slugs in policy_grants.items() if name in (slugs or [])]
        lines.append('| %s | %s | %s | %s | %s | %s |' % (
            name, kind, install.replace('|', '\\|'), (desc or '-')[:80],
            legacy.get(name, '现役'), ', '.join(grants) or '-'))
    lines += ['', '## 安装命令速查', '',
              '- TabClaw MCP（stdio wrapper，现役）：`python3 repos/TabClaw/integrations/tabclaw-mcp/mcp_server.py`'
              '（前置：TabClaw 服务运行中 :8000，`services.start` 或 one-key）',
              '- 恢复联邦三件套（mem0/openviking/weknora）：见 `archive/` 与 docs/01 服务化回归路径',
              '- 新增插件正规流程：开发中心 W6（manifest → packages → registry → policy 授权 → 本清单自动更新）', '',
              '## skills 登记区', '',
              '- （Cline skills 安装后在此登记：名称 / 来源 / 用途 / 落位 agents/init/skills/）', '',
              AUTOGEN_END, '']
    # 保留人工区（AUTOGEN_END 之后的内容）
    human = ''
    if os.path.exists(MCP_DOCS):
        old = cm.read_text(MCP_DOCS)
        if AUTOGEN_END in old:
            human = old.split(AUTOGEN_END, 1)[1]
        else:
            human = '\n## 人工踩坑记录\n\n- （安装/使用 MCP 时的踩坑与注意事项写在这里，重新生成不会覆盖）\n'
    else:
        human = '\n## 人工踩坑记录\n\n- （安装/使用 MCP 时的踩坑与注意事项写在这里，重新生成不会覆盖）\n'
    cm.write_text(MCP_DOCS, '\n'.join(lines) + human)
    return {'ok': True, 'path': os.path.relpath(MCP_DOCS, cm.ROOT), 'servers': len(servers)}
