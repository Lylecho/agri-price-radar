# -*- coding: utf-8 -*-
"""实时API回归：mock模型/快照，不联网采集、不读取开发数据库。"""
import sys
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from ml.api import create_app, ForecastEngine, DISCLAIMER, read_connection


class TestMlApi(unittest.TestCase):
    def setUp(self):
        self.engine = Mock()
        self.engine.forecast.return_value = {"model": "Prophet", "mape_test": 20.0,
            "yhat": [{"date": "2026-09-28", "yhat": 1.5}], "admitted": True, "disclaimer": DISCLAIMER}
        self.client = TestClient(create_app(self.engine, warmup=False))

    def tearDown(self):
        self.client.close()

    def test_success_and_days(self):
        response = self.client.post("/ml/forecast", json={"category": "黄瓜", "days": 1})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["disclaimer"], DISCLAIMER)
        self.engine.forecast.assert_called_once_with("黄瓜", 1)

    def test_invalid_inputs_are_400(self):
        for body in ({"category": "未知", "days": 7}, {"category": "黄瓜", "days": 0},
                     {"category": "黄瓜", "days": 8}, {"category": "黄瓜", "days": "3"},
                     {"category": "黄瓜", "days": True}, {}, {"category": "黄瓜", "url": "ignored"}):
            with self.subTest(body=body):
                response = self.client.post("/ml/forecast", json=body)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["code"], 400)
        self.engine.forecast.assert_not_called()

    def test_model_failure_is_503_without_internal_details(self):
        self.engine.forecast.side_effect = RuntimeError("internal detail")
        response = self.client.post("/ml/forecast", json={"category": "鸡蛋", "days": 7})
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("internal detail", response.text)

    def test_admission_rejection_is_not_transport_failure(self):
        self.engine.forecast.return_value.update(admitted=False, yhat=[], mape_test=40)
        response = self.client.post("/ml/forecast", json={"category": "西红柿", "days": 7})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["yhat"], [])


class TestForecastEngine(unittest.TestCase):
    def setUp(self):
        self.engine = ForecastEngine()
        self.snapshot = pd.DataFrame({"category": ["黄瓜"], "prod_name": ["黄瓜"],
                                      "date": pd.to_datetime(["2026-09-27"]), "price": [1.0]})
        self.result = {"prod_name": "黄瓜", "end": "2026-09-27", "winner": "Prophet",
                       "mape": 20, "forecast": [1.5]*7}

    def test_snapshot_cache_and_invalidation(self):
        with patch("ml.api.compare_category", return_value=self.result) as compare:
            first = self.engine.forecast("黄瓜", 1, self.snapshot)
            second = self.engine.forecast("黄瓜", 7, self.snapshot)
            self.assertEqual((len(first["yhat"]), len(second["yhat"])), (1, 7))
            self.assertEqual(compare.call_count, 1)
            self.snapshot.loc[0, "price"] = 2
            self.engine.forecast("黄瓜", 7, self.snapshot)
            self.assertEqual(compare.call_count, 2)

    def test_r2_threshold_stays_effective(self):
        self.result["mape"] = 30.001
        with patch("ml.api.compare_category", return_value=self.result):
            result = self.engine.forecast("黄瓜", 7, self.snapshot)
        self.assertFalse(result["admitted"])
        self.assertEqual(result["yhat"], [])

    def test_busy_engine_fails_fast(self):
        from fastapi import HTTPException
        self.engine.lock.acquire()
        try:
            with self.assertRaises(HTTPException) as error:
                self.engine.forecast("黄瓜", 7, self.snapshot)
            self.assertEqual(error.exception.status_code, 503)
        finally:
            self.engine.lock.release()

    def test_sqlite_connection_is_readonly(self):
        import sqlite3
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot.db"
            sqlite3.connect(path).close()
            with patch("ml.api.DB_BACKEND", "sqlite"), patch("ml.api.SQLITE_PATH", path):
                conn = read_connection()
                try:
                    with self.assertRaises(sqlite3.OperationalError):
                        conn.execute("CREATE TABLE forbidden (id INTEGER)")
                finally:
                    conn.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
