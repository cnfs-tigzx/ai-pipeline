# tigzx-dicom 二次开发知识库：TotalSegmentator AI 分割集成

> 归档时间：2026-11-07 · 阶段：P3 二次开发 · 状态：已完成并实测通过
> 关联文档：output/tigzx-dicom-dev-log.md（变更日志）、output/tigzx-dicom-report.md（章节 10）、
> repos/tigzx-dicom/plugins/totalsegmentator/README.md（插件使用）

## 1. 需求与结论

将 `repos/TotalSegmentator-master`（Python/PyTorch，CT/MR 影像 117 类解剖结构自动分割，Apache-2.0）
的能力集成进 `repos/tigzx-dicom`（Java 17 + Spring Boot 3.5.8 + MyBatis-Plus + StarRocks / Vue 3 +
Element Plus + Cornerstone3D 的 DICOM 标注工作台）。

最终形态：**插件微服务 + 源码改造**混合集成——TotalSegmentator 以 editable 源码方式装进独立
FastAPI 服务（Python 3.11 venv），Java 后端新增分割任务编排（任务表 + 状态轮询 + 结果落盘），
前端工作台新增「AI 分割」面板；分割掩膜复用前端既有体素标注体系，AI 节点与手工涂抹节点同构
（可继续编辑、可撤销、走统一保存校验）。

## 2. 架构设计思路（决策链）

### 2.1 为什么是插件微服务（而不是源码嵌入或 CLI 进程调用）

| 方案 | 结论 | 理由 |
|------|------|------|
| Java 进程内嵌 Python | 不可行 | torch/nnunetv2 是完整 Python ML 生态（数 GB 依赖），无法嵌入 JVM |
| Java ProcessBuilder 调 CLI | 放弃 | 进程管理、错误处理、进度反馈都要手搓；长任务 stdout 阻塞风险；无法承载多接口（健康检查/类清单/掩膜下载） |
| **独立 HTTP 插件服务** | **采用** | 职责清晰（AI 算力与主服务隔离）；官方已有服务化先例（MCP server 证明该形态被上游认可）；失败隔离（插件崩溃不影响标注主流程）；未来可容器化/换 GPU 机器部署 |

目录约定：插件源码进主项目仓库 `repos/tigzx-dicom/plugins/totalsegmentator/`（版本随项目走），
Python venv 与运行产物（workspace/）被 .gitignore 排除。

### 2.2 数据流与任务编排

```
前端「AI 分割」面板（SegmentationPanel.vue）
  │ POST /api/segmentation {studyId, seriesUid, task, fast}
  ▼
Java SegmentationServiceImpl（单实例互斥 AtomicBoolean + 单线程 coordinator）
  │ 1. 按 seriesUid 查实例（排序：slicePosition→InstanceNumber→SOP）
  │ 2. requireUniformGeometry：DB 元数据校验序列几何一致性（前置拦截脏数据）
  │ 3. dicom_segmentation_job 表落 PENDING；resolveImage 逐实例解析绝对路径（size/mtime 校验）
  ▼
插件 FastAPI（127.0.0.1:7860，单 worker ThreadPoolExecutor）
  │ POST /segment {dicom_files: [...], task, fast, device:"auto"}
  │ 1. series_purifier.purify：众数尺寸/方向过滤 + 法向投影等间距校验 + 位置去重
  │    有剔除 → 复制保留切片构建净化目录（TotalSegmentator 只接受目录输入）
  │ 2. SimpleITK 读净化序列 → LPS 参考网格（origin/axisX/Y/Z）
  │ 3. totalsegmentator(input=净化目录, output_type="dicom_seg", fast, device=mps/cpu)
  │ 4. dicomseg_adapter：DICOM-SEG 逐帧还原 → 每类布尔体素 → VoxelMask JSON（runs 游程）
  │ 5. 状态内存 + workspace/{job}/status.json 双写
  ▼
Java 轮询 GET /jobs/{id}（3s 间隔，30min 超时）
  │ COMPLETED → 逐类 GET /jobs/{id}/masks/{name}（envelope JSON）
  │ 落盘 data/segmentation/{jobId}/{class}.json + 类清单（体素数/体积mm³/maskUrl）写回任务表
  ▼
前端轮询 GET /api/segmentation/{jobId} → 结果列表（勾选）→
  载入所选掩膜（逐类 GET envelope）→ aiSegmentation.buildAiFinding → Finding 入 draft
  → 与手工涂抹节点同构渲染/编辑/保存
```

