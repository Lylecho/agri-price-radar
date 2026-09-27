# -*- coding: utf-8 -*-
"""Python 侧冒烟测试（无需网络与数据库）
运行: python python/tests/test_smoke.py
覆盖: 采集解析/日期校验/价格转换、单位治理过滤、预警阈值判定、品类映射一致性
"""
import sys
import unittest
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "python"))

from collector.xinfadi import parse_rows, to_f, total_of          # noqa: E402
from config.constants import CATEGORIES, OVERRIDE, PREFERRED, REPRESENTATIVES  # noqa: E402


class TestParse(unittest.TestCase):
    """采集解析层"""

    def test_价格字段转换(self):
        self.assertEqual(to_f("0.45"), 0.45)
        self.assertEqual(to_f(" 12.5 "), 12.5)
        self.assertIsNone(to_f(""))
        self.assertIsNone(to_f("-"))
        self.assertIsNone(to_f(None))
        self.assertIsNone(to_f("abc"))

    def test_总数字段优先count兼容total(self):
        self.assertEqual(total_of({"count": 1720}), 1720)
        self.assertEqual(total_of({"total": 99}), 99)
        self.assertEqual(total_of({"count": 5, "total": 99}), 5)
        self.assertEqual(total_of({}), 0)

    def test_解析真实返回结构(self):
        """字段以新发地真实返回为准(probe 确认)"""
        raw = [{
            "id": 2022848, "prodName": "大白菜", "prodCat": "蔬菜",
            "lowPrice": "0.4", "highPrice": "0.5", "avgPrice": "0.45",
            "place": "冀", "specInfo": "", "unitInfo": "斤",
            "pubDate": "2026-09-24 00:00:00",
        }]
        rows = parse_rows(raw, "大白菜")
        self.assertEqual(len(rows), 1)
        prod_name, prod_cat, low, high, avg, place, spec, unit, pub_date = rows[0]
        self.assertEqual(prod_name, "大白菜")
        self.assertEqual(prod_cat, "蔬菜")
        self.assertEqual((low, high, avg), (0.4, 0.5, 0.45))
        self.assertEqual(place, "冀")
        self.assertEqual(spec, "")
        self.assertEqual(unit, "斤")
        self.assertEqual(pub_date, "2026-09-24")   # 取前 10 位为纯日期

    def test_日期非法的行被跳过(self):
        raw = [
            {"prodName": "大白菜", "avgPrice": "0.5", "pubDate": "not-a-date"},
            {"prodName": "大白菜", "avgPrice": "0.5", "pubDate": "2026-09-24 00:00:00"},
        ]
        rows = parse_rows(raw, "大白菜")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][8], "2026-09-24")

    def test_空规格与空产地规范化为空串(self):
        """唯一约束含 place/spec_info/unit_info, 必须规范化为空串而非 None"""
        raw = [{"prodName": "散鸡蛋", "avgPrice": "5.85", "place": None,
                "specInfo": None, "unitInfo": "斤", "pubDate": "2026-09-24"}]
        rows = parse_rows(raw, "鸡蛋")
        self.assertEqual(rows[0][5], "")   # place
        self.assertEqual(rows[0][6], "")   # spec_info


class TestCategoryMapping(unittest.TestCase):
    """品类映射与单位治理结论固化"""

    def test_五个目标品类(self):
        self.assertEqual(CATEGORIES, ["大白菜", "黄瓜", "西红柿", "猪肉", "鸡蛋"])

    def test_品类词替换(self):
        self.assertEqual(OVERRIDE["猪肉"], "白条猪")
        self.assertEqual(OVERRIDE["西红柿"], "番茄")

    def test_鸡蛋使用纯斤价的散鸡蛋(self):
        """箱鸡蛋为整件计价且斤标注被污染, 必须使用散鸡蛋"""
        self.assertEqual(PREFERRED["鸡蛋"], "散鸡蛋")
        mapping = dict(REPRESENTATIVES)
        self.assertEqual(mapping["鸡蛋"], "散鸡蛋")
        self.assertEqual(mapping["西红柿"], "番茄")
        self.assertEqual(mapping["猪肉"], "白条猪")
        self.assertEqual(len(REPRESENTATIVES), 5)


class TestAlertThreshold(unittest.TestCase):
    """预警阈值判定(与 Java 侧 AlertService 同口径: |日环比| >= 阈值)"""

    @staticmethod
    def triggered(change_pct: float, threshold: float) -> bool:
        return abs(change_pct) >= threshold

    def test_超过阈值触发(self):
        self.assertTrue(self.triggered(12.5, 5.0))     # 实际触发案例: 大白菜 +12.5%
        self.assertTrue(self.triggered(-7.2, 5.0))     # 下跌同样触发

    def test_未达阈值不触发(self):
        self.assertFalse(self.triggered(0.85, 5.0))    # 鸡蛋 -0.85%
        self.assertFalse(self.triggered(4.99, 5.0))

    def test_边界等于阈值触发(self):
        self.assertTrue(self.triggered(5.0, 5.0))



