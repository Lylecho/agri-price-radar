# -*- coding: utf-8 -*-
"""
新发地批发价格采集器（里程碑0 · 选题试开发验证）
================================================
接口 : POST http://www.xinfadi.com.cn/getPriceData.html（字段以真实返回为准）

采集铁律（AGENTS.md）:
  1) 频率 ≤ 1次/秒（页间 sleep 1s）
  2) 必须携带 User-Agent
  3) 解析前先打印一条真实返回确认字段名（本脚本 probe 子命令）
  4) SQL 一律参数化 + executemany，重复数据靠唯一约束 + upsert 去重
  5) 数据快照入库，分析与预测只读库，不在请求时现场爬取

用法:
  python python/collector/xinfadi.py probe                # 单页探测: 打印第一条真实JSON + 各品类检索效果
  python python/collector/xinfadi.py collect              # 批量采集 5 品类全部可回溯历史
  python python/collector/xinfadi.py collect --only 大白菜,黄瓜   # 只采集指定品类
"""
import argparse
import json
import math
import sys
import time
from datetime import datetime
from pathlib import Path

# Windows 控制台中文输出保护（避免 GBK 编码错误）
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import requests

# 使 collector/ 能导入 python/ 下的 config 包
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config.db import get_connection, get_upsert_sql, DB_BACKEND, cursor  # noqa: E402

API_URL = "http://www.xinfadi.com.cn/getPriceData.html"
PAGE_LIMIT = 200      # 单页条数（接口实际上限 200, 超出会被截断）
INTERVAL = 1.0        # 请求间隔（秒）—— 铁律: ≤1次/秒
RETRIES = 3           # 单页失败重试次数（带退避）
MAX_PAGES = 2000      # 每品类安全页数上限, 防御死循环

HEADERS = {
    # 铁律: 必须携带 User-Agent。注意: HTTP 头只允许 latin-1 字符, UA 内禁止中文!
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 "
                   "agri-price-radar/0.1 (thesis-demo)"),
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Referer": "http://www.xinfadi.com.cn/price.html",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01",
}

# 里程碑0 目标品类（探测实测: 西红柿 count=0; 猪肉仅11条无关品 → 强制替换）
CATEGORIES = ["大白菜", "黄瓜", "西红柿", "猪肉", "鸡蛋"]
# 用户已确认的品类词替换（即使原词 count>0 也替换, 如"猪肉"的11条是"黄金福袋(猪肉馅)"等无关品）
OVERRIDE = {"猪肉": "白条猪", "西红柿": "番茄"}
# 替换词仍检索不到时的自动降级候选
FALLBACK = {"白条猪": ["前臀尖", "后臀尖"], "番茄": ["西红柿"]}

anomalies = []   # 异常台账, 采集结束统一打印/汇报


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------------------------------------------------------------- 请求层
def fetch_page(prod_name: str, current: int, limit: int = PAGE_LIMIT):
    """请求一页数据; 成功返回 (dict, 耗时s), 重试耗尽返回 (None, None)"""
    payload = {
        "limit": str(limit),
        "current": str(current),
        "pubDateStartTime": "",
        "pubDateEndTime": "",
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
            # 实测分页字段: {"current", "limit", "count"(总数), "list"}（以真实返回为准）
            if str(js.get("errcode", "0")) != "0":
                raise RuntimeError(f"errcode={js.get('errcode')}, errstr={js.get('errstr')}")
            return js, cost
        except Exception as exc:
            anomalies.append(f"{prod_name} 第{current}页 第{attempt}/{RETRIES}次请求失败: "
                             f"{type(exc).__name__}: {exc}")
            if attempt < RETRIES:
                time.sleep(2 * attempt)   # 退避 2s/4s
    return None, None


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
            str(it.get("prodName") or "").strip(),        # prod_name
            str(it.get("prodCat") or "").strip() or None, # prod_cat
            to_f(it.get("lowPrice")),                     # low_price
            to_f(it.get("highPrice")),                    # high_price
            to_f(it.get("avgPrice")),                     # avg_price
            str(it.get("place") or "").strip(),           # place（规范化''便于唯一约束判重）
            str(it.get("specInfo") or "").strip(),        # spec_info
            str(it.get("unitInfo") or "").strip(),        # unit_info
            d,                                            # pub_date
        ))
    if bad:
        anomalies.append(f"{cat}: {bad} 条记录 pubDate 无法解析, 已跳过")
    return rows


