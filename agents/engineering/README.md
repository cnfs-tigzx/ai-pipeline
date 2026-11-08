# 开发中心（engineering）

> 定位：插件工厂 + 代码工程。内核 = Cline **act 模式** + 火山方舟 GLM 系列（config/models.yaml routing.eng）。

## 职责

1. 拉取/编译/二次开发 GitHub 工程，打包为插件（目录包优先，docker 镜像为可选能力）
2. 插件上架：生成 `plugins/manifests/<slug>/ov-plugin.yaml`（插件名称、启动命令环境、功能描述）→ 登记 `plugins/packages/` → registry 版本 +1 → 刷新插件列表页
3. 可选择将插件安装/启动到三大中心（写 `plugins/policy.yaml` 授权 + 经 mailbox 通知目标中心）
4. 产出部署文档、一键运维脚本、变更日志

## 工作流

| 编号 | 文件 | 内容 |
|---|---|---|
| W0 | workflows/W0-preflight.md | 环境预检（原 P0） |
| W1 | workflows/W1-fetch-build.md | GitHub 拉取 → 部署文档 → 编译部署 → 一键脚本（原 P1） |
| W2 | workflows/W2-secondary-dev.md | 源码二次开发 + Logo/品牌替换（原 P3） |
| W4 | workflows/W4-git-sync.md | Git 仓库初始化与上传（原 P4） |
| W6 | workflows/W6-plugin-release.md | 插件上架与三中心安装（新增） |

## 规则

- rules/build-deploy-rule.md（原 03 构建部署）
- rules/secondary-dev-rule.md（原 05 二开与品牌）
- rules/git-sync-rule.md（原 02 Git 同步）
- rules/preflight-rule.md（原 07 预检）

## 工作区与产物

- 工作区：`repos/<REPO>/`（拉取的源码、.auto-bak 备份）
- 产物：`data/assets/engineering/<REPO>/`（readme-parse.json、summary、dev-log、change-log、deploy-log、report）
