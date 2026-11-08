"""clinecfg.py — Cline MCP 配置管理（把插件以 MCP 方式配置到智能体）

- 目标文件：cline_mcp_settings.json（自动探测 VSCode globalStorage 路径）
- 写前强制备份：.auto-bak/<ts>-cline-mcp/cline_mcp_settings.json（docs/05 备份回滚）
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

CANDIDATES = [
    os.path.expanduser('~/Library/Application Support/Code/User/globalStorage/'
                       'saoudrizwan.claude-dev/settings/cline_mcp_settings.json'),
    os.path.expanduser('~/.cline/cline_mcp_settings.json'),
]


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
    return {'ok': True, 'action': action, 'path': os.path.relpath(p, os.path.expanduser('~')),
            'backup': os.path.relpath(bak, cm.ROOT) if bak else None,
            'missing_env': missing, 'env_masked': env_view,
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
    return {'ok': True, 'action': 'removed', 'backup': os.path.relpath(bak, cm.ROOT),
            'note': '重启 Cline（reload MCP）后生效'}


def has_server(slug):
    cfg, _ = _read()
    return slug in cfg.get('mcpServers', {})


def server_env_masked(slug):
    cfg, _ = _read()
    env = (cfg.get('mcpServers', {}).get(slug, {}) or {}).get('env', {})
    return {k: _mask(v) for k, v in env.items()}