class TestModelAdmission(unittest.TestCase):
    """算法判定与真实内存数据库写入回归，不训练、不联网。"""

    def test_门禁边界和非有限值(self):
        from ml.model_common import admitted
        self.assertTrue(admitted(30))
        self.assertFalse(admitted(30.0001))
        self.assertTrue(admitted(0, 0))
        for value in (float("nan"), float("inf"), -1):
            self.assertFalse(admitted(value))
        for threshold in (-1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                admitted(10, threshold)

    def test_按MAPE择优而非跨模型AIC(self):
        import numpy as np
        from ml.model_common import ForecastResult, choose_best
        a = ForecastResult("ARIMA(1,1,1)", 35, np.ones(7), 1, -100)
        p = ForecastResult("Prophet", 20, np.ones(7), 1)
        self.assertIs(choose_best([a, p]), p)
        p.mape = 35
        self.assertIs(choose_best([p, a]), a)

    def test_无效预测不能胜出(self):
        import numpy as np
        from ml.model_common import ForecastResult, choose_best
        invalid = ForecastResult("Prophet", 1, np.array([-1]), 1)
        with self.assertRaises(ValueError):
            choose_best([invalid])

    def test_MAPE百分数与零分母保护(self):
        from ml.model_common import mape_percent
        self.assertAlmostEqual(mape_percent([10, 20], [11, 18]), 10)
        with self.assertRaises(ValueError):
            mape_percent([0], [1])

    def test_训练段插值不读取测试值(self):
        import numpy as np
        import pandas as pd
        from ml.model_common import prepare_series
        days = pd.date_range("2024-01-01", periods=150)
        series = pd.Series(np.ones(150), index=days).drop(days[119])
        series.iloc[119:] = 100
        full, train, test = prepare_series(series)
        self.assertEqual((len(train), len(test)), (120, 30))
        self.assertEqual(train.iloc[-1], 1)
        self.assertEqual(test.iloc[0], 100)

    def test_窗口内观测不足拒绝(self):
        import pandas as pd
        from ml.model_common import prepare_series
        with self.assertRaises(ValueError):
            prepare_series(pd.Series([1]*119, index=pd.date_range("2024-01-01", periods=119)))

    def setUp(self):
        import sqlite3
        from config.db import DDL_SQLITE
        from unittest.mock import patch
        from config.db import UPSERT_PREDICT_SQLITE
        self.conn = sqlite3.connect(":memory:")
        self.conn.executescript(DDL_SQLITE)
        self.backend = patch("ml.precompute.DB_BACKEND", "sqlite")
        self.sql = patch("ml.precompute.get_upsert_sql", return_value=UPSERT_PREDICT_SQLITE)
        self.backend.start()
        self.sql.start()
        self.result = {"category": "黄瓜", "prod_name": "黄瓜", "end": "2026-09-27",
                       "winner": "Prophet", "mape": 20.0, "forecast": [2.0]*7}

    def tearDown(self):
        self.backend.stop()
        self.sql.stop()
        self.conn.close()

    def test_重跑保留主键且不重复(self):
        from ml.precompute import publish_results
        publish_results(self.conn, [self.result])
        first = self.conn.execute("SELECT id,model,mape_test FROM predict_result ORDER BY id").fetchall()
        publish_results(self.conn, [self.result])
        self.assertEqual(first, self.conn.execute("SELECT id,model,mape_test FROM predict_result ORDER BY id").fetchall())
        self.assertEqual(len(first), 7)

    def test_降阈值清旧预测并恢复(self):
        from ml.precompute import publish_results
        publish_results(self.conn, [self.result])
        summary = publish_results(self.conn, [self.result], threshold=0)
        self.assertEqual(summary["rows_written"], 0)
        self.assertIn("跳过写入", summary["detail"])
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM predict_result").fetchone()[0], 0)
        publish_results(self.conn, [self.result])
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM predict_result").fetchone()[0], 7)

    def test_换模型移除旧模型(self):
        from ml.precompute import publish_results
        publish_results(self.conn, [self.result])
        self.result["winner"] = "ARIMA(1,1,1)"
        publish_results(self.conn, [self.result])
        self.assertEqual(self.conn.execute("SELECT DISTINCT model FROM predict_result").fetchall(), [("ARIMA(1,1,1)",)])

    def test_写入失败整批回滚(self):
        from ml.precompute import publish_results
        publish_results(self.conn, [self.result])
        before = self.conn.execute("SELECT * FROM predict_result").fetchall()
        self.result["winner"] = "ARIMA(1,1,1)"
        self.result["forecast"] = [None]
        with self.assertRaises(TypeError):
            publish_results(self.conn, [self.result])
        self.assertEqual(before, self.conn.execute("SELECT * FROM predict_result").fetchall())

if __name__ == "__main__":
    unittest.main(verbosity=2)
