# tigzx-dicom 部署知识文档

生成时间：2026-11-06 · 来源：repos/tigzx-dicom/README.md + 源码结构扫描 · 解析原始数据：readme-parse/tigzx-dicom.json

## 一、项目简介

TIGZX DICOM 影像工作台：面向 DICOM 医学影像的标注平台，支持二维标注与具备空间信息序列的三维联动。2026-11-04 起实现免登录的患者/指标影像列表与独立上传记录。当前为**本机单后台模式**：相同工作目录进程锁阻止重复启动，不允许多后台部署；结果库可供其他系统只读检索。

## 二、技术栈

| 层 | 技术 |
|----|------|
| 后端 | Java 17 · Spring Boot 3.5.8 · MyBatis-Plus 3.5.15 · dcm4che-core 5.33.0 · mysql-connector-j · H2（仅测试） |
| 前端 | Vue 3.5.43 · Vite 7 · TypeScript 5.9 · Element Plus 2.14.7 · @cornerstonejs/core+tools+dicom-image-loader 5.11.6 · vitest |
| 数据库 | StarRocks 4.1.4（唯一运行依赖数据库，FE MySQL 兼容协议端口 9030，不依赖 MySQL 服务） |

## 三、依赖清单（运行时）

- JDK 17 + Maven（后端编译与启动）
- Node.js + npm（前端依赖安装与 dev/build）
- StarRocks 4.1.4 实例（127.0.0.1:9030，库 tigzx_dicom，root/Local12345#）
- 建表 SQL：docs/sql/starrocks-business.sql（业务库）+ docs/sql/starrocks.sql（结果库）——**docs/ 目录未同步本地，待用户提供**

## 四、启动命令

### 后端（工作目录必须为 backend，配置按此加载）

```bash
cd backend && mvn spring-boot:run
```

生产方式：打包后复制 JAR 到独立运行目录，在 backend 工作目录执行 `java -jar <独立副本绝对路径>`。

### 前端

```bash
cd frontend && npm ci
npm run dev -- --host 0.0.0.0
```

package.json dev 脚本固定 `vite --host 0.0.0.0 --port 5173 --strictPort`；README 示例 `--host 192.168.180.1` 为作者局域网地址，本机可用 0.0.0.0 或本机 IP 替代。

### 访问地址

- 前端工作台：http://127.0.0.1:5173/（示例带参 http://127.0.0.1:5173/?projectId=100091&patientId=100078）
- 后端 API：http://127.0.0.1:8080（前端 /api 代理指向此）

## 五、构建方式

| 目标 | 命令 |
|------|------|
| 后端测试 | mvn -f backend/pom.xml test（自动测试用隔离 H2，不碰 StarRocks） |
| 前端测试 | npm --prefix frontend test |
| 前端构建 | npm --prefix frontend run build（vue-tsc --noEmit && vite build） |

## 六、配置项（backend/application.yml，唯一运行配置，gitignore）

| 配置 | 当前值 | 说明 |
|------|--------|------|
| server.port | 8080 | 绑定 127.0.0.1 |
| spring.datasource.url | jdbc:mysql://127.0.0.1:9030/tigzx_dicom | 9030 为 StarRocks MySQL 协议，非 MySQL |
| spring.datasource.username/password | root / Local12345# | StarRocks 凭据，勿提交文档 |
| dicom.source-root | /Users/sunmingze/codeProject/data/dicom/source | **原作者路径，本机不存在，须改** |
| dicom.local-root | /Users/sunmingze/codeProject/data/dicom/local | **原作者路径，本机不存在，须改** |
| research.core-base-url | http://127.0.0.1:7120 | 研究核心服务，本机未部署，待验证是否可选 |
| 前端 DICOM_API_TARGET | http://127.0.0.1:8080 | frontend/.env.local 与 .env.development.local |

## 七、已知坑

1. **进程锁**：相同工作目录进程锁阻止重复启动；不要部署多个后台或让其他系统写业务库
2. **建表前置**：新环境先在 StarRocks 手动执行两个建表脚本；旧 mysql*.sql 仅历史参考，不能用于当前 StarRocks
3. **9030 语义**：StarRocks FE MySQL 协议端口，保留 JDBC 驱动不代表连接 MySQL
4a. **建表入口（2026-11-07 已执行）**：starrocks-business.sql + starrocks.sql（当前完整入口，含全部增量列）；mysql*.sql 不可用于 StarRocks；2026xxxx-*.sql 仅为旧库增量迁移；tigzx_dicom 现有 9 表 + 4 视图
4. **上传语义**：必须传 projectId+patientId（可选 indicatorId）；重复 DICOM UID 不合并记录、不校验患者归属；每次上传产生独立 imageId
5. **文件存储**：DICOM 文件仅存磁盘 `dicom.source-root/.uploads`，不进数据库；旧影像不自动进入新范围列表（需执行迁移 SQL，该 SQL 也在缺失的 docs/ 内）
6. **不支持动态影像**
7. **数据目录**：`.runtime/`、`data/` 为 gitignore 运行时目录，本机需自行创建

