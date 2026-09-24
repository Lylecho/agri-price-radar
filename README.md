# 菜价雷达 · 项目蓝图（agri-price-radar）

> **唯一事实来源** · 状态: v1 基线 2026-09-24 · 由开发代理持续维护，重大变更先给方案由用户决策。
> 实现与蓝图冲突时：先与用户确认再动手（AGENTS.md 工作流程）。

**《基于 SpringBoot+Vue+Python 的农产品价格监测与短期预测系统的设计与实现》**

## 1. 项目定位

- 农产品批发价格的**行政性监测与预警工具**：走势展示 + 阈值式波动提示 + 短期预测。
- **绝不提供任何买卖建议**；所有预测展示处必须带「预测结果仅供参考」声明。
- 数据源：北京新发地批发市场（`POST http://www.xinfadi.com.cn/getPriceData.html`）。

## 2. 技术栈（锁定，禁止蓝图外引入）

| 模块 | 技术 |
|---|---|
| 采集/算法 | Python 3.10+：requests、APScheduler、pandas、statsmodels、Prophet、PyTorch、scikit-learn |
| 算法服务 | FastAPI + uvicorn（内网，前缀 `/ml`） |
| 主后端 | SpringBoot 3.x + MyBatis-Plus + MySQL 8 + Redis + Spring Security/JWT（JDK17） |
| 前端 | Vue3 + Vite + Element Plus + Axios + Pinia + ECharts（管理端 + 1920×1080 可视化大屏） |
| AI 编排 | Dify（docker compose 自部署）+ DeepSeek API，SpringBoot 经 HTTP 调用 |

## 3. 角色与权限（RBAC，W3 落地）

| 角色 | 能力 |
|---|---|
| ADMIN 超级管理员 | 全部：用户/角色/品类配置/预警阈值/任务管理 |
| DATA_ADMIN 数据管理员 | 采集任务触发与日志、数据查询、预测查看（无用户管理） |

接口层强制校验；前端按角色渲染菜单。双账号预置：admin / dataadmin（初始密码首登强制改）。

## 4. 系统架构与数据流

```
新发地接口 ──(≤1次/秒, UA, 参数化)──▶ APScheduler 定时采集进程(W1)
                                          │ 增量 upsert(唯一约束去重)
                                          ▼
                              MySQL 8 · price_daily(明细)
                                          │ 每日夜间预计算(W1)
                                          ▼
                              predict_result(7天预测) + collect_log(任务日志)
                                          │ 只读快照
        SpringBoot 主后端(W2) ◀───────────┘
        │  {code,msg,data} 统一响应 + JWT
        ├─▶ Vue3 管理端(W3)          ├─▶ 1920×1080 大屏(W5, canvas-night 暗色系)
        ├─▶ FastAPI /ml 实时预测(可选通道, 不可用时主流程不受影响)
        └─▶ Dify+DeepSeek 智能问答(W5)
```

铁律：一切分析与预测基于**已入库快照**，不得在用户请求时现场爬取。

## 5. 数据库设计（DDL）

> W1 起统一以 MySQL 8 为准；SQLite 为开发/降级后端（同一套 DDL 的变体，经 `python/config/db.py` 切换）。

### 5.1 price_daily —— 采集明细（v2，单位治理版）

```sql
CREATE TABLE price_daily (
    id          BIGINT        PRIMARY KEY AUTO_INCREMENT COMMENT '自增主键',
    prod_name   VARCHAR(64)   NOT NULL COMMENT '品名(接口原值, 如 白条猪/散鸡蛋)',
    prod_cat    VARCHAR(64)   NULL     COMMENT '品类(接口原值, 如 蔬菜)',
    low_price   DECIMAL(10,3) NULL COMMENT '最低价',
    high_price  DECIMAL(10,3) NULL COMMENT '最高价',
    avg_price   DECIMAL(10,3) NULL COMMENT '平均价',
    place       VARCHAR(64)   NOT NULL DEFAULT '' COMMENT '产地',
    spec_info   VARCHAR(128)  NOT NULL DEFAULT '' COMMENT '规格',
    unit_info   VARCHAR(16)   NOT NULL DEFAULT '' COMMENT '计价单位: 斤/箱/筐/个',
    pub_date    DATE          NOT NULL COMMENT '发布日期',
    created_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    -- v2(2026-09-24): unit_info 纳入唯一键。v1 曾因箱/斤异单位行互撞覆盖丢数据(鸡蛋教训)
    UNIQUE KEY uk_price (prod_name, pub_date, place, spec_info, unit_info),
    INDEX idx_prod_date (prod_name, pub_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='新发地批发价日度明细';
```

