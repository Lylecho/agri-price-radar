# -*- coding: utf-8 -*-
"""ARIMA：训练集 AIC 选阶，留出集 MAPE，全量重估后预测7天。"""
from time import perf_counter
import warnings
import numpy as np
from statsmodels.tsa.arima.model import ARIMA
from ml.model_common import ForecastResult, HORIZON, prepare_series, mape_percent

ARIMA_GRID = [(1, 1, 1), (2, 1, 1), (1, 1, 2), (2, 1, 2), (3, 1, 2)]


def arima_forecast(series, horizon=HORIZON):
    full, train, test = prepare_series(series)
    started = perf_counter()
    best = None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for order in ARIMA_GRID:
            try:
                fit = ARIMA(train.to_numpy(), order=order).fit()
                if np.isfinite(fit.aic) and (best is None or fit.aic < best[0]):
                    best = (fit.aic, order, fit)
            except (ValueError, np.linalg.LinAlgError):
                continue
        if best is None:
            raise RuntimeError("全部 ARIMA 候选拟合失败")
        aic, order, fit = best
        mape = mape_percent(test, fit.forecast(len(test)))
        final = ARIMA(full.to_numpy(), order=order).fit()
        forecast = np.asarray(final.forecast(horizon))
    return ForecastResult(f"ARIMA({order[0]},{order[1]},{order[2]})", mape, forecast,
                          perf_counter() - started, float(aic))
