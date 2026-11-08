"""llm.py — 契约 1 · LLM 路由（替代 LiteLLM，urllib 直连火山方舟）

- 密钥只由本模块读取：env ARK_API_KEY → 根目录密钥文件第二行（gitignored，禁入日志）
- 路由：config/models.yaml routing.<center>（primary → fallback 顺序）
- 计量：data/usage/<center>/YYYY-MM.jsonl（含 degraded 标记）
- 全部模型不可用/无密钥 → 离线模式：模板占位文本 + degraded=true
"""
import json
import os
import sys
import time
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
_CAP = os.path.dirname(_HERE)
if _CAP not in sys.path:
    sys.path.insert(0, _CAP)

import _common as cm  # noqa: E402
import _yamlmini as y  # noqa: E402

MODELS = os.path.join(cm.CONFIG, 'models.yaml')
RUNTIME = os.path.join(cm.CONFIG, 'runtime.yaml')
KEY_FILE = os.path.join(cm.ROOT, '火山方舟模型API')


def _cfg():
    return y.load(MODELS)


def _timeout_s():
    try:
        return y.load(RUNTIME).get('llm', {}).get('timeout_s', 60)
    except Exception:  # noqa: BLE001
        return 60


def ark_key():
    """密钥解析：环境变量优先；缺失回退密钥文件第二行；都无 → None。绝不回显完整值"""
    k = os.environ.get('ARK_API_KEY')
    if k:
        return k
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, encoding='utf-8') as f:
            for ln in f:
                ln = ln.strip()
                if ln.startswith('ark-'):
                    return ln
    return None


def mode():
    cfg = _cfg()
    routes = cfg.get('routing', {})
    has_real = any(not str(r.get('primary', '')).startswith('sentinel-')
                   for r in routes.values())
    if ark_key() is None or not has_real:
        return 'offline'
    return 'normal'


def _meter(center, rec):
    cm.append_jsonl(os.path.join(cm.DATA, 'usage', center, cm.month_tag() + '.jsonl'), rec)


def complete(center, task, messages, options=None):
    """主入口：路由→调用→降级→计量。返回 {text, model, usage, latency_ms, degraded}"""
    options = options or {}
    cfg = _cfg()
    prov = cfg.get('provider', {})
    route = cfg.get('routing', {}).get(center, {})
    chain = []
    if route.get('primary'):
        chain.append(route['primary'])
    for fb in route.get('fallback', []) or []:
        chain.append(fb)
    offline_cfg = cfg.get('offline_mode', {})
    key = ark_key()
    t0 = time.time()
    last_err = ''
    for model in chain:
        if str(model).startswith('sentinel-'):
            last_err = 'model not configured: ' + model
            continue
        if key is None:
            last_err = 'no api key'
            continue
        body = {
            'model': model,
            'messages': messages,
            'temperature': options.get('temperature', 0.3),
        }
        if options.get('max_tokens'):
            body['max_tokens'] = options['max_tokens']
        try:
            req = urllib.request.Request(
                prov.get('base_url', 'https://ark.cn-beijing.volces.com/api/v3') + '/chat/completions',
                data=json.dumps(body).encode('utf-8'),
                headers={'Content-Type': 'application/json',
                         'Authorization': 'Bearer ' + key})
            with urllib.request.urlopen(req, timeout=_timeout_s()) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            text = (data.get('choices') or [{}])[0].get('message', {}).get('content', '')
            usage = data.get('usage', {})
            lat = round((time.time() - t0) * 1000)
            rec = {'ts': cm.now_iso(), 'center': center, 'task': task, 'model': model,
                   'prompt_tokens': usage.get('prompt_tokens'),
                   'completion_tokens': usage.get('completion_tokens'),
                   'total_tokens': usage.get('total_tokens'),
                   'latency_ms': lat, 'degraded': False}
            _meter(center, rec)
            return {'text': text, 'model': model, 'usage': usage,
                    'latency_ms': lat, 'degraded': False}
        except Exception as e:  # noqa: BLE001
            last_err = '%s: %s' % (model, str(e)[:200])
            continue
    # 降级：离线占位
    lat = round((time.time() - t0) * 1000)
    placeholder = offline_cfg.get('placeholder', '[离线模式]')
    _meter(center, {'ts': cm.now_iso(), 'center': center, 'task': task, 'model': 'offline',
                    'prompt_tokens': None, 'completion_tokens': None, 'total_tokens': None,
                    'latency_ms': lat, 'degraded': True, 'error': last_err})
    return {'text': placeholder, 'model': 'offline', 'usage': {},
            'latency_ms': lat, 'degraded': True, 'error': last_err}


def embed(center, texts, purpose='memory'):
    """embedding 接口（演进位）：当前返回占位向量并 degraded=true"""
    cfg = _cfg()
    emb_model = cfg.get('embedding', {}).get('model', '')
    key = ark_key()
    if key and emb_model and not str(emb_model).startswith('sentinel-'):
        try:
            body = {'model': emb_model, 'input': texts}
            req = urllib.request.Request(
                cfg.get('provider', {}).get('base_url') + '/embeddings',
                data=json.dumps(body).encode('utf-8'),
                headers={'Content-Type': 'application/json',
                         'Authorization': 'Bearer ' + key})
            with urllib.request.urlopen(req, timeout=_timeout_s()) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            vectors = [d.get('embedding') for d in data.get('data', [])]
            _meter(center, {'ts': cm.now_iso(), 'center': center, 'task': 'embed:' + purpose,
                            'model': emb_model, 'degraded': False})
            return {'vectors': vectors, 'model': emb_model}
        except Exception as e:  # noqa: BLE001
            _meter(center, {'ts': cm.now_iso(), 'center': center, 'task': 'embed:' + purpose,
                            'model': 'offline', 'degraded': True, 'error': str(e)[:200]})
    return {'vectors': [[0.0]] * len(texts), 'model': 'offline-placeholder'}
