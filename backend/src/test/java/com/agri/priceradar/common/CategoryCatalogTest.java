package com.agri.priceradar.common;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * 品类目录单元测试（纯逻辑, 不依赖数据库）
 * 重点校验「单位治理」结论是否被正确固化: 鸡蛋→散鸡蛋(而非箱鸡蛋)
 */
class CategoryCatalogTest {

    @Test
    void 五个展示品类应全部存在() {
        assertEquals(5, CategoryCatalog.all().size());
        for (String c : new String[]{"大白菜", "黄瓜", "西红柿", "猪肉", "鸡蛋"}) {
            assertTrue(CategoryCatalog.isValid(c), "缺少品类: " + c);
        }
    }

    @Test
    void 品类到代表品名映射应遵循探测与单位治理结论() {
        assertEquals("大白菜", CategoryCatalog.prodNameOf("大白菜"));
        assertEquals("黄瓜", CategoryCatalog.prodNameOf("黄瓜"));
        assertEquals("番茄", CategoryCatalog.prodNameOf("西红柿"), "接口无西红柿行情, 应映射为番茄");
        assertEquals("白条猪", CategoryCatalog.prodNameOf("猪肉"), "接口猪肉仅无关品, 应映射为白条猪");
        assertEquals("散鸡蛋", CategoryCatalog.prodNameOf("鸡蛋"),
                "箱/筐鸡蛋为整件计价且斤标注被污染, 应映射为纯斤价的散鸡蛋");
    }

    @Test
    void 非法品类应返回null且校验失败() {
        assertNull(CategoryCatalog.prodNameOf("胡萝卜"));
        assertFalse(CategoryCatalog.isValid("胡萝卜"));
        assertNull(CategoryCatalog.prodNameOf(null));
    }
}