**展示品类 → 代表品名映射（采集探测+单位核查结论，代码内同步维护）：**

| 展示品类 | 代表品名 | 说明 |
|---|---|---|
| 大白菜 | 大白菜 | 精确匹配 |
| 黄瓜 | 黄瓜 | 品类词模糊采集（含小黄瓜等），图表取精确主品名 |
| 西红柿 | 番茄 | 接口无"西红柿"，用户已确认替换 |
| 猪肉 | 白条猪 | 接口"猪肉"仅11条无关品，用户已确认替换 |
| 鸡蛋 | 散鸡蛋 | 箱/筐鸡蛋为整件计价且斤标注被污染，散鸡蛋为纯斤价序列 |

**单位治理规则**：同轴对比仅取「主导单位=斤」的序列；整件价（箱/筐）单独展示或按规格折算；「斤」标注下价格超品类合理区间（如鸡蛋>15元/斤）视为上游错标，隔离告警。

### 5.2 predict_result —— 预测预计算表（W1）

```sql
CREATE TABLE predict_result (
    id            BIGINT        PRIMARY KEY AUTO_INCREMENT,
    category      VARCHAR(32)   NOT NULL COMMENT '展示品类',
    prod_name     VARCHAR(64)   NOT NULL COMMENT '代表品名',
    predict_date  DATE          NOT NULL COMMENT '预测目标日',
    yhat          DECIMAL(10,3) NOT NULL COMMENT '预测均价(元/斤)',
    model         VARCHAR(32)   NOT NULL COMMENT '模型标识, 如 ARIMA(2,1,1)',
    mape_test     DECIMAL(6,3)  NULL COMMENT '测试集MAPE(%)',
    horizon       TINYINT       NOT NULL COMMENT '距最后实测日天数(1-7)',
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_pred (category, predict_date, model),
    INDEX idx_cat_date (category, predict_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='预测预计算(日常展示只读此表)';
```

### 5.3 collect_log —— 采集/计算任务日志（W1）

```sql
CREATE TABLE collect_log (
    id            BIGINT        PRIMARY KEY AUTO_INCREMENT,
    job           VARCHAR(32)   NOT NULL COMMENT '任务名: collect / precompute',
    status        VARCHAR(16)   NOT NULL COMMENT 'SUCCESS / FAILED',
    detail        VARCHAR(1000) NULL COMMENT '摘要(异常/各品类条数等)',
    rows_written  INT           NULL COMMENT '写入/更新行数',
    started_at    DATETIME      NOT NULL,
    finished_at   DATETIME      NULL,
    INDEX idx_job_time (job, started_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='定时任务运行日志';
```

### 5.4 权限、预警与审计（W2 落地）

`sys_user` / `sys_role` / `sys_user_role` 三表已在 W2.1 建好并预置账号（DDL 见 `backend/sql/w2_auth.sql`，BCrypt 存储）：
- 角色：`ADMIN`（超级管理员）/ `DATA_ADMIN`（数据管理员）
- 预置账号（**仅开发环境**）：`admin`/`admin123`、`dataadmin`/`dataadmin123`，首次登录强制改密（顺延）
- 仍预留：`op_log`（操作审计）

**预警两表（W2.2 落地, DDL 见 `backend/sql/w22_alert.sql`）**：

```sql
CREATE TABLE alert_rule (              -- 波动预警规则
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    category VARCHAR(32) NOT NULL,
    metric   VARCHAR(16) NOT NULL DEFAULT 'DOD_PCT' COMMENT 'DOD_PCT=日环比涨跌幅(%)',
    threshold DECIMAL(6,3) NOT NULL COMMENT '阈值(绝对值,%)',
    enabled  TINYINT NOT NULL DEFAULT 1,
    remark   VARCHAR(128),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_rule (category, metric)
) COMMENT='波动预警规则';

CREATE TABLE alert_record (            -- 预警触发记录(同品类+指标+交易日唯一, 重跑幂等)
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    category VARCHAR(32) NOT NULL, metric VARCHAR(16) NOT NULL,
    trade_date DATE NOT NULL, prev_date DATE NULL,
    latest_price DECIMAL(10,3), prev_price DECIMAL(10,3),
    change_pct DECIMAL(6,3), threshold DECIMAL(6,3), message VARCHAR(255),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_record (category, metric, trade_date)
) COMMENT='波动预警记录';
```