### 2.3 关键设计决策

1. **输出走 DICOM-SEG 而非 NIfTI 手工对齐**：TotalSegmentator 内部 dicom2nifti(reorient=true)
   的 NIfTI affine 存在 y 轴翻转约定，与 DICOM LPS 网格的手工矩阵对齐不可靠（实测 affine 与
   期望矩阵不符、数值差无简单翻转解释）。改用官方 `output_type="dicom_seg"`（highdicom，
   内部已完成 NIfTI→DICOM 几何转换），再按**帧级 ImagePositionPatient** 精确匹配参考网格层索引
   （0.25 体素容差），全程不猜 affine——这是本项目最重要的技术决策。
2. **掩膜协议复用前端既有 VoxelMask 契约**：患者空间 LPS、dimensions=[columns, rows, slices]、
   runs 为 x-fastest 三维线性游程（index = x + nx·y + nx·ny·z）、世界坐标 = origin + x·axisX +
   y·axisY + z·axisZ。SimpleITK 读 DICOM 序列天然 LPS 且与该契约逐项吻合（7 项几何校验验证）。
   好处：AI 掩膜节点与手工涂抹节点同构，渲染/编辑/撤销/保存校验全部复用，零新增渲染代码。
3. **几何一致性前置拦截（与前端同一标准）**：前端 volumeGeometry.validateVolumeGeometry 已确立
   "拒绝混合几何/不规则间距而非静默扭曲"原则。Java 端提交分割前用实例索引元数据（无需读文件）
   校验同尺寸/同方向/同间距/等层距；区分两类业务错误：SEGMENTATION_SERIES_INVALID（定位像
   污染等几何不一致）、SEGMENTATION_NO_SPATIAL（Secondary Capture 无患者空间信息）。
4. **envelope 全接口统一**：项目所有 /api 接口返回 RespVO{code,message,data}，前端 api() 统一
   解析。掩膜接口初版返回裸 JSON 导致前端解析失败（见 8.4），最终统一 RespVO<JsonNode>。
5. **单并发保护**：Java（AtomicBoolean + SEGMENTATION_BUSY）与插件（max_workers=1）双层单
   任务互斥，保护 24G 内存的 Mac Mini（torch 推理内存峰值大）。

## 3. 核心协议契约（VoxelMask，前后端共同遵守）

- `dimensions: [columns, rows, slices]`（dim0 对齐 InstanceEntity.columnsCount）
- `origin`：第 0 层 ImagePositionPatient（LPS）
- `axisX = rowCosine × columnSpacing`、`axisY = columnCosine × rowSpacing`（DICOM IOP 前 3 值
  为行方向余弦、后 3 值为列方向余弦）
- `axisZ`：沿切片法向的层步进向量（origin + z·axisZ 必须逐层命中每张切片 IPP，后端
  SegmentationUtil.validate 强校验）
- `runs`：有序游程 {start, length}，全局线性索引 x-fastest（index = x + nx·y + nx·ny·z）
- 体积 = 体素数 × |det(axisX, axisY, axisZ)|（mm³，与 Java volumeMm3 公式一致）
- 参考实现：前端 voxelSegmentation.voxelWorld / segmentationGeometry.maskCenter；插件
  mask_adapter.geometry_from_image / runs_from_flat

## 4. 交付文件清单

### 插件（Python，repos/tigzx-dicom/plugins/totalsegmentator/）

