# -*- coding: utf-8 -*-
"""
APScheduler 调度进程（W1 采集服务化）
=====================================
计划(Asia/Shanghai, 用户已确认):
  - 增量采集 collect : 每日 08:00 / 14:00 / 20:00, 回看最近3天(upsert 幂等)
  - 预测预计算 precompute : 每日 21:00, 五品类 ARIMA × 未来7天 → predict_result
每次运行写 collect_log(SUCCESS/FAILED + 摘要)。

用法:
  python python/scheduler/run.py                  # 常驻调度(Ctrl+C 退出; 部署可注册为Windows服务)
  python python/scheduler/run.py --now collect    # 立即执行一次增量采集(验证用)
  python python/scheduler/run.py --now precompute # 立即执行一次预计算
  python python/scheduler/run.py --now all
"""
import argparse
import sys
import traceback
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # 引入 python/config

from apscheduler.events import EVENT_SCHEDULER_STARTED       # noqa: E402
from apscheduler.schedulers.blocking import BlockingScheduler   # noqa: E402
from apscheduler.triggers.cron import CronTrigger               # noqa: E402

from config.db import get_connection, get_insert_log_sql, cursor, DB_BACKEND  # noqa: E402
from collector.xinfadi import collect as core_collect           # noqa: E402
from ml.precompute import precompute_all as core_precompute     # noqa: E402

TZ = "Asia/Shanghai"
LOOKBACK_DAYS = 3        # 增量采集回看窗口(天)


def write_log(job: str, status: str, detail: str, rows, started: datetime, finished: datetime) -> None:
    """任务结果写 collect_log(参数化插入, 跨后端)"""
    conn = get_connection()
    with cursor(conn) as cur:
        cur.execute(get_insert_log_sql(), (
            job, status, (detail or "")[:1000], rows,
            started.isoformat(sep=" ", timespec="seconds"),
            finished.isoformat(sep=" ", timespec="seconds"),
        ))
    conn.commit()
    conn.close()


def run_with_log(job: str, fn) -> None:
    """包装: 执行 + 计时 + collect_log 记录(异常也记录, 不中断调度器)"""
    started = datetime.now()
    print(f"[{started:%H:%M:%S}] 任务 {job} 开始 ...", flush=True)
    try:
        result = fn()
        rows = result.get("rows_written") if isinstance(result, dict) else None
        if job == "collect":
            cats = result.get("categories", [])
            detail = "; ".join(f"{c['display']}:{c['count']}条" for c in cats) or "无品类"
            detail += f"; 写入(含更新){rows}行; 异常{len(result.get('anomalies', []))}条"
        else:
            detail = result.get("detail", "")
        finished = datetime.now()
        write_log(job, "SUCCESS", detail, rows, started, finished)
        print(f"[{finished:%H:%M:%S}] 任务 {job} SUCCESS: {detail}", flush=True)
    except Exception:
        finished = datetime.now()
        tb = traceback.format_exc()[-800:]
        write_log(job, "FAILED", tb, None, started, finished)
        print(f"[{finished:%H:%M:%S}] 任务 {job} FAILED:\n{tb}", flush=True)


def job_collect():
    run_with_log("collect", lambda: core_collect(days=LOOKBACK_DAYS))


def job_precompute():
    run_with_log("precompute", core_precompute)


def main() -> int:
    ap = argparse.ArgumentParser(description="菜价雷达 W1 调度进程")
    ap.add_argument("--now", choices=["collect", "precompute", "all"],
                    help="立即执行一次指定任务(验证用), 不启动常驻调度")
    args = ap.parse_args()
    print(f"数据库后端: {DB_BACKEND}")

    if args.now:
        if args.now in ("collect", "all"):
            job_collect()
        if args.now in ("precompute", "all"):
            job_precompute()
        return 0

    sched = BlockingScheduler(timezone=TZ)
    sched.add_job(job_collect, CronTrigger(hour="8,14,20", minute=0, timezone=TZ),
                  id="collect", max_instances=1, coalesce=True,
                  misfire_grace_time=3600)
    sched.add_job(job_precompute, CronTrigger(hour=21, minute=0, timezone=TZ),
                  id="precompute", max_instances=1, coalesce=True,
                  misfire_grace_time=3600)

    # 注: APScheduler 3.11 起 Job.next_run_time 仅在调度器启动后可用,
    #     故先打印触发规则, 启动后再经事件监听打印下次触发时间
    for j in sched.get_jobs():
        print(f"已注册任务: {j.id} -> {j.trigger}")

    def on_started(event):
        for j in sched.get_jobs():
            print(f"下次触发: {j.id} -> {getattr(j, 'next_run_time', '待定')}", flush=True)

    sched.add_listener(on_started, EVENT_SCHEDULER_STARTED)
    print("调度器常驻启动(Ctrl+C 退出) ...", flush=True)
    sched.start()
    return 0


if __name__ == "__main__":
    sys.exit(main())
