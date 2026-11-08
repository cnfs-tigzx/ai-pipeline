"""scrape.py — 网页抓取（urllib 起步，playwright 为演进位）+ 简单表格抽取"""
import os
import re
import sys
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
_CAP = os.path.dirname(_HERE)
if _CAP not in sys.path:
    sys.path.insert(0, _CAP)

import _common as cm  # noqa: E402

UA = 'ai-three-center-runner/0.1 (+local; scrape capability)'


def fetch(url, timeout_s=30, save=True):
    """抓取网页文本；保存到 data/tmp/scrape/（7 天可清理）"""
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    saved_to = None
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read()
            text = raw.decode('utf-8', errors='replace')
            ok, status = True, resp.status
            if save:
                p = os.path.join(cm.DATA, 'tmp', 'scrape',
                                 cm.today_tag() + '-' + cm.rand_id(6) + '.html')
                cm.write_text(p, text)
                saved_to = p
            return {'ok': ok, 'status': status, 'text': text,
                    'url': url, 'saved_to': saved_to}
    except Exception as e:  # noqa: BLE001
        return {'ok': False, 'status': 0, 'text': '', 'url': url,
                'error': str(e), 'saved_to': None}


def fetch_local_html():
    """零网络自测样例（selftest 用）"""
    html = ('<html><body><table>'
            '<tr><th>名称</th><th>数量</th></tr>'
            '<tr><td>苹果</td><td>3</td></tr>'
            '<tr><td>香蕉</td><td>5</td></tr>'
            '</table></body></html>')
    return {'ok': True, 'status': 200, 'text': html, 'url': 'local://selftest',
            'saved_to': None}


def to_rows(text, table_index=0):
    """从 HTML 中抽取第 table_index 个表格 → 二维数组（含表头）。零依赖正则实现。"""
    tables = re.findall(r'<table[^>]*>(.*?)</table>', text, re.S | re.I)
    if table_index >= len(tables):
        return []
    tbl = tables[table_index]
    rows = []
    for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', tbl, re.S | re.I):
        cells = re.findall(r'<t[hd][^>]*>(.*?)</t[hd]>', tr, re.S | re.I)
        clean = [re.sub(r'<[^>]+>', '', c).replace('&nbsp;', ' ').strip() for c in cells]
        if any(clean):
            rows.append(clean)
    return rows
