#!/usr/bin/env python3
"""control_server.py — 三中心门户本地控制台（页面↔工程互联通道）

按需拉起（非常驻）：python3 scripts/control_server.py [port=8765]
仅监听 127.0.0.1；CORS 允许 file://（null origin）；所有动作写审计。

API：
  GET  /api/state                     → inventory + 服务状态 + cline mcp 状态
  POST /api/action  JSON:
    {action: "start"|"stop",      slug}                    → services.start/stop
    {action: "status",            slug}                    → services.status
    {action: "grant"|"revoke",    slug, center}            → policy 授权 + （grant 时自动配置 Cline MCP）
    {action: "configure_mcp",     slug}                    → 仅重写 Cline MCP 条目
    {action: "mcp_disable",       slug}                    → 从 Cline 配置移除条目
安全：所有动作落 data/assets/plugins/audit/；grant 走 policy.yaml 行级编辑（与页面决策闭环同一函数）。
"""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'capabilities'))
sys.path.insert(0, os.path.join(ROOT, 'scripts'))

import _common as cm  # noqa: E402
import services.services as services  # noqa: E402
import clinecfg.clinecfg as clinecfg  # noqa: E402
import indexpage  # noqa: E402

PORT = 8765


# ---------- API 路由 ----------

PAGE_DIR = indexpage.PAGE_DIR


def _build_state():
    inv = indexpage.build()
    inv['services'] = services.all_status([p['slug'] for p in inv['plugins']] +
                                          [d['slug'] for d in inv['docker']])
    inv['cline_mcp'] = {p['slug']: clinecfg.has_server(p['slug']) for p in inv['plugins']}
    inv['control'] = {'connected': True, 'port': PORT}
    inv['config'] = indexpage.load_config()
    return inv


class Handler(BaseHTTPRequestHandler):
    def _send(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False, default=str).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, rel):
        """静态托管：仅允许 IndexPage 目录白名单（零目录穿越）"""
        safe = os.path.normpath(rel).lstrip('/')
        full = os.path.join(PAGE_DIR, safe)
        if not full.startswith(PAGE_DIR) or not os.path.isfile(full):
            self._send({'ok': False, 'error': 'not found'}, 404)
            return
        ctype = 'text/html; charset=utf-8' if full.endswith('.html') else \
            'application/json' if full.endswith('.json') else 'text/plain; charset=utf-8'
        body = open(full, 'rb').read()
        self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):  # 静默访问日志（动作审计已落盘）
        pass

    def do_OPTIONS(self):
        self._send({'ok': True})

    def do_GET(self):
        path = self.path.split('?')[0]
        try:
            if path in ('/', '/index.html'):
                self._send_file('index.html')
            elif path == '/api/state':
                self._send({'ok': True, 'state': _build_state()})
            elif path == '/api/ping':
                self._send({'ok': True, 'service': 'ai-three-center-control', 'port': PORT})
            elif path == '/api/config':
                self._send({'ok': True, 'config': indexpage.load_config()})
            elif path == '/api/docs':
                self._send(indexpage.docs_list())
            elif path.startswith('/api/static/'):
                self._send_file(path[len('/api/static/'):])
            else:
                self._send({'ok': False, 'error': 'not found'}, 404)
        except Exception as e:  # noqa: BLE001
            self._send({'ok': False, 'error': str(e)}, 500)

    def do_POST(self):
        path = self.path.split('?')[0]
        try:
            req = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))) or b'{}')
            if path == '/api/action':
                self._send(self._action(req))
            elif path == '/api/config':
                self._send(self._config_set(req))
            elif path == '/api/github':
                self._send(self._github(req))
            elif path == '/api/docs':
                self._send(self._docs(req))
            else:
                self._send({'ok': False, 'error': 'not found'}, 404)
        except Exception as e:  # noqa: BLE001
            self._send({'ok': False, 'error': str(e)}, 500)

    def _action(self, req):
        action, slug = req.get('action', ''), req.get('slug', '')
        if action == 'start':
            return services.start(slug)
        if action == 'stop':
            return services.stop(slug)
        if action == 'status':
            return services.status(slug)
        if action in ('grant', 'revoke'):
            center = req.get('center', '')
            # MCP 类条目不是插件：policy 授权矩阵只管插件/Docker 产物，MCP 走 cline_mcp_toggle
            inv = indexpage.build()
            known = {x['slug'] for x in inv['plugins'] + inv['docker']}
            if slug not in known:
                return {'ok': False, 'error':
                        '%s 是 MCP 服务（非插件）：三中心授权开关不适用。请使用 Cline 启用/停用开关'
                        '（action=mcp_toggle），或在 Cline 扩展设置中管理。' % slug}
            ok, msg = indexpage.policy_edit(center, slug, add=(action == 'grant'))
            out = {'ok': ok, 'message': msg}
            if ok and action == 'grant':
                mc = indexpage.manifest_mcp_server(slug)
                if mc:
                    out['cline'] = clinecfg.upsert_server(slug, mc)
            if ok:
                indexpage.subprocess_regen_registry()
            out['state'] = _build_state()
            return out
        if action == 'mcp_toggle':
            return clinecfg.set_disabled(slug, bool(req.get('disabled')))
        if action == 'configure_mcp':
            mc = indexpage.manifest_mcp_server(slug)
            return clinecfg.upsert_server(slug, mc) if mc else \
                {'ok': False, 'error': 'manifest 未定义 mcp_server'}
        if action == 'mcp_disable':
            return clinecfg.remove_server(slug)
        return {'ok': False, 'error': 'unknown action: ' + str(action)}

    def _config_set(self, req):
        file = req.get('file', '')
        keys = req.get('keys', [])
        value = req.get('value', '')
        ok, msg, cfg = indexpage.save_config(file, keys, value)
        return {'ok': ok, 'message': msg, 'config': cfg}

    def _github(self, req):
        action = req.get('action', '')
        if action == 'import':
            return indexpage.github_import(req.get('url', ''))
        repo = req.get('repo', '')
        if not repo:
            return {'ok': False, 'error': '缺少 repo'}
        return indexpage.github_action(repo, req.get('op', 'status'))

    def _docs(self, req):
        action = req.get('action', '')
        if action == 'outline':
            return indexpage.docs_outline(req.get('topic', ''), req.get('audience', ''))
        if action == 'full':
            return indexpage.docs_full(req.get('topic', ''), req.get('outline', ''),
                                       req.get('audience', ''))
        if action == 'write':
            return indexpage.docs_write(req.get('topic', ''), req.get('content', ''),
                                        req.get('kind', 'manuals'))
        if action == 'list':
            return indexpage.docs_list()
        return {'ok': False, 'error': 'unknown docs action'}


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        PORT = int(sys.argv[1])
    print('[control] 三中心门户控制台 http://127.0.0.1:%d（Ctrl+C 退出；非常驻，页面离线时自动降级决策导出模式）' % PORT)
    print('[control] 动作审计 → data/assets/plugins/audit/ · Cline 配置写前自动备份 .auto-bak/')
    ThreadingHTTPServer(('127.0.0.1', PORT), Handler).serve_forever()
