# 源码二次开发与品牌替换规则（05-secondary-dev-rule）

> 服务阶段：P3（二次开发任务 + 代码标识替换 + Logo 替换）。提示词：workflows/P3-secondary-dev-logo.md。
> §5.x = P3-A 源码二次开发；§6.x = P3-B 代码标识与 Logo 替换。
> 确认策略、备份回滚、日志规范见 00-base-general.md。

## 5.0 P3-A 需求接收与规划

1. 接收二次开发需求描述（功能新增/修改/优化/缺陷修复）
2. **影响面分析**：检索相关源码文件，输出涉及模块、文件清单、依赖关系
3. 输出【二次开发执行计划】：需求拆解、修改点清单、新增文件、预估影响范围 → 等待确认（高危）

## 5.1 P3-A 前置约束

**搜索边界**：仅 `repos/{REPO}/` 源码目录
**跳过目录**：.git、node_modules、dist、build、docker 构建产物、流水线产物(knowledge/readme-parse/output)

## 5.2 P3-A 执行流程

1. 备份所有待修改文件 → `repos/{REPO}/.auto-bak/{时间戳}/dev/`
2. 执行代码修改（按计划逐文件实施）
3. **编译校验**：
   - docker 模式：前端 build + 后端编译
   - native 模式：`npm run build` / `go build` / `python -m py_compile`
   - ❌ 失败 → 自动回滚：从备份恢复全部文件
4. **服务重启验证**：
   - docker 模式：仅重建受影响 service → `docker compose build <service>` → `docker compose up -d <service>`（可复用 scripts/rebuild-deploy.sh），等待确认（高危）
   - native 模式：终止旧进程（`kill <PID>`）→ 重新构建 → 重新启动 → 记录新 PID
5. **功能验证**：playwright 访问页面或 API 测试，验证需求实现效果
6. **变更清单**：记录每个文件变更（路径、原始内容片段、修改后内容、备份路径、变更原因）

## 5.3 P3-A 产物输出

| 产物 | 路径 | 内容 |
|------|------|------|
| 二次开发变更日志 | `output/{REPO}-dev-log.md` | 需求描述、影响面分析、修改清单、逐文件 diff、编译校验、验证结果、备份路径 |
| 综合报告更新 | `output/{REPO}-report.md` | 追加章节 10 |
| 任务日志 | `output/task-log.md` | 追加 |

## 6.1 P3-B 前置约束

**检索范围**（统一黑白名单）：
- ✅ 检索：vue/ts/js/html/svg/json、静态图片(png/jpg/webp/svg/ico)、前端常量、后端配置、swagger 文案、页面 title、导航栏文字、favicon/app icon/PWA icon、logo/brand/icon/watermark 资源
- ❌ 跳过：README、docs、.git、node_modules、dist、build、docker 构建产物、流水线产物(knowledge/readme-parse/output)

**搜索边界**：仅 `repos/{REPO}/` 源码目录

**文本替换逻辑**：全局区分大小写，精准替换；避免误替换变量名、包名、接口路由、数据库字段、git 标识、环境变量名、localStorage key、CLI 名、HTTP header、JWT aud、i18n key

**i18n 多语言替换专项**：
- 仅替换 value 字符串中的品牌名，保护 key 不被替换
- 执行前先干跑校验：在备份副本上试跑，确认 key/token 保护生效
- 校验残留：替换后每个 i18n 文件中品牌名应仅残留在 key 中

**变更清单**：每个文件变更记录文件路径、原始内容片段、修改后内容、备份路径

## 6.2 P3-B 文字标识替换流程

1. 输出【变更执行计划】：检索关键词、目标文件类型、黑白名单 → 等待确认（高危）
2. **双重检索**：
   - 文本检索：全局搜索品牌名文本，覆盖所有 ✅ 文件类型
   - 图片文件名检索：搜索品牌名命名的图片文件（如 `brand*.png`、`*brand*.ico`）
   - 输出两类清单：① 待修改文本清单 ② Logo 图片引用点位清单 → 等待确认（高危）
3. 备份所有待修改文件 → `repos/{REPO}/.auto-bak/{时间戳}/`
4. 执行文本替换
   - **Logo alt 文字同步替换**：遇到 `<img alt="OldBrand">` 时同步替换 alt 文字为 {BRAND}
5. → 执行 §6.4 构建发布流程

## 6.3 P3-B Logo 图片替换流程

**Logo 源目录**：`assets/tigzx-logo/`

1. 输出 Logo 替换执行计划：检索图片类型、目录范围、替换策略
2. 扫描 `repos/{REPO}/` 所有 Logo/brand/icon/watermark 图片及引用文件 → 输出待替换清单
3. 备份所有待替换文件 → `repos/{REPO}/.auto-bak/{时间戳}/logo/`
4. **执行替换**（保持原路径、原文件名覆盖）：
   - png/ico：直接覆盖
   - svg：修改内部文本节点，或替换整个 svg 文件
   - jpg/webp：将 {BRAND} Logo 转换为原文件同格式后覆盖
   - 组件 import 的图标：替换 import 指向的资源文件
5. → 执行 §6.4 构建发布流程

## 6.4 P3-B 构建发布流程

1. **编译校验**：
   - docker 模式：前端 build + 后端编译
   - native 模式：`npm run build` / `go build` 等
   - ❌ 失败 → 自动回滚：从备份恢复全部文件；docker 模式恢复上一版本镜像
2. **构建/重启**：
   - docker 模式：**仅重建受影响的 service**（如仅前端改动 → `docker compose build frontend`，可复用 scripts/rebuild-deploy.sh），重启服务 → 等待确认（高危）
   - native 模式：终止旧进程 → 重新构建 → 重新启动 → 记录新 PID
3. **健康探测**：
   - playwright 访问 Web 页面，截图验证替换效果
   - **登录策略**：页面需登录时，注册临时测试账号（如 `brandtest@{BRAND}.com`），验证完成后清理
   - **swagger 验证容错**：swagger 页面返回 401/403 时，验证源码层面替换（`docs/swagger.json` info.title、`main.go` @title annotation）即可
   - 文字替换：校验页面文字、标题、导航栏、页脚、弹窗
   - Logo 替换：截图验证顶部栏、侧边栏、登录页、首页 Logo

## 6.5 P3-B 产物输出

| 产物 | 路径 | 内容 |
|------|------|------|
| 代码变更日志 | `output/{REPO}-change-log.md` | 变更概要、待修改清单、逐文件 diff、排除清单、编译校验、发布、验证、备份、结论 |
| Logo 变更日志 | `output/{REPO}-logo-change-log.md` | 替换清单、备份路径、验证截图引用 |
| 综合报告更新 | `output/{REPO}-report.md` | 追加章节 11 |
| 任务日志 | `output/task-log.md` | 追加 |
