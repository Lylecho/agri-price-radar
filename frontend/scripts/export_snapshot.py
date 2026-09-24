# -*- coding: utf-8 -*-
"""导出近90天五品类日度均价快照 JSON(供前端规范页图表演示)
铁律: 只读已入库快照, 不现场爬取。数据源: python/data/price.db
运行: python frontend/scripts/export_snapshot.py
"""
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]        # 工作区根
sys.path.insert(0, str(ROOT / "python"))          # 引入 python/config

import pandas as pd                               # noqa: E402
from config.db import get_connection, cursor      # noqa: E402

# 品类展示名 -> 库中代表品名(采集探测 + 2026-09单位核查结论)
# 注意: 鸡蛋用"散鸡蛋"——箱/筐鸡蛋为整件计价(箱≈40+斤/箱, 200元+/箱), 且其"斤"标注被箱价污染, 不可同轴对比
REPRESENTATIVES = [
    ("大白菜", "大白菜"),
    ("黄瓜", "黄瓜"),
    ("西红柿", "番茄"),
    ("猪肉", "白条猪"),
    ("鸡蛋", "散鸡蛋"),
]
DAYS = 90


def main():
    conn = get_connection()
    with cursor(conn) as cur:
        cur.execute("SELECT prod_name, pub_date, avg_price, unit_info "
                    "FROM price_daily WHERE avg_price IS NOT NULL")
        df = pd.DataFrame(cur.fetchall(), columns=["prod_name", "pub_date", "avg_price", "unit_info"])
    conn.close()
    df["pub_date"] = pd.to_datetime(df["pub_date"])
    # 跨后端兼容: MySQL DECIMAL → Decimal(object), 显式转数值
    df["avg_price"] = pd.to_numeric(df["avg_price"], errors="coerce")
    df = df[df["avg_price"].notna()]

    ref = df["pub_date"].max()
    idx = pd.date_range(ref - timedelta(days=DAYS - 1), ref)
    out = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source": "北京新发地批发价(入库快照)",
        "days": DAYS,
        "dates": [d.strftime("%Y-%m-%d") for d in idx],
        "series": [],
    }
    for disp, name in REPRESENTATIVES:
        sub = df[df["prod_name"] == name]
        # 单位异构治理: 仅取该品名主导单位的行(如散鸡蛋只取"斤"), 剔除整件价污染
        units = sub["unit_info"].dropna()
        if len(units):
            dom = str(units.mode().iat[0])
            sub = sub[(sub["unit_info"] == dom) | (sub["unit_info"].isna())]
        s = (sub.groupby("pub_date")["avg_price"].mean().sort_index().reindex(idx))
        out["series"].append({
            "name": disp,
            "values": [None if pd.isna(v) else round(float(v), 3) for v in s],
        })

    dest = Path(__file__).resolve().parents[1] / "src" / "assets" / "data" / "price_snapshot_90d.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"已导出: {dest} ({len(out['dates'])} 天 × {len(out['series'])} 品类, 截至 {ref:%Y-%m-%d})")


if __name__ == "__main__":
    main()
