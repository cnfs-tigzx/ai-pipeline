# P3 · 二次开发 + 代码标识替换 + Logo 替换（secondary-dev-logo）

> 五大阶段之 P3。触发：功能新增/修改/优化/缺陷修复（A），或品牌化替换（B），或两者同时。
> 工作根目录：/Users/tigzx/workspace/ai-pipeline
> 全局约束：00-base-general.md（确认策略 §1.1 / 备份回滚 §1.3 / 日志 §1.4）；MCP → 04-mcp-control-rule.md
> 引用规则：05-secondary-dev-rule.md（§5.x = P3-A 二次开发；§6.x = P3-B 标识与 Logo 替换）

**输入**：{REPO}、{BRAND}、{DEPLOY_MODE}、需求描述/替换范围
**前置**：P1 已完成（repos/{REPO}/ 在本地，{DEPLOY_MODE} 已判定）

## A. 源码二次开发（规则 §5）

⚠️ 确认点（2 个）：执行计划确认 + 服务重启确认

1. 需求解析 → 影响面分析（模块/文件清单/依赖关系）→ 输出【二次开发执行计划】→ **等待确认**（高危）
2. 备份待修改文件 → `repos/{REPO}/.auto-bak/{时间戳}/dev/`（搜索边界/跳过目录见 §5.1）
3. 按计划逐文件修改
4. 编译校验（§5.2-3）：docker 模式前端 build+后端编译；native 模式 `npm run build` / `go build` / `python -m py_compile`；❌ 失败 → 从备份自动回滚
5. 服务重启验证（§5.2-4）：docker 仅重建受影响 service（可复用 `scripts/rebuild-deploy.sh` 或 `./scripts/one-key.sh restart`）→ **等待确认**（高危）；native kill 旧进程 → 重建 → 重启 → 记录新 PID
6. 功能验证：playwright 访问页面或 API 测试
7. 产物：`output/{REPO}-dev-log.md`（需求/影响面/修改清单/逐文件 diff/编译校验/验证结果/备份路径）；report 追加章节 10；task-log 追加

## B. 代码标识替换 + Logo 替换（规则 §6）

**变更范围**（§6.1 统一黑白名单）：
- ✅ 替换：页面标题、导航栏、页脚、弹窗、水印、Svg 内文字、前端静态文案、swagger 页面标题、Logo 图片(png/jpg/webp/svg/ico)、favicon/app icon/PWA icon、img alt
- ❌ 排除：包名、接口路由、数据库字段、git 标识、环境变量名、localStorage key、CLI 名、HTTP header、JWT aud、i18n key

### B-1 文字标识替换（§6.2）⚠️ 确认点：执行计划 + 双清单

1. 输出【变更执行计划】（检索关键词、目标文件类型、黑白名单）→ **等待确认**（高危）
2. 双重检索：文本检索（覆盖 ✅ 文件类型）+ 品牌名图片文件名检索 → 输出①待修改文本清单 ②Logo 引用点位清单 → **等待确认**（高危）
3. 备份 → `repos/{REPO}/.auto-bak/{时间戳}/`
4. 执行替换：i18n 专项仅替换 value 保护 key（先在备份副本干跑校验，替换后品牌名应仅残留在 key 中）；`<img alt="OldBrand">` alt 同步替换为 {BRAND}
5. → 执行 B-3 构建发布

### B-2 Logo 图片替换（§6.3）

**Logo 源**：`assets/tigzx-logo/`

1. 输出替换执行计划；扫描 repos/{REPO}/ 所有 Logo/brand/icon/watermark 图片及引用 → 待替换清单
2. 备份 → `repos/{REPO}/.auto-bak/{时间戳}/logo/`
3. 替换（保持原路径原文件名覆盖）：png/ico 直接覆盖；svg 改内部文本或整体替换；jpg/webp 转 {BRAND} Logo 同格式覆盖；组件 import 改指向
4. → 执行 B-3 构建发布

### B-3 构建发布（§6.4）⚠️ 确认点：重建/重启

1. 编译校验：❌ 失败 → 自动回滚（从备份恢复全部文件；docker 模式恢复上一版本镜像）
2. docker 仅重建受影响 service（可复用 scripts/rebuild-deploy.sh）→ **等待确认**（高危）；native kill 旧进程 → 重建 → 重启 → 记录新 PID
3. playwright 截图验证：顶部栏、侧边栏、登录页、首页 Logo、页面文字、标题、导航栏、页脚、弹窗
   - 登录策略：需登录时注册临时账号（brandtest@{BRAND}.com），验证后清理
   - swagger 容错：页面 401/403 时验证源码层（docs/swagger.json info.title、main.go @title）
4. 产物：`output/{REPO}-change-log.md` + `output/{REPO}-logo-change-log.md`；report 追加章节 11；task-log 追加

## 使用示例

```
执行 P3（secondary-dev-logo），参数：
{REPO} = WeKnora
{BRAND} = Tigzx
{DEPLOY_MODE} = docker
需求 A（二次开发）：新增用户导出功能，支持 CSV 导出用户列表
需求 B（品牌替换）：Logo 图片、页面标题、导航栏、页脚、弹窗、swagger 标题
```
