# -*- coding: utf-8 -*-
"""
新发地批发价格采集器 v2（W1 采集服务化）
=========================================
接口 : POST http://www.xinfadi.com.cn/getPriceData.html（字段以真实返回为准, 分页总数= count）

采集铁律（AGENTS.md / 蓝图 §9）:
  1) 频率 ≤ 1次/秒（页间 sleep ≥1s）
  2) 必须携带 User-Agent（ASCII, 禁中文——HTTP 头 latin-1 限制）
  3) 解析前先打印真实返回确认字段（probe 子命令）
  4) SQL 一律参数化 + executemany, 唯一约束(v2 含 unit_info) + upsert 去重
  5) 快照策略: 只写库, 分析/预测一律读库

用法:
  python python/collector/xinfadi.py probe              # 单页探测: 打印第一条真实JSON + 品类检索效果
  python python/collector/xinfadi.py collect            # 全量采集(接口可回溯的全部历史, 上限2022-01-01)
  python python/collector/xinfadi.py collect --days 3   # 增量: 只采最近3天(调度器用)
  python python/collector/xinfadi.py collect --only 大白菜,黄瓜

供调度器导入: from collector.xinfadi import collect
  collect(days=3) -> {"categories": [...], "rows_written": int, "anomalies": [...]}
"""
import argparse
import json
import math
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

# Windows 控制台中文输出保护
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import requests

# 使 collector/ 能导入 python/ 下的 config 包
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config.db import (get_connection, get_upsert_sql, cursor,  # noqa: E402
                       DB_BACKEND, placeholder)
from config.constants import CATEGORIES, OVERRIDE               # noqa: E402

API_URL = "http://www.xinfadi.com.cn/getPriceData.html"
PAGE_LIMIT = 200      # 单页条数（接口实际上限 200, 超出会被截断）
INTERVAL = 1.0        # 请求间隔（秒）—— 铁律: ≤1次/秒
RETRIES = 3           # 单页失败重试次数（带退避）
MAX_PAGES = 2000      # 每品类安全页数上限, 防御死循环

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 "
                   "agri-price-radar/1.0 (thesis)"),
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Referer": "http://www.xinfadi.com.cn/price.html",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01",
}

# 替换词仍检索不到时的自动降级候选
FALLBACK = {"白条猪": ["前臀尖", "后臀尖"], "番茄": ["西红柿"]}

anomalies = []   # 异常台账


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------------------------------------------------------------- 请求层
def fetch_page(prod_name: str, current: int, limit: int = PAGE_LIMIT,
               d_start: str = "", d_end: str = ""):
    """请求一页; 可选日期窗口(YYYY-MM-DD); 成功返回 (dict, 耗时s), 重试耗尽返回 (None, None)"""
    payload = {
        "limit": str(limit),
        "current": str(current),
        "pubDateStartTime": d_start,
        "pubDateEndTime": d_end,
        "prodPcatid": "",
        "prodCatid": "",
        "prodName": prod_name,
    }
    for attempt in range(1, RETRIES + 1):
        t0 = time.time()
        try:
            resp = requests.post(API_URL, data=payload, headers=HEADERS, timeout=20)
            cost = time.time() - t0
            resp.raise_for_status()
            # 响应编码自适应: 优先 utf-8, 失败回退 gbk（新发地响应含中文）
            try:
                txt = resp.content.decode("utf-8")
            except UnicodeDecodeError:
                txt = resp.content.decode("gbk", errors="replace")
            js = json.loads(txt)
            if str(js.get("errcode", "0")) != "0":
                raise RuntimeError(f"errcode={js.get('errcode')}, errstr={js.get('errstr')}")
            return js, cost
        except Exception as exc:
            anomalies.append(f"{prod_name} 第{current}页 第{attempt}/{RETRIES}次请求失败: "
                             f"{type(exc).__name__}: {exc}")
            if attempt < RETRIES:
                time.sleep(2 * attempt)   # 退避 2s/4s
    return None, None


def total_of(js) -> int:
    """接口返回的总条数字段（实测为 count, 兼容 total）"""
    return int(js.get("count") or js.get("total") or 0)


# ---------------------------------------------------------------- 解析层（字段以 probe 确认为准）
def to_f(v):
    """价格字段安全转 float（接口返回字符串或空）"""
    try:
        if v is None:
            return None
        s = str(v).strip()
        if s in ("", "-"):
            return None
        return float(s)
    except (TypeError, ValueError):
        return None


