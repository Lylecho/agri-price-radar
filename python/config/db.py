# -*- coding: utf-8 -*-
"""
数据库统一入口 v2（W1 采集服务化）
==================================
- 后端: MySQL(生产, APR_DB_BACKEND=mysql) / SQLite(开发与降级, 默认)
- 凭据: 环境变量或 python/.env(自动加载, 该文件已 gitignored, 密码永不入库)
- DDL v2(2026-09-24 单位治理): price_daily 唯一键纳入 unit_info(修复箱/斤异单位互撞覆盖);
  新增 predict_result(预计算) 与 collect_log(任务日志)
- 铁律: 所有 SQL 一律参数化(SQLite 用 ? / MySQL 用 %s), 严禁字符串拼接
"""
import os
import sqlite3
from contextlib import closing
from pathlib import Path

# ---------- .env 加载(不存在则跳过; 已存在的环境变量优先) ----------
ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
if ENV_PATH.exists():
    for _line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

# ---------- 后端选择 ----------
DB_BACKEND = os.environ.get("APR_DB_BACKEND", "sqlite").strip().lower()
if DB_BACKEND not in ("sqlite", "mysql"):
    raise ValueError(f"APR_DB_BACKEND 只能是 sqlite 或 mysql, 当前值: {DB_BACKEND}")

SQLITE_PATH = Path(__file__).resolve().parents[1] / "data" / "price.db"

MYSQL_CONFIG = {
    "host": os.environ.get("APR_MYSQL_HOST", "127.0.0.1"),
    "port": int(os.environ.get("APR_MYSQL_PORT", "3306")),
    "user": os.environ.get("APR_MYSQL_USER", "root"),
    "password": os.environ.get("APR_MYSQL_PWD", ""),
    "database": os.environ.get("APR_MYSQL_DB", "agri_price_radar"),
    "charset": "utf8mb4",
}

# ================================================================ DDL · MySQL
DDL_PRICE_DAILY_MYSQL = """
CREATE TABLE IF NOT EXISTS price_daily (
    id          BIGINT        PRIMARY KEY AUTO_INCREMENT COMMENT '自增主键',
    prod_name   VARCHAR(64)   NOT NULL COMMENT '品名(接口原值)',
    prod_cat    VARCHAR(64)   NULL     COMMENT '品类',
    low_price   DECIMAL(10,3) NULL COMMENT '最低价',
    high_price  DECIMAL(10,3) NULL COMMENT '最高价',
    avg_price   DECIMAL(10,3) NULL COMMENT '平均价',
    place       VARCHAR(64)   NOT NULL DEFAULT '' COMMENT '产地',
    spec_info   VARCHAR(128)  NOT NULL DEFAULT '' COMMENT '规格',
    unit_info   VARCHAR(16)   NOT NULL DEFAULT '' COMMENT '计价单位: 斤/箱/筐/个',
    pub_date    DATE          NOT NULL COMMENT '发布日期',
    created_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_price (prod_name, pub_date, place, spec_info, unit_info),
    INDEX idx_prod_date (prod_name, pub_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='新发地批发价日度明细'
"""

DDL_PREDICT_MYSQL = """
CREATE TABLE IF NOT EXISTS predict_result (
    id            BIGINT        PRIMARY KEY AUTO_INCREMENT,
    category      VARCHAR(32)   NOT NULL COMMENT '展示品类',
    prod_name     VARCHAR(64)   NOT NULL COMMENT '代表品名',
    predict_date  DATE          NOT NULL COMMENT '预测目标日',
    yhat          DECIMAL(10,3) NOT NULL COMMENT '预测均价(元/斤)',
    model         VARCHAR(32)   NOT NULL COMMENT '模型标识, 如 ARIMA(2,1,1)',
    mape_test     DECIMAL(6,3)  NULL COMMENT '测试集MAPE(%)',
    horizon       TINYINT       NOT NULL COMMENT '距最后实测日天数(1-7)',
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_pred (category, predict_date, model),
    INDEX idx_cat_date (category, predict_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='预测预计算(日常展示只读此表)'
"""

DDL_COLLECT_LOG_MYSQL = """
CREATE TABLE IF NOT EXISTS collect_log (
    id            BIGINT        PRIMARY KEY AUTO_INCREMENT,
    job           VARCHAR(32)   NOT NULL COMMENT '任务名: collect/precompute',
    status        VARCHAR(16)   NOT NULL COMMENT 'SUCCESS/FAILED',
    detail        VARCHAR(1000) NULL COMMENT '摘要',
    rows_written  INT           NULL COMMENT '写入/更新行数',
    started_at    DATETIME      NOT NULL,
    finished_at   DATETIME      NULL,
    INDEX idx_job_time (job, started_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='定时任务运行日志'
"""

