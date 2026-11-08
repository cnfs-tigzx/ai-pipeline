# capabilities/vcs — Git 操作

`vcs.py`：git 子进程封装（bash 一键脚本 `scripts/git-push.sh` 保持独立可用）。

## 接口

```
git(args, cwd) -> { ok, code, stdout, stderr }
clone(url, dest)     # 已存在则自动 pull --rebase
pull(cwd)
commit_all(cwd, message)
fsck_short(cwd)      # P1-A 完整性校验复用
```

- 推送容错（SSH 优先/被拒 rebase/无关历史）由 scripts/git-push.sh v2 承担，本模块不做网络重试
