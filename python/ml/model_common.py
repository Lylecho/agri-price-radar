# -*- coding: utf-8 -*-
"""离线模型统一评估口径，供实验与预计算共用。"""
from dataclasses import dataclass
import math
import numpy as np
import pandas as pd
from config.constants import MAPE_THRESHOLD

HORIZON = 7
LOOKBACK_DAYS = 730
MIN_POINTS = 120


@dataclass
class ForecastResult:
    model: str
    mape: float
    forecast: np.ndarray
    seconds: float
    aic: float | None = None


def prepare_series(series):
    """固定日历顺序切分；训练段插值不读取测试段，零/负价格拒绝。"""
    series = series.sort_index().astype(float)
    if len(series) < MIN_POINTS or not np.isfinite(series).all() or (series <= 0).any():
        raise ValueError("日均价不足120个观测点或包含非正/非有限值")
    daily = series.reindex(pd.date_range(series.index.min(), series.index.max(), freq="D"))
    split = int(len(daily) * 0.8)
    train = daily.iloc[:split].interpolate(limit_direction="both")
    # 测试段可利用最后训练点作插值起点，但不能反向影响训练集。
    test = pd.concat([train.iloc[-1:], daily.iloc[split:]]).interpolate(limit_direction="both").iloc[1:]
    full = daily.interpolate(limit_direction="both")
    return full, train, test


def mape_percent(actual, predicted):
    actual, predicted = np.asarray(actual, dtype=float), np.asarray(predicted, dtype=float)
    if actual.shape != predicted.shape or not actual.size or not np.isfinite(actual).all() or (actual <= 0).any():
        raise ValueError("MAPE 要求同形状且为正的实际价格")
    if not np.isfinite(predicted).all():
        return float("inf")
    return float(np.mean(np.abs((actual - predicted) / actual)) * 100)


def admitted(mape, threshold=MAPE_THRESHOLD):
    if not math.isfinite(threshold) or threshold < 0:
        raise ValueError("MAPE 阈值必须是非负有限数")
    return math.isfinite(mape) and 0 <= mape <= threshold


def choose_best(results):
    """跨模型只比较测试集 MAPE；平局优先 ARIMA，不跨模型比较 AIC。"""
    valid = [r for r in results if math.isfinite(r.mape) and r.mape >= 0
             and len(r.forecast) > 0 and np.isfinite(r.forecast).all() and (r.forecast > 0).all()]
    if not valid:
        raise ValueError("无有效候选预测")
    return min(valid, key=lambda r: (r.mape, not r.model.startswith("ARIMA"), r.model))
