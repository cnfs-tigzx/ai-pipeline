"""runtime.py — 进程/容器执行（子进程为主；docker 为可选依赖）"""
import os
import shutil
import subprocess
import sys


def run(cmd, timeout_s=120, cwd=None):
    """执行子进程；stdout 限长截断（防大输出回显）"""
    try:
        r = subprocess.run([str(c) for c in cmd], cwd=cwd, capture_output=True,
                           text=True, timeout=timeout_s)
        return {'ok': r.returncode == 0, 'code': r.returncode,
                'stdout': r.stdout[-8000:], 'stderr': r.stderr[-4000:]}
    except subprocess.TimeoutExpired:
        return {'ok': False, 'code': -1, 'stdout': '', 'stderr': 'timeout after %ss' % timeout_s}
    except FileNotFoundError as e:
        return {'ok': False, 'code': -2, 'stdout': '', 'stderr': str(e)}


def detect():
    caps = {}
    caps['python3'] = bool(shutil.which('python3'))
    caps['git'] = bool(shutil.which('git'))
    caps['docker'] = bool(shutil.which('docker'))
    if caps['docker']:
        caps['docker_daemon'] = run(['docker', 'info', '--format', 'ok'], timeout_s=10)['ok']
    return caps


def docker_available():
    """docker 为可选依赖：仅开发中心打包插件（runtime: docker）时使用"""
    caps = detect()
    return caps.get('docker', False) and caps.get('docker_daemon', False)
