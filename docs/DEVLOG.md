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

## R2 · W4 算法升级：Prophet 对比与 MAPE 准入（离线部分）

### 轮次编号

- R2，2026-09-27；标签 `v0.8.0`，分支 `main`；承接已关闭的 W3，仅交付 W4 离线模块。

### 开发目标

按蓝图 §7 完成五品类 ARIMA/Prophet 同口径对比，30% MAPE 展示准入、幂等预计算、空预测文案与论文可引用报告。不修改 Java/后端接口，不实施实时预测通道。

### 改动文件

- 新增 `python/ml/{arima_model,prophet_model,model_common,compare_models}.py`；重构 `precompute.py`，修改 constants.py、requirements.txt、tests/test_smoke.py、scheduler/run.py（避免双重任务日志）。
- 修改 `frontend/src/views/Dashboard.vue`、`components/charts/PredictChart.vue`；api/predict.js 与 api/request.js 仅增加预测404空状态适配，兼容既有接口。
- 新增 `docs/W4-MODEL-REPORT.md`、`docs/experiments/r2/{snapshot.csv,comparison.json,comparison.md}`、`docs/screenshots/r2-{rejected,prophet}.png`；更新 README §7/§12/§14 与本日志。

### 改动说明（阈值与择优结论）

1. **锁定阈值 30%（含边界）**，先比较未四舍五入测试 MAPE 择优，再判断准入。ARIMA 内部在训练集按 AIC 选阶，不将跨模型 AIC 直接比较。平局优先 ARIMA；非有限误差或非法未来价格不参选。
2. **择优结果**：大白菜 ARIMA(2,1,1)，22.149%；黄瓜 Prophet，24.869%；西红柿 ARIMA(2,1,2)，39.356%（拒绝展示）；猪肉 ARIMA(1,1,1)，5.299%；鸡蛋 Prophet，8.211%。共4品类、28条未来7天预测。两模型完整数值与耗时见报告，不沿用旧快照的误差值。
3. 固定2024-09-28至2026-09-27的730日窗口，主导斤价过滤、日度均价、584/146日顺序切分、线性插值；训练段插值不读取测试值。比较和预计算共用实现，导出带SHA-256的日均快照与实验JSON。Prophet 1.4.0官方Windows wheel安装成功，无SARIMAX替代。
4. 无DDL变更。保留uk_pred与参数化executemany upsert；准入成功撤下旧模型/旧窗口，超阈值不写入且撤下该品类旧派生预测，防止接口返回历史高误差曲线。全部模型计算完成再以单事务发布，失败回滚。collect_log记录阈值、择优、跳过原因，直接入口与调度入口各只记一次。
5. 前端按既有code=404处理空预测，显示“波动过大，暂不提供预测（仅供参考）”；网络错误保持独立提示。预测图例改为实际模型名称，保留免责声明，并防止快速切换品类的迟到请求覆盖当前结果。空契约无法区分尚未预计算与门禁拒绝，部署需先完成预计算，限制已写报告。
6. 测试输入与验收账号使用临时生成的凭据，经环境/本地忽略文件注入，不写入源码、示例或报告。

### 验证结果

- Python冒烟 **21/21**（原11+新增10）：门禁边界/NaN/非法阈值、MAPE与零分母、择优/平局、非法预测、切分边界插值、数据不足、幂等、降阈值恢复、模型切换、事务回滚。
- compare_models固定快照复跑：SHA-256、两模型MAPE（误差<1e-8）及择优完全一致。
- 真库阈值0：0条预测，collect_log SUCCESS/rows_written=0并有五品类跳过摘要；恢复30%：28条，西红柿0条。再次正常重跑：主键、模型、MAPE、日期、预测值与步长完全一致，无重复。
- 原后端接口验证：4品类各code=200、7点，model/mape_test与实验一致；西红柿code=404。无Java文件修改。
- 前端生产构建0 error；保留既有chunk体积提示。浏览器核验西红柿兜底文案及黄瓜Prophet 24.869%预测曲线，无控制台错误/警告。临时账号验收结束后清理。
- 证据：[拒绝展示](screenshots/r2-rejected.png)、[Prophet曲线](screenshots/r2-prophet.png)、[完整报告](W4-MODEL-REPORT.md)。

### 遗留问题与下一步

- R2离线目标完成，W4整体仍有FastAPI `/ml`实时通道待办。
- Prophet年周期训练不足两个完整周期存在识别限制；测试段用于选模、含少量插值日，146天一次性外推MAPE不等同7天滚动误差。保留失败对照，不夸大泛化结论；后续独立评估可采用滚动起点和额外保留段。
- 日常调度应在升级后重新启动加载新实现；本轮验收时未发现常驻调度进程，未擅自创建新的自启动配置。


## R3 · W4 算法服务：FastAPI实时通道与优雅降级

### 轮次编号

- R3，2026-09-28；分支 `main`，里程碑标签 `v0.9.0`；承接 R2/v0.8.0，关闭 W4。

### 开发目标

打通 FastAPI `/ml/forecast` → SpringBoot 登录代理 → 看板实时入口；算法故障时自动回退预计算，保持主流程与免责声明。

