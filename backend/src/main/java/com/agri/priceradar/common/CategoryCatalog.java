package com.agri.priceradar.common;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * 展示品类目录 —— 五个目标品类 ↔ 库中代表品名映射
 * 与 Python 侧 python/config/constants.py 保持一致（单一事实来源: 蓝图 README §5.1）
 *
 * 映射依据（采集探测 + 计价单位核查 2026-09）:
 *  - 西红柿 → 番茄     : 接口无"西红柿"行情
 *  - 猪肉   → 白条猪   : 接口"猪肉"仅无关品
 *  - 鸡蛋   → 散鸡蛋   : 箱/筐鸡蛋为整件计价且"斤"标注被箱价污染, 散鸡蛋为纯斤价序列
 */
public final class CategoryCatalog {

    /** 展示品类名 → 代表品名（有序, 与前端展示顺序一致） */
    private static final Map<String, String> CATEGORY_TO_PROD = new LinkedHashMap<>();

    static {
        CATEGORY_TO_PROD.put("大白菜", "大白菜");
        CATEGORY_TO_PROD.put("黄瓜", "黄瓜");
        CATEGORY_TO_PROD.put("西红柿", "番茄");
        CATEGORY_TO_PROD.put("猪肉", "白条猪");
        CATEGORY_TO_PROD.put("鸡蛋", "散鸡蛋");
    }

    private CategoryCatalog() {
    }

    public static Map<String, String> all() {
        return CATEGORY_TO_PROD;
    }

    /** 展示品类 → 代表品名; 非法品类返回 null */
    public static String prodNameOf(String category) {
        return CATEGORY_TO_PROD.get(category);
    }

    public static boolean isValid(String category) {
        return CATEGORY_TO_PROD.containsKey(category);
    }
}
