"""_common.py — capabilities 公共工具（时间戳/ID/原子写/路径）"""
import hashlib
import json
import os
import random
import string
import time
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
CONFIG = os.path.join(ROOT, 'config')


def now_iso():
    return datetime.now().astimezone().isoformat(timespec='seconds')


def month_tag():
    return datetime.now().strftime('%Y-%m')


def today_tag():
    return datetime.now().strftime('%Y-%m-%d')


def rand_id(n=4):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=n))


def run_id():
    return 'run-' + datetime.now().strftime('%Y%m%dT%H%M%S') + '-' + rand_id()


def atomic_write_json(path, obj):
    tmp = path + '.tmp'
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def append_jsonl(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(obj, ensure_ascii=False) + '\n')


def read_jsonl(path):
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding='utf-8') as f:
        for ln in f:
            ln = ln.strip()
            if ln:
                out.append(json.loads(ln))
    return out


def sha256_text(s):
    return hashlib.sha256(s.encode('utf-8')).hexdigest()


def write_text(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def read_text(path):
    with open(path, encoding='utf-8') as f:
        return f.read()
