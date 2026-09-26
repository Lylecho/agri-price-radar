# 菜价雷达 · 主后端（backend）

SpringBoot 3.3.5 + MyBatis-Plus 3.5.9 + MySQL 8，JDK 17。对应蓝图 `README.md` §4/§6。

## 一、环境要求

| 组件 | 版本 | 说明 |
|---|---|---|
| JDK | **17**（必须） | 本机 `C:\Program Files\Java\jdk-17`；PATH 默认可能是 JDK23，需显式 `JAVA_HOME` |
| Maven | 3.9+ | 本机便携安装于 `D:\Program\tools\apache-maven-3.9.16`（未加入 PATH） |
| MySQL | 8.x | 库 `agri_price_radar`，凭据经环境变量注入 |

## 二、运行

```bat
:: 1) 设置环境（凭据不写进代码/仓库）
set JAVA_HOME=C:\Program Files\Java\jdk-17
set APR_MYSQL_PWD=你的MySQL密码
:: APR_JWT_SECRET 必填（至少32字节）；构建带测试时另需 APR_TEST_PASSWORD / APR_TEST_NEW_PASSWORD
set JAVA_TOOL_OPTIONS=-Dfile.encoding=UTF-8

:: 2) 构建（-s 指定阿里云镜像，避免外网依赖）
D:\Program\tools\apache-maven-3.9.16\bin\mvn.cmd -s maven-settings.xml clean package

:: 3) 启动（默认端口 8081；本机 8080 常被其他软件占用）
"%JAVA_HOME%\bin\java.exe" -jar target\price-radar-backend-1.0.0.jar

:: 4) 运行测试（集成测试需 MySQL 可达）
set APR_MYSQL_PWD=你的MySQL密码
D:\Program\tools\apache-maven-3.9.16\bin\mvn.cmd -s maven-settings.xml test
```

可用环境变量：`APR_SERVER_PORT`（默认 8081）、`APR_MYSQL_USER`（默认 root）、`APR_MYSQL_PWD`（**必填**）。

## 三、接口（统一响应 `{code,msg,data}`）

**认证（W2.2）**

| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| POST | `/api/auth/login` | 登录, 返回 token/角色/有效期 | 公开 |
| GET | `/api/auth/me` | 当前登录用户（含 mustChangePwd） | 登录 |
| POST | `/api/auth/change-password` | 校验原密码后修改，解除首次改密限制 | 登录 |

**业务（W2.1，W2.2 起需登录）**

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/price/categories` | 五品类概览（代表品名/单位/最新价） |
| GET | `/api/price/trend?category=大白菜&days=90` | 日度均价序列（days 1–1095） |
| GET | `/api/price/change?category=鸡蛋` | 最新日环比（红涨绿跌由前端渲染） |
| GET | `/api/predict/latest?category=大白菜` | 未来7天预测 + 模型 + 测试集 MAPE + **免责声明** |

**预警（W2.2）**

| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| GET | `/api/alert/rules` | 预警规则列表 | 登录 |
| PUT | `/api/alert/rules/{id}` | 修改阈值/启用状态 | **ADMIN** |
| POST | `/api/alert/evaluate` | 立即执行一次评估 | **ADMIN** |
| GET | `/api/alert/records?page=&size=` | 预警记录分页 | 登录 |
| GET | `/api/alert/summary` | 各品类触发次数 | 登录 |

**管理端（W2.2）**

| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| GET | `/api/admin/collect/logs?page=&size=` | 任务日志分页 | DATA_ADMIN / ADMIN |
| GET | `/api/admin/collect/stats?category=` | 数据量/跨度/主导单位/非斤与疑似错标条数 | DATA_ADMIN / ADMIN |
| POST | `/api/admin/collect/trigger` | 手动触发增量采集（异步子进程） | DATA_ADMIN / ADMIN |
| GET | `/api/admin/oplog?page=&size=&username=&action=` | 审计分页，用户名/动作精确筛选 | **ADMIN** |

自测示例（PowerShell）：

```powershell
$base = 'http://localhost:8081'
$login = Invoke-RestMethod "$base/api/auth/login" -Method Post -ContentType 'application/json' `
         -Body (@{username=$env:APR_LOGIN_USER; password=$env:APR_LOGIN_PASSWORD} | ConvertTo-Json)
$h = @{ Authorization = "Bearer $($login.data.token)" }
Invoke-RestMethod "$base/api/price/categories" -Headers $h
Invoke-RestMethod "$base/api/predict/latest?category=大白菜" -Headers $h
Invoke-RestMethod "$base/api/alert/rules" -Headers $h
```

## 四、鉴权与权限模型（W2.2）