### 改动文件

- 新增 `python/ml/api.py`、`python/tests/test_ml_api.py`、`python/README.md`；修改 `ml/compare_models.py`、`requirements.txt`。
- 新增后端 `service/MlForecastClient.java`、`vo/RealtimePredictVO.java`、`RealtimePredictIntegrationTest.java`；修改 `PredictService`、`PredictController`、`GlobalExceptionHandler`、`application.yml`。
- 修改前端 `api/predict.js`、`views/Dashboard.vue`、`components/charts/PredictChart.vue`。
- 同步根 README §6/§7/§12/§14、backend/README、frontend/README、本日志；新增两张验收截图 `docs/screenshots/r3-{realtime,degraded}.png`。

### 改动说明

1. **无DDL变更**。FastAPI只读已入库快照，不调用采集器、不自动建表、不写predict_result/collect_log。MySQL会话只读、SQLite mode=ro，SQL参数化。凭据由环境/本地忽略配置注入；测试凭据运行时生成，临时验收账号已退出并清理，源码与示例无可用凭据字面量。
2. 抽出R2单品类比较函数，共用既有ARIMA/Prophet择优与 **MAPE ≤ 30%** 门禁。Java不重复实现训练算法。正常未准入返回admitted=false、空序列、degraded=false，不能回退旧曲线绕过门禁。
3. 实时服务启动预热五品类；每次请求重读快照并按内容摘要失效缓存，同快照复用计算结果。新快照只允许单个训练任务，繁忙503；冷训练可能超出Java截止时间，此次回退，计算完成后可恢复。缓存仅每品类一份，不读取预计算表冒充实时计算。
4. Java `GET /api/predict/realtime` 登录可访问，默认7天、范围1–7。HTTP完整响应默认2800ms截止，上限3000ms，连接最多500ms；无重试。超时、拒绝、5xx、无效响应统一返回预计算，degraded=true。无预计算或回退读库失败则成功空状态，不抛500。截止时间约束算法HTTP调用，不包含回退数据库耗时。
5. 前端增加“实时”徽标、实时按钮、降级提示、空回退状态；免责声明常驻。显示MAPE三位小数，准入仍使用原始数值；快速切换品类时忽略迟到结果。

### 验证结果

| 检查 | 结果与证据 |
|---|---|
| 后端 JDK17 `mvn -s maven-settings.xml test` | **50/50**，0失败/错误/跳过；原40+新增10 |
| 新增集成用例 | 真实HTTP桩：正常、慢响应头、慢响应体、关停桩后的连接拒绝、503、无效协议；另覆盖空回退、质量拒绝、参数校验与匿名鉴权；DATA_ADMIN正常访问 |
| 超时测试 | 设置400ms客户端期限，慢响应头/响应体各1200ms；均回退，断言总耗时低于1100ms通过 |
| Python `python -m unittest discover -s python/tests -v` | **29/29**，原21+API/缓存失效/繁忙/门禁/SQLite只读等8例 |
| R2固定快照复跑 | 五品类胜出模型不变，两模型MAPE差异均<1e-8；大白菜22.149%、黄瓜24.869%、西红柿39.356%拒绝、猪肉5.299%、鸡蛋8.211% |
| 真库FastAPI | 预热后黄瓜3日HTTP200/Prophet/24.869%/3点，约0.245s；西红柿HTTP200/39.356%/空序列，约0.136s |
| 浏览器完整正常链路 | 临时ADMIN登录 → 点击实时预测 → 显示绿色“实时”、大白菜ARIMA(2,1,1)、MAPE22.149%、未来7日曲线与免责声明 |
| **真实停服降级** | 确认并停止本轮uvicorn进程15600 → 同一页面再次点击实时预测 → “预计算 · 已降级”及“实时通道不可用，已回退预计算结果”，预计算曲线与趋势仍显示；控制台错误/警告0条 |
| **恢复验证** | 重启uvicorn（本轮进程24188），等待预热 → 同页点击实时预测恢复绿色“实时”，降级提示消失，无需重启主后端 |
| 前端生产构建 | 最终 `npm.cmd run build` 0 error；保留原有大于500kB的chunk提示 |
| 打包与临时数据 | 后端package成功，8081/5173可运行；临时账号r3_qa_admin已退出、角色关联与用户行已删除，忽略目录凭据文件已删除，审计记录保留 |

截图：[实时/恢复页面](screenshots/r3-realtime.png)、[实际停服回退页面](screenshots/r3-degraded.png)。本地测试原始日志在已忽略的 `backend/target/r3-*.log`，不提交运行日志和凭据。

### 遗留问题与下一步

- R3验收完成，W4整体可关闭。下一里程碑W5：按蓝图推进Dify智能问答与1920×1080可视化大屏。
- 新快照冷训练耗时可能超过代理期限，依设计降级；同快照预热/缓存后恢复。MAPE仍是R2留出测试误差，不代表未来7天保证误差。
- 前端现有chunk体积提示未扩大处理范围；本轮未创建任何自启动任务。