def parse_rows(lst: list, cat: str) -> list:
    """接口行 → 参数化 upsert 元组; 日期非法的行跳过并记入异常台账"""
    rows, bad = [], 0
    for it in lst:
        pub = str(it.get("pubDate") or "").strip()
        d = pub[:10]
        try:
            datetime.strptime(d, "%Y-%m-%d")   # 校验日期合法
        except ValueError:
            bad += 1
            continue
        rows.append((
            str(it.get("prodName") or "").strip(),
            str(it.get("prodCat") or "").strip() or None,
            to_f(it.get("lowPrice")),
            to_f(it.get("highPrice")),
            to_f(it.get("avgPrice")),
            str(it.get("place") or "").strip(),
            str(it.get("specInfo") or "").strip(),
            str(it.get("unitInfo") or "").strip(),
            d,
        ))
    if bad:
        anomalies.append(f"{cat}: {bad} 条记录 pubDate 无法解析, 已跳过")
    return rows


# ---------------------------------------------------------------- probe: 字段确认
def cmd_probe() -> int:
    log(f"数据库后端: {DB_BACKEND}")
    log("步骤1: 向新发地接口发一次单页请求(limit=10), 完整打印第一条真实返回 ...")
    js, cost = fetch_page("大白菜", 1, limit=10)
    if js is None:
        log("!! 首次请求失败, 请检查网络后重试")
        return 1
    rows = js.get("list") or []
    print("\n========== 真实返回 · 第一条完整JSON ==========")
    print(json.dumps(rows[0], ensure_ascii=False, indent=2) if rows else "(list 为空!)")
    print("========== 字段名清单 ==========")
    print(list(rows[0].keys()) if rows else "无")
    print(f"(本页 {len(rows)} 条, 接口 count={total_of(js)}, 耗时 {cost:.2f}s)\n")

    time.sleep(INTERVAL)
    log("步骤2: 核查 5 个品类词的检索效果 ...")
    for term in CATEGORIES:
        js2, _ = fetch_page(term, 1, limit=10)
        if js2 is None:
            print(f"  {term}: 请求失败")
            time.sleep(INTERVAL)
            continue
        lst = js2.get("list") or []
        names = sorted({str(r.get("prodName", "")).strip() for r in lst})
        print(f"  {term}: count={total_of(js2)}, 首页品名样本={names[:6]}")
        time.sleep(INTERVAL)
    print()
    return 0


# ---------------------------------------------------------------- 品类词解析与统计
def resolve_term(term: str) -> str:
    """先应用用户确认的 OVERRIDE 替换, 再校验检索有效性, 必要时自动降级"""
    if term in OVERRIDE:
        anomalies.append(f"品类词'{term}'按确认方案替换为'{OVERRIDE[term]}'(原词无有效行情数据)")
        term = OVERRIDE[term]
    js, _ = fetch_page(term, 1, limit=1)
    if js is not None and total_of(js) > 0:
        return term
    for fb in FALLBACK.get(term, []):
        time.sleep(INTERVAL)
        js, _ = fetch_page(fb, 1, limit=1)
        if js is not None and total_of(js) > 0:
            anomalies.append(f"品类'{term}'检索无结果, 自动降级为'{fb}'")
            return fb
    return term


def category_stats(conn, term: str):
    """品类入库统计: (展示名, 条数, 最早日期, 最新日期, [模糊品名明细])——查询跨后端参数化"""
    ph = placeholder()
    with cursor(conn) as cur:
        cur.execute(f"SELECT COUNT(*), MIN(pub_date), MAX(pub_date) FROM price_daily "
                    f"WHERE prod_name = {ph}", (term,))
        cnt, dmin, dmax = cur.fetchone()
        cur.execute(f"SELECT COUNT(*), MIN(pub_date), MAX(pub_date) FROM price_daily "
                    f"WHERE prod_name LIKE {ph}", (f"%{term}%",))
        cnt2, dmin2, dmax2 = cur.fetchone()
        if cnt2 > cnt:   # 模糊聚合更多(黄瓜/鸡蛋等同族品名), 合并展示
            cur.execute(f"SELECT prod_name, COUNT(*) FROM price_daily WHERE prod_name LIKE {ph} "
                        f"GROUP BY prod_name ORDER BY COUNT(*) DESC", (f"%{term}%",))
            names = cur.fetchall()
            dmin = min(x for x in (dmin, dmin2) if x)
            dmax = max(x for x in (dmax, dmax2) if x)
            return f"{term}(品类聚合)", cnt2, dmin, dmax, names
        return term, cnt, dmin, dmax, None


