package com.agri.priceradar.vo;

import java.math.BigDecimal;
import java.util.List;

/** 实时及降级结果沿用预测点结构，额外标注来源、准入与回退说明。 */
public record RealtimePredictVO(String category, String prodName, String model,
        BigDecimal mapeTest, List<PredictPointVO> points, String disclaimer,
        boolean degraded, String source, boolean admitted, String message) {
    public static final String DISCLAIMER = "预测结果仅供参考，不构成任何买卖建议";
}