**阈值语义（用户确认）**：`|日环比涨跌幅| ≥ 阈值` 触发，按品类配置（默认 5%）。

## 6. 接口清单（SpringBoot，统一响应 `{code, msg, data}`，code=200 成功）

> 状态标注：✅ 已实现(W2.1，端口 8081) ｜ ⏳ 待实现

| 状态 | 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|---|
| ✅ | POST | /api/auth/login | JWT 登录（返回 token + 角色） | 公开 |
| ✅ | GET | /api/auth/me | 当前登录用户（刷新校验登录态） | 登录 |
| ✅ | GET | /api/price/categories | 品类列表+代表品名+最新价+单位 | 登录 |
| ✅ | GET | /api/price/trend?category=&days= | 日度均价序列（days 1–1095） | 登录 |
| ✅ | GET | /api/price/change?category= | 最新日环比（红涨绿跌） | 登录 |
| ✅ | GET | /api/predict/latest?category= | 未来7天预测+模型+MAPE+免责声明 | 登录 |
| ✅ | GET | /api/alert/rules | 预警规则列表 | 登录 |
| ✅ | PUT | /api/alert/rules/{id} | 修改阈值/启用状态 | **ADMIN** |
| ✅ | POST | /api/alert/evaluate | 立即执行一次预警评估 | **ADMIN** |
| ✅ | GET | /api/alert/records?page=&size= | 预警记录分页 | 登录 |
| ✅ | GET | /api/alert/summary | 各品类触发次数概览 | 登录 |
| ✅ | GET | /api/admin/collect/logs?page=&size= | collect_log 分页 | DATA_ADMIN / ADMIN |
| ✅ | GET | /api/admin/collect/stats?category= | 各品类数据量/时间跨度 | DATA_ADMIN / ADMIN |
| ✅ | POST | /api/admin/collect/trigger | 手动触发一次增量采集（异步子进程） | DATA_ADMIN / ADMIN |
| ⏳ | POST | /ml/forecast | FastAPI 实时预测 `{category, days}`（内网，可降级） | 内网 |

## 7. 算法方案

- **双通道**（铁律）：日常展示读 `predict_result` 预计算表；实时预测走 SpringBoot → FastAPI `/ml`；FastAPI 不可用时主流程照常。
- W1：ARIMA（阶数网格 (1-3,1,1-2) 按 AIC 选优；近两年日度均价、主导单位过滤、缺测日线性插值；前80%/后20%切分，测试集 MAPE 随行）。
- W2.2 预警判定：`|日环比涨跌幅| ≥ 阈值`（按品类, 默认 5%），与 `/api/price/change` 同口径；每日 21:30 由 Java 侧定时任务评估，记录表唯一键保证重跑幂等。
- W4：Prophet / 特征模型（节假日、季节项）对比实验，按品类择优；MAPE 准入阈值（展示门槛）待 W4 定。
- 所有预测输出必须携带：模型标识、测试集 MAPE、「预测结果仅供参考，不构成任何买卖建议」。

## 8. Dify 方案（W5）

docker compose 自部署 + DeepSeek API；知识库=价格快照摘要+预警规则+免责声明话术；SpringBoot 经 HTTP 调用；回答强制附带数据截止日期与免责声明。

## 9. 采集规范（铁律摘录 + 已踩坑）

1. 频率 ≤1次/秒（页间 sleep ≥1s）、必须携带 User-Agent（**ASCII，禁中文**——HTTP 头 latin-1 限制）；
2. SQL 一律参数化（`?`/`%s` + executemany），重复数据靠唯一约束 + upsert；
3. 解析前先打印真实返回确认字段（接口分页字段为 `count` 而非 total；`pubDate` 形如 `2026-09-24 00:00:00`）；
4. 接口历史回溯上限 **2022-01-01**；同品名存在 箱/筐/斤 多计价轨道，上游存在错标（箱价标成斤）；
5. 外部资源本地化优先（pyecharts CDN 证书过期教训：echarts/字体均 npm 本地打包）。

## 10. 环境与部署

Windows 11 + Git Bash/cmd；Python 3.12.10（pip，清华镜像）；Node 22.19 + npm 11.8（npmmirror）；MySQL 8.0.42（凭据经 `python/.env` 注入，**gitignored**）；时区 Asia/Shanghai；文件 UTF-8。

