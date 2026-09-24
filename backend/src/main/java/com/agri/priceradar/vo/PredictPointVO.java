package com.agri.priceradar.vo;

import java.math.BigDecimal;

/**
 * 预测点（单日）
 *
 * @param date 预测目标日 yyyy-MM-dd
 * @param yhat 预测均价（元/斤）
 */
public record PredictPointVO(String date, BigDecimal yhat) {
}