- **JWT 无状态**（HS256，`jjwt` 0.12.6），不依赖 Redis；密钥必须由环境变量 `APR_JWT_SECRET` 提供（至少 32 字节，无默认值），有效期 `APR_JWT_EXPIRE_MINUTES`（默认 120 分钟）。
- 规则：`/api/auth/login` 公开；`/api/admin/oplog` 仅 ADMIN，其余 `/api/admin/**` 需 ADMIN 或 DATA_ADMIN；其余 `/api/**` 需登录。
- 细粒度：`PUT /api/alert/rules/{id}` 与 `POST /api/alert/evaluate` 用 `@PreAuthorize("hasRole('ADMIN')")` 限定超级管理员。
- 401/403 均返回统一结构（HTTP 200 + body.code），便于前端拦截器统一处理；登录失败对"用户不存在/密码错误"返回同一提示。
- 定时任务：预警评估由 `@Scheduled`（默认每日 21:30，`apr.alert.cron` 可配）执行，结果写 `collect_log`。

## 五、数据库

- 业务表由 Python 侧写入：`price_daily`(26,193 行) / `predict_result`(35 行) / `collect_log`
- 权限三表：`python python/scripts/run_sql.py backend/sql/w2_auth.sql`
- W3 首次改密迁移（**只执行一次**）：`python python/scripts/run_sql.py backend/sql/w3_password.sql`。迁移仅标记仍使用预置密码摘要的账号；迁移前备份 `sys_user`。
- 预警两表：`python python/scripts/run_sql.py backend/sql/w22_alert.sql`
- 预置账号：`admin`、`dataadmin`。执行 `w2_auth.sql` 前分别注入 `APR_ADMIN_PASSWORD_HASH` / `APR_DATA_ADMIN_PASSWORD_HASH`（BCrypt 摘要）；未提供时跳过账号创建，不含默认密码。首次执行 `w3_password.sql` 时保持相同摘要变量，以标记仍使用初始密码的账号。
- 审计表（幂等）：`python python/scripts/run_sql.py backend/sql/w3_oplog.sql`。已完成 W3 改密迁移的环境仅需追加此脚本。

## 六、测试

```bat
set APR_MYSQL_PWD=你的MySQL密码
D:\Program\tools\apache-maven-3.9.16\bin\mvn.cmd -s maven-settings.xml test
```

共 **40 例**（原 32 + 新增 8；需 MySQL 可达且已执行 `w2_auth.sql`、`w22_alert.sql`、`w3_password.sql`、`w3_oplog.sql`）：
- `CategoryCatalogTest`(3)：品类映射与单位治理结论
- `PriceApiIntegrationTest`(8)：价格/预测接口 + 参数校验
- `AuthApiIntegrationTest`(12)：登录成功/失败/无令牌/非法令牌/角色访问/当前用户/首次改密强制校验
- `AlertApiIntegrationTest`(9)：规则列表/阈值修改/**越权 403**/非法值 400/不存在 404/记录/概览/手动触发
- `OpLogApiIntegrationTest`(8)：ADMIN 可查、DATA_ADMIN 403、匿名 401、采集受理记录、四动作摘要脱敏、超长用户名截断、审计故障隔离、分页/动作校验与参数化筛选

测试前注入 `APR_TEST_PASSWORD` / `APR_TEST_NEW_PASSWORD`（6–64 字符且不同）以及数据库/JWT 环境变量。每例创建独立账号并在结束后删除，不依赖预置账号密码；审计记录保留。采集测试运行无网络桩进程，定时预警禁用。

PowerShell 可在当前进程生成临时测试凭据（不会写入文件）：

```powershell
$env:APR_TEST_PASSWORD = [Guid]::NewGuid().ToString('N')
$env:APR_TEST_NEW_PASSWORD = [Guid]::NewGuid().ToString('N')
$env:APR_JWT_SECRET = [Convert]::ToBase64String([Security.Cryptography.RandomNumberGenerator]::GetBytes(48))
# APR_MYSQL_PWD 由本地环境注入
mvn -s maven-settings.xml test
```

## 七、W3 状态与自测

- 首次改密验收：预置账号登录返回 `mustChangePwd=true`；改密前业务接口返回 403，`/api/auth/me` 与 `/api/auth/change-password` 可访问；改密成功后旧密码失效。
- 操作审计完成：登录（含失败）、改密、修改预警规则、手动采集受理均有记录；写入失败只打安全日志，不影响业务。用户名按 Unicode 字符截断到 32；摘要不包含密码、令牌或完整请求。
- 审计查询默认 page=1、size=10（最大 100）；action 为 LOGIN / CHANGE_PASSWORD / UPDATE_ALERT_RULE / TRIGGER_COLLECT。采集的 SUCCESS 仅表示受理，异步真实结果看 collect_log。IP 为直接连接地址，时间为上海时区。
- 自测：ADMIN 登录 → 改阈值 → 触发采集 → 改密 → 查询四动作；DATA_ADMIN 查询 code=403，匿名 code=401（沿用 HTTP 200 + 业务码）。品类页复用 collect/stats，零新增配置表。
- 验收记录见 [R1 DEVLOG](../docs/DEVLOG.md)。Redis 属后续环境接入，不阻断 W3 验收。
