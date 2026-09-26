# 菜价雷达 · 管理端（frontend）

Vue3 + Vite + Element Plus + Pinia + Axios + ECharts。设计语言见 `DESIGN.md`（令牌已落在 `src/styles/tokens.css`）。

## 一、运行

```bat
cd frontend
npm install                :: 首次(已装可跳过)
npm run dev                :: 开发服务器 http://localhost:5173
npm run build              :: 生产构建(输出 dist/)
npm run preview            :: 预览构建产物 http://localhost:4173
```

后端地址默认 `http://localhost:8081`（可用环境变量 `VITE_API_BASE` 覆盖）。
**前置**：后端已启动，`APR_MYSQL_PWD` / `APR_JWT_SECRET` 已注入，并已执行 `backend/sql/w3_oplog.sql`。

开发环境预置账号：`admin`（超级管理员）、`dataadmin`（数据管理员），密码由部署者配置。

## 二、页面

| 路由 | 页面 | 说明 | 可访问角色 |
|---|---|---|---|
| `/login` | 登录 | JWT 登录, 失败提示；需改密时跳转改密页 | 公开 |
| `/change-password` | 修改密码 | 首登强制改密及日常改密 | 登录用户 |
| `/dashboard` | 数据看板 | 五品类卡片(最新价+环比红涨绿跌) + 趋势图(90天/1年/3年) + 未来7天预测(虚线+MAPE+**免责声明**) | 登录用户 |
| `/collect` | 采集监控 | 各品类数据量与跨度 + 任务日志分页 + 手动触发采集 | 登录用户（触发按钮仅后端鉴权） |
| `/alert` | 预警配置 | 预警规则阈值维护 + 预警记录列表 | 规则修改仅 ADMIN |
| `/categories` | 品类管理 | 只读五品类映射、覆盖量/日期、主导单位及治理状态 | ADMIN / DATA_ADMIN |
| `/oplog` | 操作审计 | 用户名/动作筛选、分页、结果/IP/时间 | **仅 ADMIN** |
| `/style-guide` | 设计规范 | 令牌与组件可视化（W2.1 交付） | 登录用户 |

## 三、工程结构

```
src/
├─ api/          请求封装(axios 拦截器: 统一解包 {code,msg,data}, 401 自动跳登录)
│  ├─ request.js   ├─ auth.js  ├─ price.js  ├─ predict.js  ├─ collect.js  └─ oplog.js
├─ stores/       Pinia (user: token/角色, localStorage 持久化)
├─ router/       路由 + 登录守卫(未登录跳 /login)
├─ layouts/      BasicLayout(侧边栏按角色渲染 + 顶栏用户/退出)
├─ views/        Login / ChangePassword / Dashboard / CollectMonitor / AlertConfig / CategoryManage / OpLogAudit / StyleGuide
├─ components/
│  ├─ ui/        品牌组件(AppButton/AppCard/AppPill/AppCodeBlock)
│  └─ charts/    ECharts 封装(TrendChart 多系列折线, PredictChart 历史+预测虚线)
└─ styles/       tokens / base / element-theme / fonts(Inter + Noto Sans SC 本地打包)
```

## 四、约定

- **响应结构**：后端一律 `{code, msg, data}`；`code=200` 成功，`401` 未登录，`403` 无权限。
- **预测展示**：任何预测图必须带上 `disclaimer`（蓝图铁律：行政性监测工具, 不提供买卖建议）。
- **涨跌配色**：红涨绿跌（中国惯例），见 `Dashboard.vue` 的 `changeColor`。
- **离线可用**：ECharts/字体均本地打包, 不依赖外部 CDN（曾发生 pyecharts CDN 证书过期事故）。

## 五、W3 状态与自测

- 品类管理采用方案 B：映射由 CategoryCatalog / constants.py 代码同步维护，页面只读；覆盖量/日期/单位与检查条数复用 `/api/admin/collect/stats`。两新页复用 AppCard 与既有 tokens。
- 审计验收：ADMIN 可见菜单，可按用户名精确筛选、选择四动作和翻页；DATA_ADMIN 无菜单，直接访问 `/oplog` 返回看板，接口独立强制鉴权。采集审计显示受理结果。
- 首次改密已完成：运行一次 W3 数据库迁移，使用仍为预置密码的账号登录，应被引导到 `/change-password`；改密前访问 `/dashboard` 会被拦截。
- R1 两新页浏览器验收通过，`npm run build` 无错误（保留已有 chunk 体积提示）。截图和完整记录见 [DEVLOG](../docs/DEVLOG.md)。
- 后续大屏归属 W5；下一轮先推进 W4 的 Prophet 对比与 MAPE 准入。
