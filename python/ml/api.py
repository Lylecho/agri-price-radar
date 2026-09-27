# -*- coding: utf-8 -*-
"""W4 本机算法通道。启动：python python/ml/api.py（仅127.0.0.1:8001）。"""
from contextlib import asynccontextmanager
import hashlib
import logging
from pathlib import Path
import sqlite3
import sys
from threading import Lock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from config.constants import REPRESENTATIVES
from config.db import DB_BACKEND, MYSQL_CONFIG, SQLITE_PATH
from ml.compare_models import load_snapshot, compare_category
from ml.model_common import admitted

DISCLAIMER = "预测结果仅供参考，不构成任何买卖建议"
log = logging.getLogger(__name__)


def read_connection():
    """实时路径不调用自动建库入口；连接只读，不写预测表或任务表。"""
    if DB_BACKEND == "mysql":
        import pymysql
        return pymysql.connect(**MYSQL_CONFIG, connect_timeout=1, read_timeout=1, write_timeout=1,
                               init_command="SET SESSION TRANSACTION READ ONLY")
    return sqlite3.connect(SQLITE_PATH.resolve().as_uri() + "?mode=ro", uri=True)


class ForecastRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category: str
    days: int = Field(default=7, ge=1, le=7, strict=True)

    @field_validator("category")
    @classmethod
    def valid_category(cls, value):
        if value not in dict(REPRESENTATIVES):
            raise ValueError("未知品类")
        return value


class ForecastEngine:
    def __init__(self):
        self.cache = {}  # 每品类至多一份、按数据内容失效；不读取predict_result冒充实时计算。
        self.lock = Lock()

    def forecast(self, category, days, snapshot=None):
        data = load_snapshot(connection_factory=read_connection) if snapshot is None else snapshot
        subset = data[data.category == category]
        key = hashlib.sha256(subset.to_csv(index=False, float_format="%.17g").encode()).hexdigest()
        cached = self.cache.get(category)
        if cached is None or cached[0] != key:
            # 新快照只允许一个训练任务；忙时快速503，由主后端降级，避免排队拖垮服务。
            if not self.lock.acquire(blocking=False):
                raise HTTPException(503, "模型计算繁忙")
            try:
                cached = self.cache.get(category)
                if cached is None or cached[0] != key:
                    result = compare_category(data, category, dict(REPRESENTATIVES)[category])
                    cached = (key, result)
                    self.cache[category] = cached
            finally:
                self.lock.release()
        result = cached[1]
        allowed = admitted(result["mape"])
        end = pd.Timestamp(result["end"])
        points = [{"date": (end + pd.Timedelta(days=i)).strftime("%Y-%m-%d"), "yhat": round(float(v), 3)}
                  for i, v in enumerate(result["forecast"][:days], 1)] if allowed else []
        return {"category": category, "prod_name": result["prod_name"], "model": result["winner"],
                "mape_test": result["mape"], "yhat": points, "admitted": allowed,
                "snapshot_date": result["end"], "disclaimer": DISCLAIMER}


def create_app(engine=None, warmup=True):
    engine = engine or ForecastEngine()

    @asynccontextmanager
    async def lifespan(app):
        if warmup:
            try:
                snapshot = load_snapshot(connection_factory=read_connection)
                for category, _ in REPRESENTATIVES:
                    engine.forecast(category, 7, snapshot)
            except Exception as exc:
                log.warning("预热未完成: %s；请求失败时由主后端回退", type(exc).__name__)
        yield

    app = FastAPI(title="菜价雷达算法服务", lifespan=lifespan, docs_url=None, redoc_url=None)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, exc):
        return JSONResponse(status_code=400, content={"code": 400, "msg": "category须为有效品类，days须为1至7的整数", "data": None})

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return JSONResponse(status_code=exc.status_code, content={"code": exc.status_code, "msg": exc.detail, "data": None})

    @app.post("/ml/forecast")
    def forecast(body: ForecastRequest):
        try:
            data = engine.forecast(body.category, body.days)
            return {"code": 200, "msg": "成功" if data["admitted"] else "波动过大，暂不提供预测（仅供参考）", "data": data}
        except HTTPException:
            raise
        except Exception as exc:
            log.warning("实时预测不可用: %s", type(exc).__name__)
            raise HTTPException(503, "实时算法暂不可用") from None

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001, workers=1)
