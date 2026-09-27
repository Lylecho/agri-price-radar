# -*- coding: utf-8 -*-
"""离线对比：--snapshot 复用日均快照；只读入库数据，不采集、不写预测表。"""
import argparse
from dataclasses import asdict
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
from config.constants import REPRESENTATIVES, MAPE_THRESHOLD
from config.db import DB_BACKEND, get_connection, cursor
from ml.arima_model import arima_forecast
from ml.prophet_model import prophet_forecast
from ml.model_common import LOOKBACK_DAYS, HORIZON, prepare_series, choose_best, admitted


def load_snapshot(path=None, connection_factory=get_connection):
    """同一事务读取斤价日均快照；窗口锚定数据截止日，支持离线复现。"""
    if path:
        data = pd.read_csv(path, parse_dates=["date"], float_precision="round_trip")
    else:
        conn = connection_factory()
        rows = []
        sql = ("SELECT pub_date, AVG(avg_price) FROM price_daily WHERE prod_name = %s "
               "AND unit_info = %s AND avg_price IS NOT NULL GROUP BY pub_date ORDER BY pub_date"
               if DB_BACKEND == "mysql" else
               "SELECT pub_date, AVG(avg_price) FROM price_daily WHERE prod_name = ? "
               "AND unit_info = ? AND avg_price IS NOT NULL GROUP BY pub_date ORDER BY pub_date")
        try:
            for category, name in REPRESENTATIVES:
                with cursor(conn) as cur:
                    cur.execute(sql, (name, "斤"))
                    rows.extend((category, name, date, float(price)) for date, price in cur.fetchall())
        finally:
            conn.close()
        data = pd.DataFrame(rows, columns=["category", "prod_name", "date", "price"])
        data["date"] = pd.to_datetime(data["date"])
    if data.empty:
        raise ValueError("快照为空")
    data["price"] = pd.to_numeric(data["price"], errors="raise")
    end = data["date"].max()
    data = data[data["date"] >= end - pd.Timedelta(days=LOOKBACK_DAYS - 1)]
    return data.sort_values(["category", "date"]).reset_index(drop=True)


def compare_category(data, category, name, horizon=HORIZON):
    subset = data[(data.category == category) & (data.prod_name == name)]
    series = pd.Series(subset.price.to_numpy(), index=pd.DatetimeIndex(subset.date))
    full, train, test = prepare_series(series)
    candidates = [arima_forecast(series, horizon), prophet_forecast(series, horizon)]
    winner = choose_best(candidates)
    models = []
    for candidate in candidates:
        row = asdict(candidate)
        row["forecast"] = candidate.forecast.tolist()
        models.append(row)
    return {"category": category, "prod_name": name, "start": str(full.index[0].date()),
                    "end": str(full.index[-1].date()), "observed": len(series),
                    "missing": len(full) - len(series), "train_n": len(train), "test_n": len(test),
                    "test_start": str(test.index[0].date()), "models": models,
                    "winner": winner.model, "mape": winner.mape,
                    "forecast": winner.forecast.tolist()}


def compare_snapshot(data, horizon=HORIZON):
    results = []
    for category, name in REPRESENTATIVES:
        row = compare_category(data, category, name, horizon)
        results.append(row)
        print(f"{category}: " + " / ".join(
            f"{m['model']} MAPE={m['mape']:.3f}% 耗时={m['seconds']:.2f}s" for m in row["models"])
            + f" -> {row['winner']}", flush=True)
    return results


def table(results, threshold=MAPE_THRESHOLD):
    lines = ["| 品类 | ARIMA阶数 | ARIMA MAPE% | ARIMA耗时s | Prophet MAPE% | Prophet耗时s | 择优 | 准入 |",
             "|---|---|---:|---:|---:|---:|---|---|"]
    for r in results:
        a, p = r["models"]
        lines.append(f"| {r['category']} | {a['model']} | {a['mape']:.3f} | {a['seconds']:.2f} | "
                     f"{p['mape']:.3f} | {p['seconds']:.2f} | {r['winner']} | {'通过' if admitted(r['mape'], threshold) else '暂停展示'} |")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("python/data/model-comparison"))
    args = parser.parse_args()
    data = load_snapshot(args.snapshot)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    csv = data.to_csv(index=False, float_format="%.17g", date_format="%Y-%m-%d", lineterminator="\n")
    (args.output_dir / "snapshot.csv").write_text(csv, encoding="utf-8")
    results = compare_snapshot(data)
    payload = {"snapshot_sha256": hashlib.sha256(csv.encode()).hexdigest(), "threshold": MAPE_THRESHOLD,
               "versions": {p: version(p) for p in ("prophet", "statsmodels", "pandas", "numpy")},
               "results": results}
    (args.output_dir / "comparison.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    report = table(results)
    (args.output_dir / "comparison.md").write_text(report + "\n", encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