## 八、部署踩坑清单（P1 实际踩坑实录）

### 8.1 构建网络（Maven）

- **坑**：dcm4che-core 5.33.0 的依赖链引用 `org.weasis.core:weasis-core-img-bom:4.9.0.1`，仅托管于 `raw.github.com/nroduit/mvn-repo`，国内 Connection reset；central 无此包（404）
- **解**：~/.m2/settings.xml 配 mirror（按仓库 id 精确 mirrorOf=nroduit-mvn-repo-master）→ gh-proxy.com 代理 raw.githubusercontent；central → 阿里云 public 加速
- **验证残留**：mvn 下载时 dcm4che.org 仓库的 cached not-found 警告无害；`find ~/.m2 -name '*.lastUpdated' -delete` 清缓存标记

### 8.2 brew 安装中断

- **坑**：brew install 执行中被 kill（pkill）→ maven 的 Cellar 目录损坏但 opt 符号链接残留（dangling），后续 install 报 "Bottle destination already exists"
- **解**：`brew reinstall maven` 重建（keg marked linked 警告无害）
- **教训**：kill brew 后必须用 reinstall 而非 install

### 8.3 StarRocks 镜像拉取（核心踩坑）

- **现象**：docker.io 直连超时；daemon mirrors（1ms/daocloud/rat.dev 等）对该镜像卡 "Pulling fs layer" 或深度限速（123→580→130KB/s 波动）；免费加速站对大文件按流量限速
- **关键弯路**：1ms.run 的 blob 307 重定向至 cloudfront-docker-cf.mrs.1ms.run，**签名 URL 会过期**（Expires 参数），过期后 Range 请求被忽略（200 全量），表现为 aria2 "Invalid range header"——新签名前几次请求可能也不稳定
- **最终解**：**发现系统代理 127.0.0.1:7892 → curl -x 代理直连 registry-1.docker.io：3.2MB/s 且完整支持 Range（206）**→ aria2 -x16 -s32 全部 9 blob 逐个 sha256 校验 → OCI layout tar → docker load
- **教训**：排查镜像拉取问题时优先检查本机代理（scutil --proxy），代理直连官方源往往秒杀一切加速镜像站

### 8.4 StarRocks on OrbStack

- **坑**：OrbStack VM 默认 vm.max_map_count=262144，低于 StarRocks BE 官方建议 2000000
- **解**：`docker run --rm --privileged busybox sysctl -w vm.max_map_count=2000000`（所有容器共享内核，即时生效）；**OrbStack VM 重启后回落**，需幂等补设（已内置 one-key.sh start / /tmp/starrocks-setup.sh）
- orb CLI 的 machine 概念不适用于主 docker VM（"no machines found"）

### 8.5 StarRocks allin1 初始化

- FE 启动快（9030 端口 ~10s 就绪），root 默认无密码；`SET PASSWORD FOR 'root' = PASSWORD('...')` 设置后必须用新密码重连验证
- 容器内自带 mysql client，可直接 exec 初始化；库 tigzx_dicom 与 application.yml 数据源对应

### 8.6 one-key.sh native 进程管理

- **坑 1**：mvn spring-boot:run 的 java 是 mvn 子进程，kill mvn 会遗留孤儿 java 继续占 8080
- **解**：stop 按「端口 lsof → PID 文件 → pkill spring-boot:run」三重清理 + 等待端口释放（连续 3 次空闲判定）+ SIGKILL 兜底
- **坑 2**：Spring Boot SIGTERM 后优雅关闭需数秒，stop 后立即 status/start 会看到旧进程残留（000/200 闪变），等待循环必须覆盖此窗口
- **坑 3**：npm run dev（vite）进程树 npm→sh→node 三层，PID 文件记录的是 npm；端口监听者是 node 孙进程，清理逻辑必须同时覆盖
- **坑 4（操作层）**：并发执行多个含长 sleep 的运维命令会互相打架（stop 杀掉刚 start 的进程）；运维命令务必原子化串行执行
