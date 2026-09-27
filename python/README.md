# Python 采集、离线预测与实时算法通道

## R3 启动（项目根目录）

```powershell
python -m pip install -r python/requirements.txt
python python/ml/api.py
```

入口固定单进程绑定 `127.0.0.1:8001`，仅供同机 SpringBoot 调用，不绑定公网地址。数据库必须已按根 README 初始化并有入库快照；凭据由 `APR_MYSQL_*` 环境变量或已忽略的 `python/.env` 注入，`APR_DB_BACKEND=mysql`。SQLite 使用已有 `python/data/price.db`，只读打开。服务不自动建表、采集或写预测表。

启动会预热五品类，请等待 `Application startup complete`。每次请求读取现有快照，以品类数据内容摘要判断缓存失效；同一快照复用 R2 模型计算结果。新快照仅允许一个训练任务，其他需要训练的请求快速503。冷计算可能超过 Java 的2.8秒期限，当前请求回退预计算；计算完成后的请求复用新结果。日常预测仍由 `python python/ml/precompute.py` 发布，与实时通道相互独立。

## 协议

`POST /ml/forecast`，JSON请求示例：

```json
{"category":"黄瓜","days":3}
```

响应统一 `{code,msg,data}`。成功 data 字段：

| 字段 | 含义 |
|---|---|
| category / prod_name | 品类 / 代表品名 |
| model / mape_test | R2同口径择优模型 / 未四舍五入测试MAPE百分比 |
| yhat | 按日期排序的 `{date: "YYYY-MM-DD", yhat: 数值}` 数组 |
| admitted | MAPE ≤ 30% 是否准入 |
| snapshot_date | 最后入库日，预测从次日起算 |
| disclaimer | 预测结果仅供参考，不构成任何买卖建议 |

- 品类仅限大白菜、黄瓜、西红柿、猪肉、鸡蛋；days为整数1–7，省略默认7；字符串、布尔、额外字段与非法品类均HTTP400。
- 正常HTTP200/code200；超过门禁仍HTTP200，`admitted=false/yhat=[]`，属于质量拒绝。
- 读库失败、模型异常或计算繁忙HTTP503，错误响应不暴露凭据和内部异常内容。Java统一降级；前端不直接访问本服务。
- 与离线链路共用 `compare_category`：近730天、斤价日均、80/20切分、插值与MAPE择优完全一致；阈值与科学评估局限见 [模型报告](../docs/W4-MODEL-REPORT.md)。

## 自测

```powershell
python -m unittest discover -s python/tests -v
python python/ml/compare_models.py --help
```

R3共29例（原21+API与缓存/只读/门禁8例）。API测试使用注入引擎和临时SQLite，不训练真实模型、不读取业务库。真实快照复跑与浏览器停服回退证据见 [DEVLOG](../docs/DEVLOG.md)。停止入口进程可模拟算法服务不可用，重启并预热后再次点击看板“实时预测”恢复。
