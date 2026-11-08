"""services.py — 插件服务生命周期（native PID 管理 / docker compose）

实例策略（plugins/README §三）：默认单例共享。状态落 data/runs/services/<slug>.json。
启动方式取 manifest 的 env.start（native）或 package.json 的 stack（docker compose）。
"""
import json
import os
import signal
import subprocess
import sys
import time
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
_CAP = os.path.dirname(_HERE)
if _CAP not in sys.path:
    sys.path.insert(0, _CAP)

import _common as cm  # noqa: E402
import _yamlmini as y  # noqa: E402
import runtime.runtime as rt  # noqa: E402

STATE_DIR = os.path.join(cm.DATA, 'runs', 'services')
MANIFESTS = os.path.join(cm.ROOT, 'plugins', 'manifests')
PACKAGES = os.path.join(cm.ROOT, 'plugins', 'packages')


def _load(slug):
    mpath = os.path.join(MANIFESTS, slug, 'ov-plugin.yaml')
    m = y.load(mpath) if os.path.exists(mpath) else {}
    pj = os.path.join(PACKAGES, slug, 'package.json')
    pkg = json.load(open(pj, encoding='utf-8')) if os.path.exists(pj) else {}
    return m, pkg


def _state_path(slug):
    return os.path.join(STATE_DIR, slug + '.json')