| 文件 | 职责 |
|------|------|
| server.py | FastAPI：GET /health、POST /segment（异步任务）、GET /jobs/{id}、GET /jobs/{id}/masks/{name}；全部异常分支写 traceback 日志 |
| mask_adapter.py | SimpleITK 读序列（GDCM 按文件头发现，兼容无扩展名）；VoxelMask 几何头；x-fastest 游程；affine 组装与校验 |
| series_purifier.py | 众数几何净化 + 等间距/位置校验；SeriesPurityError 业务错误；净化目录构建 |
| dicomseg_adapter.py | DICOM-SEG 逐帧读取还原：SegmentLabel 类名 + PerFrame IPP 匹配层索引 |
| tests/test_mask_adapter.py（6 用例）、tests/test_series_purifier.py（5 用例） | 协议与净化单测 |
| tests/verify_geometry.py | 真实序列 7 项几何校验（LPS vs DICOM tag） |
| tests/verify_alignment.py | 端到端 6 项对齐校验（Java instance 元数据 vs 掩膜） |
| tests/replay_user_flow.py、tests/replay_poll.py | 完整用户流模拟（走 vite 代理 + envelope） |
| tests/add_uid.py、tests/diag_*.py | 匿名化样例补 UID、affine/上传数据诊断 |
| README.md | 安装/启动/接口/协议说明 |

### Java 后端（backend/src/main/java/com/tigzx/dicom/）

| 文件 | 职责 |
|------|------|
| core/enums/SegmentationStatus.java | PENDING/RUNNING/COMPLETED/FAILED |
| core/enums/ExceptionEnum.java | 新增 SEGMENTATION_BUSY、SEGMENTATION_PLUGIN_UNAVAILABLE、SEGMENTATION_SERIES_INVALID、SEGMENTATION_NO_SPATIAL |
| modular/entity/SegmentationJobEntity.java | 任务持久化（status/studyId/seriesUid/seriesDirectory/task/fast/classesResult/errorMessage） |
| modular/mapper/SegmentationJobMapper.java | MyBatis-Plus BaseMapper |
| config/SegmentationProperties.java | segmentation.* 配置（plugin-base-url、mask-root、轮询间隔、超时、默认 task、maxClasses） |
| modular/model/dto/SegmentationRequestDTO.java | studyId+seriesUid 必填；task/roiSubset 白名单正则 |
| modular/model/vo/SegmentationJobVO.java、SegmentationClassVO.java | 响应 VO（类清单含 voxels/volumeMm3/maskUrl） |
| modular/service/SegmentationService.java、impl/SegmentationServiceImpl.java | 编排核心（见 2.2） |
| modular/controller/SegmentationController.java | 3 个接口，掩膜返回 RespVO<JsonNode> |
| src/test/resources/schema.sql | H2 表 dicom_segmentation_job |
| src/test/java/com/tigzx/dicom/SegmentationIntegrationTest.java | 4 用例（内嵌 HttpServer 模拟插件：全链路/混合几何拒绝/序列不存在/非法参数） |

### 前端（frontend/src/）

| 文件 | 职责 |
|------|------|
| SegmentationPanel.vue | 对话框：序列/任务选择、提交、轮询（2s）、常驻任务状态行、结果勾选列表、载入 |
| aiSegmentation.ts | 纯函数：AiMaskItem/SegmentationJob/SegmentationClass 类型、maskSliceIndex（中心层定位）、buildAiFinding（掩膜→空间 SEGMENTATION 节点） |
| aiSegmentation.test.ts | 3 用例 |
| App.vue（修改） | 异步引入面板 + header「AI 分割」按钮 + applyAiMasks（批量 buildAiFinding → change 入 draft） |
| .gitignore（修改） | 排除插件 .venv/workspace/__pycache__、.pytest_cache |

### SQL 与配置

| 文件 | 职责 |
|------|------|
| data/test/sql/20261107-segmentation-job.sql | StarRocks 建表（已执行） |
| backend/application.yml | segmentation 配置块（plugin-base-url=http://127.0.0.1:7860、mask-root） |

## 5. 接口协议速查

