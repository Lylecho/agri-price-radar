# -*- coding: utf-8 -*-
"""通用 SQL 脚本执行器（W2 起 DDL/种子数据维护用）
用法: python python/scripts/run_sql.py <sql文件路径> [<sql文件路径> ...]
凭据来自 python/.env（与采集/预计算同源）, 不在命令行暴露密码。
"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "python"))

from config.db import DB_BACKEND, MYSQL_CONFIG, get_connection, cursor  # noqa: E402


def split_statements(sql_text: str):
    """先剥离整行注释再按分号切分(注释内的分号不得影响切分),
    跳过空段。本项目 SQL 不含带分号的字符串字面量, 故无需更复杂的词法分析。"""
    no_comments = "\n".join(
        ln for ln in sql_text.splitlines() if not ln.strip().startswith("--"))
    for raw in no_comments.split(";"):
        stmt = raw.strip()
        if stmt:
            yield stmt


def run_file(conn, path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    n = 0
    with cursor(conn) as cur:
        for stmt in split_statements(text):
            cur.execute(stmt)
            n += 1
    conn.commit()
    print(f"  {path.name}: 执行 {n} 条语句 OK")
    return n


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    if DB_BACKEND != "mysql":
        print(f"!! 当前后端为 {DB_BACKEND}, 本脚本面向 MySQL; 请在 python/.env 设置 APR_DB_BACKEND=mysql")
        return 1
    print(f"目标: {MYSQL_CONFIG['user']}@{MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}"
          f"/{MYSQL_CONFIG['database']}")
    conn = get_connection()
    for arg in sys.argv[1:]:
        p = Path(arg)
        if not p.is_absolute():
            p = ROOT / arg
        if not p.exists():
            print(f"!! 文件不存在: {p}")
            conn.close()
            return 1
        run_file(conn, p)
    conn.close()
    print("完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
