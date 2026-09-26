# 开发记录

## R1 · W3 收尾：操作审计、只读品类管理与仓库归档

### 轮次编号

- R1，2026-09-27；里程碑 W3；发布标签 `v0.7.0`，分支 `main`。
- 进入本轮前：W1/W2 已完成；W3 登录、看板、采集监控、预警配置和首次改密已交付，剩余品类管理与操作审计。既有 `bad6a06` 随本轮一并推送。

### 开发目标

关闭蓝图 §14 的 W3 剩余两项，完成四动作审计、ADMIN 审计查询、只读品类页，整理运行文档与仓库，形成可运行且可回归的 W3 保存节点。

### 改动文件

- 数据库：`backend/sql/w3_oplog.sql`；凭据注入调整涉及 `w2_auth.sql`、`w3_password.sql`、`python/scripts/run_sql.py`。
- 后端：`aspect/{AuditAction,Audited,OperationAuditAspect}.java`，`entity/OpLog.java`，`mapper/OpLogMapper.java`，`service/OpLogService.java`，`controller/OpLogController.java`；修改 AuthService、AlertService、CollectTriggerService、SecurityConfig、GlobalExceptionHandler、PriceDailyMapper、CategoryStatsVO、pom.xml、application.yml。
- 前端：`views/OpLogAudit.vue`、`views/CategoryManage.vue`、`api/oplog.js`；修改 router/index.js、BasicLayout.vue、Login.vue。
- 回归：`OpLogApiIntegrationTest.java`、ApiTestBase、AuthApiIntegrationTest、`src/test/resources/collect_stub.py`。
- 归档：根 README §5.1/§5.4/§6/§12/§14，backend/frontend README，`.gitignore`，本日志及 `docs/screenshots/r1-{oplog,categories}.png`。ROUND-PLAN 仅删除过期的默认密码示例。

### 改动说明（含锁定决策）

1. **DDL 已确认**：新增 op_log，字段 id、user_id、username、action、target、独立 result、detail、ip、created_at；user_id 可空。username 保持 VARCHAR(32)，建立 (username,created_at)、(action,created_at)、created_at 索引。CREATE TABLE IF NOT EXISTS 幂等，文件头注明用途、执行命令、幂等范围，蓝图 §5.4 同步原始 DDL。之前已批准的 sys_user.must_change_pwd 迁移保持不变，本轮现有环境不重复执行该 ALTER。
2. **品类采用方案 B**：只读；映射由 CategoryCatalog / constants.py 代码同步维护，零新增配置表，符合蓝图 §5.1。复用 collect/stats 展示数量、跨度、主导单位，以及非斤/缺失单位数、散鸡蛋斤价超过 15 元的疑似错标数；页面检查不自动隔离或修改明细。
3. **TRIGGER_COLLECT 只记录受理结果**：trigger() 返回 true → SUCCESS，false → FAILED；异常亦记失败。异步真实执行结果由 collect_log 记录，op_log 不做第二次记录。
4. **安全验收约束**：查询/写入均绑定 SQL 参数；凭据只经环境变量注入。移除源码、示例与测试中的可用默认凭据；初始化 BCrypt 摘要由 APR_ADMIN_PASSWORD_HASH / APR_DATA_ADMIN_PASSWORD_HASH 注入，JWT 无默认密钥；测试凭据由 APR_TEST_PASSWORD / APR_TEST_NEW_PASSWORD 注入。关闭默认 SQL 参数打印。历史提交不重写。
5. 审计 AOP 覆盖 LOGIN / CHANGE_PASSWORD / UPDATE_ALERT_RULE / TRIGGER_COLLECT；登录参数校验失败也记录。身份解析、摘要构造与入库均有异常隔离，审计失败仅打安全日志，不影响原业务返回或异常。用户名按 Unicode 码点截断到 32，兼容 MySQL 8 严格模式及 utf8mb4。
6. 审计摘要不记录密码、令牌、完整请求或可夹带凭据的自由文本备注；IP 取直接连接地址，不信任客户端 X-Forwarded-For。时间按 Asia/Shanghai。
7. GET /api/admin/oplog 默认 page=1、size=10（最大 100），支持 username/action 精确筛选；接口和方法均校验 ADMIN，前端同步菜单和路由限制。沿用统一响应与既有 HTTP 200 + code=401/403 约定。
8. 两新页复用 AppCard/AppButton 与既有 tokens，提供加载/错误反馈。`.mimosa/` 加入忽略规则。原始 32 项回归改用独立临时账号，采集测试使用无网络进程桩，避免反复抓取。

### 验证结果

| 检查 | 结果 |
|---|---|
| JDK17：backend 下 `mvn -s maven-settings.xml test` | 40/40 通过，0 失败/错误/跳过；原 32 + 新增 8 |
| 新增审计回归 | ADMIN 可查、DATA_ADMIN 403、匿名 401、采集后落行、四动作与摘要脱敏、超长 Unicode 用户名、审计写入故障不影响登录、非法参数与 SQL 注入字符串筛选 |
| Python：`python -m unittest discover -s python/tests -v` | 11/11 通过 |
| 前端：`npm run build`（Windows 使用 npm.cmd） | 0 error；保留已有 chunk 超过 500 kB 提示 |
| 后端打包与启动 | package 成功；8081 启动，5173 前端可用 |
| op_log DDL | 本地执行成功，再次执行成功，已有记录保留 |
| 真实接口流程 | 临时 ADMIN 登录 → 阈值改为 6.25 → 手动采集受理 → 改密，四动作均成功落行；随后阈值恢复到 5.0 |
| 采集结果 | 仅 1 条 TRIGGER_COLLECT 审计，真实采集进程完成，执行日志留在 collect_log |
| 浏览器：ADMIN | 两新页正常显示；用户名与采集动作组合筛选仅 1 条；四动作审计截图归档 |
| 浏览器：DATA_ADMIN | 审计菜单不可见，直接访问 /oplog 返回看板；品类页可访问；控制台未发现错误或警告 |
| 品类一致性 | 大白菜→大白菜 1719，黄瓜→黄瓜 3408，西红柿→番茄 5063，猪肉→白条猪 3380，鸡蛋→散鸡蛋 1691；与 collect/stats 一致；均覆盖 2022-01-01 至 2026-09-26，主导单位斤，当前异常检查计数均为 0 |
| 验收数据清理 | 临时浏览器账号 r1_qa_admin/r1_qa_data 已删除，审计记录保留；业务规则已恢复 |

截图：[操作审计](screenshots/r1-oplog.png)、[品类管理](screenshots/r1-categories.png)。

### 遗留问题与下一步

- W3 无阻断项，满足关闭条件。构建体积提示作为后续优化记录，不在本轮扩大范围。
- 新环境需注入数据库/JWT 凭据和初始化密码摘要；历史迁移仅执行一次，已有环境按 backend/README 追加审计表即可。
- R2 对应 W4：基于固定入库快照做 Prophet 与 ARIMA 对比，并落实 MAPE 准入阈值 30%；预测展示继续保留“预测结果仅供参考”。FastAPI 实时通道随后按蓝图推进。