def _pid_alive(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except (ValueError, ProcessLookupError, PermissionError):
        return False


def _load_state(slug):
    p = _state_path(slug)
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {}


def _save_state(slug, st):
    cm.atomic_write_json(_state_path(slug), st)


def _audit(slug, action, detail):
    cm.append_jsonl(os.path.join(cm.DATA, 'assets', 'plugins', 'audit', cm.today_tag() + '.jsonl'),
                    {'ts': cm.now_iso(), 'slug': slug, 'action': action, **detail})


def _health(url, timeout_s=3):
    """解析 manifest health（'GET <url> -> <code>' 或纯 URL）并探测"""
    if not url:
        return None
    import re
    m = re.match(r'GET\s+(\S+)\s*->\s*(\d+)', str(url).strip())
    if m:
        expect, target = int(m.group(2)), m.group(1)
    elif str(url).strip().startswith('http'):
        expect, target = 200, str(url).strip()
    else:
        return None
    try:
        with urllib.request.urlopen(target, timeout=timeout_s) as resp:
            return {'ok': resp.status == expect, 'status': resp.status}
    except Exception as e:  # noqa: BLE001
        return {'ok': False, 'status': 0, 'error': str(e)[:120]}


def start(slug):
    """启动插件实例。native: 后台子进程+PID；docker: compose up -d（页面点击即人工确认，全量审计）"""
    m, pkg = _load(slug)
    env = m.get('env', {}) or {}
    kind = pkg.get('runtime') or m.get('runtime', 'native')
    workdir = os.path.join(cm.ROOT, env.get('workdir', ''))
    if kind == 'docker':
        stack = pkg.get('stack', {}) or {}
        compose = stack.get('compose_file')
        if not compose:
            return {'ok': False, 'error': 'package.json 未登记 stack.compose_file'}
        args = ['docker', 'compose', '-f', os.path.join(cm.ROOT, compose), 'up', '-d']
        cwd = os.path.join(cm.ROOT, stack['project_dir']) if stack.get('project_dir') else None
        r = rt.run(args, timeout_s=300, cwd=cwd)
        _audit(slug, 'start', {'runtime': 'docker', 'ok': r['ok'], 'cmd': ' '.join(args)})
        st = {'runtime': 'docker', 'status': 'running' if r['ok'] else 'failed',
              'detail': (r['stdout'] or r['stderr'])[-300:], 'updated_at': cm.now_iso()}
        _save_state(slug, st)
        return {**r, 'status': st['status']}
    # native
    start_cmd = env.get('start', '')
    if not start_cmd:
        return {'ok': False, 'error': 'manifest 未定义 env.start'}
    if not os.path.isdir(workdir):
        return {'ok': False, 'error': 'workdir 不存在: ' + workdir}
    old = _load_state(slug)
    health0 = _health(env.get('health', ''))
    # 主判据 = 端口实况（health 通即已在运行；pid 在 bash exec/僵尸怪癖下会漂移）
    if health0 and health0.get('ok'):
        return {'ok': True, 'status': 'running', 'pid': old.get('pid'), 'health': health0,
                'note': '已在运行（健康探测通过）'}
    if old.get('pid') and _pid_alive(old['pid']):
        # pid 活着但 health 未通：仍按已在运行处理（可能在启动中），提示等待
        return {'ok': True, 'status': 'running', 'pid': old['pid'],
                'health': health0, 'note': '进程存在但健康探测未通过，请稍后刷新'}
    logf = os.path.join(cm.ROOT, 'output', '%s-native.log' % slug)
    venv_bin = os.path.join(workdir, '.venv', 'bin')
    child_env = {**os.environ, 'PATH': venv_bin + ':' + os.environ['PATH']} \
        if env.get('use_venv', True) and os.path.isdir(venv_bin) else dict(os.environ)
    with open(logf, 'ab') as lf:
        # start_new_session：子进程自成为进程组长，stop 时 killpg 可整树终止（防 uvicorn 孤儿）
        proc = subprocess.Popen(start_cmd, shell=True, cwd=workdir,
                                stdout=lf, stderr=subprocess.STDOUT, env=child_env,
                                start_new_session=True)
    pid = proc.pid
    wait_s = int(env.get('health_wait_s', 10))
    health = None
    for _ in range(wait_s):
        time.sleep(1)
        health = _health(env.get('health', ''))
        if health and health.get('ok'):
            break
    st = {'runtime': 'native', 'pid': pid, 'status': 'running' if _pid_alive(pid) else 'failed',
          'health': health, 'log': os.path.relpath(logf, cm.ROOT), 'updated_at': cm.now_iso()}
    _save_state(slug, st)
    _audit(slug, 'start', {'runtime': 'native', 'pid': pid, 'health': health,
                           'cmd': start_cmd[:120]})
    return {'ok': st['status'] == 'running', **st}


def stop(slug):
    """停止插件实例。docker: compose down；native: SIGTERM→SIGKILL"""
    m, pkg = _load(slug)
    kind = pkg.get('runtime') or m.get('runtime', 'native')
    if kind == 'docker':
        stack = pkg.get('stack', {}) or {}
        compose = stack.get('compose_file')
        if not compose:
            return {'ok': False, 'error': 'package.json 未登记 stack.compose_file'}
        r = rt.run(['docker', 'compose', '-f', os.path.join(cm.ROOT, compose), 'down'],
                   timeout_s=300)
        _audit(slug, 'stop', {'runtime': 'docker', 'ok': r['ok']})
        _save_state(slug, {'runtime': 'docker', 'status': 'stopped', 'updated_at': cm.now_iso()})
        return {**r, 'status': 'stopped'}
    st = _load_state(slug)
    pid = st.get('pid')
    killed = []
    if pid:
        try:
            pgid = os.getpgid(int(pid))
            os.killpg(pgid, signal.SIGTERM)
            for _ in range(10):
                time.sleep(0.5)
                if not _pid_alive(pid):
                    break
            else:
                try:
                    os.killpg(pgid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass
            killed.append(pid)
        except (ProcessLookupError, PermissionError, ValueError):
            pass  # pid 已漂移/僵尸 → 走端口兜底
    # 端口兜底：无论 pid 跟踪是否有效，端口仍被占即按 lsof 清理（防孤儿）
    import re
    h = str((m.get('env', {}) or {}).get('health', ''))
    pm = re.search(r':(\d+)', h)
    if pm:
        port = pm.group(1)
        r2 = rt.run(['lsof', '-ti', ':' + port], timeout_s=15)
        orphans = [p for p in r2.get('stdout', '').split() if p.isdigit()]
        for op in orphans:
            try:
                os.kill(int(op), signal.SIGKILL)
                killed.append(int(op))
            except (ProcessLookupError, PermissionError):
                pass
        if orphans:
            _audit(slug, 'stop_orphan', {'port': port, 'killed': killed})
    _save_state(slug, {**st, 'status': 'stopped', 'pid': None, 'updated_at': cm.now_iso()})
    _audit(slug, 'stop', {'runtime': 'native', 'killed': killed})
    return {'ok': True, 'status': 'stopped', 'killed': killed}


def status(slug):
    """单插件实例状态（native: PID+健康探测；docker: compose ps）"""
    m, pkg = _load(slug)
    env = m.get('env', {}) or {}
    st = _load_state(slug)
    if (pkg.get('runtime') or m.get('runtime', 'native')) == 'docker':
        stack = pkg.get('stack', {}) or {}
        compose = (stack.get('compose_file') or 'x')
        r = rt.run(['docker', 'compose', '-f', os.path.join(cm.ROOT, compose),
                    'ps', '--format', 'json'], timeout_s=30)
        running = r['ok'] and r['stdout'].strip() not in ('', '[]')
        return {'slug': slug, 'runtime': 'docker',
                'status': 'running' if running else 'stopped', 'detail': r['stdout'][:200]}
    alive = bool(st.get('pid') and _pid_alive(st['pid']))
    health = _health(env.get('health', ''))
    return {'slug': slug, 'runtime': 'native', 'pid': st.get('pid'),
            'status': 'running' if (alive or (health and health.get('ok'))) else 'stopped',
            'health': health, 'log': st.get('log', '')}


def all_status(slugs=None):
    if slugs is None:
        slugs = [d for d in os.listdir(MANIFESTS)
                 if os.path.exists(os.path.join(MANIFESTS, d, 'ov-plugin.yaml'))] \
            if os.path.isdir(MANIFESTS) else []
    return [status(s) for s in slugs]
