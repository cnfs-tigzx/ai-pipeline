"""_yamlmini.py — 极简 YAML 子集解析器（零第三方依赖）

限制（docs/02-目录规范.md §五）：
- 两空格缩进；map 嵌套、'- ' 列表项、列表项内联 map（'- key: v' 后跟子字段，子字段缩进须比项缩进大 ≥2）
- 标量：字符串/整数/浮点/true/false/null；双引号字符串原样保留
- 注释：整行 '#' 与未引号内的 ' #'（'#' 前须为空白）
- 仅支持空流式集合 [] 与 {}；不支持锚点、块标量(| >)、多行字符串、复杂转义
- 值为空且下一行缩进更深 → 视为子 map/list；否则为 None
"""
import re

_KEY_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_\-.]*$')


def _strip_comment(line):
    out, in_s, in_d = [], False, False
    for i, c in enumerate(line):
        if c == "'" and not in_d:
            in_s = not in_s
        elif c == '"' and not in_s:
            in_d = not in_d
        elif c == '#' and not in_s and not in_d:
            if i == 0 or line[i - 1] in ' \t':
                break
        out.append(c)
    return ''.join(out).rstrip()


def _parse_scalar(s):
    s = s.strip()
    if s == '':
        return None
    if len(s) >= 2 and s[0] == s[-1] and s[0] in '"\'':
        return s[1:-1]
    low = s.lower()
    if low == 'true':
        return True
    if low == 'false':
        return False
    if low in ('null', '~'):
        return None
    if re.fullmatch(r'-?\d+', s):
        return int(s)
    if re.fullmatch(r'-?\d+\.\d+', s):
        return float(s)
    return s


def _is_keyval(rest):
    if ':' not in rest:
        return False
    if '://' in rest and rest.partition('://')[0] + ':' in rest.split()[0]:
        return False
    k, _, v = rest.partition(':')
    if not k.strip() or not _KEY_RE.match(k.strip()):
        return False
    v = v.strip()
    if v.startswith('//'):
        return False
    return True


def parse(text):
    root = {}
    stack = [(-1, root)]          # (push_indent, container)
    pending = None                # (key_indent, key, parent_container)

    for raw in text.splitlines():
        line = _strip_comment(raw)
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(' '))
        content = line.strip()

        # 处理"键值为空，等待子级"的悬挂状态
        if pending is not None:
            p_ind, p_key, p_parent = pending
            pending = None
            if indent <= p_ind:
                if content == '[]':
                    lst = []
                    p_parent[p_key] = lst
                    stack.append((p_ind, lst))
                    continue
                if content == '{}':
                    d = {}
                    p_parent[p_key] = d
                    stack.append((p_ind, d))
                    continue
                p_parent[p_key] = None
            else:
                if content == '[]':
                    lst = []
                    p_parent[p_key] = lst
                    stack.append((p_ind, lst))
                    continue
                if content == '{}':
                    d = {}
                    p_parent[p_key] = d
                    stack.append((p_ind, d))
                    continue
                if content.startswith('- '):
                    lst = []
                    p_parent[p_key] = lst
                    stack.append((p_ind, lst))
                else:
                    d = {}
                    p_parent[p_key] = d
                    stack.append((p_ind, d))

        # 回退到正确容器层
        while indent <= stack[-1][0]:
            stack.pop()
        container = stack[-1][1]

        if content.startswith('- ') or content == '-':
            rest = content[2:].strip() if content != '-' else ''
            if not isinstance(container, list):
                raise ValueError('yamlmini: list item outside list: ' + content)
            if not rest:
                continue
            if _is_keyval(rest):
                k, _, v = rest.partition(':')
                k = k.strip()
                v = v.strip()
                d = {}
                container.append(d)
                if v == '':
                    pending = (indent + 1, k, d)
                else:
                    d[k] = _parse_scalar(v)
                stack.append((indent + 1, d))
            else:
                container.append(_parse_scalar(rest))
        else:
            if ':' not in content:
                raise ValueError('yamlmini: bad line: ' + content)
            k, _, v = content.partition(':')
            k = k.strip().strip('"\'')
            v = v.strip()
            if not isinstance(container, dict):
                raise ValueError('yamlmini: key line inside list: ' + content)
            if v == '':
                pending = (indent, k, container)
            elif v == '[]':
                lst = []
                container[k] = lst
                stack.append((indent, lst))
            elif v == '{}':
                d = {}
                container[k] = d
                stack.append((indent, d))
            else:
                container[k] = _parse_scalar(v)

    if pending is not None:
        p_ind, p_key, p_parent = pending
        p_parent[p_key] = None
    return root


def load(path):
    with open(path, encoding='utf-8') as f:
        return parse(f.read())


def loads(text):
    return parse(text)