# ---------------------------------------------------------------- collect: 全量/增量
def collect(only: str | None = None, days: int | None = None) -> dict:
    """采集核心(供 CLI 与调度器共用)。
    days=None 全量; days=N 增量: 日期窗口 = [今天-N+1, 今天]（upsert 幂等, 重复跑安全）"""
    ph_dates = ""
    d_start = d_end = ""
    if days:
        today = date.today()
        d_start = (today - timedelta(days=days - 1)).isoformat()
        d_end = today.isoformat()
        ph_dates = f", 窗口 {d_start}~{d_end}"

    cats = [c.strip() for c in only.split(",") if c.strip()] if only else list(CATEGORIES)
    conn = get_connection()
    upsert_sql = get_upsert_sql()
    log(f"数据库后端: {DB_BACKEND}; 品类: {cats}; 模式: {'增量' if days else '全量'}{ph_dates}")

    resolved = []
    for c in cats:
        resolved.append(resolve_term(c))
        time.sleep(INTERVAL)

    summaries, rows_written = [], 0
    for cat in resolved:
        first, cost = fetch_page(cat, 1, d_start=d_start, d_end=d_end)
        if first is None:
            log(f"!! {cat} 首页请求失败, 跳过该品类")
            continue
        total = total_of(first)
        pages = min(MAX_PAGES, max(1, math.ceil(total / PAGE_LIMIT)))
        log(f"—— {cat}: 接口 count={total}, 共 {pages} 页, 首页耗时 {cost:.2f}s ——")

        rows = parse_rows(first.get("list") or [], cat)
        if rows:
            with cursor(conn) as cur:
                cur.executemany(upsert_sql, rows)   # 铁律: 参数化 executemany
            conn.commit()
            rows_written += len(rows)

        fail_streak, done = 0, 1
        for page in range(2, pages + 1):
            time.sleep(INTERVAL)                    # 铁律: ≤1次/秒
            js, _ = fetch_page(cat, page, d_start=d_start, d_end=d_end)
            if js is None:
                fail_streak += 1
                if fail_streak >= 3:
                    anomalies.append(f"{cat}: 连续{fail_streak}页失败, 提前终止(已抓{done}/{pages}页)")
                    break
                continue
            fail_streak = 0
            rows = parse_rows(js.get("list") or [], cat)
            if rows:
                with cursor(conn) as cur:
                    cur.executemany(upsert_sql, rows)
                conn.commit()
                rows_written += len(rows)
            done += 1
            if page % 10 == 0 or page == pages:
                log(f"  {cat} 进度: {done}/{pages} 页")

        disp, cnt, dmin, dmax, detail = category_stats(conn, cat)
        extra = f", 品名明细: {detail[:4]}" if detail else ""
        log(f"【{cat} 完成】入库 {cnt} 条, 时间跨度 {dmin} ~ {dmax}{extra}")
        summaries.append({"term": cat, "display": disp, "count": cnt,
                          "min_date": str(dmin), "max_date": str(dmax)})

    conn.close()
    print("\n========== 异常台账 ==========")
    for a in anomalies or ["无异常"]:
        print(" -", a)
    return {"categories": summaries, "rows_written": rows_written, "anomalies": list(anomalies)}


def main() -> int:
    ap = argparse.ArgumentParser(description="新发地批发价采集器(W1)")
    ap.add_argument("cmd", choices=["probe", "collect"], help="probe=单页字段探测; collect=批量采集")
    ap.add_argument("--only", default=None, help="只采集指定品类, 逗号分隔, 如: 大白菜,黄瓜")
    ap.add_argument("--days", type=int, default=None, help="增量模式: 只采最近N天(如 3)")
    args = ap.parse_args()
    if args.cmd == "probe":
        return cmd_probe()
    collect(only=args.only, days=args.days)
    return 0


if __name__ == "__main__":
    sys.exit(main())
