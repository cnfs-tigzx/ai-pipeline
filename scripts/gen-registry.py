#!/usr/bin/env python3
"""gen-registry.py — 从 plugins/manifests + policy.yaml 生成 config/tools.registry.json
用法：
  python3 scripts/gen-registry.py           # 重建 registry 并版本 +1
  python3 scripts/gen-registry.py --html    # 同时刷新 plugins-registry.html
零第三方依赖（标准库 + capabilities/_yamlmini）。
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'capabilities'))

import _yamlmini as y  # noqa: E402
import _common as cm  # noqa: E402

MANIFESTS = os.path.join(ROOT, 'plugins', 'manifests')
POLICY = os.path.join(ROOT, 'plugins', 'policy.yaml')
REGISTRY = os.path.join(cm.CONFIG, 'tools.registry.json')
HTML = os.path.join(ROOT, 'plugins-registry.html')


def build():
    policy = y.load(POLICY)
    grants = policy.get('grants', {})
    tools = []
    plugins = []
    if os.path.isdir(MANIFESTS):
        for slug in sorted(os.listdir(MANIFESTS)):
            mpath = os.path.join(MANIFESTS, slug, 'ov-plugin.yaml')
            if not os.path.exists(mpath):
                continue
            m = y.load(mpath)
            granted_centers = [c for c, slugs in grants.items() if slug in (slugs or [])]
            plugins.append({'slug': slug, 'name': m.get('name', slug),
                            'description': m.get('description', ''),
                            'version': m.get('version', ''), 'runtime': m.get('runtime', ''),
                            'env': m.get('env', {}), 'grants': granted_centers})
            for tname, spec in (m.get('tools', {}) or {}).items():
                tools.append({'name': '%s__%s' % (slug, tname),
                              'slug': slug,
                              'description': spec.get('description', ''),
                              'side_effect': spec.get('class', '') in ('db_write', 'scrape_remote'),
                              'risk': spec.get('risk', 'low'),
                              'class': spec.get('class', ''),
                              'granted_centers': granted_centers})
    reg_path = REGISTRY
    old = json.load(open(reg_path, encoding='utf-8')) if os.path.exists(reg_path) else {'version': 0}
    reg = {'version': old.get('version', 0) + 1, 'generated_at': cm.now_iso(),
           'generated_by': 'scripts/gen-registry.py', 'tools': tools, 'plugins': plugins}
    cm.atomic_write_json(reg_path, reg)
    return reg


def render_html(reg):
    rows = []
    for p in reg.get('plugins', []):
        env = p.get('env', {})
        grants = ', '.join(p.get('grants', [])) or '未授权'
        tool_rows = ''.join(
            '<tr><td><code>%s</code></td><td>%s</td><td>%s</td><td>%s</td></tr>' % (
                t['name'], t['description'], t.get('class', '-'),
                ', '.join(t.get('granted_centers', [])) or '-')
            for t in reg.get('tools', []) if t['slug'] == p['slug']) or '<tr><td colspan=4>（未声明工具）</td></tr>'
        rows.append(
            '<section><h2>%s <small>(%s · v%s · %s · 授权: %s)</small></h2>'
            '<p>%s</p>'
            '<h3>启动命令环境</h3><pre>%s</pre>'
            '<h3>工具清单</h3><table><tr><th>工具名</th><th>描述</th><th>类别</th><th>授权中心</th></tr>%s</table>'
            '</section>' % (
                p['name'], p['slug'], p.get('version', '-'), p.get('runtime', '-'), grants,
                p['description'],
                '\n'.join('%s: %s' % (k, v) for k, v in env.items()) or '-',
                tool_rows))
    html = '''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<title>ai-three-center 插件列表</title>
<style>body{font-family:-apple-system,system-ui,sans-serif;max-width:960px;margin:2rem auto;padding:0 1rem;color:#222}
h1{border-bottom:2px solid #4a7;font-size:1.4rem}h2{margin-top:1.6rem}h3{font-size:1rem;color:#555}
small{color:#777;font-weight:normal}code{background:#f4f4f4;padding:1px 5px;border-radius:3px}
pre{background:#f7f7f7;padding:.8rem;border-radius:6px;overflow-x:auto;font-size:.85rem}
table{border-collapse:collapse;width:100%%}th,td{border:1px solid #ddd;padding:6px 10px;text-align:left;font-size:.9rem}
th{background:#f0f0f0}.ver{color:#4a7;font-weight:bold}</style></head><body>
<h1>插件列表 <span class="ver">registry v%d</span></h1>
<p>生成时间：%s · 由 scripts/gen-registry.py 生成（纯静态零服务）</p>
%s</body></html>''' % (reg['version'], reg['generated_at'], '\n'.join(rows))
    cm.write_text(HTML, html)


if __name__ == '__main__':
    reg = build()
    print('registry v%d  tools=%d plugins=%d' % (
        reg['version'], len(reg['tools']), len(reg['plugins'])))
    if '--html' in sys.argv:
        render_html(reg)
        print('html ->', os.path.relpath(HTML, ROOT))
