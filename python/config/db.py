# -*- coding: utf-8 -*-
"""
数据库连接统一入口（里程碑0 · SQLite / MySQL 可切换）
=====================================================
- 当前默认后端: SQLite  → python/data/price.db（本机 MySQL 虽已安装 8.0.42，
  但 root 免密登录被拒、无可用凭据，故里程碑0先用 SQLite 零成本跑通）
- 切换 MySQL : 设置环境变量 APR_DB_BACKEND=mysql，
  并通过环境变量 APR_MYSQL_HOST/PORT/USER/PWD/DB 覆盖连接参数（或直接改下方 MYSQL_CONFIG），
  迁移时执行 python/config/migrate_to_mysql.py（W1 阶段提供）或手动执行 DDL_MYSQL。
- 铁律: 所有 SQL 一律参数化（SQLite 用 ?，MySQL 用 %s），严禁字符串拼接。
"""
import os
import sqlite3
from contextlib import closing
from pathlib import Path

# ---------- 后端选择（默认 sqlite） ----------
DB_BACKEND = os.environ.get("APR_DB_BACKEND", "sqlite").strip().lower()
if DB_BACKEND not in ("sqlite", "mysql"):
    raise ValueError(f"APR_DB_BACKEND 只能是 sqlite 或 mysql, 当前值: {DB_BACKEND}")

# SQLite 数据文件路径: python/data/price.db
SQLITE_PATH = Path(__file__).resolve().parents[1] / "data" / "price.db"

# ---------- MySQL 连接参数（迁移阶段使用, 密码从环境变量读取, 不硬编码） ----------
MYSQL_CONFIG = {
    "host": os.environ.get("APR_MYSQL_HOST", "127.0.0.1"),
    "port": int(os.environ.get("APR_MYSQL_PORT", "3306")),
    "user": os.environ.get("APR_MYSQL_USER", "root"),
    "password": os.environ.get("APR_MYSQL_PWD", ""),
    "database": os.environ.get("APR_MYSQL_DB", "agri_price_radar"),
    "charset": "utf8mb4",
}

# ---------- 表结构（字段与新发地接口真实返回对齐, 按日去重） ----------
# 去重键: (prod_name, pub_date, place, spec_info) 唯一约束, 空 NULL 统一存 ''
# （SQLite/MySQL 的 UNIQUE 对 NULL 不判重, 故 place/spec_info 规范化为空字符串）
DDL_SQLITE = """
CREATE TABLE IF NOT EXISTS price_daily (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,        -- 自增主键
    prod_name   TEXT    NOT NULL,                        -- 品名, 如: 大白菜
    prod_cat    TEXT,                                     -- 品类, 如: 白菜类
    low_price   REAL,                                     -- 最低价
    high_price  REAL,                                     -- 最高价
    avg_price   REAL,                                     -- 平均价
    place       TEXT    NOT NULL DEFAULT '',              -- 产地
    spec_info   TEXT    NOT NULL DEFAULT '',              -- 规格
    unit_info   TEXT,                                     -- 单位, 如: 元/公斤
    pub_date    TEXT    NOT NULL,                         -- 发布日期(纯日期 YYYY-MM-DD)
    created_at  TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    UNIQUE (prod_name, pub_date, place, spec_info)        -- 唯一约束: 去重键
);
CREATE INDEX IF NOT EXISTS idx_price_daily_prod_date ON price_daily (prod_name, pub_date);
"""

DDL_MYSQL = """
CREATE TABLE IF NOT EXISTS price_daily (
    id          BIGINT        PRIMARY KEY AUTO_INCREMENT COMMENT '自增主键',
    prod_name   VARCHAR(64)   NOT NULL COMMENT '品名',
    prod_cat    VARCHAR(64)   NULL     COMMENT '品类',
    low_price   DECIMAL(10,3) NULL     COMMENT '最低价',
    high_price  DECIMAL(10,3) NULL     COMMENT '最高价',
    avg_price   DECIMAL(10,3) NULL     COMMENT '平均价',
    place       VARCHAR(64)   NOT NULL DEFAULT '' COMMENT '产地',
    spec_info   VARCHAR(128)  NOT NULL DEFAULT '' COMMENT '规格',
    unit_info   VARCHAR(32)   NULL     COMMENT '单位',
    pub_date    DATE          NOT NULL COMMENT '发布日期',
    created_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_prod_date_place_spec (prod_name, pub_date, place, spec_info),
    INDEX idx_prod_date (prod_name, pub_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='新发地批发价日度明细(里程碑0)'
"""

# ---------- 参数化 upsert（SQLite: ON CONFLICT ... DO UPDATE ≈ MySQL 的 ON DUPLICATE KEY） ----------
UPSERT_SQLITE = """
INSERT INTO price_daily
    (prod_name, prod_cat, low_price, high_price, avg_price,
     place, spec_info, unit_info, pub_date)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT (prod_name, pub_date, place, spec_info) DO UPDATE SET
    prod_cat  = excluded.prod_cat,
    low_price = excluded.low_price,
    high_price= excluded.high_price,
    avg_price = excluded.avg_price,
    unit_info = excluded.unit_info,
    updated_at= datetime('now','localtime')
"""

UPSERT_MYSQL = """
INSERT INTO price_daily
    (prod_name, prod_cat, low_price, high_price, avg_price,
     place, spec_info, unit_info, pub_date)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
ON DUPLICATE KEY UPDATE
    prod_cat  = VALUES(prod_cat),
    low_price = VALUES(low_price),
    high_price= VALUES(high_price),
    avg_price = VALUES(avg_price),
    unit_info = VALUES(unit_info),
    updated_at= CURRENT_TIMESTAMP
"""


def get_connection():
    """获取数据库连接（按 DB_BACKEND 切换; 连接时自动建表, 幂等）"""
    if DB_BACKEND == "mysql":
        try:
            import pymysql  # 延迟导入: 未安装 pymysql 时不影响 SQLite 模式
        except ImportError as exc:
            raise RuntimeError("MySQL 后端需要先 pip install pymysql") from exc
        conn = pymysql.connect(**MYSQL_CONFIG)
        with conn.cursor() as cur:
            cur.execute(DDL_MYSQL)   # 幂等建表
        conn.commit()
        return conn
    SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(SQLITE_PATH))
    conn.executescript(DDL_SQLITE)   # 幂等建表
    return conn


def get_upsert_sql() -> str:
    """返回当前后端的参数化 upsert 语句（铁律: 占位符传参, 不拼接）"""
    return UPSERT_MYSQL if DB_BACKEND == "mysql" else UPSERT_SQLITE


def placeholder() -> str:
    """当前后端的占位符样式（SQLite: ?  /  MySQL: %s）"""
    return "%s" if DB_BACKEND == "mysql" else "?"


def cursor(conn):
    """跨后端游标上下文（sqlite3.Cursor 不支持 with, 用 closing 统一两种后端）"""
    return closing(conn.cursor())


if __name__ == "__main__":
    # 自测: 连接 + 建表 + 打印后端信息
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    conn = get_connection()
    with cursor(conn) as cur:
        cur.execute("SELECT COUNT(*) FROM price_daily")
        print(f"后端={DB_BACKEND}, sqlite路径={SQLITE_PATH}, price_daily 现有 {cur.fetchone()[0]} 条")
    conn.close()