| 接口 | 请求/响应要点 |
|------|--------------|
| POST /api/segmentation | {studyId, seriesUid, task?, fast?, roiSubset?, maxClasses?} → RespVO<SegmentationJobVO>；同步校验失败返回 409 + 中文业务错误 |
| GET /api/segmentation/{jobId} | RespVO<SegmentationJobVO>：status/classes[{name,voxels,volumeMm3,maskUrl}]/errorMessage |
| GET /api/segmentation/{jobId}/masks/{class} | RespVO<VoxelMask JSON>（envelope 内联，几十至百 KB/类） |
| POST /segment（插件直连） | {dicom_files 或 dicom_dir, task, fast, device, roi_subset?, max_classes} → {job_id, status}；Java 为唯一调用方 |
| GET /health（插件直连） | {status, version, torch, mps, default_device} |


## 6. 环境搭建（含全部陷阱的正确姿势）

### 6.1 Python 插件环境

```bash
cd repos/tigzx-dicom/plugins/totalsegmentator
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python \
  -e /Users/tigzx/workspace/ai-pipeline/repos/TotalSegmentator-master \
  fastapi 'uvicorn[standard]' pydicom highdicom
.venv/bin/python -m uvicorn server:app --host 127.0.0.1 --port 7860
```

- 系统默认 python3 是 3.15（torch 不支持），必须 venv 锁 3.11
- torch 2.15.0（arm64 wheel 自带 MPS）；首次分割自动下载权重约 1.5GB → ~/.totalsegmentator
- 插件进程需常驻；重启后已完成任务可经 workspace/{job}/status.json 恢复查询

### 6.2 Java 后端（JDK 17 陷阱）

- homebrew 默认 openjdk 已升 27 → Lombok 注解处理静默失败（报"找不到符号 getSourceRoot"
  等连锁错误，实际是 getter 未生成）
- 必须 JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home
- one-key.sh（v3）已内置该 JAVA_HOME；手动 mvn 时必须 export

### 6.3 测试数据

- 可分割：data/dicom/source/ai-ct-demo-uid（20 层 512×512 轴位 CT，2mm 层距，带完整几何；
  源自 TotalSegmentator example_ct_dicom + tests/add_uid.py 补 UID；备份副本在
  /Users/tigzx/workspace/ai-pipeline/data/dicom-demo/ai-ct-demo-uid）
- 不可分割（学习样本）：TEST/CLD-740527-20250814 的 Embolism 系列是 Secondary Capture
  （SOPClassUID 1.2.840.10008.5.1.4.1.1.7，无 IOP/IPP/PixelSpacing），仅能 2D 标注

## 7. 测试体系与验收基线

| 层级 | 工具/入口 | 基线 |
|------|----------|------|
| 插件协议单测 | .venv/bin/python -m pytest tests/ | 11/11 |
| 真实序列几何 | tests/verify_geometry.py <dir> | 7/7 PASS |
| 端到端几何对齐 | tests/verify_alignment.py <jobId> [class] | 6/6 PASS |
| 完整用户流模拟 | tests/replay_user_flow.py | 提交→轮询→载入全部掩膜，runs 与清单逐类一致 |
| 后端全量 | mvn test（JAVA_HOME=openjdk@17） | 45/45 |
| 前端全量 | npm test + npm run build | 114/114 + 构建成功 |
| 手工验收 | 前端上传 ai-ct-demo-uid → AI 分割 → 载入 → 保存 → 刷新仍在 | 页面由用户验收 |

## 8. 踩坑全记录（按时间序，含判定方法）

### 8.1 dicom2nifti 的 NIfTI 翻转不可靠 → 改 DICOM-SEG

- 现象：插件首跑"geometry mismatch: affine mismatch"，nifti y 轴步进 +0.9766 与期望 -0.9766
  符号相反、origin 差值无简单翻转解释
- 判定：diag_affine.py 对比 dicom2nifti(reorient=true) affine 与 LPS_TO_RAS@A_sitk
- 解决：弃手工 affine 对齐；用官方 output_type=dicom_seg + 帧级 IPP 匹配（零猜测）

### 8.2 官方测试 DICOM 匿名化无 UID

- 现象：扫描 indexedCount=0 / skippedCount=20
- 判定：pydicom 查 Study/Series/SOP UID 全空串
- 解决：tests/add_uid.py 生成带 UID 副本（不改上游仓库）

