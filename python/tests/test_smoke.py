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


if __name__ == "__main__":
    unittest.main(verbosity=2)
