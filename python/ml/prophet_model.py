# -*- coding: utf-8 -*-
"""Prophet 固定配置对照：年/周季节项，保持与 ARIMA 一致的评估输入。"""
from time import perf_counter
import numpy as np
import pandas as pd
from ml.model_common import ForecastResult, HORIZON, prepare_series, mape_percent


def prophet_forecast(series, horizon=HORIZON):
    from prophet import Prophet
    full, train, test = prepare_series(series)
    started = perf_counter()

    def fit(values):
        # 训练段不足两年，显式启用低阶年周期；固定参数，禁止用留出集调参。
        model = Prophet(yearly_seasonality=5, weekly_seasonality=3, daily_seasonality=False,
                        seasonality_mode="additive", changepoint_prior_scale=0.05,
                        seasonality_prior_scale=10, uncertainty_samples=0)
        return model.fit(pd.DataFrame({"ds": values.index, "y": values.to_numpy()}), seed=42)

    model = fit(train)
    pred = model.predict(pd.DataFrame({"ds": test.index}))["yhat"].to_numpy()
    mape = mape_percent(test, pred)
    final = fit(full)
    dates = pd.date_range(full.index[-1] + pd.Timedelta(days=1), periods=horizon)
    forecast = np.asarray(final.predict(pd.DataFrame({"ds": dates}))["yhat"])
    return ForecastResult("Prophet", mape, forecast, perf_counter() - started)
