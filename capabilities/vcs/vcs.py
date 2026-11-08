"""vcs.py — 契约侧 Git 操作（子进程封装；一键脚本见 scripts/git-push.sh）"""
import os
import subprocess
import sys


def git(args, cwd=None, timeout_s=120):
    r = subprocess.run(['git'] + list(args), cwd=cwd, capture_output=True, text=True,
                       timeout=timeout_s)
    return {'ok': r.returncode == 0, 'code': r.returncode,
            'stdout': r.stdout, 'stderr': r.stderr}


def clone(url, dest, timeout_s=600):
    if os.path.exists(os.path.join(dest, '.git')):
        return pull(dest, timeout_s=timeout_s)
    return git(['clone', url, dest], timeout_s=timeout_s)


def pull(cwd, timeout_s=300):
    return git(['pull', '--rebase'], cwd=cwd, timeout_s=timeout_s)


def commit_all(cwd, message, timeout_s=120):
    r1 = git(['add', '-A'], cwd=cwd)
    if not r1['ok']:
        return r1
    r2 = git(['commit', '-m', message], cwd=cwd)
    # 无变更时 commit 返回非 0，视为成功
    if 'nothing to commit' in (r2.get('stdout', '') + r2.get('stderr', '')):
        return {'ok': True, 'code': 0, 'stdout': 'nothing to commit', 'stderr': ''}
    return r2


def fsck_short(cwd):
    return git(['fsck', '--short'], cwd=cwd)
