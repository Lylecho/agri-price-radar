# -*- coding: utf-8 -*-
"""
SQLite → MySQL 存量迁移（W1）
==============================
前提: python/.env 已配置 APR_DB_BACKEND=mysql 及凭据(模板见 python/.env.example)
运行: python python/scripts/migrate_to_mysql.py
特性: upsert 幂等, 可重复执行; 迁移后所有模块(db.py 加载 .env)自动走 MySQL
"""
import sqlite3
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]          # 工作区根
sys.path.insert(0, str(ROOT / "python"))            # 引入 python/config

from config.db import (DB_BACKEND, MYSQL_CONFIG, SQLITE_PATH,          # noqa: E402
                       DDL_SQLITE, sqlite_upgrade_v2,
                       get_connection, cursor,
                       UPSERT_PRICE_MYSQL, UPSERT_PREDICT_MYSQL,
                       INSERT_LOG_MYSQL)

CHUNK = 1000


def copy_table(sq, my, src_sql: str, insert_sql: str, label: str) -> int:
    """流式分批拷贝(参数化), 返回行数"""
    n = 0
    cur_sq = sq.execute(src_sql)
    with cursor(my) as cur_my:
        while True:
            rows = cur_sq.fetchmany(CHUNK)
            if not rows:
                break
            cur_my.executemany(insert_sql, rows)
            n += len(rows)
    my.commit()
    print(f"  {label}: 迁移 {n} 行")
    return n


def main() -> int:
    if DB_BACKEND != "mysql":
        print("!! 请先在 python/.env 设置 APR_DB_BACKEND=mysql 并填写凭据(见 .env.example)")
        return 1
    print(f"MySQL 目标: {MYSQL_CONFIG['user']}@{MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}"
          f"/{MYSQL_CONFIG['database']}")

    # 1) SQLite 侧先升级到 v2 结构(幂等), 确保两端 schema 一致
    sq = sqlite3.connect(str(SQLITE_PATH))
    sqlite_upgrade_v2(sq)
    sq.executescript(DDL_SQLITE)

    # 2) MySQL 侧建库建表(幂等)
    my = get_connection()
    print("开始迁移 ...")
    total = 0
    total += copy_table(
        sq, my,
        "SELECT prod_name, prod_cat, low_price, high_price, avg_price, "
        "place, spec_info, unit_info, pub_date FROM price_daily",
        UPSERT_PRICE_MYSQL, "price_daily")
    total += copy_table(
        sq, my,
        "SELECT category, prod_name, predict_date, yhat, model, mape_test, horizon "
        "FROM predict_result",
        UPSERT_PREDICT_MYSQL, "predict_result")
    total += copy_table(
        sq, my,
        "SELECT job, status, detail, rows_written, started_at, finished_at FROM collect_log",
        INSERT_LOG_MYSQL, "collect_log")

    # 3) 校验
    print("== MySQL 侧行数校验 ==")
    with cursor(my) as cur:
        for t in ("price_daily", "predict_result", "collect_log"):
            cur.execute(f"SELECT COUNT(*) FROM {t}")   # 表名为代码内常量, 无注入
            print(f"  {t}: {cur.fetchone()[0]} 行")
    sq.close()
    my.close()
    print(f"迁移完成, 共 {total} 行(upsert 幂等, 可重复执行)。后续所有模块将直接读写 MySQL。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