### 8.3 homebrew openjdk 27 导致 Lombok 静默失效

- 现象：编译报大量"找不到符号 getSourceRoot"/"无法将枚举构造器应用到给定类型"
- 判定：错误涉及全部 Lombok 类；java -version 为 27
- 解决：export JAVA_HOME=openjdk@17；one-key.sh 已内置

### 8.4 掩膜接口缺 envelope 导致前端静默失败

- 现象：用户点"载入所选掩膜"无反应；Console: api.ts:26 请求失败
- 判定：DevTools 报错栈 + 掩膜接口返回裸 JSON（RespVO 缺失）
- 解决：RespVO<JsonNode> 包装；同时前端结果列表另有字段名 bug（见 8.5）

### 8.5 前后端字段命名不一致（camelCase vs snake_case）

- 现象：结果列表渲染 TypeError（undefined.toFixed）→ UI 冻结"分割完毕无反应"
- 判定：后端 VO volumeMm3（camelCase）vs 前端接口 volume_mm3
- 解决：统一 volumeMm3 + ?? 容错；经验——跨语言字段映射必须在集成测试中用真实 JSON 断言，
  而非两端各自定义类型

### 8.6 Integer 引用比较（==）导致干净序列被误拒

- 现象：几何校验上线后，真实 512×512 序列被 SEGMENTATION_SERIES_INVALID 误拒；
  测试 fixture（16×16）却通过
- 判定：Integer 超出 -128~127 缓存区，!= 比较对象引用；fixture 尺寸在缓存区内侥幸通过
- 解决：改 .equals()；fixture 尺寸改 200（缓存区外）固化回归

### 8.7 Secondary Capture 序列无空间信息直达插件

- 现象：用户对截图类序列（Embolism SC）分割报裸 IndexError（插件内部）
- 判定：21 层 slicePosition 全 0（无 IOP/IPP 回退特征）；任务创建于校验部署前为历史任务
- 解决：SEGMENTATION_NO_SPATIAL 精准报错 + 插件全异常分支补 traceback 日志
  （此前任务失败完全静默，无日志可查）

### 8.8 StarRocks 建表需手动执行

- 现象：POST /api/segmentation 报 BadSqlGrammarException
- 解决：docker exec -i starrocks-tigzx mysql ... < data/test/sql/20261107-segmentation-job.sql
  （新表必须随代码同步执行；H2 schema.sql 仅覆盖测试）

## 9. 使用指南（用户操作流）

1. 上传：工作台（projectId+patientId 入口）选择含 CT 序列的文件夹上传（要求：带患者空间
   信息、单一几何网格、无定位像混入；Secondary Capture 截图类不支持）
2. 打开影像 → 头部「AI 分割」→ 选序列与任务（total）→ 开始分割（约 10~60 秒/序列，
   MPS 加速；面板有任务 ID 与状态行）
3. 结果列表勾选器官（默认全选非空类）→ 「载入所选掩膜」→ 生成"AI · 类名"节点
4. 可继续手工编辑（涂抹/擦除），节点面板「保存当前节点」持久化到 StarRocks
5. 确认持久化：刷新页面重开影像，标注仍在；掩膜文件在
   data/segmentation/{jobId}/{class}.json

## 10. 遗留约束与后续建议

- 插件常驻管理未纳入 one-key.sh：建议后续以 launchd plist 或容器化托管（含健康检查自愈）
- 权重离线部署：需预下载 ~/.totalsegmentator；内网环境需打通 backend.totalsegmentator.com
  或预置权重
- 商业 license 任务（vertebrae_pp、lung_vessels、body_stats 等）未集成入口，仅开放 Apache
  任务（total 系）
- 后端 listSeries 的 volumeEligible 判定仅检查元数据存在性，未做一致性校验；建议后续与
  requireUniformGeometry 规则对齐，让"不可 3D 重建"的序列在列表阶段即提示
- device 参数默认 auto（MPS 优先）；MPS 出现数值异常时可传 cpu 回退
- 批量分割（多序列排队）、DICOM-SEG/RTSTRUCT 导出、其他 task（心血管/椎体细化）为
  潜在迭代方向

