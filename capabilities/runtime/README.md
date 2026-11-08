# capabilities/runtime — 进程/容器执行

`runtime.py`：子进程执行 + 环境能力探测。**docker 为可选依赖**（仅开发中心打包 `runtime: docker` 插件时调用本机 OrbStack docker CLI）。

## 接口

```
run(cmd, timeout_s=120, cwd=None) -> { ok, code, stdout, stderr }   # stdout 限长截断
detect() -> { python3, git, docker, docker_daemon? }
docker_available() -> bool
```

- 新工程自身运行零容器、零端口、零 compose（docs/04 §一）
- 一次性运维脚本（one-key.sh / pipeline.sh 等）保持 bash，本模块供 flow 节点编排调用
