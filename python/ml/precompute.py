# -*- coding: utf-8 -*-
"""
预测预计算（W1）：五品类 ARIMA × 未来7天 → predict_result 表
=============================================================
铁律（蓝图 §7 双通道）:
  - 只读已入库快照(price_daily), 不现场爬取;
  - 日常展示只读 predict_result 预计算表, 本任务由调度器每日夜间触发(21:00);
  - 所有输出携带模型标识 + 测试集MAPE; 前端展示必须附「预测结果仅供参考」。

运行: python python/ml/precompute.py     (或经 scheduler/run.py 定时触发)
"""
import sys
import warnings
from datetime import timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # 引入 python/config

import numpy as np                                              # noqa: E402
import pandas as pd                                             # noqa: E402
from config.db import (get_connection, get_upsert_sql, cursor,  # noqa: E402
                       DB_BACKEND, placeholder)
from config.constants import REPRESENTATIVES                    # noqa: E402

warnings.filterwarnings("ignore")     # ARIMA 收敛告警等噪音

HORIZON = 7                          # 预测天数
LOOKBACK_DAYS = 730                  # 训练窗口: 近两年日度均价
MIN_POINTS = 120                     # 最少观测数(不足则跳过该品类)
ARIMA_GRID = [(1, 1, 1), (2, 1, 1), (1, 1, 2), (2, 1, 2), (3, 1, 2)]


def load_daily_avg(conn, name: str):
    """代表品名 → 日度均价序列(单位治理: 仅取该品名主导单位的行)"""
    ph = placeholder()
    with cursor(conn) as cur:
        cur.execute(f"SELECT pub_date, avg_price, unit_info FROM price_daily "
                    f"WHERE prod_name = {ph} AND avg_price IS NOT NULL", (name,))
        df = pd.DataFrame(cur.fetchall(), columns=["pub_date", "avg_price", "unit_info"])
    if df.empty:
        return None
    df["pub_date"] = pd.to_datetime(df["pub_date"])
    # 跨后端兼容: MySQL DECIMAL 经 pymysql 返回 Decimal(object dtype), 必须显式转数值
    df["avg_price"] = pd.to_numeric(df["avg_price"], errors="coerce")
    df = df[df["avg_price"].notna()]
    units = df["unit_info"].dropna()
    if len(units):
        dom = str(units.mode().iat[0])
        df = df[(df["unit_info"] == dom) | (df["unit_info"].isna())]
    return df.groupby("pub_date")["avg_price"].mean().sort_index()


def arima_forecast(s: pd.Series, horizon: int = HORIZON):
    """连续日序列 → 前80%/后20%切分, 网格按AIC选一个ARIMA, 返回(阶数, 测试MAPE, 未来预测)"""
    from statsmodels.tsa.arima.model import ARIMA
    idx = pd.date_range(s.index[0], s.index[-1], freq="D")
    y = s.reindex(idx).interpolate(limit_direction="both")      # 少量缺测日线性插值
    n = len(y)
    n_tr = int(n * 0.8)
    train, test = y.iloc[:n_tr].to_numpy(), y.iloc[n_tr:].to_numpy()

    best_order, best_aic, best_fit = None, np.inf, None
    for order in ARIMA_GRID:
        try:
            m = ARIMA(train, order=order).fit()
            if m.aic < best_aic:
                best_order, best_aic, best_fit = order, m.aic, m
        except Exception as exc:
            print(f"  ARIMA{order} 拟合失败: {exc}")
    if best_fit is None:
        raise RuntimeError("所有候选 ARIMA 阶数均拟合失败")

    pred_test = np.asarray(best_fit.forecast(steps=len(test)))
    mape = float(np.mean(np.abs((test - pred_test) / test)) * 100)

    final = ARIMA(y.to_numpy(), order=best_order).fit()          # 全量重估同一阶数
    fc = np.asarray(final.forecast(steps=horizon))
    return best_order, mape, fc


def precompute_all(horizon: int = HORIZON) -> dict:
    """对五个品类跑 ARIMA 并 upsert 进 predict_result; 返回摘要(供 collect_log)"""
    conn = get_connection()
    upsert_sql = get_upsert_sql("predict")
    cutoff_note = pd.Timestamp.now().normalize() - pd.Timedelta(days=LOOKBACK_DAYS)
    lines, rows_written = [], 0

    for cat, name in REPRESENTATIVES:
        s_full = load_daily_avg(conn, name)
        if s_full is None or len(s_full) < MIN_POINTS:
            lines.append(f"{cat}({name}): 数据不足({0 if s_full is None else len(s_full)} 点 < {MIN_POINTS}), 跳过")
            continue
        s = s_full[s_full.index >= cutoff_note]
        order, mape, fc = arima_forecast(s, horizon)
        model = f"ARIMA({order[0]},{order[1]},{order[2]})"
        last_date = s.index[-1]
        with cursor(conn) as cur:
            for i, v in enumerate(fc, start=1):
                cur.execute(upsert_sql, (
                    cat, name, (last_date + timedelta(days=i)).strftime("%Y-%m-%d"),
                    round(float(v), 3), model, round(mape, 3), i,
                ))
                rows_written += 1
        conn.commit()
        lines.append(f"{cat}({name}): {model}, 测试集MAPE={mape:.2f}%, "
                     f"预测 {last_date + timedelta(days=1):%Y-%m-%d} ~ "
                     f"{last_date + timedelta(days=horizon):%Y-%m-%d} 共{horizon}条")
        print(f"[{cat}] {model} MAPE={mape:.2f}% -> 未来{horizon}天已写入")

    conn.close()
    detail = "; ".join(lines)
    print(f"\n预计算完成(后端={DB_BACKEND}): {detail}")
    return {"rows_written": rows_written, "detail": detail, "lines": lines}


if __name__ == "__main__":
    precompute_all()
