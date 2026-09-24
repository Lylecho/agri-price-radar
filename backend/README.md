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

## 三、接口（W2.1 已实现，统一响应 `{code,msg,data}`）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/price/categories` | 五品类概览（代表品名/单位/最新价） |
| GET | `/api/price/trend?category=大白菜&days=90` | 日度均价序列（days 1–1095） |
| GET | `/api/price/change?category=鸡蛋` | 最新日环比（红涨绿跌由前端渲染） |
| GET | `/api/predict/latest?category=大白菜` | 未来7天预测 + 模型 + 测试集 MAPE + **免责声明** |
| GET | `/api/admin/collect/logs?page=1&size=10` | 任务日志分页 |
| GET | `/api/admin/collect/stats?category=大白菜` | 单品类数据量与跨度 |

自测示例：

```bat
curl http://localhost:8081/api/price/categories
curl "http://localhost:8081/api/predict/latest?category=大白菜"
```

## 四、数据库

- 业务表由 Python 侧建表并写入：`price_daily`(26,193 行) / `predict_result`(35 行) / `collect_log`
- 权限三表（`sys_user` / `sys_role` / `sys_user_role`）执行：`python python/scripts/run_sql.py backend/sql/w2_auth.sql`
- 预置账号（**仅开发环境**，首次登录后强制改密）：`admin`/`admin123`、`dataadmin`/`dataadmin123`（BCrypt 存储）

## 五、待办（W2.2）

- `spring-boot-starter-security` + JWT 登录、双角色强制校验（`/api/admin/**` 需 DATA_ADMIN+）
- 手动触发采集接口 `POST /api/admin/collect/trigger`
- Redis 缓存接入（当前未安装 Redis，暂用默认内存缓存，配置可切换）
