# -*- coding: utf-8 -*-
"""W4离线择优预计算。--snapshot 固定快照，--threshold 默认30；不采集、不改接口。
低阈值验证会撤下旧预测；验证后以默认阈值重跑恢复。
"""
import argparse
from datetime import datetime
from pathlib import Path
import sys
from zoneinfo import ZoneInfo
import pandas as pd
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config.constants import MAPE_THRESHOLD
from config.db import get_connection, get_upsert_sql, get_insert_log_sql, cursor, DB_BACKEND
from ml.model_common import HORIZON, admitted
from ml.compare_models import load_snapshot, compare_snapshot


def publish_results(conn, results, threshold=MAPE_THRESHOLD):
    """整批原子发布；撤下旧派生结果防止门禁拒绝后接口继续展示旧模型。
    既有 uk_pred/upsert 不变，同一快照重跑行内容幂等。
    """
    admitted(0, threshold)
    delete_sql = ("DELETE FROM predict_result WHERE category = %s" if DB_BACKEND == "mysql"
                  else "DELETE FROM predict_result WHERE category = ?")
    retire_sql = ("DELETE FROM predict_result WHERE category = %s AND (model <> %s OR predict_date < %s OR predict_date > %s)"
                  if DB_BACKEND == "mysql" else
                  "DELETE FROM predict_result WHERE category = ? AND (model <> ? OR predict_date < ? OR predict_date > ?)")
    lines, count = [], 0
    try:
        with cursor(conn) as cur:
            for result in results:
                category = result["category"]
                if not admitted(result["mape"], threshold):
                    cur.execute(delete_sql, (category,))
                    lines.append(f"{category}: {result['winner']} MAPE={result['mape']:.3f}% 超过{threshold:g}%，跳过写入并撤下旧预测")
                    continue
                end = pd.Timestamp(result["end"])
                cur.execute(retire_sql, (category, result["winner"],
                            (end + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
                            (end + pd.Timedelta(days=HORIZON)).strftime("%Y-%m-%d")))
                rows = [(category, result["prod_name"], (end + pd.Timedelta(days=i)).strftime("%Y-%m-%d"),
                         round(float(value), 3), result["winner"], round(result["mape"], 3), i)
                        for i, value in enumerate(result["forecast"], start=1)]
                cur.executemany(get_upsert_sql("predict"), rows)
                count += len(rows)
                lines.append(f"{category}: {result['winner']} MAPE={result['mape']:.3f}% 通过{threshold:g}%门槛，写入{len(rows)}条")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return {"rows_written": count, "detail": "; ".join(lines), "lines": lines}


def precompute_all(horizon=HORIZON, threshold=MAPE_THRESHOLD, snapshot=None, record_log=True):
    admitted(0, threshold)
    if horizon != HORIZON:
        raise ValueError("当前展示协议固定为未来7天")
    started = datetime.now(ZoneInfo("Asia/Shanghai")).replace(tzinfo=None)
    status, detail, count = "FAILED", "预计算未完成", 0
    conn = get_connection()
    try:
        results = compare_snapshot(load_snapshot(snapshot), horizon)
        summary = publish_results(conn, results, threshold)
        status, detail, count = "SUCCESS", summary["detail"], summary["rows_written"]
        print(detail, flush=True)
        return summary
    except Exception as exc:
        detail = f"预计算失败（{type(exc).__name__}），未发布新批次"
        raise
    finally:
        try:
            if record_log:
                with cursor(conn) as cur:
                    cur.execute(get_insert_log_sql(), ("precompute", status, detail[:1000], count,
                                started.isoformat(sep=" "), datetime.now(ZoneInfo("Asia/Shanghai")).replace(tzinfo=None).isoformat(sep=" ")))
                conn.commit()
        finally:
            conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--threshold", type=float, default=MAPE_THRESHOLD)
    args = parser.parse_args()
    precompute_all(threshold=args.threshold, snapshot=args.snapshot)