# ================================================================ DDL · SQLite
DDL_PRICE_DAILY_SQLITE = """
CREATE TABLE IF NOT EXISTS price_daily (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    prod_name   TEXT    NOT NULL,
    prod_cat    TEXT,
    low_price   REAL,
    high_price  REAL,
    avg_price   REAL,
    place       TEXT    NOT NULL DEFAULT '',
    spec_info   TEXT    NOT NULL DEFAULT '',
    unit_info   TEXT    NOT NULL DEFAULT '',
    pub_date    TEXT    NOT NULL,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    UNIQUE (prod_name, pub_date, place, spec_info, unit_info)
);
"""

DDL_SQLITE = DDL_PRICE_DAILY_SQLITE + """
CREATE INDEX IF NOT EXISTS idx_price_daily_prod_date ON price_daily (prod_name, pub_date);
CREATE TABLE IF NOT EXISTS predict_result (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    category      TEXT    NOT NULL,
    prod_name     TEXT    NOT NULL,
    predict_date  TEXT    NOT NULL,
    yhat          REAL    NOT NULL,
    model         TEXT    NOT NULL,
    mape_test     REAL,
    horizon       INTEGER NOT NULL,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at    TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    UNIQUE (category, predict_date, model)
);
CREATE INDEX IF NOT EXISTS idx_pred_cat_date ON predict_result (category, predict_date);
CREATE TABLE IF NOT EXISTS collect_log (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    job           TEXT    NOT NULL,
    status        TEXT    NOT NULL,
    detail        TEXT,
    rows_written  INTEGER,
    started_at    TEXT    NOT NULL,
    finished_at   TEXT
);
CREATE INDEX IF NOT EXISTS idx_cl_job_time ON collect_log (job, started_at);
"""

# ================================================================ 参数化 SQL
UPSERT_PRICE_SQLITE = """
INSERT INTO price_daily
    (prod_name, prod_cat, low_price, high_price, avg_price, place, spec_info, unit_info, pub_date)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT (prod_name, pub_date, place, spec_info, unit_info) DO UPDATE SET
    prod_cat = excluded.prod_cat, low_price = excluded.low_price,
    high_price = excluded.high_price, avg_price = excluded.avg_price,
    unit_info = excluded.unit_info, updated_at = datetime('now','localtime')
"""

UPSERT_PRICE_MYSQL = """
INSERT INTO price_daily
    (prod_name, prod_cat, low_price, high_price, avg_price, place, spec_info, unit_info, pub_date)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
ON DUPLICATE KEY UPDATE
    prod_cat = VALUES(prod_cat), low_price = VALUES(low_price),
    high_price = VALUES(high_price), avg_price = VALUES(avg_price),
    unit_info = VALUES(unit_info), updated_at = CURRENT_TIMESTAMP
"""

UPSERT_PREDICT_SQLITE = """
INSERT INTO predict_result
    (category, prod_name, predict_date, yhat, model, mape_test, horizon)
VALUES (?, ?, ?, ?, ?, ?, ?)
ON CONFLICT (category, predict_date, model) DO UPDATE SET
    prod_name = excluded.prod_name, yhat = excluded.yhat,
    mape_test = excluded.mape_test, horizon = excluded.horizon,
    updated_at = datetime('now','localtime')
"""

UPSERT_PREDICT_MYSQL = """
INSERT INTO predict_result
    (category, prod_name, predict_date, yhat, model, mape_test, horizon)
VALUES (%s, %s, %s, %s, %s, %s, %s)
ON DUPLICATE KEY UPDATE
    prod_name = VALUES(prod_name), yhat = VALUES(yhat),
    mape_test = VALUES(mape_test), horizon = VALUES(horizon), updated_at = CURRENT_TIMESTAMP
"""

INSERT_LOG_SQLITE = ("INSERT INTO collect_log "
                     "(job, status, detail, rows_written, started_at, finished_at) "
                     "VALUES (?, ?, ?, ?, ?, ?)")
INSERT_LOG_MYSQL = ("INSERT INTO collect_log "
                    "(job, status, detail, rows_written, started_at, finished_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s)")


# ================================================================ 连接与升级
def cursor(conn):
    """跨后端游标上下文(sqlite3.Cursor 不支持 with, 用 closing 统一)"""
    return closing(conn.cursor())