**调度常驻（W2.2）**：采集/预计算由 `python python/scheduler/run.py` 常驻执行（08/14/20 采集, 21 预计算）；
- 快捷启动：双击 `python/scheduler/start-scheduler.bat`（纯 ASCII 脚本, 规避 cmd 代码页问题）
- 开机自启：**已部署用户启动文件夹** `%APPDATA%\...\Startup\菜价雷达-采集调度.bat`（用户级, 无需管理员）
- 计划任务（可选, 需管理员）：`powershell -ExecutionPolicy Bypass -File python/scheduler/register-task.ps1`（本机因权限被拒, 脚本已就绪待提权执行）
- 预警评估由 **Java 侧** `@Scheduled`（每日 21:30）执行, 与 Python 调度分工；结果统一写 `collect_log`

**Java 侧（W2）**：JDK **17**（`C:\Program Files\Java\jdk-17`；PATH 默认是 JDK23，须显式 `JAVA_HOME`）；Maven 3.9.16 便携安装于 `D:\Program\tools\apache-maven-3.9.16`；后端端口 **8081**（本机 8080 常被其他软件占用，可用 `APR_SERVER_PORT` 覆盖）；数据库密码经 `APR_MYSQL_PWD` 注入；JWT 密钥经 `APR_JWT_SECRET` 覆盖（生产必须改）。

**前端（W3）**：`cd frontend && npm run dev`（5173, 已配 CORS 允许本机来源）；后端地址经 `VITE_API_BASE` 覆盖（默认 http://localhost:8081）。

Redis：**本机未安装**，W2 暂用默认内存缓存，接口不依赖 Redis；待安装后按配置切换（蓝图 §2 技术栈保留 Redis）。

## 11. 目录结构

```
agri-price-radar/
├─ AGENTS.md               开发铁律（人机共用）
├─ README.md               本蓝图（唯一事实来源）
├─ python/                 采集/算法/调度
│  ├─ config/db.py         双后端连接 + DDL + .env 加载
│  ├─ collector/xinfadi.py 采集器（probe / collect 全量 / collect --days N 增量）
│  ├─ scheduler/run.py     APScheduler 常驻进程（W1）
│  ├─ ml/precompute.py     预计算 → predict_result（W1）
│  ├─ scripts/             迁移/维护脚本（migrate_to_mysql.py 等）
│  └─ data/price.db        SQLite（gitignored）
├─ frontend/               Vue3（设计系统已就绪: tokens/EP主题/组件/规范页）
├─ demo/                   里程碑0独立演示（quick_view.py → price_demo.html）
└─ backend/                SpringBoot 工程（W2 创建）
```

## 12. 里程碑

| 阶段 | 内容 | 状态 |
|---|---|---|
| M0 | 选题试开发验证：探测/入库/演示页/ARIMA 预览 | ✅ 2026-09-24（v0.2.0） |
| — | 前端设计系统（令牌/EP主题/组件/规范页/单位治理） | ✅ 2026-09-24（v0.3.0） |
| **W1** | **采集服务化：DDL v2 迁移 + 增量采集 + APScheduler 定时 + MySQL 切换 + predict_result 预计算 + collect_log** | ✅ 2026-09-24（本地完成，待推送） |
| W2 | SpringBoot 后端：§6 接口 + JWT/RBAC + Redis | ✅ W2.1+W2.2 完成（鉴权/预警/触发/告警测试） |
| W3 | Vue3 管理端（品类管理/趋势/预测/任务日志页） | ▶ 登录+看板+采集监控+预警配置 已交付; 品类管理/改密待补 |
| W3 | Vue3 管理端（品类管理/趋势/预测/任务日志页） | 待启动 |
| W4 | 算法升级：Prophet 对比、MAPE 准入、FastAPI /ml 通道 | 待启动 |
| W5 | Dify 智能问答 + 1920×1080 可视化大屏（canvas-night） | 待启动 |

## 13. 风险与对策（踩坑台账）

