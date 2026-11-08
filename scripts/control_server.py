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


def _build_state():
    inv = indexpage.build()
    inv['services'] = services.all_status([p['slug'] for p in inv['plugins']] +
                                          [d['slug'] for d in inv['docker']])
    inv['cline_mcp'] = {p['slug']: clinecfg.has_server(p['slug']) for p in inv['plugins']}
    inv['control'] = {'connected': True, 'port': PORT}
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

    def log_message(self, fmt, *args):  # 静默访问日志（动作审计已落盘）
        pass

    def do_OPTIONS(self):
        self._send({'ok': True})

    def do_GET(self):
        if self.path == '/api/state':
            try:
                self._send({'ok': True, 'state': _build_state()})
            except Exception as e:  # noqa: BLE001
                self._send({'ok': False, 'error': str(e)}, 500)
        elif self.path == '/api/ping':
            self._send({'ok': True, 'service': 'ai-three-center-control', 'port': PORT})
        else:
            self._send({'ok': False, 'error': 'not found'}, 404)

    def do_POST(self):
        if self.path != '/api/action':
            self._send({'ok': False, 'error': 'not found'}, 404)
            return
        try:
            req = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))) or b'{}')
            action, slug = req.get('action', ''), req.get('slug', '')
            if action == 'start':
                out = services.start(slug)
            elif action == 'stop':
                out = services.stop(slug)
            elif action == 'status':
                out = services.status(slug)
            elif action in ('grant', 'revoke'):
                center = req.get('center', '')
                ok, msg = indexpage.policy_edit(center, slug, add=(action == 'grant'))
                out = {'ok': ok, 'message': msg}
                if ok and action == 'grant':
                    mc = indexpage.manifest_mcp_server(slug)
                    if mc:
                        out['cline'] = clinecfg.upsert_server(slug, mc)
                if ok:
                    indexpage.subprocess_regen_registry()
                out['state'] = _build_state()
            elif action == 'configure_mcp':
                mc = indexpage.manifest_mcp_server(slug)
                out = clinecfg.upsert_server(slug, mc) if mc else \
                    {'ok': False, 'error': 'manifest 未定义 mcp_server'}
            elif action == 'mcp_disable':
                out = clinecfg.remove_server(slug)
            else:
                out = {'ok': False, 'error': 'unknown action: ' + str(action)}
            self._send(out)
        except Exception as e:  # noqa: BLE001
            self._send({'ok': False, 'error': str(e)}, 500)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        PORT = int(sys.argv[1])
    print('[control] 三中心门户控制台 http://127.0.0.1:%d（Ctrl+C 退出；非常驻，页面离线时自动降级决策导出模式）' % PORT)
    print('[control] 动作审计 → data/assets/plugins/audit/ · Cline 配置写前自动备份 .auto-bak/')
    ThreadingHTTPServer(('127.0.0.1', PORT), Handler).serve_forever()
