package com.agri.priceradar.vo;

import java.math.BigDecimal;

/**
 * 品类概览（服务层组装）
 *
 * @param category     展示品类
 * @param prodName     库中代表品名
 * @param unit        计价单位
 * @param latestDate  最新数据日期
 * @param latestPrice 最新均价
 */
public record CategoryVO(String category, String prodName, String unit,
                         String latestDate, BigDecimal latestPrice) {
}