def _sqlite_needs_upgrade(conn) -> bool:
    """v1→v2 检测: price_daily 存在但没有任何包含 unit_info 的唯一索引"""
    with cursor(conn) as cur:
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='price_daily'")
        if cur.fetchone() is None:
            return False                       # 表不存在, executescript 会按 v2 新建
        cur.execute("PRAGMA index_list('price_daily')")
        uniq = [r[1] for r in cur.fetchall() if r[2]]          # (seq, name, unique, ...)
        for idx in uniq:
            cur.execute(f"PRAGMA index_info('{idx}')")         # 只查索引名, 无用户输入
            cols = [r[2] for r in cur.fetchall()]
            if "unit_info" in cols:
                return False                   # 已是 v2
        return True


def sqlite_upgrade_v2(conn) -> None:
    """v1→v2 迁移(幂等): 重建 price_daily 使 unit_info 入唯一键, 旧行全量保留。
    注: 此前 v1 时期被覆盖丢失的行无法找回, 如需完整可重跑全量采集。"""
    if not _sqlite_needs_upgrade(conn):
        return
    with cursor(conn) as cur:
        cur.execute("SELECT COUNT(*) FROM price_daily")
        before = cur.fetchone()[0]
        cur.execute("DROP INDEX IF EXISTS idx_price_daily_prod_date")   # 防改名后索引名占用
        cur.execute("ALTER TABLE price_daily RENAME TO price_daily_v1")
    conn.executescript(DDL_PRICE_DAILY_SQLITE)                          # 新建 v2 表
    with cursor(conn) as cur:
        cur.execute("""
            INSERT INTO price_daily
                (prod_name, prod_cat, low_price, high_price, avg_price,
                 place, spec_info, unit_info, pub_date)
            SELECT prod_name, prod_cat, low_price, high_price, avg_price,
                   place, spec_info, COALESCE(unit_info, ''), pub_date
            FROM price_daily_v1
        """)
        cur.execute("DROP TABLE price_daily_v1")
    conn.commit()
    conn.executescript(DDL_SQLITE)                                      # 补齐索引与其余表(幂等)
    with cursor(conn) as cur:
        cur.execute("SELECT COUNT(*) FROM price_daily")
        after = cur.fetchone()[0]
    print(f"[db] price_daily v1→v2 迁移完成(unit_info 入唯一键): {before} 行 -> {after} 行")


def get_connection():
    """获取连接(自动建表; SQLite 自动执行 v1→v2 升级; MySQL 自动建库)"""
    if DB_BACKEND == "mysql":
        try:
            import pymysql
        except ImportError as exc:
            raise RuntimeError("MySQL 后端需要先: pip install pymysql") from exc
        cfg = dict(MYSQL_CONFIG)
        db_name = cfg.pop("database")
        conn = pymysql.connect(**cfg)                       # 先连服务端
        with conn.cursor() as cur:
            cur.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                        "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        conn.select_db(db_name)
        for ddl in (DDL_PRICE_DAILY_MYSQL, DDL_PREDICT_MYSQL, DDL_COLLECT_LOG_MYSQL):
            with conn.cursor() as cur:
                cur.execute(ddl)                            # 幂等建表
        conn.commit()
        return conn

    SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(SQLITE_PATH))
    sqlite_upgrade_v2(conn)                                 # v1→v2(内部幂等)
    conn.executescript(DDL_SQLITE)                          # 幂等建表/索引
    return conn


def get_upsert_sql(kind: str = "price") -> str:
    """参数化 upsert 语句(kind: price | predict)"""
    if kind == "predict":
        return UPSERT_PREDICT_MYSQL if DB_BACKEND == "mysql" else UPSERT_PREDICT_SQLITE
    return UPSERT_PRICE_MYSQL if DB_BACKEND == "mysql" else UPSERT_PRICE_SQLITE


def get_insert_log_sql() -> str:
    return INSERT_LOG_MYSQL if DB_BACKEND == "mysql" else INSERT_LOG_SQLITE


def placeholder() -> str:
    """当前后端的参数占位符(SQLite: ? / MySQL: %s), 供构造参数化查询使用"""
    return "%s" if DB_BACKEND == "mysql" else "?"


if __name__ == "__main__":
    # 自测: 连接 + 建表/升级 + 打印各表行数
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    conn = get_connection()
    with cursor(conn) as cur:
        for t in ("price_daily", "predict_result", "collect_log"):
            cur.execute(f"SELECT COUNT(*) FROM {t}")        # 表名为代码内常量, 无注入
            print(f"后端={DB_BACKEND} | {t}: {cur.fetchone()[0]} 行 | sqlite路径={SQLITE_PATH if DB_BACKEND=='sqlite' else '-'}")
    conn.close()
