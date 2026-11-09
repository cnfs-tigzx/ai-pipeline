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


def yaml_set(path, keys, value, indent_unit='  '):
    """行级 YAML 写回：按 key 路径定位目标行，替换值部分（保留行内注释）。

    keys: ['routing', 'eng', 'primary']；value 为 str/int/float/bool 或 '[]' 占位删除
    返回 (changed, old_line/new_line)。目标不存在时追加到其父键块尾。
    """
    lines = read_text(path).splitlines()
    # 逐层定位：i 层 key 的行号
    cur_indent = -1
    cur_line_no = None
    for depth, key in enumerate(keys):
        want_indent = cur_indent + len(indent_unit) if cur_indent >= 0 else 0
        found = None
        start = (cur_line_no + 1) if cur_line_no is not None else 0
        for i in range(start, len(lines)):
            ln = lines[i]
            if not ln.strip() or ln.strip().startswith('#'):
                continue
            ind = len(ln) - len(ln.lstrip(' '))
            if ind <= cur_indent and cur_line_no is not None:
                break  # 离开父块
            if ind == want_indent and ln.strip().startswith(key + ':'):
                found = i
                break
        if found is None:
            # 父块内追加（仅支持最后一层缺失；中间层缺失返回失败）
            if depth == len(keys) - 1 and cur_line_no is not None:
                ins = cur_line_no + 1
                while ins < len(lines) and (not lines[ins].strip() or
                                            len(lines[ins]) - len(lines[ins].lstrip(' ')) > want_indent or
                                            lines[ins].strip().startswith('- ') or
                                            lines[ins].strip().startswith('#')):
                    ins += 1
                # 插在父块最后一条同/深缩进行之后
                j = ins
                while j > cur_line_no + 1 and (not lines[j - 1].strip()):
                    j -= 1
                lines.insert(j, indent_unit * (depth) + key + ': ' + str(value))
                write_lines(path, lines)
                return True, None, lines[j]
            return False, '未找到键路径: ' + '/'.join(keys), None
        cur_indent = want_indent
        cur_line_no = found
        # 若该行值为空且子级存在，继续下一层
    # 替换目标行值
    ln = lines[cur_line_no]
    key = keys[-1]
    comment = ''
    if '#' in ln and not ln.strip().startswith('#'):
        idx = ln.rfind(' #')
        if idx > -1:
            comment = ' ' + ln[idx:].strip()
    old = ln
    lines[cur_line_no] = (want_indent * ' ') + key + ': ' + str(value) + comment
    write_lines(path, lines)
    return True, old, lines[cur_line_no]


def write_lines(path, lines):
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    os.replace(tmp, path)