def total_of(js) -> int:
    """接口返回的总条数字段（实测为 count, 兼容 total）"""
    return int(js.get("count") or js.get("total") or 0)


# ---------------------------------------------------------------- probe: 先确认字段再动手
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
    log("步骤2: 核查 5 个品类词的检索效果（判断精确/模糊匹配, 尤其'猪肉'）...")
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


# ---------------------------------------------------------------- collect: 批量采集
def resolve_term(term: str) -> str:
    """品类词解析: 先应用用户确认的 OVERRIDE 替换, 再校验检索有效性, 必要时自动降级"""
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
    """品类入库统计: (展示名, 精确条数, 最早日期, 最新日期, [关键词聚合明细])
    说明: 黄瓜/鸡蛋等为模糊检索, 会连同 小黄瓜/柴鸡蛋 等同族品名一起入库,
    故同时报告精确品名条数与关键词聚合条数。"""
    with cursor(conn) as cur:
        cur.execute("SELECT COUNT(*), MIN(pub_date), MAX(pub_date) FROM price_daily WHERE prod_name = ?",
                    (term,))
        cnt, dmin, dmax = cur.fetchone()
        cur.execute("SELECT COUNT(*), MIN(pub_date), MAX(pub_date) FROM price_daily WHERE prod_name LIKE ?",
                    (f"%{term}%",))
        cnt2, dmin2, dmax2 = cur.fetchone()
        if cnt2 > cnt:   # 模糊聚合更多 → 合并展示
            cur.execute("SELECT prod_name, COUNT(*) FROM price_daily WHERE prod_name LIKE ? "
                        "GROUP BY prod_name ORDER BY COUNT(*) DESC", (f"%{term}%",))
            names = cur.fetchall()
            disp = f"{term}(品类聚合)"
            dmin, dmax = min(x for x in (dmin, dmin2) if x), max(x for x in (dmax, dmax2) if x)
            return disp, cnt2, dmin, dmax, names
        return term, cnt, dmin, dmax, None


def cmd_collect(only: str | None) -> int:
    cats = [c.strip() for c in only.split(",") if c.strip()] if only else list(CATEGORIES)
    conn = get_connection()
    upsert_sql = get_upsert_sql()
    log(f"数据库后端: {DB_BACKEND}")
    log(f"开始采集品类: {cats}（单页 {PAGE_LIMIT} 条, 间隔 {INTERVAL}s, 预计耗时见进度日志）")

    resolved = []
    for c in cats:
        resolved.append(resolve_term(c))
        time.sleep(INTERVAL)

    for cat in resolved:
        first, cost = fetch_page(cat, 1)
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

        fail_streak, done = 0, 1
        for page in range(2, pages + 1):
            time.sleep(INTERVAL)                    # 铁律: ≤1次/秒
            js, _ = fetch_page(cat, page)
            if js is None:
                fail_streak += 1
                if fail_streak >= 3:
                    anomalies.append(f"{cat}: 连续{fail_streak}页失败, 提前终止该品类(已抓{done}/{pages}页)")
                    break
                continue
            fail_streak = 0
            rows = parse_rows(js.get("list") or [], cat)
            if rows:
                with cursor(conn) as cur:
                    cur.executemany(upsert_sql, rows)
                conn.commit()
            done += 1
            if page % 10 == 0 or page == pages:
                log(f"  {cat} 进度: {done}/{pages} 页")

        disp, cnt, dmin, dmax, detail = category_stats(conn, cat)
        extra = f", 品名明细: {detail[:4]}" if detail else ""
        log(f"【{cat} 完成】入库 {cnt} 条, 时间跨度 {dmin} ~ {dmax}{extra}")

    conn.close()
    print("\n========== 异常台账 ==========")
    if anomalies:
        for a in anomalies:
            print(" -", a)
    else:
        print(" - 无异常")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="新发地批发价采集器(里程碑0)")
    ap.add_argument("cmd", choices=["probe", "collect"], help="probe=单页字段探测; collect=批量采集")
    ap.add_argument("--only", default=None, help="只采集指定品类, 逗号分隔, 如: 大白菜,黄瓜")
    args = ap.parse_args()
    return cmd_probe() if args.cmd == "probe" else cmd_collect(args.only)


if __name__ == "__main__":
    sys.exit(main())