| 风险 | 对策 |
|---|---|
| 上游单位错标（箱价标斤） | §5.1 单位治理规则 + 合理区间校验 |
| 同品名异单位撞唯一键覆盖 | DDL v2：unit_info 入唯一键 |
| 接口限流/封禁 | ≤1次/秒 + 退避重试 + collect_log 告警 |
| 外部 CDN 失效（已发生：pyecharts 证书过期） | echarts/字体本地打包；镜像回退链 |
| 跨后端类型差异（已发生：MySQL DECIMAL 经 pymysql 返回 Decimal → pandas object dtype，`.interpolate()` 报错） | 所有读数值列的模块统一 `pd.to_numeric(..., errors="coerce")`（precompute / export_snapshot / quick_view 已修） |
| 上游 MAPE 偏高（黄瓜 36%、西红柿 49%，波动大） | W4 引入 Prophet/季节项与特征模型，按品类择优并设展示阈值 |
| MySQL 凭据泄露 | python/.env 注入且 gitignored |
| 接口改版字段变化 | probe 模式随时人工复核字段 |
| **PowerShell/cmd 与外部工具交互（已发生）** | `-Dfile.encoding` 被 pwsh 拆坏 → 改用 `JAVA_TOOL_OPTIONS`；`&&` 在 PowerShell 5.1 不可用；`.bat` 中文在 cmd 代码页下解析失败 → **bat 一律纯 ASCII**；`.ps1` 含中文须存 UTF-8 **BOM** |
| **APScheduler 3.11 API 变更（已发生）** | `Job.next_run_time` 仅在 `sched.start()` 后可用 → 启动前打印触发规则, 启动后经 `EVENT_SCHEDULER_STARTED` 监听打印 |
| 调度进程崩溃后静默停摆 | 启动文件夹自启 + 启动脚本；建议后续接入心跳告警（W3+） |

## 14. 开发清单

- [x] M0：新发地单页探测 + 5品类全量入库（26,193条，2022-01-01~2026-09-24）
- [x] M0：demo 页（90天趋势/3年走势/环比/ARIMA 7天+MAPE）
- [x] M0：SQLite 可切换存储层（db.py）
- [x] 设计系统：tokens/EP主题/品牌组件/规范页（v0.3.0）
- [x] 蓝图 README.md v1 基线（本文档）
- [x] W1：DDL v2（unit 入唯一键）+ 存量自动迁移（26,193 行无损，箱/斤双轨共存已验证）
- [x] W1：采集器增量模式（`collect --days N`，日期窗口已实测）
- [x] W1：APScheduler 定时进程（采集 08/14/20 点 + 预计算 21 点；`--now` 手动触发）
- [x] W1：MySQL 迁移与切换（`.env` 凭据，26,193 行迁入 `agri_price_radar`）
- [x] W1：predict_result 预计算（5 品类 × 7 天，含模型与 MAPE）+ collect_log 任务日志
- [x] W1：远程仓库推送（GitHub 凭据与代理待处理）
- [x] W2.1：SpringBoot 工程骨架（SpringBoot 3.3.5 + MyBatis-Plus + JDK17 + 阿里云镜像 + mvnw 免装）
- [x] W2.1：只读接口 4 个（categories/trend/change/predict）+ 管理端 2 个（logs/stats）
- [x] W2.1：统一响应 `{code,msg,data}` + 全局异常处理 + 参数校验（越界/未知品类/缺参 → 400）
- [x] W2.1：RBAC 三表 + 预置双角色账号（BCrypt）
- [x] W2.1：测试 11 例全绿（CategoryCatalogTest 3 + PriceApiIntegrationTest 8）
- [x] W2.2：JWT 登录（/api/auth/login、/api/auth/me）+ 双角色强制校验（/api/admin/** 需角色, /api/alert/rules 改阈值仅 ADMIN）
- [x] W2.2：401/403 统一响应结构；越权用例测试通过
- [x] W2.2：预警模块（alert_rule / alert_record 两表 + 日环比阈值判定 + 每日21:30定时 + 手动评估接口）
- [x] W2.2：手动触发采集接口（异步子进程复用 Python 采集器, 互斥保护, 结果写 collect_log）
- [x] W2.2：后端测试 30 例全绿（新增 AuthApiIntegrationTest 10 + AlertApiIntegrationTest 9）
- [x] W2.2：调度进程常驻修复（APScheduler 3.11 `next_run_time` 缺陷）+ 启动脚本 + 启动文件夹自启
- [x] W2.2：前端基础设施（axios 封装/401 拦截/Pinia/路由守卫）+ 登录页 + 数据看板 + 采集监控 + 预警配置
- [x] W2.2：Python 冒烟测试 11 例全绿
- [x] W2.2：生产 profile 关闭 SQL 打印
- [ ] W3：品类管理、首次登录强制改密、操作审计（op_log）
- [ ] W4：Prophet 对比、MAPE 准入阈值、FastAPI /ml 实时通道
- [ ] W5：Dify 智能问答 + 1920×1080 可视化大屏
