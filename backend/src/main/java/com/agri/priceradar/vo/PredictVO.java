package com.agri.priceradar.vo;

import java.math.BigDecimal;
import java.util.List;

/**
 * 预测结果视图
 *
 * @param model      模型标识, 如 ARIMA(2,1,1)
 * @param mapeTest   测试集 MAPE(%)
 * @param disclaimer 免责声明（铁律: 所有预测展示必须携带「预测结果仅供参考」）
 */
public record PredictVO(String category, String prodName, String model,
                        BigDecimal mapeTest, List<PredictPointVO> points,
                        String disclaimer) {

    public static final String DISCLAIMER = "预测结果仅供参考, 不构成任何买卖建议";
}
